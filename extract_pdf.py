
from pathlib import Path
import json
import fitz

PDF_DIR = Path("data/pdf")
OUTPUT_DIR = Path("data/extracted")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

pdf_files = sorted(PDF_DIR.glob("*.pdf"))

if not pdf_files:
    print("ERREUR : aucun PDF dans data/pdf")
    raise SystemExit(1)

for pdf_path in pdf_files:
    pages = []

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()

            pages.append({
                "doc_id": pdf_path.stem,
                "langue": pdf_path.stem.rsplit("_", 1)[-1],
                "page": page_num,
                "texte": text
            })

    output_path = OUTPUT_DIR / f"{pdf_path.stem}.json"

    output_path.write_text(
        json.dumps(pages, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    empty_pages = sum(not p["texte"] for p in pages)

    print(
        f"OK {pdf_path.name} : "
        f"{len(pages)} pages, "
        f"{empty_pages} pages vides"
    )

print("Extraction terminée !")
