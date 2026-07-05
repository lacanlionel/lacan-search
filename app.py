from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import sqlite3
import re
import secrets
import os

app = FastAPI()
security = HTTPBasic()

# Redirection HTTP → HTTPS en production
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
if os.getenv("RENDER"):   # variable injectée automatiquement par Render
    app.add_middleware(HTTPSRedirectMiddleware)

# ── Authentification ─────────────────────────────────────
# Configurez via variables d'environnement sur Render :
#   AUTH_USER=votre_login
#   AUTH_PASS=votre_mot_de_passe
# En local, les valeurs par défaut ci-dessous s'appliquent.

AUTH_USER = os.getenv("AUTH_USER", "lacan")
AUTH_PASS = os.getenv("AUTH_PASS", "recherche")

def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username.encode(), AUTH_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), AUTH_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Accès non autorisé",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

DB = "lacan_v2.db"
RESULTS_PER_PAGE = 50


def get_conn():
    return sqlite3.connect(DB)


def sort_sem_key(s):
    m = re.search(r'Séminaire (\d+)(?: bis)?', s)
    if m:
        n = int(m.group(1))
        bis = 0.5 if 'bis' in s else 0
        return n + bis
    return 999


def clean_text(text):

    if not text:
        return ""

    # mots coupés
    text = re.sub(
        r'(\w+)-\n(\w+)',
        r'\1\2',
        text
    )

    # watermark
    text = re.sub(
        r'052zylxkhbix1205',
        '',
        text
    )

    # mentions ALI
    text = re.sub(
        r'—— Association Lacanienne Internationale.*?interdites\. ——',
        '',
        text,
        flags=re.DOTALL
    )

    # suites de chiffres isolés
    text = re.sub(
        r'(?:\n\d+\n){4,}',
        '\n',
        text
    )

    # numéros de page
    text = re.sub(
        r'—\s*\d+\s*—',
        '',
        text
    )

    # lignes vides multiples
    text = re.sub(
        r'\n{3,}',
        '\n\n',
        text
    )

    return text.strip()


@app.get("/", response_class=HTMLResponse)
def search(
    request: Request,
    _: str = Depends(require_auth),
    q: str = "",
    page: int = 1,
    sort: str = "score"
):
    print("SORT =", sort)
    results = []
    count = 0

    previous_page = None
    next_page = None

    if q.strip():

        offset = (page - 1) * RESULTS_PER_PAGE

        conn = get_conn()

        if sort == "date":
            order_by = "date_iso ASC"
        else:
            order_by = "score ASC"

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM lecons
            WHERE lecons MATCH ?
            """,
            (q,)
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT
                rowid,
                date_lecon,
                date_iso,
                seminaire,
                page_debut,
                snippet(
                    lecons,
                    5,
                    '<mark>',
                    '</mark>',
                    ' ... ',
                    50
                ) AS extrait,
                bm25(lecons) AS score
            FROM lecons
            WHERE lecons MATCH ?
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (
                q,
                RESULTS_PER_PAGE,
                offset
            )
        )

        for (
            rowid,
            date_lecon,
            date_iso,
            seminaire,
            page_debut,
            extrait,
            score
        ) in rows:

            results.append({
                "rowid": rowid,
                "date": date_lecon,
                "seminaire": seminaire,
                "page": page_debut,
                "score": round(abs(score), 3),
                "extrait": extrait
            })

        conn.close()

        if page > 1:
            previous_page = page - 1

        if count > page * RESULTS_PER_PAGE:
            next_page = page + 1

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "q": q,
            "sort": sort,
            "results": results,
            "count": count,
            "page": page,
            "previous_page": previous_page,
            "next_page": next_page
        }
    )


@app.get("/lecon/{rowid}", response_class=HTMLResponse)
def lecon(
    request: Request,
    rowid: int,
    _: str = Depends(require_auth)
):

    conn = get_conn()

    row = conn.execute(
        """
        SELECT
            date_lecon,
            date_iso,
            seminaire,
            page_debut,
            contenu
        FROM lecons
        WHERE rowid = ?
        """,
        (rowid,)
    ).fetchone()

    conn.close()

    if row is None:

        return HTMLResponse(
            "<h1>Leçon introuvable</h1>",
            status_code=404
        )

    date_lecon, date_iso,seminaire, page_debut, contenu = row

    contenu = clean_text(contenu)

    return templates.TemplateResponse(
        request=request,
        name="lecon.html",
        context={
            "date": date_lecon,
            "date_iso": date_iso,
            "seminaire": seminaire,
            "page": page_debut,
            "contenu": contenu
        }
    )


@app.get("/stats", response_class=HTMLResponse)
def stats(
    request: Request,
    _: str = Depends(require_auth),
    terme: str = ""
):
    conn = get_conn()

    # Liste des séminaires
    seminaire_rows = conn.execute(
        "SELECT DISTINCT seminaire FROM lecons ORDER BY seminaire"
    ).fetchall()
    all_seminaires = sorted(
        [r[0].strip() for r in seminaire_rows],
        key=sort_sem_key
    )

    # Stats générales
    total_lecons = conn.execute("SELECT COUNT(*) FROM lecons").fetchone()[0]
    total_chars = conn.execute("SELECT SUM(LENGTH(contenu)) FROM lecons").fetchone()[0]

    # Distribution par séminaire
    dist_rows = conn.execute(
        "SELECT seminaire, COUNT(*) as nb, SUM(LENGTH(contenu)) as taille FROM lecons GROUP BY seminaire"
    ).fetchall()
    distribution = sorted(
        [{"seminaire": r[0].strip(), "nb": r[1], "taille": r[2]} for r in dist_rows],
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
        by_sem = {r[0].strip(): r[1] for r in rows}
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


@app.get("/health")
def health():

    return {
        "status": "ok",
        "database": DB
    }
