import fitz
import csv

doc = fitz.open("pdf/lacan_index.pdf")

toc = doc.get_toc()

with open("toc.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    writer.writerow([
        "level",
        "page",
        "title"
    ])

    for level, title, page in toc:
        writer.writerow([
            level,
            page,
            title
        ])

print("Export terminé : toc.csv")
print("Entrées :", len(toc))