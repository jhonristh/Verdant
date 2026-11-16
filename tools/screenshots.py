"""Generate sample PDF and capture offscreen screenshots at 3 desktop resolutions."""
import hashlib
import os
import sys
from pathlib import Path

# Add Verdant to sys.path
verdant_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(verdant_dir))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import fitz
from PySide6.QtWidgets import QApplication

import app
import app_qt


def create_sample_pdf(pdf_path: Path):
    doc = fitz.open()
    # Pages 1 to 8: Normal text
    for i in range(1, 9):
        page = doc.new_page()
        page.insert_text((50, 50), f"SAMPLE REPORT 2022 - PAGE {i}", fontsize=16)
        if i == 1:
            page.insert_text((50, 100), "Executive Summary and Annual Financial Overview.", fontsize=13)
        elif i == 2:
            page.insert_text((50, 100), "Environmental compliance risk and clean-up cost of PHP 12 million.", fontsize=13)
        elif i == 3:
            page.insert_text((50, 100), "Carbon pricing mechanisms, internal carbon tax, and emission reduction.", fontsize=13)
        elif i == 4:
            page.insert_text((50, 100), "SDG 13 Climate Action: The company manages emissions through targets.", fontsize=13)
        else:
            page.insert_text((50, 100), f"Corporate operations and governance disclosures for section {i}.", fontsize=12)

    # Pages 9 and 10: Scanned image-only pages (need OCR)
    for i in (9, 10):
        # Create an offscreen page, render to image, insert as image
        temp_doc = fitz.open()
        tp = temp_doc.new_page()
        tp.insert_text((72, 100), f"SCANNED FINANCIAL STATEMENT ANNEX {i}", fontsize=18)
        tp.insert_text((72, 150), "Audit Committee Charter and Statutory Reports.", fontsize=14)
        pix = tp.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        temp_doc.close()

        scanned_page = doc.new_page()
        scanned_page.insert_image(scanned_page.rect, stream=img_bytes)

    # Pages 11 and 12: Text
    for i in (11, 12):
        page = doc.new_page()
        page.insert_text((50, 50), f"REPORT FINAL NOTES - PAGE {i}", fontsize=14)
        page.insert_text((50, 100), "Independent assurance statement and conclusion.", fontsize=12)

    doc.save(pdf_path)
    doc.close()
    return pdf_path


def main():
    qapp = QApplication.instance() or QApplication([])

    out_dir = verdant_dir / "qa_screens"
    out_dir.mkdir(parents=True, exist_ok=True)

    data_dir = verdant_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sample_pdf_path = data_dir / "Sample_Corporation_Integrated_Report_FY2022.pdf"
    create_sample_pdf(sample_pdf_path)

    # Setup Workbench
    window = app_qt.Workbench()
    company = "Aboitiz Power Corporation"
    year = "2022"

    project_id = window.store.project(company, year)
    window.project_id = project_id
    window.active_company = company
    window.active_year = year
    window.company.setCurrentText(company)
    window.year.setCurrentText(year)

    digest = hashlib.sha256(sample_pdf_path.read_bytes()).hexdigest()
    window.store.add_report(project_id, sample_pdf_path, digest, 12, 2)
    window.load_reports()
    window.check_for_score()
    window.show()
    qapp.processEvents()

    resolutions = [
        (1920, 1080),
        (1536, 864),
        (1280, 720)
    ]

    for w, h in resolutions:
        window.resize(w, h)
        qapp.processEvents()

        # 1. PDF reader (All PDF pages)
        window.work_tabs.setCurrentIndex(0)
        window.view_tabs.setCurrentIndex(0)
        window.toggle_warning(False)
        qapp.processEvents()
        window.grab().save(str(out_dir / f"{w}x{h}_01_pdf_reader_all_pages.png"))

        # 2. PDF reader (Highlighted page)
        window.work_tabs.setCurrentIndex(0)
        window.view_tabs.setCurrentIndex(1)
        window.render_page()
        qapp.processEvents()
        window.grab().save(str(out_dir / f"{w}x{h}_02_pdf_reader_highlighted.png"))

        # 3. PDF reader with OCR details popup open
        window.work_tabs.setCurrentIndex(0)
        window.toggle_warning(True)
        qapp.processEvents()
        window.grab().save(str(out_dir / f"{w}x{h}_03_pdf_reader_ocr_popup.png"))
        window.toggle_warning(False)
        qapp.processEvents()

        # 4. Checklist and decisions
        window.work_tabs.setCurrentIndex(1)
        qapp.processEvents()
        window.grab().save(str(out_dir / f"{w}x{h}_04_checklist_and_decisions.png"))

        # 5. Score overview
        window.work_tabs.setCurrentIndex(2)
        qapp.processEvents()
        window.grab().save(str(out_dir / f"{w}x{h}_05_score_overview.png"))

        print(f"Captured all 5 screens for {w}x{h}")

    window.close()
    print("Done generating screenshots in qa_screens/")


if __name__ == "__main__":
    main()
