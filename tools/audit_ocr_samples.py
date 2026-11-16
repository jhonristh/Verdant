"""OCR one scanned page from several reports without changing source PDFs."""
import csv
from pathlib import Path

import fitz
from ocr_support import extract_missing_pages, find_tessdata

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT.parent / "Sample Companies"
AUDIT = ROOT / "output" / "qa" / "corpus_audit.csv"
OUTPUT = ROOT / "output" / "qa" / "ocr_samples.csv"

with AUDIT.open(encoding="utf-8-sig", newline="") as stream:
    rows = sorted(csv.DictReader(stream), key=lambda row: int(row["blank_pages"]), reverse=True)

selected = []
companies = set()
for row in rows:
    company = Path(row["path"]).parts[0]
    if company in companies or int(row["blank_pages"]) < 20:
        continue
    companies.add(company)
    selected.append(row)
    if len(selected) == 10:
        break

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("path", "page", "ocr_characters", "error"))
    for row in selected:
        path = CORPUS / row["path"]
        with fitz.open(path) as pdf:
            blanks = [number for number, page in enumerate(pdf, 1) if not page.get_text("text").strip()]
        number = blanks[len(blanks) // 2]
        results, errors = extract_missing_pages([(str(path), "audit", [number])], find_tessdata())
        writer.writerow((row["path"], number, len(results[0][3]) if results else 0, " | ".join(errors)))
        print(f"{len(results)}/{len(errors)} {row['path']} page {number}", flush=True)
