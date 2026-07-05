import sqlite3

conn = sqlite3.connect("lacan.db")

date = "16 juin 1971"

row = conn.execute("""
SELECT
    page_debut,
    page_fin,
    LENGTH(contenu),
    contenu
FROM lecons
WHERE date_lecon = ?
""", (date,)).fetchone()

print("Page début :", row[0])
print("Page fin   :", row[1])
print("Taille     :", row[2])

print("\n--- FIN DU TEXTE ---\n")
print(row[3][-5000:])