from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sqlite3
import re
from typing import Optional

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

DB = "lacan_v2.db"
RESULTS_PER_PAGE = 30

SEMINAIRES_ORDRE = [
    "Séminaire 1", "Séminaire 2", "Séminaire 3", "Séminaire 4", "Séminaire 5",
    "Séminaire 6", "Séminaire 7", "Séminaire 8", "Séminaire 9", "Séminaire 10",
    "Séminaire 11", "Séminaire 12", "Séminaire 13", "Séminaire 14", "Séminaire 15",
    "Séminaire 16", "Séminaire 17", "Séminaire 18", "Séminaire 19",
    "Séminaire 19 bis", "Séminaire 20", "Séminaire 21", "Séminaire 22",
    "Séminaire 23", "Séminaire 24", "Séminaire 25"
]


def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    text = re.sub(r'052zylxkhbix1205', '', text)
    text = re.sub(r'—— Association Lacanienne Internationale.*?interdites\. ——', '', text, flags=re.DOTALL)
    text = re.sub(r'(?:\n\d+\n){4,}', '\n', text)
    text = re.sub(r'—\s*\d+\s*—', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def get_all_seminaires(conn):
    rows = conn.execute(
        "SELECT DISTINCT seminaire FROM lecons ORDER BY seminaire"
    ).fetchall()
    seminaires = [r[0].strip() for r in rows]
    # Tri numérique
    def sort_key(s):
        m = re.search(r'Séminaire (\d+)(?: bis)?', s)
        if m:
            n = int(m.group(1))
            bis = 0.5 if 'bis' in s else 0
            return n + bis
        return 999
    return sorted(seminaires, key=sort_key)


def kwic(contenu, terme, window=100):
    """Concordancier : Key Word In Context"""
    if not terme or not contenu:
        return []
    pattern = re.compile(re.escape(terme), re.IGNORECASE)
    results = []
    for m in pattern.finditer(contenu):
        pos = m.start()
        start = max(0, pos - window)
        end = min(len(contenu), m.end() + window)
        gauche = contenu[start:pos]
        mot = contenu[pos:m.end()]
        droite = contenu[m.end():end]
        # Couper proprement aux espaces
        if start > 0 and ' ' in gauche:
            gauche = '…' + gauche[gauche.index(' '):]
        if end < len(contenu) and ' ' in droite:
            cut = droite.rfind(' ')
            droite = droite[:cut] + '…'
        results.append({
            "gauche": gauche,
            "mot": mot,
            "droite": droite,
            "position": pos
        })
    return results


def highlight_text(contenu, terme):
    """Surligne toutes les occurrences d'un terme dans le texte complet"""
    if not terme:
        return contenu
    pattern = re.compile(f'({re.escape(terme)})', re.IGNORECASE)
    return pattern.sub(r'<mark>\1</mark>', contenu)


@app.get("/", response_class=HTMLResponse)
def search(
    request: Request,
    q: str = "",
    seminaire: str = "",
    date_min: str = "",
    date_max: str = "",
    sort: str = "score",
    page: int = 1
):
    results = []
    count = 0
    previous_page = None
    next_page = None

    conn = get_conn()
    all_seminaires = get_all_seminaires(conn)

    if q.strip():
        offset = (page - 1) * RESULTS_PER_PAGE

        # Construction de la requête avec filtres optionnels
        where_clauses = ["lecons MATCH ?"]
        params = [q]

        if seminaire:
            where_clauses.append("seminaire = ?")
            params.append(seminaire)

        if date_min:
            where_clauses.append("date_iso >= ?")
            params.append(date_min)

        if date_max:
            where_clauses.append("date_iso <= ?")
            params.append(date_max)

        where_sql = " AND ".join(where_clauses)

        if sort == "date":
            order_by = "date_iso ASC"
        else:
            order_by = "score ASC"

        count = conn.execute(
            f"SELECT COUNT(*) FROM lecons WHERE {where_sql}",
            params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT
                rowid,
                date_lecon,
                date_iso,
                seminaire,
                page_debut,
                snippet(lecons, 5, '<mark>', '</mark>', ' … ', 64) AS extrait,
                bm25(lecons) AS score
            FROM lecons
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            params + [RESULTS_PER_PAGE, offset]
        )

        for row in rows:
            results.append({
                "rowid": row["rowid"],
                "date": row["date_lecon"],
                "date_iso": row["date_iso"],
                "seminaire": row["seminaire"].strip(),
                "page": row["page_debut"],
                "score": round(abs(row["score"]), 3),
                "extrait": row["extrait"]
            })

        if page > 1:
            previous_page = page - 1
        if count > page * RESULTS_PER_PAGE:
            next_page = page + 1

    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "q": q,
            "sort": sort,
            "seminaire": seminaire,
            "date_min": date_min,
            "date_max": date_max,
            "results": results,
            "count": count,
            "page": page,
            "previous_page": previous_page,
            "next_page": next_page,
            "all_seminaires": all_seminaires,
        }
    )


@app.get("/lecon/{rowid}", response_class=HTMLResponse)
def lecon(
    request: Request,
    rowid: int,
    q: str = "",
    back: str = "/"
):
    conn = get_conn()

    row = conn.execute(
        """
        SELECT rowid, date_lecon, date_iso, seminaire, page_debut, page_fin, contenu
        FROM lecons
        WHERE rowid = ?
        """,
        (rowid,)
    ).fetchone()

    if row is None:
        conn.close()
        return HTMLResponse("<h1>Leçon introuvable</h1>", status_code=404)

    seminaire = row["seminaire"]
    date_iso = row["date_iso"]

    # Navigation prev/next dans le même séminaire, ordonné par date
    nav_rows = conn.execute(
        "SELECT rowid, date_lecon, date_iso FROM lecons WHERE seminaire = ? ORDER BY date_iso, rowid",
        (seminaire,)
    ).fetchall()

    prev_lecon = None
    next_lecon = None
    lecon_num = None
    total_lecons = len(nav_rows)

    for i, nav in enumerate(nav_rows):
        if nav["rowid"] == rowid:
            lecon_num = i + 1
            if i > 0:
                prev_lecon = {"rowid": nav_rows[i-1]["rowid"], "date": nav_rows[i-1]["date_lecon"]}
            if i < len(nav_rows) - 1:
                next_lecon = {"rowid": nav_rows[i+1]["rowid"], "date": nav_rows[i+1]["date_lecon"]}
            break

    # Sommaire du séminaire
    sommaire = [{"rowid": r["rowid"], "date": r["date_lecon"], "date_iso": r["date_iso"]} for r in nav_rows]

    contenu = clean_text(row["contenu"])

    # KWIC si terme de recherche
    kwic_results = []
    nb_occurrences = 0
    if q.strip():
        kwic_results = kwic(contenu, q.strip())
        nb_occurrences = len(kwic_results)
        contenu = highlight_text(contenu, q.strip())

    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="lecon.html",
        context={
            "rowid": rowid,
            "date": row["date_lecon"],
            "date_iso": date_iso,
            "seminaire": seminaire.strip(),
            "page": row["page_debut"],
            "contenu": contenu,
            "q": q,
            "back": back,
            "prev_lecon": prev_lecon,
            "next_lecon": next_lecon,
            "sommaire": sommaire,
            "lecon_num": lecon_num,
            "total_lecons": total_lecons,
            "kwic_results": kwic_results,
            "nb_occurrences": nb_occurrences,
        }
    )


@app.get("/seminaire/{nom}", response_class=HTMLResponse)
def seminaire_view(request: Request, nom: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT rowid, date_lecon, date_iso, page_debut, LENGTH(contenu) as taille FROM lecons WHERE seminaire = ? ORDER BY date_iso, rowid",
        (nom + " ",)  # les séminaires ont un espace trailing dans la DB
    ).fetchall()
    # essayer sans espace si pas trouvé
    if not rows:
        rows = conn.execute(
            "SELECT rowid, date_lecon, date_iso, page_debut, LENGTH(contenu) as taille FROM lecons WHERE seminaire = ? ORDER BY date_iso, rowid",
            (nom,)
        ).fetchall()
    conn.close()
    lecons = [{"rowid": r["rowid"], "date": r["date_lecon"], "date_iso": r["date_iso"], "page": r["page_debut"], "taille": r["taille"]} for r in rows]
    return templates.TemplateResponse(
        request=request,
        name="seminaire.html",
        context={"seminaire": nom, "lecons": lecons}
    )


@app.get("/stats", response_class=HTMLResponse)
def stats(request: Request, terme: str = ""):
    conn = get_conn()
    all_seminaires = get_all_seminaires(conn)

    # Stats générales
    total_lecons = conn.execute("SELECT COUNT(*) FROM lecons").fetchone()[0]
    total_chars = conn.execute("SELECT SUM(LENGTH(contenu)) FROM lecons").fetchone()[0]

    # Distribution par séminaire
    dist_rows = conn.execute(
        "SELECT seminaire, COUNT(*) as nb, SUM(LENGTH(contenu)) as taille FROM lecons GROUP BY seminaire"
    ).fetchall()
    distribution = sorted(
        [{"seminaire": r["seminaire"].strip(), "nb": r["nb"], "taille": r["taille"]} for r in dist_rows],
        key=lambda x: sort_sem_key(x["seminaire"])
    )

    # Recherche de terme pour stats
    terme_stats = []
    if terme.strip():
        rows = conn.execute(
            """
            SELECT seminaire, COUNT(*) as nb
            FROM lecons
            WHERE lecons MATCH ?
            GROUP BY seminaire
            """,
            (terme,)
        ).fetchall()
        by_sem = {r["seminaire"].strip(): r["nb"] for r in rows}
        for d in distribution:
            terme_stats.append({
                "seminaire": d["seminaire"],
                "nb_lecons": d["nb"],
                "nb_avec_terme": by_sem.get(d["seminaire"], 0),
                "pct": round(100 * by_sem.get(d["seminaire"], 0) / d["nb"], 1) if d["nb"] else 0
            })

    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="stats.html",
        context={
            "total_lecons": total_lecons,
            "total_chars": total_chars,
            "distribution": distribution,
            "terme": terme,
            "terme_stats": terme_stats,
            "all_seminaires": all_seminaires,
        }
    )


def sort_sem_key(s):
    m = re.search(r'Séminaire (\d+)(?: bis)?', s)
    if m:
        n = int(m.group(1))
        bis = 0.5 if 'bis' in s else 0
        return n + bis
    return 999


@app.get("/health")
def health():
    return {"status": "ok", "database": DB}
