import fitz
import sqlite3
import re

PDF_PATH = "pdf/lacan_index.pdf"
DB_PATH = "lacan.db"

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
    page_debut,
    page_fin,
    contenu
)
""")

lecons = []
seminaire_courant = None

for level, title, page in toc:

    if level == 2 and title.startswith("Séminaire"):
        seminaire_courant = title

    elif level == 3 and title.startswith("Leçon du"):

        lecons.append({
            "seminaire": seminaire_courant,
            "titre": title,
            "page": page
        })

print("Leçons trouvées :", len(lecons))

for i, lecon in enumerate(lecons):

    page_debut = lecon["page"]

    if i < len(lecons) - 1:
        page_fin = lecons[i + 1]["page"] - 1
    else:
        page_fin = len(doc)

    texte = []

    for p in range(page_debut - 1, page_fin):
        texte.append(doc[p].get_text())

    contenu = "\n".join(texte)

    date_lecon = lecon["titre"].replace("Leçon du", "").strip()

    cur.execute("""
    INSERT INTO lecons
    (
        seminaire,
        date_lecon,
        page_debut,
        page_fin,
        contenu
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        lecon["seminaire"],
        date_lecon,
        str(page_debut),
        str(page_fin),
        contenu
    ))

    if i % 25 == 0:
        print(i, "/", len(lecons))

conn.commit()
conn.close()

print()
print("Base créée :", DB_PATH)