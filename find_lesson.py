import fitz

doc = fitz.open("pdf/lacan_index.pdf")

search_text = "Leçon du 18 novembre 1953"

count = 0

for page_num in range(len(doc)):
    text = doc[page_num].get_text()

    if search_text in text:
        count += 1
        print()
        print("Occurrence", count)
        print("Page :", page_num + 1)
        print("-" * 50)
        print(text[:1000])

        if count >= 5:
            break
