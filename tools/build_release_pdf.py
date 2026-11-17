"""Generate the reviewer-facing release and QA handoff PDF."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def build(destination, test_count, before_mb, after_mb, after_files):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleGreen", parent=styles["Title"], textColor=colors.HexColor("#184832"), alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="SectionGreen", parent=styles["Heading2"], textColor=colors.HexColor("#184832"), spaceBefore=14, spaceAfter=5))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=9, leading=13, spaceAfter=5))
    doc = SimpleDocTemplate(str(destination), pagesize=(8.5*inch, 11*inch),
                            leftMargin=0.65*inch, rightMargin=0.65*inch,
                            topMargin=0.55*inch, bottomMargin=0.55*inch)
    story = [Paragraph("Verdant - Release and QA Handoff", styles["TitleGreen"]),
             Paragraph("Windows test ZIP | 17 November 2026", styles["BodySmall"])]

    def section(title, text):
        story.append(KeepTogether([Paragraph(title, styles["SectionGreen"]),
                                   Paragraph(text, styles["BodySmall"])]))

    section("1. Master workbook export", "The long Scores export remains. A new master-layout workbook has ESG_Scores, SDG_Scores, Evidence_Log and README sheets. It keeps unreviewed decisions blank, includes all roster company-years, and uses SDG point formulas. The supplied master is never modified. The fixture compares three company-years cell by cell. LibreOffice recalculation could not be run because LibreOffice is not installed on this computer.")
    section("2. Portable workpapers", "Selecting a company or fiscal year opens its workpaper. Reports use relative paths under a chosen folder when possible and retain SHA-256 hashes. Missing reports can be relinked. One company-year can be exchanged in a .verdant package with decisions, evidence, audit history, OCR text and report references. Imports preview conflicts before applying newer timestamps. Roster import accepts a Companies sheet.")
    section("3. Honest rule-based leads", "The overview separates items with leads, reviewed items and supported reviewed items. Manual ESG/SDG totals remain the official saved totals. The rule checker requires a company cue plus a figure or named program/body, rejects list-only SDG mentions, and penalizes contents pages. Low, medium and high confidence include plain-language reasons. There are no AI or LLM calls.")
    section("4. Review workflow", "Save and next skips reviewed items. Next with a lead, Y/N, Alt+Right, Ctrl+F and F3 are available. A single find bar searches this PDF, all PDFs or the checklist. PDF import, OCR and lead finding run in background with progress and Cancel. Bulk Not found applies only to unreviewed items without hits after confirmation and writes a bulk audit tag.")
    section("5. Page and setup clarity", "The form distinguishes PDF pages from printed page labels. PDF pages are the default export reference; a setting can use printed pages where saved. First run asks for reports folder, scorer name and optional roster. The score overview stays in a tab, and splitter positions persist.")
    section("6. Windows package", f"PyInstaller exclusions remove unused modules. Measured package size changed from {before_mb:.1f} MB / 277 files to {after_mb:.1f} MB / {after_files} files. An isolated startup smoke test kept the built EXE running for eight seconds without an immediate crash. The ZIP is for testing, not a signed installer.")

    test_rows = [["Command", "Result"],
                 [".venv\\Scripts\\python.exe -m unittest discover -s tests -v", f"{test_count} tests passed"],
                 ["Real Aboitiz Integrated Report FY2022", "141 pages; page 78 contains typhoon; 26 rule-based leads"],
                 ["Real Aboitiz Annual Report FY2022", "422 pages; extraction 0.91 seconds; 418 pages with text"],
                 ["Packaged EXE startup", "Started and remained running at 8 seconds"]]
    table = Table(test_rows, colWidths=[3.5*inch, 3.5*inch], hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#214B37")),
                               ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                               ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#B8C9BE")),
                               ("VALIGN", (0,0), (-1,-1), "TOP"),
                               ("FONTSIZE", (0,0), (-1,-1), 8),
                               ("BOTTOMPADDING", (0,0), (-1,-1), 7),
                               ("TOPPADDING", (0,0), (-1,-1), 7)]))
    story.append(KeepTogether([Paragraph("Automated verification", styles["SectionGreen"]), table]))
    section("Manual QA before client release", "[ ] Check 1366x768 at Windows 150% scaling, including the first-run screen and all three tabs.<br/>[ ] Import a 200+ page PDF and time the UI response.<br/>[ ] Import a PDF whose filename says the wrong FY; confirm the skip warning.<br/>[ ] OCR one image-only PDF; inspect highlighted page and extracted text.<br/>[ ] Save, close and reopen a workpaper; compare decisions and audit history.<br/>[ ] Paste a new export into a COPY of the master workbook; recalculate in LibreOffice or Excel and inspect formulas.<br/>[ ] Move a PDF and verify Missing plus relink by hash.<br/>[ ] Move a .verdant workpaper between two PCs and verify conflict handling.")
    section("Limits", "Real scanned company reports, actual 150% Windows display behavior, SmartScreen, cross-PC timestamps, and LibreOffice recalculation remain client-environment checks. The rule-based leads can miss evidence or produce false positives; reviewers must inspect each passage before saving Found (1).")
    doc.build(story)
    return destination


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--tests", type=int, required=True)
    parser.add_argument("--before-mb", type=float, required=True)
    parser.add_argument("--after-mb", type=float, required=True)
    parser.add_argument("--after-files", type=int, required=True)
    args = parser.parse_args()
    build(args.output, args.tests, args.before_mb, args.after_mb, args.after_files)
