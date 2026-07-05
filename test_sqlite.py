import sqlite3

conn = sqlite3.connect(":memory:")

conn.execute("""
CREATE VIRTUAL TABLE test
USING fts5(contenu)
""")

print("FTS5 OK")