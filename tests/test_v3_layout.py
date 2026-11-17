import csv
import hashlib
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
from PySide6.QtCore import Qt, QSettings, QByteArray
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QApplication

import app
import app_qt


class V3LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = app.DB_PATH
        app.DB_PATH = Path(self.temp.name) / "test_v3.db"
        self.window = app_qt.Workbench()

    def tearDown(self):
        self.window.saved_form = self.window.form_state()
        self.window.close()
        self.window.store.db.close()
        app.DB_PATH = self.original_db_path
        self.temp.cleanup()

    def _setup_dummy_pdf(self, pages_text=None, num_scanned=0):
        if pages_text is None:
            pages_text = ["Normal page text content"]
        pdf_path = Path(self.temp.name) / "test_doc_FY2022.pdf"
        doc = fitz.open()
        for t in pages_text:
            p = doc.new_page()
            if t:
                p.insert_text((50, 50), t)
        for _ in range(num_scanned):
            doc.new_page()
        doc.save(pdf_path)
        doc.close()
        project = self.window.store.project("Test PLC", "2022")
        digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        self.window.store.add_report(project, pdf_path, digest, len(pages_text) + num_scanned, num_scanned)
        self.window.project_id = project
        self.window.active_company = "Test PLC"
        self.window.active_year = "2022"
        self.window.company.addItem("Test PLC")
        self.window.company.setCurrentText("Test PLC")
        self.window.load_reports()
        return pdf_path

    def _wait_background(self):
        deadline = time.monotonic() + 20
        while self.window.busy and time.monotonic() < deadline:
            self.qt.processEvents(); time.sleep(0.01)
        self.qt.processEvents()
        self.assertFalse(self.window.busy)

    def test_background_import_and_leads_keep_reader_available(self):
        project = self.window.store.project("Test PLC", "2022")
        self.window.project_id = project
        self.window.active_company = "Test PLC"; self.window.active_year = "2022"
        self.window.company.addItem("Test PLC"); self.window.company.setCurrentText("Test PLC")
        path = Path(self.temp.name) / "annual_FY2022.pdf"
        pdf = fitz.open(); page = pdf.new_page()
        page.insert_text((50, 50), "Our environmental compliance risk cost PHP 10 million.")
        pdf.save(path); pdf.close()
        with patch.object(app_qt.QFileDialog, "getOpenFileNames", return_value=([str(path)], "")):
            self.window.import_pdfs_background()
        self.assertTrue(self.window.busy)
        self.assertTrue(self.window.task_cancel.isVisibleTo(self.window) or not self.window.isVisible())
        self._wait_background()
        self.assertEqual(len(self.window.docs), 1)
        self.window.find_leads_background()
        self.assertTrue(self.window.busy)
        self._wait_background()
        self.assertEqual(self.window.suggestions["E1"]["suggestion"], 1)

    # Test 1: Splitter properties
    def test_1_reader_splitter_properties(self):
        self.assertEqual(self.window.reader_splitter.orientation(), Qt.Orientation.Horizontal)
        self.assertEqual(self.window.reader_splitter.count(), 2)
        self.assertGreaterEqual(self.window.reader_splitter.handleWidth(), 6)

    # Test 2: Vertical budget & hit list at 3 standard resolutions
    def test_2_vertical_budget_and_hit_list(self):
        self._setup_dummy_pdf(["The company reports carbon pricing and climate metrics with 50% reduction."], num_scanned=2)
        self.window.show()

        budgets = [(1920, 1080), (1536, 864), (1280, 720)]
        for w, h in budgets:
            self.window.resize(w, h)
            self.qt.processEvents()
            # Left pane (PDF pane) height
            left_pane = self.window.reader_splitter.widget(0)
            # Qt may clamp requested dimensions to the actual display geometry.
            min_pane_height = max(280, int(self.window.height() * 0.45))
            self.assertGreaterEqual(left_pane.height(), min_pane_height,
                f"At {self.window.width()}x{self.window.height()}, left pane height {left_pane.height()} < required {min_pane_height}")
            # Hit list is visible and at least 120 px
            self.assertTrue(self.window.hit_list.isVisible())
            self.assertGreaterEqual(self.window.hit_list.height(), 120,
                f"At {w}x{h}, hit list height {self.window.hit_list.height()} < 120")
            # Pin button is inside window bounds
            pin_geo = self.window.pin_button.mapTo(self.window, self.window.pin_button.rect().bottomRight())
            self.assertLessEqual(pin_geo.y(), self.window.height(), f"Pin button pushed below window bottom at {w}x{h}")

    def test_compact_logical_size_for_1366_by_768_at_150_percent(self):
        self._setup_dummy_pdf(["climate risk on this page"])
        self.window.show(); self.window.resize(911, 512); self.qt.processEvents()
        self.assertLessEqual(self.window.minimumWidth(), 911)
        self.assertLessEqual(self.window.minimumHeight(), 512)
        self.assertLessEqual(sum(self.window.reader_splitter.sizes()), self.window.width())
        self.assertTrue(self.window.work_tabs.isVisible())
        pin_bottom = self.window.pin_button.mapTo(self.window, self.window.pin_button.rect().bottomRight())
        self.assertLessEqual(pin_bottom.y(), self.window.height())

    # Test 3: Opening OCR details popup does NOT change PDF view size
    def test_3_ocr_popup_does_not_resize_pdf_view(self):
        self._setup_dummy_pdf(["Some text"], num_scanned=3)
        self.window.show()
        self.qt.processEvents()
        size_before = self.window.continuous_pdf.size()
        self.window.toggle_warning(True)
        self.qt.processEvents()
        size_after = self.window.continuous_pdf.size()
        self.assertEqual(size_before, size_after)
        self.assertFalse(self.window.warning_popup.isHidden())
        self.window.toggle_warning(False)
        self.qt.processEvents()
        self.assertTrue(self.window.warning_popup.isHidden())

    # Test 4: Tab/button texts contain no mnemonic artefacts
    def test_4_no_mnemonic_artefacts(self):
        tab_text = self.window.work_tabs.tabText(1)
        self.assertEqual(tab_text, "Checklist and decisions")
        self.assertNotIn("&", tab_text)
        self.assertNotIn("_", tab_text)
        btn_text = self.window.focus_button.text()
        self.assertNotIn("&", btn_text)
        self.assertNotIn("_", btn_text)
        self.assertEqual(self.window.work_menu_button.text(), "Workpaper ▾")

    # Test 5: Status bar message cleared, spinbox and viewer in sync
    def test_5_status_bar_and_navigation_agreement(self):
        pdf_path = self._setup_dummy_pdf(["Page one text", "Page two text", "Page three text"], num_scanned=2)
        self.window.show()
        self.qt.processEvents()

        # Status bar does not say "Rendering"
        self.assertNotIn("Rendering", self.window.statusBar().currentMessage())

        # step_page next
        self.window.step_page(1)
        self.qt.processEvents()
        self.assertEqual(self.window.page_target[1], 2)
        self.assertEqual(self.window.page_number.value(), 2)
        self.assertEqual(self.window.continuous_pdf.pageNavigator().currentPage() + 1, 2)

        # jump_to_page
        self.window.page_number.setValue(3)
        self.window.jump_to_page()
        self.qt.processEvents()
        self.assertEqual(self.window.page_target[1], 3)
        self.assertEqual(self.window.page_number.value(), 3)
        self.assertEqual(self.window.continuous_pdf.pageNavigator().currentPage() + 1, 3)

        # review_missing_pages jumps to first missing page (page 4)
        self.window.review_missing_pages()
        self.qt.processEvents()
        self.assertEqual(self.window.page_target[1], 4)
        self.assertEqual(self.window.page_number.value(), 4)
        self.assertEqual(self.window.continuous_pdf.pageNavigator().currentPage() + 1, 4)

    # Test 6: Zoom controls in both modes and footer percentage
    def test_6_zoom_controls_and_footer_percentage(self):
        self._setup_dummy_pdf(["Sample page for zoom"], num_scanned=0)
        self.window.show()
        self.qt.processEvents()

        # Mode 0: All PDF pages
        self.window.view_tabs.setCurrentIndex(0)
        initial_zoom = self.window.continuous_pdf.zoomFactor()
        self.window.change_zoom(1.25)
        self.assertAlmostEqual(self.window.continuous_pdf.zoomFactor(), initial_zoom * 1.25, delta=0.05)
        footer = self.window.page_label.text()
        expected_pct = f"{round(self.window.continuous_pdf.zoomFactor() * 100)}%"
        self.assertIn(expected_pct, footer)

        # Mode 1: Highlighted page
        self.window.view_tabs.setCurrentIndex(1)
        self.window.render_page()
        self.window.change_zoom(1.25)
        self.assertIn("%", self.window.page_label.text())

    # Test 7: Switching to All PDF pages does not trigger PyMuPDF pixmap render
    def test_7_switching_to_all_pages_does_not_render_highlight(self):
        self._setup_dummy_pdf(["Sample page text"], num_scanned=0)
        self.window.show()
        self.qt.processEvents()

        # Highlighted page renders on tab 1
        self.window.view_tabs.setCurrentIndex(1)
        self.qt.processEvents()

        # Switch to Tab 0: must not render pixmap
        with patch.object(fitz.Page, "get_pixmap") as mock_pixmap:
            self.window.view_tabs.setCurrentIndex(0)
            self.qt.processEvents()
            mock_pixmap.assert_not_called()

    # Test 8: Corrupt / old saved splitter state resilience
    def test_8_corrupt_splitter_state_resilience(self):
        # Save corrupt state
        self.window.settings.setValue("reader_splitter_v2", QByteArray(b"garbage_invalid_state"))
        self.window.load_reports()
        sizes = self.window.reader_splitter.sizes()
        self.assertEqual(len(sizes), 2)
        self.assertGreaterEqual(sizes[0], 300)
        self.assertGreaterEqual(sizes[1], 200)

    # Test 9: Very long doc name and long keywords do not overflow
    def test_9_long_document_and_keywords_do_not_overflow(self):
        long_name = "VERY_LONG_COMPANY_SUSTAINABILITY_ANNUAL_FINANCIAL_GOVERNANCE_REPORT_EXPANDED_2022_" + ("X" * 120) + ".pdf"
        pdf_path = Path(self.temp.name) / long_name
        doc = fitz.open(); doc.new_page(); doc.save(pdf_path); doc.close()
        project = self.window.store.project("Test PLC", "2022")
        digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        self.window.store.add_report(project, pdf_path, digest, 1, 0)
        self.window.project_id = project
        self.window.active_company = "Test PLC"; self.window.active_year = "2022"
        self.window.load_reports()

        # Inject long keywords
        item = dict(self.window.items[0])
        item["keywords"] = [f"very_long_keyword_string_term_{i}" for i in range(40)]
        self.window.select_item(item)
        self.window.resize(1280, 720)
        self.window.show()
        self.qt.processEvents()

        # Splitter widths should not blow up beyond window width
        sizes = self.window.reader_splitter.sizes()
        self.assertLessEqual(sizes[0] + sizes[1], self.window.width())

    def test_pdf_search_navigates_and_highlights_extracted_match(self):
        self._setup_dummy_pdf(["First page", "A climate risk is disclosed here", "Another climate risk"])
        self.window.pdf_search.setText("climate risk")
        self.window.find_pdf_text(1)
        self.assertEqual(self.window.page_target[1], 2)
        self.assertEqual(self.window.extracted_text.textCursor().selectedText(), "climate risk")
        self.assertIn("1 / 2", self.window.pdf_search_count.text())
        self.window.find_pdf_text(1)
        self.assertEqual(self.window.page_target[1], 3)
        self.assertIn("2 / 2", self.window.pdf_search_count.text())

    def test_shared_find_bar_filters_checklist_and_searches_all_pdfs(self):
        self._setup_dummy_pdf(["One report has climate risk"])
        other = Path(self.temp.name) / "other_FY2022.pdf"
        pdf = fitz.open(); pdf.new_page().insert_text((50, 50), "Second report has climate risk")
        pdf.save(other); pdf.close()
        digest = hashlib.sha256(other.read_bytes()).hexdigest()
        self.window.store.add_report(self.window.project_id, other, digest, 1, 0)
        self.window.load_reports()
        self.window.find_scope.setCurrentText("All PDFs")
        self.window.pdf_search.setText("climate risk")
        self.window.find_pdf_text(1)
        self.assertIn("1 / 2", self.window.pdf_search_count.text())
        self.window.find_pdf_text(1)
        self.assertIn("2 / 2", self.window.pdf_search_count.text())
        self.window.find_scope.setCurrentText("Checklist")
        self.window.pdf_search.setText("E1")
        self.window.find_pdf_text(1)
        self.assertEqual(self.window.work_tabs.currentIndex(), 1)
        self.assertEqual(self.window.filter.text(), "E1")

    def test_pin_uses_selected_passage_and_source_page(self):
        self._setup_dummy_pdf(["A climate risk is disclosed here"])
        self.window.extracted_text.setFocus()
        self.window.reader_tabs.setCurrentIndex(1)
        cursor = self.window.extracted_text.textCursor()
        cursor.setPosition(2)
        cursor.setPosition(14, cursor.MoveMode.KeepAnchor)
        self.window.extracted_text.setTextCursor(cursor)
        self.window.pin_hit()
        self.assertEqual(self.window.evidence.toPlainText(), "")
        self.assertEqual(self.window.decision_pins.count(), 1)
        self.assertEqual(self.window.store.evidence_pins(self.window.project_id, "E1")[0]["excerpt"], "climate risk")
        self.assertEqual(self.window.pages.text(), "1")

    def test_pin_extracted_selection_uses_current_page_with_stale_hit(self):
        self._setup_dummy_pdf(["climate risk first", "climate risk second"])
        self.window.select_item(next(item for item in self.window.items if item["id"] == "E4"))
        self.window.hit_list.setCurrentRow(0)
        self.window.page_target = (self.window.docs[0][0], 2)
        self.window.render_page()
        self.window.reader_tabs.setCurrentIndex(1)
        cursor = self.window.extracted_text.textCursor()
        cursor.setPosition(13)
        cursor.setPosition(19, cursor.MoveMode.KeepAnchor)
        self.window.extracted_text.setTextCursor(cursor)
        self.window.pin_hit()
        self.assertEqual(self.window.pages.text(), "2")
        self.assertEqual(self.window.decision_pins.count(), 1)
        self.assertEqual(self.window.store.evidence_pins(self.window.project_id, "E4")[0]["excerpt"], "second")

    def test_multiple_pins_follow_score_category_across_pdfs_and_pages(self):
        first = self._setup_dummy_pdf(["first climate risk passage", "next climate risk passage"])
        second = Path(self.temp.name) / "second_FY2022.pdf"
        pdf = fitz.open(); pdf.new_page().insert_text((50, 50), "other climate risk passage")
        pdf.save(second); pdf.close()
        digest = hashlib.sha256(second.read_bytes()).hexdigest()
        self.window.store.add_report(self.window.project_id, second, digest, 1, 0)
        self.window.load_reports()
        self.window.select_item(next(item for item in self.window.items if item["id"] == "E4"))
        self.window.reader_tabs.setCurrentIndex(1)
        for name, page, passage in ((first.name, 2, "next climate risk"),
                                    (second.name, 1, "other climate risk")):
            self.window.page_target = (name, page)
            self.window.render_page()
            text = self.window.extracted_text.toPlainText()
            self.assertIn(passage, text, f"{name} PDF page {page}: {text!r}")
            start = text.index(passage)
            cursor = self.window.extracted_text.textCursor()
            cursor.setPosition(start); cursor.setPosition(start + len(passage), cursor.MoveMode.KeepAnchor)
            self.window.extracted_text.setTextCursor(cursor)
            self.window.pin_hit()
        self.assertEqual(self.window.current["id"], "E4")
        self.assertEqual(self.window.decision_pins.count(), 2)
        self.assertEqual(self.window.reader_pins.count(), 2)
        self.assertEqual({pin["document"] for pin in self.window.store.evidence_pins(self.window.project_id, "E4")},
                         {first.name, second.name})
        self.window.found.setChecked(True)
        self.assertTrue(self.window.save())
        self.assertIsNone(self.window.store.score_records(self.window.project_id)["E4"]["evidence"])
        self.window.select_item(self.window.items[0])
        self.window.select_item(next(item for item in self.window.items if item["id"] == "E4"))
        self.assertEqual(self.window.decision_pins.count(), 2)
        self.assertEqual(self.window.evidence.toPlainText(), "")
        self.window.decision_pins.setCurrentRow(0)
        self.window.remove_selected_pin()
        self.assertEqual(self.window.decision_pins.count(), 1)
        self.assertEqual(self.window.store.scores(self.window.project_id)["E4"][0], 1)

    def test_ocr_completion_recalculates_saved_proposals(self):
        path = self._setup_dummy_pdf([""], num_scanned=0)
        self.window.suggestions = {item["id"]: {"suggestion": 0, "confidence": "low", "hits": []} for item in self.window.items}
        self.window.ocr_project_id = self.window.project_id
        self.window.ocr_worker = None
        self.window.ocr_completed([(str(path), hashlib.sha256(path.read_bytes()).hexdigest(), 1,
                                    "climate risk policy 25 percent")], [])
        self.assertIn("climate risk", self.window.docs[0][1][0])
        self.assertTrue(self.window.suggestions["E4"]["hits"])

    def test_all_sdg_goals_use_one_two_three_weighted_points(self):
        project = self.window.project_id = self.window.store.project("Test PLC", "2022")
        for number in range(1, 18):
            for stage in ("Identified", "Managed", "Reported"):
                self.window.store.save_score(project, f"SDG{number}-{stage}", 1, "Evidence", "report.pdf", "1")
        self.window.refresh_totals()
        self.assertIn("SDG 102/102", self.window.prediction_totals.text())
        self.window.select_item(next(item for item in self.window.items if item["id"] == "SDG9-Reported"))
        self.assertIn("6 / 6", self.window.stage_total.text())

    def test_selecting_company_opens_workpaper_without_open_button(self):
        self.window.companies.append("Test PLC")
        self.window.company.addItem("Test PLC")
        self.assertEqual(self.window.year.currentText(), "Choose fiscal year")
        self.window.company.setCurrentText("Test PLC")
        self.window.company.activated.emit(self.window.company.currentIndex())
        self.assertIsNone(self.window.project_id)
        self.window.year.setCurrentText("2022")
        self.window.year.activated.emit(self.window.year.currentIndex())
        self.assertEqual(self.window.active_company, "Test PLC")
        self.assertEqual(self.window.active_year, "2022")

    def test_workpaper_help_popup_and_button_tips(self):
        help_button = next(button for button in self.window.findChildren(app_qt.QPushButton)
                           if button.text() == "? Help")
        help_button.click()
        self.assertTrue(self.window.help_dialog.isVisible())
        self.assertIn("reports folder", self.window.help_dialog.windowTitle().lower() + " " +
                      self.window.help_dialog.findChild(app_qt.QListWidget).item(3).text().lower())
        self.assertIn("actions", self.window.work_menu_button.toolTip())
        menu = self.window.work_menu_button.menu()
        for action in menu.actions():
            if action.text():
                self.assertTrue(action.toolTip(), action.text())
        self.window.help_dialog.close()
        next(action for action in menu.actions() if action.text() == "Help for these actions").trigger()
        self.assertTrue(self.window.help_dialog.isVisible())
        for button in self.window.findChildren(app_qt.QPushButton):
            self.assertTrue(button.toolTip(), button.text())

    def test_credits_page_contains_only_name(self):
        index = next(index for index in range(self.window.work_tabs.count())
                     if self.window.work_tabs.tabText(index) == "Credits")
        page = self.window.work_tabs.widget(index)
        self.assertEqual([label.text() for label in page.findChildren(app_qt.QLabel)], ["Jargon"])

    def test_one_general_spreadsheet_export_control(self):
        buttons = [button.text() for button in self.window.controls_panel.findChildren(app_qt.QPushButton)]
        self.assertEqual(buttons.count("Export sheets"), 1)
        actions = [action.text() for action in self.window.work_menu_button.menu().actions()]
        self.assertIn("Export sheets", actions)
        self.assertNotIn("Export Excel", actions)
        self.assertNotIn("Export for master workbook", actions)
        output = Path(self.temp.name) / "general.xlsx"
        with patch.object(app_qt.QFileDialog, "getSaveFileName", return_value=(str(output), "Excel (*.xlsx)")):
            self.window.export_sheets()
        self.assertTrue(output.exists())
        with output.open("rb") as stream:
            self.assertEqual(stream.read(2), b"PK")


if __name__ == "__main__":
    unittest.main()
