import sqlite3

conn = sqlite3.connect("lacan.db")

mot = input("Recherche : ")

row = conn.execute("""
SELECT COUNT(*)
FROM lecons
WHERE lecons MATCH ?
""", (mot,)).fetchone()

print("Résultats :", row[0])