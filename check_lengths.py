import sqlite3

conn = sqlite3.connect("lacan_v2.db")

rows = conn.execute("""
SELECT
    date_lecon,
    seminaire,
    LENGTH(contenu) as taille
FROM lecons
ORDER BY taille DESC
LIMIT 20
""").fetchall()

for date_lecon, seminaire, taille in rows:
    print(f"{taille:>8} caractères | {date_lecon} | {seminaire}")

conn.close()