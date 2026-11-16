import tempfile
import csv
import hashlib
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import app_qt
import fitz
from PySide6.QtCore import QSettings
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QApplication, QMessageBox, QTreeWidget


class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = app.DB_PATH
        app.DB_PATH = Path(self.temp.name) / "test.db"
        self.window = app_qt.Workbench()

    def tearDown(self):
        self.window.saved_form = self.window.form_state()
        self.window.close()
        self.window.store.db.close()
        app.DB_PATH = self.original_db_path
        self.temp.cleanup()

    def test_contract_and_reviewed_zero(self):
        self.assertEqual(len(self.window.items), 81)
        self.assertEqual(sum(item["weight"] for item in self.window.items if item["kind"] == "SDG"), 102)
        self.window.project_id = self.window.store.project("Test PLC", "2022")
        self.window.store.save_score(self.window.project_id, "E1", 0, "", "", "")
        self.window.refresh_totals()
        self.assertIn("Run Check for score",self.window.prediction_totals.text())
        self.assertIn("Manual confirmed: ESG 0/30, SDG 0/102",self.window.prediction_totals.text())
        self.assertEqual(self.window.reviewed_tile.value.text(), "1 / 81")
        self.assertEqual(self.window.progress.value(), 1)
        with (Path(self.temp.name)/"scores_readable.csv").open(encoding="utf-8-sig",newline="") as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["manual_score"],"0")
        self.assertEqual(rows[0]["proposed_score"],"")

    def test_work_tabs_keep_scores_readable_and_open_selected_item(self):
        self.window.project_id=self.window.store.project("Test PLC","2022")
        self.window.refresh_totals()
        self.assertEqual(self.window.work_tabs.currentIndex(),0)
        self.assertIn("Proposed ESG",self.window.review_score_strip.text())
        self.window.work_tabs.setCurrentIndex(2)
        self.assertEqual(self.window.score_tree.topLevelItemCount(),2)
        row=self.window.score_tree.topLevelItem(0).child(0).child(1)
        self.window.open_score_item(row)
        self.assertEqual(self.window.current["id"],"E2")
        self.assertEqual(self.window.work_tabs.currentIndex(),1)
        self.window.work_tabs.setCurrentIndex(0)
        self.assertEqual(self.window.work_tabs.tabText(0),"PDF reader")
        self.assertEqual(self.window.work_tabs.tabText(1),"Checklist and decisions")
        self.assertEqual(self.window.continuous_pdf.pageMode(),QPdfView.PageMode.MultiPage)

    def test_dirty_cancel_then_discard(self):
        first = self.window.current
        self.window.evidence.setPlainText("unfinished note")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            self.assertFalse(self.window.select_item(self.window.items[1]))
        self.assertIs(self.window.current, first)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            self.assertTrue(self.window.select_item(self.window.items[1]))

    def test_grouped_filter(self):
        self.window.filter.setText("SDG13")
        self.assertEqual(self.window.item_list.count(), 4)  # goal header plus 3 stages
        self.assertFalse(self.window.item_list.item(0).flags() & app_qt.Qt.ItemFlag.ItemIsSelectable)

    def test_long_warning_keeps_reading_and_decision_fields_available(self):
        self.window.resize(1100, 700)
        self.window.project_id = self.window.store.project("Test PLC", "2022")
        self.window.docs = [("annual.pdf", ["energy cost increased in 2022"])]
        self.window.refresh_center()
        self.window.doc_warning.setText("OCR warning for a long report\n" * 12)
        self.window.warning_scroll.show()
        self.window.show()
        self.qt.processEvents()
        self.assertLessEqual(self.window.warning_scroll.height(), 108)
        self.assertGreaterEqual(self.window.view_tabs.height(), 170)
        self.assertGreaterEqual(self.window.evidence.height(), 145)

    def test_reopen_and_legacy_export_blanks(self):
        project=self.window.store.project("Test PLC", "2023")
        self.window.project_id=project
        self.window.company.setCurrentText("Test PLC")
        self.window.year.setCurrentText("2023")
        self.window.store.save_score(project,"E1",0,"","","")
        self.window.store.save_score(project,"SDG1-Identified",1,"Company program","annual.pdf","4")
        second=app.Store()
        try:
            self.assertEqual(second.scores(project)["E1"][0],0)
            self.assertEqual(second.scores(project)["SDG1-Identified"][0],1)
        finally: second.db.close()
        output=Path(self.temp.name)/"scores.xlsx"
        with patch.object(app_qt.QFileDialog,"getSaveFileName",return_value=(str(output),"Excel (*.xlsx)")):
            self.window.export_excel()
        from openpyxl import load_workbook
        workbook=load_workbook(output,read_only=True,data_only=True)
        rows={row[3]:row for row in workbook["Scores"].iter_rows(min_row=2,values_only=True)}
        self.assertEqual(rows["E1"][4],0)
        self.assertEqual(rows["SDG1-Identified"][6],1)
        self.assertIsNone(rows["E2"][4])
        workbook.close()

    def test_status_chip_and_empty_state(self):
        self.assertEqual(self.window.status_chip.text(), "No workpaper")
        self.window.project_id = self.window.store.project("Test PLC", "2024")
        self.window.refresh_totals(); self.window.refresh_center()
        self.assertEqual(self.window.status_chip.text(), "Ready")
        self.assertEqual(self.window.empty_title.text(), "Import PDFs to begin")
        self.window.evidence.setPlainText("draft")
        self.assertEqual(self.window.status_chip.text(), "Unsaved edits")

    def test_check_for_score_suggests_without_saving(self):
        self.window.project_id=self.window.store.project("Test PLC","2022")
        self.window.docs=[("annual.pdf",["The company reports environmental compliance risk and a 2022 clean-up cost of PHP 10 million."])]
        original=self.window.progress_dialog; dialogs=[]; values=[]
        def record(*args):
            dialog=original(*args); dialogs.append(dialog)
            set_value=dialog.setValue
            def track(value): values.append(value); set_value(value)
            dialog.setValue=track
            return dialog
        with patch.object(self.window,"progress_dialog",side_effect=record):
            self.window.check_for_score()
        self.assertEqual(values[-1],81)
        self.assertEqual(self.window.store.scores(self.window.project_id),{})
        self.assertEqual(self.window.esg_tile.value.text(),"1 / 30")
        self.assertIn("Automated proposal",self.window.prediction_totals.text())
        self.assertFalse(self.window.review_toggle.isChecked())
        self.assertEqual(len(self.window.store.predictions(self.window.project_id)),81)
        with (Path(self.temp.name)/"scores_readable.csv").open(encoding="utf-8-sig",newline="") as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),81)
        self.assertEqual(next(row for row in rows if row["item_id"]=="E1")["proposed_score"],"1")
        self.window.search_hits()
        self.assertTrue(self.window.hit_list.item(0).text().startswith("1.  "))
        self.window.store.save_score(self.window.project_id,"E1",1,"passage","annual.pdf","1")
        with (Path(self.temp.name)/"scores_readable.csv").open(encoding="utf-8-sig",newline="") as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(next(row for row in rows if row["item_id"]=="E1")["manual_score"],"1")
        self.window.review_toggle.setChecked(True)
        self.assertIn("Proposed 1",self.window.score_hint.text())
        self.assertEqual(self.window.reviewed_tile.bar.value(),0)
        self.window.apply_prediction()
        self.assertTrue(self.window.found.isChecked())
        self.assertEqual(self.window.doc_name.text(),"annual.pdf")
        self.assertEqual(self.window.pages.text(),"1")
        self.assertEqual(self.window.store.scores(self.window.project_id)["E1"][0],1)

    def test_score_summary_groups_esg_and_sdg_items(self):
        self.window.project_id=self.window.store.project("Test PLC","2022")
        self.window.docs=[("annual.pdf",["The company reports environmental compliance risk and a 2022 clean-up cost of PHP 10 million."])]
        self.window.check_for_score()
        self.window.show_score_summary()
        tree=self.window.summary_dialog.findChild(QTreeWidget)
        self.assertEqual(tree.topLevelItemCount(),2)
        self.assertEqual(tree.topLevelItem(0).childCount(),3)
        self.assertEqual(tree.topLevelItem(0).child(0).childCount(),10)
        self.assertEqual(tree.topLevelItem(0).child(0).child(0).text(1),"1/1")
        self.assertEqual(tree.topLevelItem(1).childCount(),17)
        self.window.summary_dialog.close()

    def test_pdf_import_shows_page_progress(self):
        pdf_path=Path(self.temp.name)/"annual_FY2022.pdf"
        document=fitz.open(); document.new_page(); document.new_page(); document.save(pdf_path); document.close()
        self.window.project_id=self.window.store.project("Test PLC","2022")
        original=self.window.progress_dialog; dialogs=[]; values=[]
        def record(*args):
            dialog=original(*args); dialogs.append(dialog)
            set_value=dialog.setValue
            def track(value): values.append(value); set_value(value)
            dialog.setValue=track
            return dialog
        with patch.object(app_qt.QFileDialog,"getOpenFileNames",return_value=([str(pdf_path)],"PDF files (*.pdf)")), \
             patch.object(self.window,"progress_dialog",side_effect=record), \
             patch.object(QMessageBox,"warning"):
            self.window.import_pdfs()
        self.assertEqual(dialogs[0].maximum(),2)
        self.assertEqual(values[-1],2)
        self.assertEqual(len(self.window.store.reports(self.window.project_id)),1)

    def test_cancel_import_keeps_partial_pdf_out_of_store(self):
        pdf_path=Path(self.temp.name)/"annual_FY2022.pdf"
        document=fitz.open(); document.new_page(); document.new_page(); document.save(pdf_path); document.close()
        self.window.project_id=self.window.store.project("Test PLC","2022")
        original=self.window.progress_dialog
        def cancel_after_one(*args):
            dialog=original(*args); set_value=dialog.setValue
            def track(value):
                set_value(value)
                if value==1: dialog.cancel()
            dialog.setValue=track
            return dialog
        with patch.object(app_qt.QFileDialog,"getOpenFileNames",return_value=([str(pdf_path)],"PDF files (*.pdf)")), \
             patch.object(self.window,"progress_dialog",side_effect=cancel_after_one):
            self.window.import_pdfs()
        self.assertEqual(self.window.store.reports(self.window.project_id),[])

    def test_cancel_scoring_preserves_saved_proposals(self):
        self.window.project_id=self.window.store.project("Test PLC","2022")
        self.window.docs=[("annual.pdf",["environmental compliance risk and cost PHP 10 million"])]
        self.window.check_for_score()
        previous=self.window.store.predictions(self.window.project_id)
        original=self.window.progress_dialog
        def cancel_after_one(*args):
            dialog=original(*args); set_value=dialog.setValue
            def track(value):
                set_value(value)
                if value==1: dialog.cancel()
            dialog.setValue=track
            return dialog
        with patch.object(self.window,"progress_dialog",side_effect=cancel_after_one):
            self.window.check_for_score()
        self.assertEqual(self.window.store.predictions(self.window.project_id),previous)

    def test_prediction_skips_other_fiscal_year_reports(self):
        self.window.project_id=self.window.store.project("Test PLC","2022")
        self.window.year.setCurrentText("2022")
        self.window.docs=[("annual_FY2022.pdf",["Unrelated text"]),
                          ("annual_FY2023.pdf",["The company reports environmental compliance risk and a 2023 clean-up cost of PHP 10 million."])]
        self.window.check_for_score()
        self.assertEqual(self.window.suggestions["E1"]["suggestion"],0)
        self.assertIn("1 other-year PDF",self.window.prediction_totals.text())

    def test_saved_prediction_reopens_for_company_year(self):
        pdf_path=Path(self.temp.name)/"annual_FY2022.pdf"
        document=fitz.open(); page=document.new_page()
        page.insert_text((50,50),"The company reports environmental compliance risk and a clean-up cost of PHP 10 million.")
        document.save(pdf_path); document.close()
        project=self.window.store.project("Test PLC","2022")
        self.window.store.add_report(project,pdf_path,hashlib.sha256(pdf_path.read_bytes()).hexdigest(),1,0)
        self.window.project_id=project
        self.window.company.addItem("Test PLC"); self.window.company.setCurrentText("Test PLC")
        self.window.year.setCurrentText("2022")
        self.window.after_open("Test PLC","2022")
        self.window.check_for_score()
        self.assertEqual(self.window.esg_tile.value.text(),"1 / 30")
        self.window.after_open("Test PLC","2022")
        self.assertEqual(self.window.esg_tile.value.text(),"1 / 30")
        self.assertEqual(len(self.window.suggestions),81)
        self.assertFalse(self.window.review_toggle.isChecked())

    def test_cached_ocr_text_becomes_searchable_and_invalidates_proposals(self):
        pdf_path=Path(self.temp.name)/"scan_FY2022.pdf"
        document=fitz.open(); document.new_page(); document.save(pdf_path); document.close()
        project=self.window.store.project("Test PLC","2022")
        digest=hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        self.window.store.add_report(project,pdf_path,digest,1,1)
        self.window.project_id=project; self.window.active_company="Test PLC"; self.window.active_year="2022"
        self.window.load_reports()
        self.assertEqual(len(self.window.ocr_tasks),1)
        self.assertEqual(self.window.hits,[])
        self.assertEqual(self.window.store.save_ocr_pages(project,[(str(pdf_path),digest,1,
            "The company reports environmental compliance risk and a clean-up cost of PHP 10 million.")]),1)
        self.window.load_reports()
        self.assertEqual(self.window.ocr_tasks,[])
        self.assertTrue(self.window.hits)
        self.assertIn("environmental compliance risk",self.window.docs[0][1][0])
        self.window.store.add_report(project,pdf_path,"different hash",1,1)
        self.assertEqual(self.window.store.ocr_text(project,pdf_path,"different hash"),{})

    def test_scanned_pdf_opens_before_ocr_and_warning_collapses(self):
        pdf_path=Path(self.temp.name)/"scan_FY2022.pdf"
        document=fitz.open(); document.new_page(); document.new_page(); document.save(pdf_path); document.close()
        project=self.window.store.project("Test PLC","2022")
        digest=hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        self.window.store.add_report(project,pdf_path,digest,2,2)
        self.window.project_id=project; self.window.active_company="Test PLC"; self.window.active_year="2022"
        self.window.settings=QSettings(str(Path(self.temp.name)/"viewer.ini"),QSettings.Format.IniFormat)
        self.window.load_reports(); self.window.show(); self.qt.processEvents()
        self.assertEqual(self.window.view_tabs.tabText(0),"All PDF pages")
        self.assertEqual(self.window.pdf_model.pageCount(),2)
        self.assertEqual(self.window.view_tabs.currentIndex(),0)
        self.assertEqual(self.window.page_target,(pdf_path.name,1))
        self.window.view_tabs.setCurrentIndex(1)
        self.assertFalse(self.window.page_image.pixmap().isNull())
        self.window.view_tabs.setCurrentIndex(0)
        self.assertIn("No extractable text",self.window.page_status.text())
        self.window.warning_toggle.setChecked(False); self.qt.processEvents()
        self.assertTrue(self.window.warning_details.isHidden())
        self.assertIn("2 page(s) need OCR",self.window.ocr_summary.text())
        self.window.warning_toggle.setChecked(True); self.qt.processEvents()
        self.assertLessEqual(self.window.warning_scroll.height(),96)
        self.assertTrue(self.window.settings.value("ocr_warning_expanded",type=bool))
        self.window.page_number.setValue(2); self.window.jump_to_page()
        self.assertEqual(self.window.page_target,(pdf_path.name,2))
        self.window.reader_tabs.setCurrentIndex(1)
        self.assertEqual(self.window.extracted_text.toPlainText(),"")
        self.window.set_zoom_mode("page")
        self.assertIn("%",self.window.page_label.text())

    def test_ocr_button_recovers_scanned_page_for_prediction(self):
        pdf_path=Path(self.temp.name)/"scan_FY2022.pdf"
        source=fitz.open(); page=source.new_page()
        page.insert_text((72,100),"ENVIRONMENTAL COMPLIANCE RISK",fontsize=22)
        page.insert_text((72,150),"COST PHP 10 MILLION",fontsize=22)
        image=page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes("png")
        scanned=fitz.open(); target=scanned.new_page(width=page.rect.width,height=page.rect.height)
        target.insert_image(target.rect,stream=image)
        scanned.save(pdf_path); scanned.close(); source.close()
        project=self.window.store.project("Test PLC","2022")
        digest=hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        self.window.store.add_report(project,pdf_path,digest,1,1)
        self.window.project_id=project; self.window.active_company="Test PLC"; self.window.active_year="2022"
        self.window.company.addItem("Test PLC"); self.window.company.setCurrentText("Test PLC")
        self.window.load_reports()
        self.assertEqual(len(self.window.ocr_tasks),1)
        with patch.object(QMessageBox,"warning") as warning:
            self.window.start_ocr()
            self.window.warning_toggle.setChecked(False)
            deadline=time.monotonic()+20
            while self.window.ocr_running and time.monotonic()<deadline:
                self.qt.processEvents(); time.sleep(.01)
            self.qt.processEvents()
        self.assertFalse(self.window.ocr_running)
        warning.assert_not_called()
        self.assertEqual(self.window.ocr_tasks,[])
        self.assertIn((pdf_path.name,1),self.window.ocr_page_refs)
        self.window.check_for_score()
        self.assertEqual(self.window.suggestions["E1"]["suggestion"],1)
        self.window.search_hits(); self.window.show_hit(0)
        self.assertIn("highlighted match(es)",self.window.page_label.text())
        self.assertNotIn("0 highlighted match(es)",self.window.page_label.text())

    def test_selective_ocr_only_processes_requested_page(self):
        pdf_path=Path(self.temp.name)/"scan_FY2022.pdf"
        source=fitz.open(); page=source.new_page()
        page.insert_text((72,100),"ENVIRONMENTAL COMPLIANCE RISK",fontsize=22)
        image=page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes("png")
        scanned=fitz.open()
        for _ in range(2):
            target=scanned.new_page(width=page.rect.width,height=page.rect.height)
            target.insert_image(target.rect,stream=image)
        scanned.save(pdf_path); scanned.close(); source.close()
        project=self.window.store.project("Test PLC","2022")
        digest=hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        self.window.store.add_report(project,pdf_path,digest,2,2)
        self.window.project_id=project; self.window.active_company="Test PLC"; self.window.active_year="2022"
        self.window.load_reports()
        self.window.page_target=(pdf_path.name,1)
        with patch.object(QMessageBox,"warning") as warning:
            self.window.start_ocr("current")
            deadline=time.monotonic()+20
            while self.window.ocr_running and time.monotonic()<deadline:
                self.qt.processEvents(); time.sleep(.01)
            self.qt.processEvents()
        warning.assert_not_called()
        self.assertEqual(self.window.ocr_tasks[0][2],[2])
        self.assertEqual(set(self.window.store.ocr_text(project,pdf_path,digest)),{1})

    def test_changed_year_requires_opening_new_workpaper(self):
        self.window.project_id=self.window.store.project("Test PLC","2022")
        self.window.active_company="Test PLC"; self.window.active_year="2022"
        self.window.docs=[("annual_FY2022.pdf",["environmental compliance risk and cost 10 million"])]
        self.window.year.setCurrentText("2023")
        with patch.object(QMessageBox,"warning") as warning:
            self.window.check_for_score()
        warning.assert_called_once()
        self.assertEqual(self.window.store.predictions(self.window.project_id),{})

    def test_delete_project_removes_related_rows(self):
        store=self.window.store
        project=store.project("Test PLC","2022")
        store.save_score(project,"E1",1,"excerpt","annual.pdf","1")
        store.add_report(project,Path(self.temp.name)/"annual.pdf","abc",1,0)
        store.delete_project(project)
        self.assertEqual(store.projects(),[])
        for table in ("reports","scores","audit_log"):
            self.assertEqual(store.db.execute(f"SELECT count(*) FROM {table} WHERE project_id=?",(project,)).fetchone()[0],0)

    def test_supported_requires_evidence_and_prerequisite(self):
        self.window.project_id = self.window.store.project("Test PLC", "2024")
        self.window.select_item(self.window.items[0])
        self.window.found.setChecked(True)
        self.assertFalse(self.window.save_button.isEnabled())
        self.window.doc_name.setText("a.pdf"); self.window.pages.setText("3"); self.window.evidence.setPlainText("text")
        self.assertTrue(self.window.save_button.isEnabled())
        self.window.saved_form = self.window.form_state()
        managed = next(i for i in self.window.items if i["id"] == "SDG1-Managed")
        self.window.select_item(managed)
        self.assertFalse(self.window.found.isEnabled())

    def test_cascade_clears_dependents_with_audit(self):
        store = self.window.store
        project = self.window.project_id = store.project("Test PLC", "2024")
        for stage in ("Identified", "Managed"):
            store.save_score(project, f"SDG1-{stage}", 1, "x", "a.pdf", "1")
        self.window.select_item(next(i for i in self.window.items if i["id"] == "SDG1-Identified"))
        self.window.absent.setChecked(True)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.assertTrue(self.window.save())
        self.assertEqual(store.scores(project)["SDG1-Managed"][0], 0)
        n = store.db.execute("SELECT COUNT(*) FROM audit_log WHERE item_id='SDG1-Managed'").fetchone()[0]
        self.assertEqual(n, 3 - 1)  # initial save + cascade


if __name__ == "__main__":
    unittest.main()
