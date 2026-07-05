import fitz
import re

PDF_PATH = "pdf/lacan_index.pdf"

doc = fitz.open(PDF_PATH)

SEMINAIRE_PATTERN = re.compile(
    r"Séminaire\s*(\d*)\s*-\s*(.+?)\s*:\s*(\d{4}-\d{4})"
)

LECON_PATTERN = re.compile(
    r"Leçon du\s+(.+)"
)

seminaire = None
count = 0

for page_num in range(26, 80):  # zone table des matières
    text = doc[page_num].get_text()

    for line in text.splitlines():

        line = line.strip()

        sem = SEMINAIRE_PATTERN.search(line)

        if sem:
            numero = sem.group(1)
            titre = sem.group(2)

            seminaire = f"Séminaire {numero} - {titre}"

            print()
            print("=" * 60)
            print(seminaire)
            print("=" * 60)

        lec = LECON_PATTERN.search(line)

        if lec and seminaire:
            count += 1
            print(f"{count:03d} | {lec.group(1)}")

print()
print("Nombre total de leçons :", count)