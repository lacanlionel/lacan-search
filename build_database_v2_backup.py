import fitz
import sqlite3
import re

MOIS = {
    "janvier": "01",
    "février": "02",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "août": "08",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "décembre": "12",
    "decembre": "12"
}

def make_iso(date_txt):

    m = re.search(
        r"(\d{1,2})\s+([a-zéûôîàèù]+)\s+(\d{4})",
        date_txt.lower()
    )

    if not m:
        return ""

    jour, mois, annee = m.groups()

    mois = MOIS.get(mois, "01")

    return f"{annee}-{mois}-{int(jour):02d}"



PDF_PATH = "pdf/lacan_index.pdf"
DB_PATH = "lacan_v2.db"

def clean_text(text):

    # mots coupés
    text = re.sub(
        r"(\w+)-\n(\w+)",
        r"\1\2",
        text
    )

    # suppression code ALI
    text = re.sub(
        r"052zylxkhbix1205",
        "",
        text
    )

    lines = []

    for line in text.splitlines():

        l = line.strip()

        # ligne vide
        if not l:
            lines.append("")
            continue

        # caractères isolés
        if len(l) == 1:
            continue

        # numéros de page
        if re.match(r"^—\s*\d+\s*—$", l):
            continue

        # entête ALI
        if "Association Lacanienne Internationale" in l:
            continue

        lines.append(line)

    text = "\n".join(lines)

    # paragraphes
    paragraphs = []
    current = []

    for line in text.splitlines():

        l = line.strip()

        if not l:

            if current:
                paragraphs.append(" ".join(current))
                current = []

            continue

        current.append(l)

    if current:
        paragraphs.append(" ".join(current))

    text = "\n\n".join(paragraphs)

    return text.strip()

doc = fitz.open(PDF_PATH)
toc = doc.get_toc()

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS lecons")

cur.execute("""
CREATE VIRTUAL TABLE lecons
USING fts5(
    seminaire,
    date_lecon,
    date_iso,
    page_debut,
    page_fin,
    contenu
)
""")

sections = []
seminaire_courant = None

for level, title, page in toc:

    if level == 2 and title.startswith("Séminaire"):
        seminaire_courant = title

    if level == 3:
        sections.append({
            "title": title.strip(),
            "page": page,
            "seminaire": seminaire_courant
        })

print("Sections niveau 3 :", len(sections))

nb_lecons = 0

for i, section in enumerate(sections):

    page_debut = section["page"]

    if i < len(sections) - 1:
        page_fin = sections[i + 1]["page"] - 1
    else:
        page_fin = len(doc)

    titre = section["title"]

    if not titre.startswith("Leçon"):
        continue

    texte_pages = []

    for p in range(page_debut - 1, page_fin):

        try:
            page_text = doc[p].get_text()
            texte_pages.append(page_text)

        except Exception as e:
            print("Erreur page", p + 1, e)

    contenu = "\n".join(texte_pages)

# nettoyage du texte
    contenu = clean_text(contenu)

    date_lecon = titre.replace("Leçon du", "").strip()
    date_lecon = date_lecon.replace("1054", "1954")
    date_iso = make_iso(date_lecon)
    
    cur.execute(
        """
        INSERT INTO lecons
        (
          seminaire,    
          date_lecon,
          date_iso,
          page_debut,
          page_fin,
          contenu
        )
    VALUES (?, ?, ?, ?, ?, ?)
    """, 
        (
        section["seminaire"],
        date_lecon,
        date_iso,
        str(page_debut),
        str(page_fin),
        contenu
        )
    )

    nb_lecons += 1

    if nb_lecons % 25 == 0:
        print(nb_lecons)

conn.commit()
conn.close()

print()
print("Leçons importées :", nb_lecons)
print("Base créée :", DB_PATH)