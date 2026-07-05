import fitz

doc = fitz.open("pdf/lacan_index.pdf")

toc = doc.get_toc()

print("Nombre d'entrées :", len(toc))
print()

for entry in toc[:50]:
    level, title, page = entry
    print(f"{level} | Page {page} | {title}")