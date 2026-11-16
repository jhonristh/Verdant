"""Generate the current repair and verification handoff PDF."""
from pathlib import Path
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "Verdant_Repair_QA_Handoff.pdf"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

lines = [
    ("Verdant repair and QA handoff", 17, True),
    ("17 November 2026 | Source: Verdant | Dataset: Sample Companies", 10, False),
    ("Scope and status", 13, True),
    ("This report records verified software behavior. Automated proposals remain reviewer decisions.", 10, False),
    ("Completed repairs", 13, True),
    ("- Added PDF text search with next/previous navigation, match count and extracted-text selection.", 10, False),
    ("- Refreshed persisted score proposals after OCR adds searchable text.", 10, False),
    ("- Pinned a selected passage with its PDF filename and page as evidence.", 10, False),
    ("- Capped visible matched rows consistently with list indexing (200-row UI limit).", 10, False),
    ("- Recognized four-digit fiscal years beyond the previously hardcoded 2022-2025 set.", 10, False),
    ("- Synced PDF navigation controls and text status when scrolling the continuous reader.", 10, False),
    ("- Restored the app_qt.main startup entrypoint and removed the fitz deprecation warning.", 10, False),
    ("Verification", 13, True),
    ("- Full automated suite: 51 tests passed, including seven new regression tests.", 10, False),
    ("- run.cmd stayed open in a startup smoke test with no stderr output.", 10, False),
    ("- Word-coordinate fallback fixed a native PDF search geometry miss in Emperador FY2023.", 10, False),
    ("- Both corpus spot-check geometry misses now resolve through word coordinates.", 10, False),
    ("- Alsons FY2023 page 10: OCR recovered 3,111 characters from a blank-text scan.", 10, False),
    ("- Ten additional scanned pages from different dataset folders yielded OCR text.", 10, False),
    ("- OCR raster test verified text and PDF highlight rectangles on an image-only page.", 10, False),
    ("- All 17 SDG goals at all three stages total 102/102 weighted points.", 10, False),
    ("- Aboitiz FY2022: E4 found 15 pages across the integrated and annual reports.", 10, False),
    ("- Integrated Report PDF page 78: typhoon, scenario analysis and TCFD matched.", 10, False),
    ("- UI opened page 78 and rendered one visible highlighted match.", 10, False),
    ("- PDF search selected Scenario Analysis and navigated to PDF page 71.", 10, False),
    ("- Current rubric proposed SDG 18/102 for the two FY2022 Aboitiz reports.", 10, False),
    ("- Windows executable built successfully and remained running in an eight-second smoke check.", 10, False),
    ("Scoring interpretation", 13, True),
    ("SDG proposals require goal-specific identification and stage prerequisites.", 10, False),
    ("A generic keyword alone does not award points; reviewers may override with cited evidence.", 10, False),
    ("The revised workbook specifies 102 points; the older Final Scoring PDF says 51.", 10, False),
    ("Verdant follows the revised workbook. Resolve this document conflict before final sign-off.", 10, False),
    ("Limits requiring further review", 13, True),
    ("- 9,683 blank-text pages require selective OCR; this audit did not OCR all of them.", 10, False),
    ("- Image-only PDF text can be searchable after OCR while PDF geometry is unavailable.", 10, False),
    ("- A human review of the visible packaged UI remains advisable before client release.", 10, False),
]

summary_path = ROOT / "output" / "qa" / "corpus_audit_summary.json"
if summary_path.exists():
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    lines[lines.index(("Verification", 13, True)) + 1:lines.index(("Verification", 13, True)) + 1] = [
        (f"- Corpus audit: {summary['files']} PDFs, {summary['pages']} pages; {summary['errors']} unreadable PDFs.", 10, False),
        (f"- {summary['blank_pages']} blank-text and {summary['sparse_pages']} sparse-text pages need review.", 10, False),
        (f"- Native text/geometry spot checks found {summary['search_mismatches']} mismatches.", 10, False),
    ]

pdf = canvas.Canvas(str(OUTPUT), pagesize=A4)
width, height = A4
y = height - 48
for text, size, heading in lines:
    if y < 72:
        pdf.showPage()
        y = height - 48
    pdf.setFont("Helvetica-Bold" if heading else "Helvetica", size)
    pdf.setFillColor(colors.HexColor("#17412e") if heading else colors.HexColor("#202c26"))
    pdf.drawString(48, y, text)
    y -= 22 if heading else 17
pdf.setStrokeColor(colors.HexColor("#8fac9a"))
pdf.line(48, 36, width - 48, 36)
pdf.save()
print(OUTPUT)
