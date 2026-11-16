import csv
import hashlib
import tempfile
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

    # Test 1: Splitter properties
    def test_1_reader_splitter_properties(self):
        self.assertEqual(self.window.reader_splitter.orientation(), Qt.Orientation.Horizontal)
        self.assertEqual(self.window.reader_splitter.count(), 2)
        self.assertGreaterEqual(self.window.reader_splitter.handleWidth(), 6)

    # Test 2: Vertical budget & hit list at 3 standard resolutions
    def test_2_vertical_budget_and_hit_list(self):
        self._setup_dummy_pdf(["The company reports carbon pricing and climate metrics with 50% reduction."], num_scanned=2)
        self.window.show()

        budgets = [
            (1920, 1080, 640),
            (1536, 864, 500),
            (1280, 720, 400),
        ]
        for w, h, min_pane_height in budgets:
            self.window.resize(w, h)
            self.qt.processEvents()
            # Left pane (PDF pane) height
            left_pane = self.window.reader_splitter.widget(0)
            self.assertGreaterEqual(left_pane.height(), min_pane_height,
                f"At {w}x{h}, left pane height {left_pane.height()} < required {min_pane_height}")
            # Hit list is visible and at least 120 px
            self.assertTrue(self.window.hit_list.isVisible())
            self.assertGreaterEqual(self.window.hit_list.height(), 120,
                f"At {w}x{h}, hit list height {self.window.hit_list.height()} < 120")
            # Pin button is inside window bounds
            pin_geo = self.window.pin_button.mapTo(self.window, self.window.pin_button.rect().bottomRight())
            self.assertLessEqual(pin_geo.y(), h, f"Pin button pushed below window bottom at {w}x{h}")

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

    def test_pin_uses_selected_passage_and_source_page(self):
        self._setup_dummy_pdf(["A climate risk is disclosed here"])
        self.window.extracted_text.setFocus()
        self.window.reader_tabs.setCurrentIndex(1)
        cursor = self.window.extracted_text.textCursor()
        cursor.setPosition(2)
        cursor.setPosition(14, cursor.MoveMode.KeepAnchor)
        self.window.extracted_text.setTextCursor(cursor)
        self.window.pin_hit()
        self.assertEqual(self.window.evidence.toPlainText(), "climate risk")
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
        self.assertEqual(self.window.evidence.toPlainText(), "second")

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


if __name__ == "__main__":
    unittest.main()
