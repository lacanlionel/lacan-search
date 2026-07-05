import fitz

PDF_PATH = "pdf/lacan_index.pdf"

doc = fitz.open(PDF_PATH)

print(f"Nombre de pages : {len(doc)}")

print("\n--- PAGE 27 (table des matières) ---\n")

page = doc[26]   # page 27 du PDF (index Python commence à 0)

text = page.get_text()

print(text[:5000])