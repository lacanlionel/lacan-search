import sqlite3
import zipfile
from bs4 import BeautifulSoup

DB = "lacan_V2.db"
EPUB = "ecrits.epub"

conn = sqlite3.connect(DB)
cur = conn.cursor()

with zipfile.ZipFile(EPUB) as z:

    for name in z.namelist():

        if not name.endswith(".html"):
            continue

        if any(x in name for x in [
            "cover",
            "copy",
            "toc",
            "table",
            "index",
            "bibli",
            "termes",
            "notes"
        ]):
            continue

        print("Import :", name)

        html = z.read(name)

        soup = BeautifulSoup(html, "html.parser")

        titre = ""

        h = soup.find(["h1", "h2", "h3"])

        if h:
            titre = h.get_text(" ", strip=True)

        texte = soup.get_text(" ", strip=True)

        cur.execute(
            """
            INSERT INTO documents
            (
                type,
                titre,
                date,
                seminaire,
                contenu
            )
            VALUES (?,?,?,?,?)
            """,
            (
                "ECRITS",
                titre,
                "",
                "Écrits",
                texte
            )
        )

conn.commit()
conn.close()

print("Terminé")