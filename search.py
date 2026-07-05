rows = conn.execute("""
SELECT
    date_lecon,
    seminaire
FROM lecons
WHERE lecons MATCH ?
LIMIT 100
""", (mot,))