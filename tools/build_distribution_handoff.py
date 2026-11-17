"""Write the five current handoff PDFs and the concise plain-text operator guide."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer


DATE = "17 November 2026"
GREEN = colors.HexColor("#164b32")
INK = colors.HexColor("#24342b")


def write_pdf(path, title, subtitle, sections):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="VerdantTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=18, leading=23, textColor=GREEN, spaceAfter=8))
    styles.add(ParagraphStyle(name="VerdantSection", parent=styles["Heading2"], fontName="Helvetica-Bold",
                              fontSize=11, leading=15, textColor=GREEN, spaceBefore=10, spaceAfter=5))
    styles.add(ParagraphStyle(name="VerdantBody", parent=styles["BodyText"], fontName="Helvetica",
                              fontSize=9, leading=13, textColor=INK, spaceAfter=5))
    styles.add(ParagraphStyle(name="VerdantSmall", parent=styles["VerdantBody"], fontSize=8,
                              leading=11, textColor=colors.HexColor("#56705f")))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=17*mm, bottomMargin=17*mm, title=title, author="Jargon")
    story = [Paragraph(escape(title), styles["VerdantTitle"]),
             Paragraph(escape(subtitle + " | " + DATE), styles["VerdantSmall"]), Spacer(1, 4*mm)]
    for heading, lines in sections:
        block = [Paragraph(escape(heading), styles["VerdantSection"])]
        for line in lines:
            block.append(Paragraph(escape(line), styles["VerdantBody"]))
        story.append(KeepTogether(block[:2]))
        story.extend(block[2:])
    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(GREEN)
        canvas.line(18*mm, 13*mm, A4[0]-18*mm, 13*mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(INK)
        canvas.drawString(18*mm, 9*mm, "Verdant Disclosure Scorer")
        canvas.drawRightString(A4[0]-18*mm, 9*mm, str(document.page))
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


FEATURES = """VERDANT - FEATURES AND HOW TO USE
Release: 17 November 2026 (source revision d04a01c)

FEATURES
- Local company/fiscal-year workpapers with autosaved decisions, audit history and portable .verdant transfer.
- PDF reader with page navigation, zoom, fit, text search, match navigation and matched-page filters.
- Native PDF text extraction plus selective OCR for image-only pages. OCR results join later searches and leads.
- 30 ESG criteria and 17 SDGs in three stages (Identified, Managed, Reported), for 30 ESG and 102 SDG possible points.
- Rule-based leads use SDG numbers, titles and topic terms. Leads are suggestions, never saved scores.
- Clearly marked lead/no-text-hit states and separate saved Supported/Not supported decisions.
- Multiple pinned passages per score category across different PDFs and pages; optional reviewer note.
- One Excel workbook per open workspace: Summary, Decisions and Evidence pins.
- Button tips and a Help popup; credit appears at the bottom of Help.

HOW TO USE
1. Extract the correct package fully. Windows: run Verdant_Disclosure_Scorer.exe. Mac build kits: read START_HERE.txt and build on the matching Mac before distributing the resulting app.
2. Complete first-run setup: choose a reports folder, optional roster, and scorer name.
3. Choose a company and fiscal year. Attach the correct report PDFs with Add PDFs.
4. Open PDF reader. Search this PDF or all attached PDFs. Use the match controls and page controls to inspect sources.
5. If a page has no extractable text, run OCR current or selected pages. Check the extracted text and PDF viewer afterward.
6. Click Find leads. Inspect each lead and its PDF page. No text hit means no extracted-text match; it is not proof of no disclosure.
7. In Checklist and decisions, select a category. Choose Found (1) or Not found (0). For Found, enter an evidence PDF and PDF page. The reviewer note is optional.
8. Pin any relevant passages from the reader or extracted-text panel. Pins remain attached to the score category when switching reports and pages.
9. Click Save and next. Previous item and Next item navigate without saving; unsaved edits prompt before leaving.
10. Review Score overview. Export sheets for the currently open company/fiscal-year workbook, or export .verdant for transfer.

DATA AND UPDATES
- Back up the app's data folder and the original PDF reports before an update. Close Verdant first.
- The Windows ZIP is a portable app, not an installer. Extract a new version to a separate writable folder, then copy the previous data folder while Verdant is closed. Do not overwrite old data blindly.
- On Mac, app data is under ~/Library/Application Support/Verdant/data. A .verdant transfer does not include PDF binaries.
- Lead scoring is rule-based and can miss or misclassify passages. Only the reviewer's saved decisions count.
"""


def build(directory):
    directory = Path(directory)
    operator = [
        ("Start and open", ["Windows: extract the complete portable ZIP and run Verdant_Disclosure_Scorer.exe. Mac: build the app on the matching Mac using its kit. The Mac kits are source build kits, not ready-made apps.",
                            "Choose a writable reports folder and optional roster at first run. Choose both company and fiscal year; no year is selected by default. Add PDFs for that company-year."]),
        ("Read and search PDFs", ["Use Previous/Next, page jump, zoom, Fit width and Fit page. The find bar searches this PDF, all PDFs or checklist items; Previous match and Next match move between results.",
                                  "Matched pages list candidate pages. Select a result to inspect the PDF, extracted text and evidence context. Search may miss image-only pages until OCR completes."]),
        ("OCR and leads", ["Run OCR current or selected pages when the app reports missing extractable text. Check the extracted text and visible PDF page after OCR; OCR can contain recognition errors.",
                           "Find leads scans the selected fiscal year's reports. Green LEAD FOUND is a suggested lead; amber HIT NEEDS REVIEW is a weak match; red NO TEXT HIT means no match in extracted text. None is a saved decision."]),
        ("Save decisions", ["Select a score category in Checklist and decisions. Choose Found (1) or Not found (0). Found requires a document and PDF page reference; a reviewer note is optional.",
                            "Pin selected passages from different reports/pages. Pins follow the score category, not the currently displayed PDF page. Use lead fills the form but does not save. Save and next records the decision; Previous item and Next item navigate without saving.",
                            "SDG stages are Identified (1 point), Managed (2), and Reported (3). A later stage requires the earlier stage to be supported. Review all evidence manually."]),
        ("Review and export", ["Score overview separates rule-based leads from saved confirmed points. ESG maximum is 30; SDG maximum is 102. Unreviewed items remain blank.",
                              "Export sheets creates one XLSX for the open company-year: Summary, Decisions, Evidence pins. The Decisions sheet distinguishes saved scores from leads. Export workpaper (.verdant) transfers one workspace, but not the PDF binaries."]),
        ("Help and preservation", ["Hover over buttons or click ? Help for short descriptions. Back up the data folder and PDF reports before an update. Close Verdant before copying data. The Help popup ends with the credit 'tool made by jargon'."]),
    ]
    technical = [
        ("Purpose and boundaries", ["Verdant is an offline desktop review workbench. It extracts text from local PDF reports, supports selective OCR, finds rule-based leads, and records reviewer decisions with source pages and audit history. It does not send reports to a cloud service or decide scores automatically."]),
        ("Scoring model", ["The rubric has 30 ESG binary criteria and 17 SDGs with three weighted stages each: 1 + 2 + 3 points per goal, 102 SDG points in total. The current rubric includes goal number, official title and topic terms for each SDG.",
                            "Lead rules require context such as a company cue and concrete figure or named program. Contents pages and SDG lists are weak evidence. A lead can be wrong or absent even when a disclosure exists; manual review governs the saved score."]),
        ("Implementation", ["PySide6 provides the desktop UI and PDF viewer; PyMuPDF extracts PDF text and page geometry; Tesseract-backed OCR recovers image-only pages; SQLite stores workpapers, scores, pins, OCR text and audit records; openpyxl writes one-workspace Excel snapshots.",
                            "The current PDF search, matched-page list, extracted-text panel and highlight overlay use the same selected category. OCR text is cached by PDF hash and invalidates old lead proposals when changed."]),
        ("Data and export", ["Each workpaper is keyed by company and fiscal year. Multiple evidence pins can reference different documents/pages for the same score category. The reviewer note is optional and blank when not entered.",
                            "The Excel workbook contains Summary, Decisions and Evidence pins. Leads and confirmed scores are separate columns. The .verdant transfer includes workpaper data and report references, not PDF binaries."]),
        ("Limits", ["OCR text and highlight geometry may vary with scan quality. Search terms are recall aids, not proof of disclosure. Reports with misleading filenames may need manual fiscal-year review. Mac builds require platform-specific validation before they are given to clients."]),
    ]
    developer = [
        ("Source of truth", ["Only the Verdant source directory should be edited. The release packages are generated outputs. Current tested source revision: d04a01c. Do not use the older V2 ZIPs as source for updates."]),
        ("Windows build", ["Use a Windows 11 machine with Python and the requirements installed. Run build_qt_exe.ps1 in the source directory. It invokes PyInstaller on app.py and includes resources/. Validate the generated dist/Verdant_Disclosure_Scorer executable before packaging.",
                           "The portable ZIP contains the complete one-directory app. Keep _internal beside the EXE. It does not include saved data or client PDFs."]),
        ("Intel Big Sur build", ["Build on the target Intel Mac running macOS 11.x with Python 3.11. Unpack the Intel build kit, run Build_Verdant.command, then run the automated tests and smoke-check the generated Verdant.app. The pinned PySide6 6.5.3 wheel supports macOS 11 universal2."]),
        ("M4 build", ["Build on the M4 Mac with macOS 14 or newer and Python 3.12. Unpack the M4 build kit, run Build_Verdant.command, then test the generated Verdant.app. PySide6 6.12 macOS wheels target macOS 14 or newer."]),
        ("Data locations", ["Windows portable builds store data beside the EXE in data/. Mac packaged builds use ~/Library/Application Support/Verdant/data. Source runs store data in the source folder. Keep client data and original PDFs out of release ZIPs."]),
        ("Release gate", ["Verify ZIP integrity and hashes, executable startup, import, OCR, lead finding, decision save/reopen, pin persistence and one-workspace Excel export on each target OS. PyInstaller cannot create a verified Mac app from Windows."]),
    ]
    qa = [
        ("Verified on Windows", ["The current source test suite passed 71 tests on Windows on 17 November 2026. Tests cover OCR, search, PDF highlights, evidence pins, SDG scoring, navigation, workpaper transfer and per-workspace Excel export.",
                                "This document does not claim that every client PDF was manually reviewed. The sample company corpus was used in earlier targeted checks; unreviewed scan quality remains a case-by-case concern."]),
        ("Current release status", ["Windows portable executable: built and local smoke-tested for startup and export. Intel Big Sur and M4 ZIPs are complete source build kits, not compiled client apps. Native Mac build and runtime checks remain to be run on those Macs."]),
        ("Operational checks before client handoff", ["On each client platform: open the app, import a native-text PDF and an image-only PDF, run selective OCR, confirm text and PDF highlight, find a lead, save and reopen both Supported and Not supported decisions, pin passages across pages, and export a one-workspace XLSX.",
                                                       "Keep the old data folder until the new app reads it correctly. Verify an imported .verdant workpaper and relink a moved PDF. Check a second device and the target display scale."]),
        ("Known limitations", ["Rule-based leads are suggestions and can be false positives or misses. OCR depends on scan quality. Unsigned Windows/Mac binaries may produce OS publisher warnings. Mac build kits require Python and internet access for dependency installation."]),
    ]
    installer = [
        ("What to distribute", ["The current Windows deliverable is a portable one-directory ZIP, not a new setup EXE. Extract the whole folder and run Verdant_Disclosure_Scorer.exe. The earlier Verdant_Setup.exe belongs to an older release and must not be presented as this update."]),
        ("Update procedure", ["Close Verdant. Back up the old data folder and original PDF reports. Extract the new ZIP to a separate writable folder. Copy the old data folder into the new app folder while the app is closed. Open the new EXE and verify workpapers, scores, evidence pins and PDF links before removing the old folder.",
                              "If a PDF path changed, use Workpaper > Relink missing PDF. A .verdant workpaper export can transfer a single company-year, but it does not contain PDF binaries."]),
        ("Verification and scope", ["The Windows ZIP is built from the current source and checked locally. The Mac ZIPs are build kits, not native apps. No package contains client workpapers, imported PDFs or the sample-company report corpus."]),
    ]
    documents = {
        "Verdant_Operator_Guide.pdf": ("Verdant Operator Guide", "Step-by-step user workflow", operator),
        "Verdant_Technical_Paper.pdf": ("Verdant Technical Paper", "Scoring, architecture and limits", technical),
        "Verdant_Developer_Deployment_Guide.pdf": ("Verdant Developer and Deployment Guide", "Build and release procedure", developer),
        "Verdant_QA_Release_Status.pdf": ("Verdant QA and Release Status", "Verified checks and remaining platform gates", qa),
        "Verdant_Installer_Release_Addendum.pdf": ("Verdant Distribution Addendum", "Portable Windows update procedure", installer),
    }
    for name, (title, subtitle, sections) in documents.items():
        write_pdf(directory / name, title, subtitle, sections)
    (directory.parent / "FEATURES_AND_HOW_TO_USE.txt").write_text(FEATURES, encoding="utf-8")
    return list(documents)


if __name__ == "__main__":
    import sys
    for name in build(sys.argv[1]):
        print(name)
