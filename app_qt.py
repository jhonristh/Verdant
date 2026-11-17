"""Qt review workbench for the ESG/SDG disclosure scorer."""
import hashlib
import re
import shutil
import sys
from collections import OrderedDict
from html import escape
from pathlib import Path

import pymupdf as fitz
from PySide6.QtCore import Qt, QSettings, QThread, Signal, QPoint, QPointF, QBuffer, QIODevice
from PySide6.QtGui import QAction, QColor, QFont, QImage, QKeySequence, QIcon, QPainter, QPen, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QDialog, QInputDialog, QMessageBox, QPushButton, QProgressBar, QProgressDialog, QRadioButton, QScrollArea, QSplitter,
    QSpinBox, QStackedWidget, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QSizePolicy, QMenu, QToolButton, QAbstractSpinBox)

from app import Store, RUBRIC, DATA_DIR, keyword_pattern, load_companies
from verdant.config import RESOURCES_DIR
from scoring_assist import assess_all
from ocr_support import extract_missing_pages, find_tessdata, parse_page_numbers
from pdf_highlights import keyword_rects
from verdant.services.master_export import export_master_workbook
from verdant.services.template_export import export_general_workbook
from verdant.domain.rubric import build_items
from verdant.services.workpaper_transfer import export_workpaper, import_workpaper


STYLE = """
QMainWindow, QWidget { background:#101a17; color:#edf4ef; font-family:'Segoe UI'; font-size:14px; }
QLabel, QRadioButton, QCheckBox { background:transparent; }
QFrame#panel { background:#17231e; border:1px solid #30473b; border-radius:12px; }
QFrame#brandBar { background:#132b20; border:1px solid #305641; border-radius:10px; max-height:56px; }
QFrame#tile { background:#17231e; border:1px solid #30473b; border-radius:12px; }
QFrame#inset { background:#1d2b23; border:1px solid #30473b; border-radius:8px; }
QFrame#rule { background:#30473b; max-height:1px; min-height:1px; border:0; }
QFrame#vrule { background:#30473b; max-width:1px; min-width:1px; border:0; margin:3px 4px; }
QLabel#muted { color:#a9bbb0; }
QLabel#brand { font-size:20px; font-weight:700; color:#f2fbf5; }
QLabel#heading { font-size:18px; font-weight:700; }
QLabel#paneTitle { font-size:15px; font-weight:700; color:#f2fbf5; }
QLabel#section { color:#a9bbb0; font-size:12px; font-weight:700; letter-spacing:1px; }
QLabel#tileLabel { color:#a9bbb0; font-size:12px; font-weight:600; }
QLabel#tileValue { color:#f2fbf5; font-size:24px; font-weight:700; }
QLabel#tileNote { color:#a9bbb0; font-size:12px; }
QLabel#perspective { background:#1d2b23; border:1px solid #3c5847; border-radius:10px; padding:3px 10px; color:#cfe6d8; font-size:12px; font-weight:600; }
QLabel#warn { background:#3a2f12; border:1px solid #8a6d1f; border-radius:8px; padding:8px 10px; color:#f3d38a; }
QFrame#ocrWarning { background:#302811; border:1px solid #806823; border-radius:8px; }
QFrame#ocrDetailsPopup { background:#17241e; border:1px solid #507860; border-radius:8px; }
QLabel#hint { color:#f3d38a; font-size:12px; }
QLabel#prediction { background:#203b2b; border:1px solid #4e9a67; border-radius:8px; padding:10px; color:#f2fbf5; font-size:14px; }
QLabel#empty { color:#a9bbb0; font-size:16px; }
QLabel#chip { border-radius:12px; padding:4px 14px; font-weight:700; font-size:12px; }
QLabel#chip[state="none"] { background:#26332c; color:#a9bbb0; border:1px solid #3c5847; }
QLabel#chip[state="ready"] { background:#183a29; color:#8fe0b0; border:1px solid #2f7a52; }
QLabel#chip[state="dirty"] { background:#3a2f12; color:#f3d38a; border:1px solid #8a6d1f; }
QLabel#chip[state="progress"] { background:#1b3550; color:#9fcdf5; border:1px solid #3a6f9f; }
QLabel#chip[state="complete"] { background:#245d42; color:#e9fbef; border:1px solid #50b879; }
QLineEdit, QComboBox, QTextEdit, QListWidget, QSpinBox { background:#1d2b23; color:#edf4ef; border:1px solid #3c5847; border-radius:8px; padding:6px 8px; selection-background-color:#245d42; }
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus, QSpinBox:focus { border:2px solid #7fd4a2; }
QComboBox { min-height:24px; }
QComboBox QAbstractItemView { background:#1d2b23; color:#edf4ef; selection-background-color:#245d42; }
QPushButton { background:#26382e; color:#edf4ef; border:1px solid #42634d; border-radius:8px; padding:7px 13px; font-weight:600; }
QPushButton:hover { background:#355340; }
QPushButton:focus { border:2px solid #7fd4a2; }
QPushButton:disabled { background:#1d2b23; color:#6f8277; border-color:#30473b; }
QPushButton#primary { background:#298a56; border-color:#329a61; color:#ffffff; font-weight:700; }
QPushButton#primary:hover { background:#36a76a; }
QPushButton#primary:disabled { background:#1f3a2c; color:#7e9a89; border-color:#30473b; }
QPushButton#cornerStrip { background:#17251f; border:1px solid #30473b; border-radius:6px; padding:4px 12px; font-size:12px; font-weight:600; color:#cfe6d8; }
QPushButton#cornerStrip:hover { background:#243c2f; border-color:#50b879; color:#f2fbf5; }
QPushButton#toolBtn { padding:5px 10px; font-size:13px; font-weight:600; }
QToolButton { background:#26382e; color:#edf4ef; border:1px solid #42634d; border-radius:8px; padding:7px 13px; font-weight:600; }
QToolButton:hover, QToolButton:pressed { background:#355340; }
QToolButton::menu-indicator { image:none; width:0; }
QMenu { background:#1d2b23; color:#edf4ef; border:1px solid #42634d; padding:5px; }
QMenu::item { padding:8px 22px; }
QMenu::item:selected { background:#245d42; }
QListWidget::item { padding:7px 8px; border-radius:5px; }
QListWidget::item:selected { background:#245d42; color:#f2fbf5; }
QProgressBar { background:#26372d; border:0; border-radius:3px; max-height:6px; min-height:6px; }
QProgressBar::chunk { background:#50b879; border-radius:3px; }
QStatusBar { background:#13231b; color:#a9bbb0; border-top:1px solid #30473b; }
QRadioButton { padding:4px 2px; spacing:8px; }
QRadioButton::indicator { width:14px; height:14px; border-radius:8px; border:2px solid #5d7a69; background:#101a17; }
QRadioButton::indicator:checked { background:#50b879; border:2px solid #9be3b8; }
QRadioButton:focus { color:#ffffff; }
QRadioButton:disabled { color:#6f8277; }
QTabWidget::pane { border:1px solid #30473b; border-radius:8px; top:-1px; }
QTabBar::tab { background:#17231e; color:#a9bbb0; padding:7px 15px; border:1px solid #30473b; border-bottom:0; border-top-left-radius:8px; border-top-right-radius:8px; margin-right:2px; }
QTabBar::tab:selected { background:#245d42; color:#f2fbf5; }
QScrollArea { border:0; background:transparent; }
QListWidget#checklist { border:0; background:transparent; padding:0; }
QListWidget#checklist:focus { border:0; }
QScrollBar:vertical { background:#19271f; width:10px; margin:2px 1px; border:0; }
QScrollBar::handle:vertical { background:#597663; min-height:32px; border-radius:4px; }
QScrollBar::handle:vertical:hover { background:#7fad8a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
QSplitter::handle:horizontal { background:#23382c; width:7px; }
QSplitter::handle:horizontal:hover { background:#46785c; }
QSplitter::handle:horizontal:pressed { background:#60a880; }
QSplitter::handle:vertical { background:#23382c; height:7px; }
QSplitter::handle:vertical:hover { background:#46785c; }
QSplitter::handle:vertical:pressed { background:#60a880; }
"""

STAGES = ("Identified", "Managed", "Reported")
PREREQ = {"Managed": "Identified", "Reported": "Managed"}
ARROW = "\u25b8 "
GAP = "\u00a0\u00a0 "
MARKS = {"supported": "\u25cf", "unsupported": "\u2212", "open": "\u25cb"}

WORKPAPER_HELP = {
    "Choose company and fiscal year": "Show the selectors. Choose both fields to open a company-year workpaper.",
    "Saved workspaces": "Open a previously saved company-year workpaper.",
    "Add PDFs": "Attach report PDFs to the current workpaper. The original files stay in place.",
    "Choose reports folder": "Set the folder used to resolve portable report paths.",
    "Relink missing PDF": "Locate a moved report and verify it by hash or filename.",
    "Import roster...": "Load company names from the Companies sheet of an XLSX workbook.",
    "Scorer name and evidence page setting": "Set the scorer name and choose PDF or printed pages for exports.",
    "Export workpaper (.verdant)": "Share this company-year's decisions, audit and OCR text without PDF binaries.",
    "Import workpaper (.verdant)": "Merge a shared workpaper after reviewing any decision conflicts.",
    "Find leads": "Search reports for rule-based evidence leads; only saved review decisions count as scores.",
    "Mark items with no hits as Not found": "Confirm bulk Not found decisions for unreviewed items with no extracted-text hits.",
    "Export sheets": "Create one new XLSX using the consolidated workbook template and all saved workpapers.",
    "Help for these actions": "Open a popup explaining each workpaper action and button.",
}

BUTTON_HELP = {
    "Workspaces": WORKPAPER_HELP["Saved workspaces"],
    "Export sheets": WORKPAPER_HELP["Export sheets"],
    "Add PDFs": WORKPAPER_HELP["Add PDFs"],
    "Find leads": WORKPAPER_HELP["Find leads"],
    "Previous match": "Go to the previous find result (wraps to the last result).",
    "Next match": "Go to the next find result; F3 does the same.",
    "◀ Prev": "Show the previous PDF page.",
    "Next ▶": "Show the next PDF page.",
    "Go": "Jump to the PDF page number entered beside this button.",
    "−": "Zoom out on the PDF page.",
    "+": "Zoom in on the PDF page.",
    "Fit width": "Fit the PDF page to the reader width.",
    "Fit page": "Fit the full PDF page in the reader.",
    "OCR current": "Recognize text on the current image-only PDF page.",
    "OCR all missing": "Recognize text on all pages flagged as image-only.",
    "OCR selected pages": "Choose specific image-only PDF pages for OCR.",
    "Cancel OCR": "Stop OCR after the current page; completed pages stay available.",
    "Review pages": "Open the PDF reader to inspect the matching pages.",
    "Pin selected passage": "Add this passage and PDF page to the selected score category; existing pins remain.",
    "Remove selected pin": "Remove the selected pinned passage from this score category.",
    "Checklist and decisions": "Open the checklist and decision form for the selected item.",
    "Hide manual review": "Show or hide the manual decision controls.",
    "Use lead": "Fill the decision form with the best lead; inspect the source before saving.",
    "Save and next": "Save this decision and move to the next unreviewed item (Alt+Right).",
    "Next with a lead": "Jump to the next unreviewed item that has a lead.",
    "Score summary": "Open a detailed list of rule-based leads and saved decisions.",
    "Expand all": "Expand every score group.",
    "Collapse all": "Collapse every score group.",
    "Open selected": "Open the selected saved workpaper.",
    "Delete selected": "Delete the selected saved workpaper after confirmation.",
    "Cancel task": "Request cancellation of the background import or lead search.",
    "Browse reports folder": "Choose the main folder containing company PDF reports.",
    "Browse roster": "Choose an XLSX roster with a Companies sheet.",
    "Continue": "Save first-run setup and open the workbench.",
    "? Help": "Open the button guide and read what each control does.",
    "Close": "Close this popup.",
}


def make_items():
    return build_items(RUBRIC)


class OCRWorker(QThread):
    progress = Signal(int, int, str, int)
    completed = Signal(object, object)

    def __init__(self, tasks, tessdata):
        super().__init__(); self.tasks = tasks; self.tessdata = tessdata

    def run(self):
        try:
            results, errors = extract_missing_pages(self.tasks, self.tessdata,
                lambda done, total, name, page: self.progress.emit(done, total, name, page),
                should_cancel=self.isInterruptionRequested)
        except Exception as exc:
            results, errors = [], [f"OCR could not start: {exc}"]
        self.completed.emit(results, errors)


class LeadWorker(QThread):
    progress = Signal(int, int, str)
    completed = Signal(object, str)

    def __init__(self, items, documents, company):
        super().__init__()
        self.items = items; self.documents = documents; self.company = company

    def run(self):
        try:
            def advance(done, total, code):
                if self.isInterruptionRequested(): raise OperationCancelled()
                self.progress.emit(done, total, code)
            results = assess_all(self.items, self.documents, advance, self.company)
            self.completed.emit(results, "")
        except OperationCancelled:
            self.completed.emit(None, "canceled")
        except Exception as exc:
            self.completed.emit(None, str(exc))


class ImportWorker(QThread):
    progress = Signal(int, int, str)
    completed = Signal(object, object, bool)

    def __init__(self, paths):
        super().__init__()
        self.paths = paths

    def run(self):
        records = []; errors = []; completed = 0; total = 0; canceled = False
        for raw in self.paths:
            try:
                with fitz.open(raw) as pdf: total += len(pdf)
            except Exception as exc:
                errors.append(f"{Path(raw).name}: {exc}")
        for raw in self.paths:
            if self.isInterruptionRequested(): canceled = True; break
            path = Path(raw)
            try:
                pages = []
                with fitz.open(path) as pdf:
                    for number, page in enumerate(pdf, 1):
                        if self.isInterruptionRequested(): raise OperationCancelled()
                        pages.append(page.get_text("text"))
                        completed += 1
                        self.progress.emit(completed, total, f"{path.name} · PDF page {number}/{len(pdf)}")
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        if self.isInterruptionRequested(): raise OperationCancelled()
                        digest.update(chunk)
                records.append((str(path), digest.hexdigest(), len(pages), sum(not text.strip() for text in pages)))
            except OperationCancelled:
                canceled = True; break
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self.completed.emit(records, errors, canceled)


class OperationCancelled(Exception):
    pass


class Tile(QFrame):
    """Metric tile: label, value, progress bar, note. Each tile measures a different thing."""
    def __init__(self, label, maximum, note):
        super().__init__(); self.setObjectName("tile"); self.maximum = maximum
        box = QVBoxLayout(self); box.setContentsMargins(16, 12, 16, 12); box.setSpacing(4)
        self.label = QLabel(label); self.label.setObjectName("tileLabel")
        self.value = QLabel(f"0 / {maximum}"); self.value.setObjectName("tileValue")
        self.bar = QProgressBar(); self.bar.setRange(0, maximum); self.bar.setTextVisible(False)
        self.note = QLabel(note); self.note.setObjectName("tileNote")
        for widget in (self.label, self.value, self.bar, self.note): box.addWidget(widget)
        self.set_value(0)

    def set_value(self, value):
        self.value.setText(f"{value} / {self.maximum}"); self.bar.setValue(value)
        self.setAccessibleName(f"{self.label.text()} {value} of {self.maximum}")


class OCRDetailsPopup(QFrame):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("ocrDetailsPopup")

    def hideEvent(self, event):
        super().hideEvent(event)
        self.closed.emit()


class Workbench(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Verdant | Disclosure Scorer")
        self.setWindowIcon(QIcon(str(RESOURCES_DIR / "brand_mark.svg")))
        self.setMinimumSize(860, 480)
        self.store = Store()
        self.items = make_items()
        self.companies = load_companies()
        self.project_id = None
        self.active_company = None
        self.active_year = None
        self.docs = []
        self.doc_paths = {}
        self.ocr_tasks = []
        self.ocr_page_refs = set()
        self.ocr_running = False
        self.ocr_worker = None
        self.ocr_state = ""
        self.busy = False
        self.hits = []
        self.visible_hits = []
        self.suggestions = {}
        self.skipped_reports = 0
        self.current = None
        self.saved_form = None
        self.loading_form = False
        self.page_target = None
        self.pdf_loaded_path = None
        self.pdf_buffer = None
        self.highlight_cache = {}
        self.render_cache = OrderedDict()
        self.render_cache_bytes = 0
        self.page_bounds_cache = {}
        self._navigating = False
        self._current_label = ""
        self._current_match_count = 0
        self._current_ocr_highlight = False
        self.zoom_mode = "width"
        self.zoom_scale = 1.0
        self.ocr_failed_pages = set()
        self.ocr_current = None
        self.pending_selection = None
        self.background_worker = None
        self.background_project_id = None
        self.background_skipped = 0
        self.settings = QSettings(str(DATA_DIR / "viewer.ini"), QSettings.Format.IniFormat)
        self.build_ui()
        self.company.activated.connect(lambda *_: self.open_project())
        self.year.activated.connect(lambda *_: self.open_project())
        saved_geom = self.settings.value("geometry")
        if saved_geom:
            self.restoreGeometry(saved_geom)
        else:
            screen = QApplication.primaryScreen()
            if screen:
                avail = screen.availableGeometry()
                self.resize(max(860, int(avail.width() * 0.92)), max(480, int(avail.height() * 0.92)))
            else:
                self.resize(1500, 920)
        self.select_item(self.items[0])
        self.refresh_totals()

    def panel(self):
        frame = QFrame(); frame.setObjectName("panel")
        return frame

    def button(self, text, callback, primary=False):
        button = QPushButton(text)
        button.clicked.connect(callback)
        help_text = BUTTON_HELP.get(text, "Open the score overview." if text.startswith("Reviewed ") else f"Use {text}.")
        button.setToolTip(help_text)
        button.setAccessibleDescription(help_text)
        if primary:
            button.setObjectName("primary")
        else:
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        return button

    def show_help(self):
        previous = getattr(self, "help_dialog", None)
        if previous: previous.close()
        dialog = QDialog(self)
        dialog.setWindowTitle("Verdant button guide")
        dialog.resize(740, 510)
        outer = QVBoxLayout(dialog)
        intro = QLabel("Select a control to see what it does. Hover over any button for the same short tip.")
        intro.setWordWrap(True); outer.addWidget(intro)
        row = QHBoxLayout(); listing = QListWidget(); detail = QLabel()
        detail.setWordWrap(True); detail.setAlignment(Qt.AlignmentFlag.AlignTop)
        detail.setMinimumWidth(300)
        entries = {**WORKPAPER_HELP, **BUTTON_HELP,
                   "Choose fiscal year": "Select the fiscal year covered by the report. No year is preselected.",
                   "Find scope": "Search this PDF, all attached PDFs, or the checklist with the shared find bar."}
        for name, description in entries.items():
            item = QListWidgetItem(name); item.setData(Qt.ItemDataRole.UserRole, description)
            listing.addItem(item)
        listing.currentItemChanged.connect(lambda item, *_: detail.setText(item.data(Qt.ItemDataRole.UserRole) if item else ""))
        listing.setCurrentRow(0)
        row.addWidget(listing, 2); row.addWidget(detail, 3); outer.addLayout(row)
        outer.addWidget(self.button("Close", dialog.close))
        credit = QLabel("tool made by jargon")
        credit.setObjectName("muted")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(credit)
        self.help_dialog = dialog
        dialog.show()

    def progress_dialog(self, title, label, maximum):
        dialog = QProgressDialog(label, "Cancel", 0, maximum, self)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False); dialog.setAutoReset(False)
        dialog.show()
        return dialog

    def pane_title(self, text):
        label = QLabel(text); label.setObjectName("paneTitle"); return label

    def build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(16, 10, 16, 10); layout.setSpacing(8)

        # Header: brand, workpaper context, status chip (max ~56 px)
        brand = QFrame(); brand.setObjectName("brandBar"); brand.setFixedHeight(54)
        head = QHBoxLayout(brand); head.setContentsMargins(14, 6, 14, 6); head.setSpacing(12)
        mark = QLabel(); mark.setPixmap(self.windowIcon().pixmap(26, 26)); head.addWidget(mark)
        name = QLabel("verdant."); name.setObjectName("brand"); head.addWidget(name)
        descriptor = QLabel("Disclosure Scorer"); descriptor.setObjectName("muted"); head.addWidget(descriptor)
        head.addSpacing(16)
        context = QVBoxLayout(); context.setSpacing(0)
        self.context_title = QLabel("Company Workpaper"); self.context_title.setObjectName("heading")
        self.context_sub = QLabel("No workpaper open"); self.context_sub.setObjectName("muted")
        context.addWidget(self.context_title); context.addWidget(self.context_sub)
        head.addLayout(context); head.addStretch()

        work_menu = QMenu(self)
        work_menu.addAction("Choose company and fiscal year", lambda: self.controls_panel.setVisible(True))
        work_menu.addAction("Saved workspaces", self.open_saved)
        work_menu.addAction("Add PDFs", self.import_pdfs_background)
        work_menu.addAction("Choose reports folder", self.choose_reports_folder)
        work_menu.addAction("Relink missing PDF", self.relink_missing_pdf)
        work_menu.addAction("Import roster...", self.import_roster)
        work_menu.addAction("Scorer name and evidence page setting", self.configure_reviewer)
        work_menu.addAction("Export workpaper (.verdant)", self.export_portable_workpaper)
        work_menu.addAction("Import workpaper (.verdant)", self.import_portable_workpaper)
        work_menu.addAction("Find leads", self.find_leads_background)
        work_menu.addAction("Mark items with no hits as Not found", self.bulk_mark_no_hits)
        work_menu.addSeparator(); work_menu.addAction("Export sheets", self.export_sheets)
        work_menu.addSeparator(); work_menu.addAction("Help for these actions", self.show_help)
        work_menu.setToolTipsVisible(True)
        for action in work_menu.actions():
            if action.text() in WORKPAPER_HELP:
                action.setToolTip(WORKPAPER_HELP[action.text()])
                action.setStatusTip(WORKPAPER_HELP[action.text()])

        self.work_menu_button = QToolButton()
        self.work_menu_button.setText("Workpaper ▾")
        self.work_menu_button.setMenu(work_menu)
        self.work_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.work_menu_button.setToolTip("Open workpaper actions. Hover over an action for its purpose.")
        head.addWidget(self.work_menu_button)
        head.addWidget(self.button("? Help", self.show_help))

        self.status_chip = QLabel("No workpaper"); self.status_chip.setObjectName("chip")
        self.status_chip.setProperty("state", "none"); head.addWidget(self.status_chip)
        layout.addWidget(brand)

        # Workpaper toolbar (collapsible)
        controls = self.panel(); row = QHBoxLayout(controls); row.setContentsMargins(12, 8, 12, 8); row.setSpacing(8)
        self.company = QComboBox(); self.company.addItem("Select a company"); self.company.addItems(self.companies)
        self.company.setMinimumWidth(260); self.company.setAccessibleName("Company"); row.addWidget(self.company, 3)
        self.year = QComboBox(); self.year.addItem("Choose fiscal year"); self.year.addItems(["2022", "2023", "2024", "2025"])
        self.year.setAccessibleName("Fiscal year covered")
        self.year.setToolTip("Choose the fiscal year covered by the report. No year is selected by default."); row.addWidget(self.year, 1)
        row.addWidget(self.button("Workspaces", self.open_saved))
        row.addWidget(self.button("Add PDFs", self.import_pdfs_background))
        row.addWidget(self.button("Find leads", self.find_leads_background))
        row.addWidget(self.button("Export sheets", self.export_sheets))
        self.controls_panel = controls
        layout.addWidget(controls)

        # Main work tabs
        self.work_tabs = QTabWidget()
        self.work_tabs.setObjectName("workTabs")
        layout.addWidget(self.work_tabs, 1)

        # Corner widget in tab bar for score summary
        self.review_score_strip = self.button("Reviewed 0/81 · Supported 0/81 | Score overview", lambda: self.work_tabs.setCurrentIndex(2))
        self.review_score_strip.setObjectName("cornerStrip")
        self.work_tabs.setCornerWidget(self.review_score_strip, Qt.Corner.TopRightCorner)

        # Tab 0: PDF reader
        review_page = QWidget(); review_layout = QVBoxLayout(review_page)
        review_layout.setContentsMargins(0, 6, 0, 0); review_layout.setSpacing(6)
        self.work_tabs.addTab(review_page, "PDF reader")

        # Tab 1: Checklist and decisions (B1: no '&' mnemonic)
        scoring_page = QWidget(); scoring_layout = QVBoxLayout(scoring_page)
        scoring_layout.setContentsMargins(0, 6, 0, 0); scoring_layout.setSpacing(6)
        self.work_tabs.addTab(scoring_page, "Checklist and decisions")

        # Tab 2: Score overview
        scores_page = QWidget(); scores_layout = QVBoxLayout(scores_page)
        scores_layout.setContentsMargins(4, 10, 4, 4); scores_layout.setSpacing(10)
        self.work_tabs.addTab(scores_page, "Score overview")

        # Score overview page layout
        tiles = QHBoxLayout(); tiles.setSpacing(12)
        self.esg_tile = Tile("Items with leads", len(self.items), "Evidence to inspect")
        self.sdg_tile = Tile("Supported (reviewed)", len(self.items), "Saved decisions only")
        self.reviewed_tile = Tile("Reviewed", len(self.items), "Saved decisions")
        for tile in (self.esg_tile, self.sdg_tile, self.reviewed_tile): tiles.addWidget(tile, 1)
        self.progress = self.reviewed_tile.bar
        scores_layout.addLayout(tiles)

        self.prediction_totals = QLabel()
        self.prediction_totals.setObjectName("prediction"); self.prediction_totals.setWordWrap(True)
        self.prediction_totals.hide()
        summary_row = QHBoxLayout(); summary_row.setSpacing(10)
        summary_row.addWidget(self.prediction_totals, 1)
        summary_row.addWidget(self.button("Score summary", self.show_score_summary))
        scores_layout.addLayout(summary_row)

        self.score_tree = QTreeWidget(); self.configure_score_tree(self.score_tree)
        self.score_tree.itemActivated.connect(self.open_score_item)
        self.score_tree.itemDoubleClicked.connect(self.open_score_item)
        scores_layout.addWidget(self.score_tree, 1)

        score_actions = QHBoxLayout(); score_actions.addStretch()
        score_actions.addWidget(self.button("Expand all", self.score_tree.expandAll))
        score_actions.addWidget(self.button("Collapse all", self.score_tree.collapseAll))
        scores_layout.addLayout(score_actions)
        self.work_tabs.currentChanged.connect(self.work_tab_changed)

        # ------------------------------------------------------------------
        # Build PDF Reader Tab (Tab 0) with 2-pane QSplitter
        # ------------------------------------------------------------------
        self.center_stack = QStackedWidget()
        review_layout.addWidget(self.center_stack, 1)

        empty = QWidget(); el = QVBoxLayout(empty); el.setAlignment(Qt.AlignmentFlag.AlignCenter); el.setSpacing(12)
        self.empty_title = QLabel("Open a workpaper to begin"); self.empty_title.setObjectName("empty")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_body = QLabel("Choose a company and fiscal year to open its workpaper."); self.empty_body.setObjectName("muted")
        self.empty_body.setAlignment(Qt.AlignmentFlag.AlignCenter); self.empty_body.setWordWrap(True)
        self.empty_action = self.button("Add PDFs", self.import_pdfs_background, True)
        el.addWidget(self.empty_title); el.addWidget(self.empty_body); el.addWidget(self.empty_action, 0, Qt.AlignmentFlag.AlignCenter)
        self.center_stack.addWidget(empty)  # index 0

        # LEFT PANE: PDF pane (~58% width, min 540 px)
        left_pdf_pane = self.panel()
        ll_pdf = QVBoxLayout(left_pdf_pane)
        ll_pdf.setContentsMargins(10, 8, 10, 6)
        ll_pdf.setSpacing(6)
        left_pdf_pane.setMinimumWidth(540)

        # 1-line compact OCR strip (~34 px tall)
        self.warning_panel = QFrame()
        self.warning_panel.setObjectName("ocrWarning")
        self.warning_panel.setFixedHeight(34)
        warn_row = QHBoxLayout(self.warning_panel)
        warn_row.setContentsMargins(10, 2, 10, 2)
        warn_row.setSpacing(8)

        self.ocr_summary = QLabel()
        self.ocr_summary.setObjectName("hint")
        self.ocr_summary.setStyleSheet("font-weight:600;")
        warn_row.addWidget(self.ocr_summary, 1)

        self.ocr_progress_bar = QProgressBar()
        self.ocr_progress_bar.setRange(0, 100)
        self.ocr_progress_bar.setFixedHeight(8)
        self.ocr_progress_bar.setTextVisible(False)
        self.ocr_progress_bar.hide()
        warn_row.addWidget(self.ocr_progress_bar, 1)

        self.warning_toggle = QPushButton("Details ▾")
        self.warning_toggle.setToolTip("Show or hide OCR status and pages that still need text recognition.")
        self.warning_toggle.setObjectName("toolBtn")
        self.warning_toggle.setCheckable(True)
        self.warning_toggle.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        warn_row.addWidget(self.warning_toggle)
        ll_pdf.addWidget(self.warning_panel)

        # OCR details popup (overlays PDF, does not resize PDF view)
        self.warning_popup = OCRDetailsPopup(self)
        self.warning_details = self.warning_popup
        popup_layout = QVBoxLayout(self.warning_popup)
        popup_layout.setContentsMargins(10, 10, 10, 10)
        popup_layout.setSpacing(8)

        self.warning_scroll = QScrollArea()
        self.warning_scroll.setWidgetResizable(True)
        self.warning_scroll.setMaximumHeight(96)
        self.warning_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.doc_warning = QLabel()
        self.doc_warning.setObjectName("warn")
        self.doc_warning.setWordWrap(True)
        self.doc_warning.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.warning_scroll.setWidget(self.doc_warning)
        popup_layout.addWidget(self.warning_scroll)

        warning_actions = QGridLayout()
        warning_actions.setSpacing(6)
        self.ocr_button = self.button("OCR all missing", lambda: self.start_ocr("all"))
        self.ocr_selected_button = self.button("OCR selected pages", lambda: self.start_ocr("selected"))
        self.review_ocr_button = self.button("Review pages", self.review_missing_pages)
        self.cancel_ocr_button = self.button("Cancel OCR", self.cancel_ocr)
        self.cancel_ocr_button.hide()
        warning_actions.addWidget(self.ocr_button, 0, 0)
        warning_actions.addWidget(self.ocr_selected_button, 0, 1)
        warning_actions.addWidget(self.review_ocr_button, 1, 0)
        warning_actions.addWidget(self.cancel_ocr_button, 1, 1)
        popup_layout.addLayout(warning_actions)

        self.warning_toggle.toggled.connect(self.toggle_warning)
        self.warning_popup.closed.connect(lambda: self.warning_toggle.setChecked(False) if self.warning_toggle.isChecked() else None)
        self.warning_panel.hide()

        # Document row: combo + status
        document_row = QHBoxLayout()
        document_row.setSpacing(8)
        self.pdf_document = QComboBox()
        self.pdf_document.setAccessibleName("PDF document")
        self.pdf_document.currentIndexChanged.connect(self.open_selected_document)
        self.page_status = QLabel("No document")
        self.page_status.setObjectName("muted")
        document_row.addWidget(self.pdf_document, 1)
        document_row.addWidget(self.page_status)
        ll_pdf.addLayout(document_row)

        # Toolbar row: navigation + zoom + OCR
        nav = QHBoxLayout()
        nav.setSpacing(5)
        self.page_prev = self.button("◀ Prev", lambda: self.step_page(-1))
        self.page_prev.setObjectName("toolBtn")
        self.page_number = QSpinBox()
        self.page_number.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.page_number.setFixedWidth(64)
        self.page_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_number.setMinimum(1); self.page_number.setMaximum(1)
        self.page_number.setAccessibleName("PDF page number")
        self.page_number.editingFinished.connect(self.jump_to_page)

        self.page_total = QLabel("/ 0"); self.page_total.setObjectName("muted")
        self.page_jump = self.button("Go", self.jump_to_page); self.page_jump.setObjectName("toolBtn")
        self.page_next = self.button("Next ▶", lambda: self.step_page(1)); self.page_next.setObjectName("toolBtn")

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine); sep1.setObjectName("vrule")
        self.btn_zoom_out = self.button("−", lambda: self.change_zoom(1/1.25)); self.btn_zoom_out.setObjectName("toolBtn")
        self.btn_zoom_in = self.button("+", lambda: self.change_zoom(1.25)); self.btn_zoom_in.setObjectName("toolBtn")
        self.btn_fit_width = self.button("Fit width", lambda: self.set_zoom_mode("width")); self.btn_fit_width.setObjectName("toolBtn")
        self.btn_fit_page = self.button("Fit page", lambda: self.set_zoom_mode("page")); self.btn_fit_page.setObjectName("toolBtn")

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.VLine); sep2.setObjectName("vrule")
        self.btn_ocr_current = self.button("OCR current", lambda: self.start_ocr("current")); self.btn_ocr_current.setObjectName("toolBtn")

        for w in (self.page_prev, self.page_number, self.page_total, self.page_jump, self.page_next,
                  sep1, self.btn_zoom_out, self.btn_zoom_in, self.btn_fit_width, self.btn_fit_page,
                  sep2, self.btn_ocr_current):
            nav.addWidget(w)
        nav.addStretch()
        ll_pdf.addLayout(nav)
        search_row = QHBoxLayout()
        self.pdf_search = QLineEdit()
        self.pdf_search.setPlaceholderText("Search text in this PDF")
        self.pdf_search.setClearButtonEnabled(True)
        self.pdf_search.returnPressed.connect(lambda: self.find_pdf_text(1))
        self.pdf_search.textChanged.connect(self.reset_pdf_search)
        self.find_scope = QComboBox()
        self.find_scope.addItems(["This PDF", "All PDFs", "Checklist"])
        self.find_scope.currentIndexChanged.connect(self.reset_pdf_search)
        self.pdf_search_count = QLabel("0 matches")
        search_row.addWidget(self.pdf_search, 1)
        search_row.addWidget(self.find_scope)
        search_row.addWidget(self.button("Previous match", lambda: self.find_pdf_text(-1)))
        search_row.addWidget(self.button("Next match", lambda: self.find_pdf_text(1)))
        search_row.addWidget(self.pdf_search_count)
        layout.insertLayout(2, search_row)

        # PDF view tabs: ONLY All PDF pages | Highlighted page
        self.view_tabs = QTabWidget()
        self.view_tabs.setObjectName("viewTabs")

        self.pdf_model = QPdfDocument(self)
        self.continuous_pdf = QPdfView()
        self.continuous_pdf.setDocument(self.pdf_model)
        self.continuous_pdf.setPageMode(QPdfView.PageMode.MultiPage)
        self.continuous_pdf.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.continuous_pdf.pageNavigator().currentPageChanged.connect(self.continuous_page_changed)
        self.view_tabs.addTab(self.continuous_pdf, "All PDF pages")

        page_box = QWidget(); pb = QVBoxLayout(page_box); pb.setContentsMargins(4, 4, 4, 4); pb.setSpacing(4)
        self.page_image = QLabel("Select a PDF to view its original page.")
        self.page_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_scroll = QScrollArea(); self.page_scroll.setWidgetResizable(False)
        self.page_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_scroll.setWidget(self.page_image)
        pb.addWidget(self.page_scroll, 1)
        self.view_tabs.addTab(page_box, "Highlighted page")

        self.view_tabs.currentChanged.connect(self.viewer_mode_changed)
        ll_pdf.addWidget(self.view_tabs, 1)

        # Single-line elided footer
        self.page_label = QLabel("No page selected"); self.page_label.setObjectName("muted")
        self.page_label.setFixedHeight(22)
        ll_pdf.addWidget(self.page_label)

        # RIGHT PANE: Evidence pane (~42% width, min 420 px)
        right_evidence_pane = self.panel()
        rl_ev = QVBoxLayout(right_evidence_pane)
        rl_ev.setContentsMargins(12, 8, 12, 6)
        rl_ev.setSpacing(6)
        right_evidence_pane.setMinimumWidth(320)

        self.item_title = QLabel()
        self.item_title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        self.item_title.setWordWrap(True)
        rl_ev.addWidget(self.item_title)

        self.terms = QLabel(); self.terms.setObjectName("muted")
        self.terms.setFixedHeight(20)
        rl_ev.addWidget(self.terms)

        self.score_hint = QLabel("Import PDFs, then click Find leads to inspect rule-based evidence.")
        self.score_hint.setObjectName("hint"); self.score_hint.setWordWrap(True)
        rl_ev.addWidget(self.score_hint)

        filter_row = QHBoxLayout(); filter_row.setSpacing(8)
        self.keyword_filter = QLineEdit()
        self.keyword_filter.setPlaceholderText("Filter matched pages by word or phrase")
        self.keyword_filter.setClearButtonEnabled(True)
        self.keyword_filter.textChanged.connect(self.display_hits)
        self.keyword_filter.hide()
        self.hit_count = QLabel("0 hits"); self.hit_count.setObjectName("muted")
        filter_row.addWidget(self.keyword_filter, 1)
        filter_row.addWidget(self.hit_count)
        rl_ev.addLayout(filter_row)

        self.hit_list = QListWidget()
        self.hit_list.setMinimumHeight(120)
        self.hit_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.hit_list.setWordWrap(True); self.hit_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.hit_list.currentRowChanged.connect(self.show_hit)
        rl_ev.addWidget(self.hit_list, 2)

        self.reader_tabs = QTabWidget()
        self.preview = QTextEdit(); self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Select a search hit to read its context.")
        self.reader_tabs.addTab(self.preview, "Evidence context")

        self.extracted_text = QTextEdit(); self.extracted_text.setReadOnly(True)
        self.extracted_text.setPlaceholderText("This page has no extractable text. View the original PDF and run OCR if needed.")
        self.reader_tabs.addTab(self.extracted_text, "Extracted text")
        rl_ev.addWidget(self.reader_tabs, 3)

        self.reader_pin_label = QLabel("Pinned passages for current category: 0")
        self.reader_pin_label.setObjectName("muted")
        rl_ev.addWidget(self.reader_pin_label)
        self.reader_pins = QListWidget(); self.reader_pins.setMinimumHeight(66)
        self.reader_pins.setMaximumHeight(110)
        self.reader_pins.setToolTip("Passages pinned to the selected score category, across PDF files and pages.")
        rl_ev.addWidget(self.reader_pins)

        action_row = QHBoxLayout(); action_row.setSpacing(8)
        self.pin_button = self.button("Pin selected passage", self.pin_hit)
        self.focus_button = self.button("Checklist and decisions", lambda: self.work_tabs.setCurrentIndex(1))
        self.focus_button.setToolTip("Open checklist and decision form")
        action_row.addWidget(self.pin_button)
        action_row.addWidget(self.focus_button)
        action_row.addStretch()
        rl_ev.addLayout(action_row)

        # Reader splitter
        self.reader_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.reader_splitter.setChildrenCollapsible(False)
        self.reader_splitter.setHandleWidth(7)
        self.reader_splitter.addWidget(left_pdf_pane)
        self.reader_splitter.addWidget(right_evidence_pane)
        self.reader_splitter.setStretchFactor(0, 3)
        self.reader_splitter.setStretchFactor(1, 2)

        saved_reader = self.settings.value("reader_splitter_v2")
        if saved_reader and self.reader_splitter.restoreState(saved_reader):
            sizes = self.reader_splitter.sizes()
            if not (len(sizes) == 2 and sizes[0] >= 300 and sizes[1] >= 200):
                self.reader_splitter.setSizes([800, 580])
        else:
            self.reader_splitter.setSizes([800, 580])

        self.reader_splitter.splitterMoved.connect(
            lambda *_: self.settings.setValue("reader_splitter_v2", self.reader_splitter.saveState())
        )
        self.center_stack.addWidget(self.reader_splitter)  # index 1

        # ------------------------------------------------------------------
        # Build Checklist and decisions Tab (Tab 1) with clean 2-pane splitter
        # ------------------------------------------------------------------
        self.checklist_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.checklist_splitter.setChildrenCollapsible(False)
        self.checklist_splitter.setHandleWidth(7)

        # Left: checklist
        left = self.panel(); ll = QVBoxLayout(left); ll.setContentsMargins(14, 14, 14, 12); ll.setSpacing(8)
        left.setMinimumWidth(235); left.setMaximumWidth(410)
        ll.addWidget(self.pane_title("Checklist"))
        self.filter = QLineEdit(); self.filter.setPlaceholderText("Filter code, title or keyword")
        self.filter.setClearButtonEnabled(True); self.filter.textChanged.connect(self.render_items); ll.addWidget(self.filter)
        self.filter.hide()
        legend = QLabel(f"{MARKS['open']} not reviewed   {MARKS['unsupported']} not supported   {MARKS['supported']} supported")
        legend.setObjectName("muted"); legend.setStyleSheet("font-size:12px;"); ll.addWidget(legend)
        self.item_list = QListWidget(); self.item_list.setObjectName("checklist")
        self.item_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.item_list.setWordWrap(True); self.item_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.item_list.currentRowChanged.connect(self.item_row_changed)
        ll.addWidget(self.item_list, 1)
        self.checklist_splitter.addWidget(left)

        # Right: decision form
        right = self.panel(); outer = QVBoxLayout(right); outer.setContentsMargins(4, 4, 4, 4)
        right.setMinimumWidth(340)
        decision_scroll = QScrollArea(); decision_scroll.setWidgetResizable(True)
        decision_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(decision_scroll)
        decision_body = QWidget()
        decision_scroll.setWidget(decision_body)
        rl = QVBoxLayout(decision_body); rl.setContentsMargins(10, 10, 10, 8); rl.setSpacing(8)
        rl.addWidget(self.pane_title("Decision"))
        self.criterion = QLabel(); self.criterion.setWordWrap(True); self.criterion.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold)); rl.addWidget(self.criterion)
        self.perspective = QLabel(); self.perspective.setObjectName("perspective"); rl.addWidget(self.perspective, 0, Qt.AlignmentFlag.AlignLeft)
        self.rule = QLabel(); self.rule.setObjectName("muted"); self.rule.setWordWrap(True); rl.addWidget(self.rule)
        self.stage_box = QFrame(); self.stage_box.setObjectName("inset"); sb = QVBoxLayout(self.stage_box); sb.setContentsMargins(12, 10, 12, 10); sb.setSpacing(4)
        self.stage_rows = [QLabel() for _ in STAGES]
        for label in self.stage_rows: label.setTextFormat(Qt.TextFormat.RichText); sb.addWidget(label)
        self.stage_total = QLabel(); self.stage_total.setObjectName("muted"); sb.addWidget(self.stage_total)
        rl.addWidget(self.stage_box)
        self.prediction = QLabel("Run Find leads to see a source passage.")
        self.prediction.setObjectName("prediction"); self.prediction.setWordWrap(True); rl.addWidget(self.prediction)
        self.review_toggle = self.button("Hide manual review", lambda: None)
        self.review_toggle.setCheckable(True); self.review_toggle.setChecked(True)
        rl.addWidget(self.review_toggle)
        self.manual_box = QWidget(); form = QVBoxLayout(self.manual_box)
        form.setContentsMargins(0, 0, 0, 0); form.setSpacing(8)
        options = QHBoxLayout()
        self.absent = QRadioButton("Not found (0)"); self.found = QRadioButton("Found (1)")
        options.addWidget(self.absent); options.addWidget(self.found); form.addLayout(options)
        self.stage_context = QLabel(); self.stage_context.setObjectName("muted"); self.stage_context.setWordWrap(True); form.addWidget(self.stage_context)
        self.apply_prediction_button = self.button("Use lead", self.apply_prediction)
        self.apply_prediction_button.setEnabled(False); form.addWidget(self.apply_prediction_button)
        form.addWidget(QLabel("Evidence document"))
        self.doc_name = QLineEdit(); self.doc_name.setPlaceholderText("Select a hit or enter the document name"); form.addWidget(self.doc_name)
        form.addWidget(QLabel("PDF page reference(s)"))
        self.pages = QLineEdit(); self.pages.setPlaceholderText("e.g. 8, 44"); form.addWidget(self.pages)
        form.addWidget(QLabel("Printed page label(s), if shown"))
        self.printed_pages = QLineEdit(); self.printed_pages.setPlaceholderText("Optional page label in the report"); form.addWidget(self.printed_pages)
        self.decision_pin_label = QLabel("Pinned passages: 0")
        form.addWidget(self.decision_pin_label)
        self.decision_pins = QListWidget(); self.decision_pins.setMinimumHeight(85)
        self.decision_pins.setToolTip("All pinned passages for this score category. Select one to remove it.")
        form.addWidget(self.decision_pins)
        form.addWidget(self.button("Remove selected pin", self.remove_selected_pin))
        form.addWidget(QLabel("Reviewer note (optional)"))
        self.evidence = QTextEdit(); self.evidence.setMinimumHeight(145)
        self.evidence.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.evidence.setPlaceholderText("Optional manual note. Leave blank to export a blank value.")
        form.addWidget(self.evidence, 1)
        self.validation = QLabel(); self.validation.setObjectName("hint"); self.validation.setWordWrap(True); form.addWidget(self.validation)
        self.save_button = self.button("Save and next", self.save_and_next, True); form.addWidget(self.save_button)
        form.addWidget(self.button("Next with a lead", self.next_with_lead))
        rl.addWidget(self.manual_box, 1)
        self.review_toggle.toggled.connect(self.toggle_manual_review)

        self.checklist_splitter.addWidget(right)
        self.checklist_splitter.setStretchFactor(0, 1)
        self.checklist_splitter.setStretchFactor(1, 2)

        saved_chk = self.settings.value("checklist_splitter_v2")
        if saved_chk and self.checklist_splitter.restoreState(saved_chk):
            pass
        else:
            self.checklist_splitter.setSizes([380, 800])
        self.checklist_splitter.splitterMoved.connect(
            lambda *_: self.settings.setValue("checklist_splitter_v2", self.checklist_splitter.saveState())
        )
        scoring_layout.addWidget(self.checklist_splitter, 1)
        self.splitter = self.checklist_splitter

        for signal in (self.found.toggled, self.absent.toggled, self.doc_name.textChanged, self.pages.textChanged, self.printed_pages.textChanged, self.evidence.textChanged):
            signal.connect(lambda *_: self.on_form_changed())

        self.statusBar().showMessage("Open a company-year workpaper to begin")
        self.task_progress = QProgressBar(); self.task_progress.setFixedWidth(140); self.task_progress.hide()
        self.task_cancel = self.button("Cancel task", self.cancel_background); self.task_cancel.hide()
        self.statusBar().addPermanentWidget(self.task_progress)
        self.statusBar().addPermanentWidget(self.task_cancel)
        save_action = QAction(self); save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save); self.addAction(save_action)
        next_action = QAction(self); next_action.setShortcut("Alt+Right")
        next_action.triggered.connect(self.save_and_next); self.addAction(next_action)
        for key, callback in (("Y", lambda: self.found.setChecked(True)),
                              ("N", lambda: self.absent.setChecked(True)),
                              ("Ctrl+F", lambda: self.pdf_search.setFocus()),
                              ("F3", lambda: self.find_pdf_text(1))):
            action = QAction(self); action.setShortcut(key); action.triggered.connect(callback); self.addAction(action)
        self.found.setToolTip("Found (1) · Y")
        self.absent.setToolTip("Not found (0) · N")
        self.save_button.setToolTip("Save and next unreviewed · Alt+Right")
        self.pdf_search.setToolTip("Find in PDF · Ctrl+F; next match · F3")
        QWidget.setTabOrder(self.filter, self.item_list)

    # ---- state helpers -------------------------------------------------
    def work_tab_changed(self, index):
        if index == 2:
            self.populate_score_tree(self.score_tree)

    def open_score_item(self, row, *_):
        code = row.data(0, Qt.ItemDataRole.UserRole)
        if not code: return
        item = next((entry for entry in self.items if entry["id"] == code), None)
        if item and self.select_item(item):
            self.work_tabs.setCurrentIndex(1)

    def all_scores(self):
        return self.store.scores(self.project_id) if self.project_id else {}

    def toggle_manual_review(self, open_form):
        self.manual_box.setVisible(open_form)
        self.review_toggle.setText("Hide manual review" if open_form else "Review / adjust manually")

    def toggle_warning(self, expanded):
        self.warning_toggle.blockSignals(True)
        self.warning_toggle.setChecked(expanded)
        self.warning_toggle.setText("Collapse ▴" if expanded else "Details ▾")
        self.warning_toggle.blockSignals(False)
        self.settings.setValue("ocr_warning_expanded", expanded)
        if expanded:
            if self.warning_panel.isVisible():
                pos = self.warning_panel.mapToGlobal(QPointF(0, self.warning_panel.height() + 2).toPoint())
                self.warning_popup.setMinimumWidth(max(420, self.warning_panel.width()))
                self.warning_popup.move(pos)
                self.warning_popup.show()
                self.warning_popup.raise_()
            else:
                self.warning_popup.show()
        else:
            self.warning_popup.hide()

    def review_missing_pages(self):
        if not self.ocr_tasks: return
        path, _, numbers = self.ocr_tasks[0]
        self.page_target = (Path(path).name, numbers[0])
        self.view_tabs.setCurrentIndex(0)
        self.render_page()

    def continuous_page_changed(self, index):
        if getattr(self, "_navigating", False): return
        if not self.pdf_loaded_path or index < 0: return
        name = Path(self.pdf_loaded_path).name
        if name not in self.doc_paths: return
        self.page_target = (name, index + 1)
        self.page_number.blockSignals(True)
        self.page_number.setValue(index + 1)
        self.page_number.blockSignals(False)
        self.update_extracted_text()
        total = len(next((pages for document, pages in self.docs if document == name), []))
        self.page_prev.setEnabled(index > 0)
        self.page_next.setEnabled(index + 1 < total)
        self.page_status.setText("OCR completed · review recommended" if (name, index + 1) in self.ocr_page_refs else "Native text available" if self.extracted_text.toPlainText().strip() else "No extractable text · OCR pending")
        self.update_page_footer()

    def sync_continuous_pdf(self, name, number):
        path = self.doc_paths.get(name)
        if not path: return
        was_navigating = self._navigating
        self._navigating = True
        try:
            if self.pdf_loaded_path != str(path):
                self.pdf_model.close()
                if self.pdf_buffer:
                    self.pdf_buffer.close(); self.pdf_buffer.deleteLater(); self.pdf_buffer = None
                if sys.platform == "darwin":
                    # Keep large scanned reports on disk on memory-limited Macs.
                    self.pdf_model.load(str(path))
                else:
                    self.pdf_buffer = QBuffer(self.pdf_model)
                    self.pdf_buffer.setData(path.read_bytes())
                    self.pdf_buffer.open(QIODevice.OpenModeFlag.ReadOnly)
                    self.pdf_model.load(self.pdf_buffer)
                self.pdf_loaded_path = str(path)
            if self.pdf_model.pageCount() > 0 and self.continuous_pdf.pageNavigator().currentPage() != number - 1:
                self.continuous_pdf.pageNavigator().jump(number - 1, QPointF(), 0)
        finally:
            self._navigating = was_navigating

    def set_status(self, text, state):
        self.status_chip.setText(text); self.status_chip.setProperty("state", state)
        self.status_chip.style().unpolish(self.status_chip); self.status_chip.style().polish(self.status_chip)

    def refresh_status(self):
        if not self.project_id: return self.set_status("No workpaper", "none")
        done = len(self.all_scores())
        if self.saved_form is not None and self.form_state() != self.saved_form: self.set_status("Unsaved edits", "dirty")
        elif done == len(self.items): self.set_status("Complete", "complete")
        elif done: self.set_status("Review in progress", "progress")
        else: self.set_status("Ready", "ready")

    def refresh_center(self):
        if not self.project_id:
            self.empty_title.setText("Open a workpaper to begin")
            self.empty_body.setText("Choose a company and fiscal year to open its workpaper.")
            self.empty_action.hide(); self.center_stack.setCurrentIndex(0)
        elif not self.docs:
            self.empty_title.setText("Import PDFs to begin")
            self.empty_body.setText("Add the company's report PDFs for this fiscal year. Reports stay where they are; only their hash and page count are recorded.")
            self.empty_action.show(); self.center_stack.setCurrentIndex(0)
        else: self.center_stack.setCurrentIndex(1)

    def on_form_changed(self):
        if self.loading_form: return
        self.update_validation(); self.refresh_status()

    def evidence_missing(self):
        return [n for n, v in (("document", self.doc_name.text().strip()), ("page", self.pages.text().strip())) if not v]

    def update_validation(self):
        missing = self.evidence_missing() if self.found.isChecked() else []
        self.validation.setText("Found needs a " + ", ".join(missing) + " before it can be saved." if missing else "")
        decided = self.found.isChecked() or self.absent.isChecked()
        self.save_button.setEnabled(bool(self.project_id) and decided and not missing)

    # ---- checklist -----------------------------------------------------
    def render_items(self):
        current_id = self.current["id"] if self.current else None
        self.item_list.blockSignals(True); self.item_list.clear()
        scores = self.all_scores()
        query = self.filter.text().casefold().strip()
        last_group = None
        for item in self.items:
            if query and query not in f"{item['id']} {item['title']} {item['pillar']} {' '.join(item['keywords'])}".casefold(): continue
            if item["pillar"] != last_group:
                last_group = item["pillar"]
                group = [candidate for candidate in self.items if candidate["pillar"] == last_group]
                reviewed = sum(candidate["id"] in scores for candidate in group)
                header = QListWidgetItem(f"{last_group.upper()}   \u00b7   {reviewed}/{len(group)} reviewed")
                font = header.font(); font.setBold(True); font.setPointSizeF(font.pointSizeF() * 0.9 if font.pointSizeF() > 0 else 9)
                header.setFont(font); header.setForeground(QColor("#a9bbb0")); header.setBackground(QColor("#13231b"))
                header.setFlags(Qt.ItemFlag.NoItemFlags); self.item_list.addItem(header)
            if item["id"] in scores:
                supported = scores[item["id"]][0] == 1
                marker = MARKS["supported" if supported else "unsupported"]; state = "supported" if supported else "reviewed, not supported"
            else: marker = MARKS["open"]; state = "not reviewed"
            lead = self.suggestions.get(item["id"])
            lead_text = f"  ·  proposed {lead['suggestion']}" if lead and item["id"] not in scores else ""
            row = QListWidgetItem(f"{marker}  {item['id']}  {item['title']}{lead_text}")
            if item["id"] in scores and scores[item["id"]][0] == 1: row.setForeground(QColor("#8fe0b0"))
            elif item["id"] not in scores: row.setForeground(QColor("#edf4ef"))
            else: row.setForeground(QColor("#a9bbb0"))
            row.setToolTip(f"{item['id']} \u2014 {item['title']} ({state})" + (f"; {lead['label']}" if lead else ""))
            row.setData(Qt.ItemDataRole.UserRole, item["id"]); self.item_list.addItem(row)
            if item["id"] == current_id: self.item_list.setCurrentItem(row)
        self.item_list.blockSignals(False)
        if not query and current_id == self.items[0]["id"]:
            self.item_list.scrollToTop()

    def item_row_changed(self, row):
        item = self.item_list.item(row)
        if item and item.data(Qt.ItemDataRole.UserRole):
            code = item.data(Qt.ItemDataRole.UserRole)
            self.select_item(next(i for i in self.items if i["id"] == code), redraw=False)

    def prerequisite_met(self, item, scores):
        required = PREREQ.get(item.get("stage"))
        return not required or scores.get(f"SDG{item['number']}-{required}", (0,))[0] == 1

    def select_item(self, item, redraw=True):
        if self.current and self.current["id"] != item["id"] and not self.confirm_unsaved():
            self.render_items(); return False
        self.loading_form = True
        self.current = item
        scores = self.all_scores()
        saved = scores.get(item["id"])
        self.item_title.setText(f"{item['id']}  {item['title']}")
        self.criterion.setText(f"{item['id']} \u00b7 {item['title']}")
        terms_text = "Search terms: " + ", ".join(item["keywords"])
        self.terms.setText(terms_text)
        self.terms.setToolTip(terms_text)
        self.update_prediction(item)
        if item["kind"] == "SDG":
            self.perspective.setText("SDG \u00b7 inside-out impact materiality")
            self.rule.setText(f"Stage weight {item['weight']} pt. Identified \u2192 Managed \u2192 Reported; each stage needs its own evidence.")
            self.update_stage_panel(scores)
            self.stage_box.show()
        else:
            self.perspective.setText("ESG \u00b7 outside-in financial materiality")
            self.rule.setText("Score 1 only for company-specific qualifying evidence beyond a generic mention. 1 point if supported.")
            self.stage_box.hide()
        locked = not self.prerequisite_met(item, scores)
        self.stage_context.setText(f"Locked: {PREREQ.get(item.get('stage'))} must be supported first." if locked else "")
        self.absent.setAutoExclusive(False); self.found.setAutoExclusive(False)
        self.absent.setChecked(bool(saved and saved[0] == 0)); self.found.setChecked(bool(saved and saved[0] == 1))
        self.absent.setAutoExclusive(True); self.found.setAutoExclusive(True)
        self.found.setEnabled(not locked or self.found.isChecked())
        self.doc_name.setText((saved[2] or "") if saved else ""); self.pages.setText((saved[3] or "") if saved else "")
        self.printed_pages.setText(self.store.score_records(self.project_id).get(item["id"], {}).get("printed_pages", "") if saved else "")
        self.evidence.setPlainText((saved[1] or "") if saved else "")
        self.refresh_pins(update_fields=not bool(saved))
        self.search_hits()
        self.saved_form = self.form_state(); self.loading_form = False
        self.update_validation(); self.refresh_status()
        if redraw: self.render_items()
        return True

    def update_prediction(self, item):
        lead = self.suggestions.get(item["id"])
        self.score_hint.setText((lead["label"] + ". " + lead["reason"]) if lead else "Import PDFs, then click Find leads.")
        if lead:
            best = lead["hits"][0] if lead["hits"] else None
            source = f"\nBest hit: {best['document']}, PDF p. {best['page']}" if best else "\nNo matching extractable passage"
            self.prediction.setText(f"{lead['label']}  ·  evidence lead only\n{lead['reason']}{source}")
        else: self.prediction.setText("Run Find leads to see a source passage.")
        self.apply_prediction_button.setEnabled(bool(lead and self.project_id))

    def form_state(self):
        return (self.found.isChecked(), self.absent.isChecked(), self.doc_name.text(),
                self.pages.text(), self.printed_pages.text(), self.evidence.toPlainText())

    def confirm_unsaved(self):
        if self.loading_form or self.saved_form is None or self.form_state() == self.saved_form: return True
        answer = QMessageBox.question(self, "Unsaved edits", "Save changes to this decision before continuing?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Cancel: return False
        if answer == QMessageBox.StandardButton.Save: return self.save() is True
        return True

    def closeEvent(self, event):
        if self.busy:
            event.ignore(); return
        if self.ocr_running:
            QMessageBox.information(self, "OCR in progress", "Wait for the current OCR run to finish before closing Verdant.")
            event.ignore(); return
        if not self.confirm_unsaved(): event.ignore(); return
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("reader_splitter_v2", self.reader_splitter.saveState())
        self.settings.setValue("checklist_splitter_v2", self.checklist_splitter.saveState())
        self.pdf_model.close()
        if self.pdf_buffer: self.pdf_buffer.close()
        if hasattr(self, "warning_popup"): self.warning_popup.close()
        event.accept()

    # ---- search and evidence viewer -------------------------------------
    def report_matches_year(self, name):
        year = self.active_year or self.year.currentText()
        named_years = set(re.findall(r"(?<!\d)20\d{2}(?!\d)", name))
        return not named_years or year in named_years

    def eligible_documents(self):
        eligible = []; skipped = []
        for name, pages in self.docs:
            (eligible if self.report_matches_year(name) else skipped).append((name, pages))
        return eligible, skipped

    def search_hits(self):
        self.hits = []
        eligible, _ = self.eligible_documents()
        for name, pages in eligible:
            for number, text in enumerate(pages, 1):
                found = [term for term in self.current["keywords"] if keyword_pattern(term).search(text)]
                if found:
                    match = keyword_pattern(found[0]).search(text)
                    excerpt = text[max(0, match.start() - 300):min(len(text), match.end() + 700)].replace("\n", " ")
                    self.hits.append((name, number, found, excerpt))
        self.hits.sort(key=lambda hit: (-len(hit[2]), hit[0], hit[1]))
        self.display_hits()
        self.refresh_center()

    def display_hits(self):
        query = self.keyword_filter.text().casefold().strip()
        self.visible_hits = [hit for hit in self.hits if not query or query in hit[3].casefold() or query in hit[0].casefold() or any(query in term.casefold() for term in hit[2])][:200]
        self.hit_list.clear(); self.preview.clear()
        for index, (name, number, found, _) in enumerate(self.visible_hits, 1):
            ocr_mark = " · OCR" if (name, number) in self.ocr_page_refs else ""
            row = QListWidgetItem(f"{index}.  {name} \u00b7 PDF page {number} \u00b7 {len(found)} term(s){ocr_mark}")
            row.setToolTip(row.text()); self.hit_list.addItem(row)
        if self.visible_hits:
            self.hit_count.setText(f"{len(self.visible_hits)} shown of {len(self.hits)} matching page(s) for this FY. Select a numbered hit to inspect the passage.")
        elif self.hits:
            self.hit_count.setText("No matching page passes this filter. Clear the filter to see all keyword hits.")
        else:
            self.hit_count.setText("No keyword matches. This is not proof of absence: inspect the report before scoring 0, and OCR image-only pages.")

    def show_hit(self, row):
        if row < 0 or row >= len(self.visible_hits): return
        name, number, found, excerpt = self.visible_hits[row]
        html = escape(excerpt)
        for term in sorted(found, key=len, reverse=True):
            html = re.sub(re.escape(escape(term)), lambda m: f'<mark style="background:#e0a82e;color:#101a17">{m.group()}</mark>', html, flags=re.I)
        source = " · OCR text" if (name, number) in self.ocr_page_refs else ""
        self.preview.setHtml(f'<p style="color:#a9bbb0">{escape(name)} \u00b7 PDF page {number}{source}</p><p style="line-height:1.5">{html}</p>')
        self.reader_tabs.setCurrentIndex(0)
        self.page_target = (name, number)
        self.pdf_document.blockSignals(True); self.pdf_document.setCurrentText(name); self.pdf_document.blockSignals(False)
        self.view_tabs.setCurrentIndex(1); self.render_page()

    def open_selected_document(self):
        name = self.pdf_document.currentText()
        if not name or name not in self.doc_paths: return
        self.page_target = (name, 1); self.render_page()

    def jump_to_page(self):
        name = self.pdf_document.currentText()
        if not name or name not in self.doc_paths: return
        self.page_target = (name, self.page_number.value()); self.render_page()

    def viewer_mode_changed(self, index):
        if index == 1:
            self.render_page()
        elif index == 0:
            if self.page_target:
                self.sync_continuous_pdf(self.page_target[0], self.page_target[1])
        self.update_page_footer()

    def update_extracted_text(self):
        if not self.page_target: self.extracted_text.clear(); return
        name, number = self.page_target
        pages = next((pages for document, pages in self.docs if document == name), [])
        text = pages[number - 1] if 1 <= number <= len(pages) else ""
        self.extracted_text.setPlainText(text if text.strip() else "")

    def reset_pdf_search(self):
        self.pdf_search_index = -1
        if self.find_scope.currentText() == "Checklist":
            self.filter.setText(self.pdf_search.text())
            self.pdf_search_count.setText("Checklist filtered")
            return
        self.filter.clear()
        self.pdf_search_count.setText("Press Enter to search" if self.pdf_search.text().strip() else "0 matches")

    def find_pdf_text(self, direction=1):
        if self.find_scope.currentText() == "Checklist":
            self.work_tabs.setCurrentIndex(1)
            self.filter.setText(self.pdf_search.text())
            return
        name = self.pdf_document.currentText()
        documents = self.docs if self.find_scope.currentText() == "All PDFs" else [
            (document, pages) for document, pages in self.docs if document == name]
        query = self.pdf_search.text().strip()
        matches = [(document, number, match.start(), match.end())
                   for document, pages in documents for number, text in enumerate(pages, 1)
                   for match in re.finditer(re.escape(query), text, re.I)] if query else []
        if not matches:
            self.pdf_search_count.setText("0 matches")
            return
        self.pdf_search_index = (getattr(self, "pdf_search_index", -1) + direction) % len(matches)
        document, number, start, end = matches[self.pdf_search_index]
        if self.pdf_document.currentText() != document:
            self.pdf_document.setCurrentText(document)
        self.page_target = (document, number)
        self.view_tabs.setCurrentIndex(1)
        self.render_page()
        self.reader_tabs.setCurrentIndex(1)
        cursor = self.extracted_text.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
        self.extracted_text.setTextCursor(cursor)
        self.extracted_text.ensureCursorVisible()
        self.pdf_search_count.setText(f"{self.pdf_search_index + 1} / {len(matches)} matches")

    def change_zoom(self, factor):
        if self.view_tabs.currentIndex() == 0:
            self.continuous_pdf.setZoomMode(QPdfView.ZoomMode.Custom)
            new_zoom = min(3.0, max(0.35, self.continuous_pdf.zoomFactor() * factor))
            self.continuous_pdf.setZoomFactor(new_zoom)
        else:
            if self.zoom_mode != "custom":
                self.zoom_scale = self.current_page_scale()
            self.zoom_mode = "custom"
            self.zoom_scale = min(3.0, max(0.35, self.zoom_scale * factor))
            self.render_page()
        self.update_page_footer()

    def set_zoom_mode(self, mode):
        if self.view_tabs.currentIndex() == 0:
            self.continuous_pdf.setZoomMode(QPdfView.ZoomMode.FitToWidth if mode == "width" else QPdfView.ZoomMode.FitInView)
        else:
            self.zoom_mode = mode
            self.render_page()
        self.update_page_footer()

    def current_page_scale(self):
        if not self.page_target: return 1.0
        name, number = self.page_target; path = self.doc_paths.get(name)
        if not path: return 1.0
        bounds_key = (str(path), number)
        if bounds_key not in self.page_bounds_cache:
            with fitz.open(path) as pdf:
                self.page_bounds_cache[bounds_key] = pdf[number - 1].rect
        bounds = self.page_bounds_cache[bounds_key]
        width = max(300, self.page_scroll.viewport().width() - 16)
        height = max(250, self.page_scroll.viewport().height() - 16)
        if self.zoom_mode == "page": return min(3.0, max(0.35, min(width / bounds.width, height / bounds.height)))
        if self.zoom_mode == "width": return min(3.0, max(0.35, width / bounds.width))
        return self.zoom_scale

    def step_page(self, delta):
        if not self.page_target: return
        name, number = self.page_target
        total = len(next(pages for doc, pages in self.docs if doc == name))
        self.page_target = (name, min(max(1, number + delta), total)); self.render_page()

    def render_page(self):
        if not self.page_target: return
        name, number = self.page_target
        path = self.doc_paths.get(name)
        if not path: return
        self.sync_continuous_pdf(name, number)

        pages = next((pages for document, pages in self.docs if document == name), [])
        total = len(pages)
        self.page_number.blockSignals(True)
        self.page_number.setMaximum(max(1, total))
        self.page_number.setValue(number)
        self.page_number.blockSignals(False)
        self.page_total.setText(f"/ {total}")
        self.pdf_document.blockSignals(True)
        self.pdf_document.setCurrentText(name)
        self.pdf_document.blockSignals(False)
        self.page_prev.setEnabled(number > 1)
        self.page_next.setEnabled(number < total)

        page_text = pages[number - 1] if 1 <= number <= len(pages) else ""
        if self.ocr_current == (name, number) and self.ocr_running: status = "OCR processing"
        elif (name, number) in self.ocr_failed_pages: status = "OCR failed · retry available"
        elif (name, number) in self.ocr_page_refs: status = "OCR completed · review recommended"
        elif page_text.strip(): status = "Native text available"
        else: status = "No extractable text · OCR pending"
        self.page_status.setText(status)
        self.update_extracted_text()

        # Render highlighted page pixmap only when Highlighted page tab (index 1) is visible
        if self.view_tabs.currentIndex() == 1:
            try:
                scale = self.current_page_scale()
                search_term = self.pdf_search.text().strip()
                cache_key = (str(path), path.stat().st_mtime_ns, number, self.current["id"], search_term, round(scale, 3))
                if cache_key in self.render_cache:
                    pixmap, label, total, match_count, ocr_highlight = self.render_cache[cache_key]
                    self.render_cache.move_to_end(cache_key)
                else:
                    self.statusBar().showMessage(f"Rendering {name}, PDF page {number}...")
                    with fitz.open(path) as pdf:
                        page = pdf[number - 1]; label = page.get_label() if hasattr(page, "get_label") else ""
                        ocr = (name, number) in self.ocr_page_refs
                        highlight_key = (str(path), number, self.current["id"], search_term)
                        if highlight_key not in self.highlight_cache:
                            tessdata = find_tessdata() if ocr else None
                            self.highlight_cache[highlight_key] = keyword_rects(page, [search_term] if search_term else self.current["keywords"],
                                ocr=ocr and bool(tessdata), tessdata=tessdata)
                        rectangles = self.highlight_cache[highlight_key]
                        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                        painter = QPainter(image); painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
                        painter.setPen(QPen(QColor(150, 95, 0), 2))
                        for rect in rectangles:
                            x, y, w, h = (int(rect.x0 * scale), int(rect.y0 * scale), int(rect.width * scale), int(rect.height * scale))
                            painter.fillRect(x, y, w, h, QColor(255, 200, 60, 175)); painter.drawRect(x, y, w, h)
                        painter.end(); total = len(pdf); match_count = len(rectangles)
                        ocr_highlight = ocr and bool(find_tessdata())
                        pixmap = QPixmap.fromImage(image)
                    self.render_cache[cache_key] = (pixmap, label, total, match_count, ocr_highlight)
                    self.render_cache_bytes += pixmap.width() * pixmap.height() * 4
                    while self.render_cache_bytes > 80 * 1024 * 1024 and len(self.render_cache) > 1:
                        _, (old, _, _, _, _) = self.render_cache.popitem(last=False)
                        self.render_cache_bytes -= old.width() * old.height() * 4
                self.page_image.setPixmap(pixmap); self.page_image.resize(pixmap.size())
                self._current_label = label
                self._current_match_count = match_count
                self._current_ocr_highlight = ocr_highlight
            except Exception as exc:
                self.page_image.setText(f"Could not render page: {exc}")
            finally:
                self.statusBar().clearMessage()
        else:
            self._current_label = ""
            self._current_match_count = 0
            self._current_ocr_highlight = False
            self.statusBar().clearMessage()

        self.update_page_footer()

    def update_page_footer(self):
        if not self.page_target:
            self.page_label.setText("No page selected")
            self.page_label.setToolTip("")
            return
        name, number = self.page_target
        pages = next((pages for document, pages in self.docs if document == name), [])
        total = len(pages)
        label = getattr(self, "_current_label", "")
        printed = f" \u00b7 printed page label \u201c{label}\u201d" if label and label != str(number) else " \u00b7 printed page number not detected"
        ocr_note = " · OCR text" if (name, number) in self.ocr_page_refs else ""
        if self.view_tabs.currentIndex() == 0:
            scale_pct = round(self.continuous_pdf.zoomFactor() * 100)
            highlight_note = "continuous reader"
        else:
            scale_pct = round(self.current_page_scale() * 100)
            mc = getattr(self, "_current_match_count", 0)
            oh = getattr(self, "_current_ocr_highlight", False)
            highlight_note = f"{mc} highlighted match(es)" if oh or (name, number) not in self.ocr_page_refs else "OCR highlight geometry unavailable"
        full_text = f"{name} \u00b7 PDF page {number} of {total}{printed}{ocr_note} · {highlight_note} · {scale_pct}%"
        self.page_label.setText(full_text)
        self.page_label.setToolTip(full_text)

    def pin_hit(self):
        if not self.project_id or not self.current:
            return
        row = self.hit_list.currentRow()
        from_extracted = self.reader_tabs.currentIndex() == 1
        selected = self.extracted_text.textCursor().selectedText() if from_extracted else self.preview.textCursor().selectedText()
        if row < 0 and not (selected and self.page_target): return
        if selected and from_extracted and self.page_target:
            name, number = self.page_target
            excerpt = ""
        else:
            name, number, _, excerpt = self.visible_hits[row] if row >= 0 else (*self.page_target, [], "")
            if self.page_target and self.page_target != (name, number):
                return QMessageBox.information(self, "Select a passage", "This hit belongs to another PDF page. Select text on the current page before pinning.")
        passage = selected.replace("\u2029", "\n").strip() if selected else excerpt.strip()
        if not passage:
            return QMessageBox.information(self, "Select a passage", "Select text in Evidence context or Extracted text before pinning.")
        printed_page = ""
        path = self.doc_paths.get(name)
        if path:
            try:
                with fitz.open(path) as pdf:
                    printed_page = pdf[number - 1].get_label() or ""
            except Exception:
                pass
        self.store.add_evidence_pin(self.project_id, self.current["id"], name, number, passage, printed_page)
        self.refresh_pins(update_fields=True)
        self.statusBar().showMessage(f"Pinned {name}, PDF page {number} to {self.current['id']}", 4000)

    def refresh_pins(self, update_fields=False):
        code = self.current["id"] if self.current else ""
        pins = self.store.evidence_pins(self.project_id, code) if self.project_id and code else []
        for listing in (self.reader_pins, self.decision_pins):
            listing.clear()
            for pin in pins:
                snippet = pin["excerpt"].replace("\n", " ")
                row = QListWidgetItem(f"{pin['document']} · PDF p. {pin['page']} · {snippet[:95]}")
                row.setData(Qt.ItemDataRole.UserRole, pin["id"])
                row.setToolTip(pin["excerpt"])
                listing.addItem(row)
        self.reader_pin_label.setText(f"Pinned passages for {code}: {len(pins)}")
        self.decision_pin_label.setText(f"Pinned passages for {code}: {len(pins)}")
        if update_fields and pins:
            documents = list(dict.fromkeys(pin["document"] for pin in pins))
            pages = list(dict.fromkeys(str(pin["page"]) for pin in pins))
            printed = list(dict.fromkeys(pin["printed_page"] for pin in pins if pin["printed_page"]))
            self.doc_name.setText("; ".join(documents))
            self.pages.setText(", ".join(pages))
            self.printed_pages.setText(", ".join(printed))
        self.update_validation()

    def remove_selected_pin(self):
        selected = self.decision_pins.currentItem() or self.reader_pins.currentItem()
        if not selected or not self.project_id:
            return
        pin_id = selected.data(Qt.ItemDataRole.UserRole)
        self.store.remove_evidence_pin(self.project_id, self.current["id"], pin_id)
        pins = self.store.evidence_pins(self.project_id, self.current["id"])
        if pins:
            self.refresh_pins(update_fields=True)
        else:
            self.refresh_pins()
        self.statusBar().showMessage(f"Removed pin from {self.current['id']}", 4000)

    def choose_reports_folder(self):
        root = QFileDialog.getExistingDirectory(self, "Choose reports folder",
            str(self.store.reports_root() or Path.home()))
        if not root: return
        try: self.store.set_reports_root(root)
        except Exception as exc: return QMessageBox.warning(self, "Reports folder", str(exc))
        if self.project_id: self.load_reports()
        self.statusBar().showMessage(f"Reports folder: {root}", 8000)

    def relink_missing_pdf(self):
        if not self.project_id: return QMessageBox.information(self, "Workpaper", "Select a company and fiscal year first.")
        missing = [(path, digest) for path, digest, _, _ in self.store.reports(self.project_id) if not Path(path).exists()]
        if not missing: return QMessageBox.information(self, "Reports", "No missing PDFs in this workpaper.")
        labels = [f"{Path(path).name}  [{digest[:12]}]" for path, digest in missing]
        label, ok = QInputDialog.getItem(self, "Relink missing PDF", "Missing report", labels, 0, False)
        if not ok: return
        old, digest = missing[labels.index(label)]
        candidate, _ = QFileDialog.getOpenFileName(self, "Locate replacement PDF", str(self.store.reports_root() or Path.home()), "PDF files (*.pdf)")
        if not candidate: return
        actual = hashlib.sha256(Path(candidate).read_bytes()).hexdigest()
        allow_name = False
        if actual != digest:
            if Path(candidate).name.casefold() != Path(old).name.casefold():
                return QMessageBox.warning(self, "PDF mismatch", "Neither the file hash nor filename matches the missing report.")
            allow_name = QMessageBox.question(self, "PDF changed",
                "The filename matches but SHA-256 differs. Relinking will discard cached OCR and score leads for this PDF. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Yes
            if not allow_name: return
        try: method = self.store.relink_report(self.project_id, old, candidate, allow_name)
        except Exception as exc: return QMessageBox.warning(self, "Relink failed", str(exc))
        self.load_reports(); self.statusBar().showMessage(f"Relinked by {method}: {Path(candidate).name}", 8000)

    def import_roster(self):
        source, _ = QFileDialog.getOpenFileName(self, "Import company roster", "", "Excel (*.xlsx)")
        if not source: return
        self.apply_roster_path(source)

    def apply_roster_path(self, source):
        try:
            names = load_companies(Path(source))
            if not names: raise ValueError("The Companies sheet has no company names in column C from row 4.")
            destination = DATA_DIR / "roster.xlsx"
            if Path(source).resolve() != destination.resolve(): shutil.copy2(source, destination)
        except Exception as exc: return QMessageBox.warning(self, "Roster import failed", str(exc))
        self.companies = names
        selected = self.company.currentText()
        self.company.blockSignals(True); self.company.clear(); self.company.addItem("Select a company")
        self.company.addItems(names)
        if selected in names: self.company.setCurrentText(selected)
        self.company.blockSignals(False)
        self.statusBar().showMessage(f"Imported roster with {len(names)} companies.", 8000)

    def first_run_setup(self):
        if self.store.setting("first_run_complete"):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Welcome to Verdant")
        dialog.setMinimumWidth(560)
        layout = QVBoxLayout(dialog)
        intro = QLabel("Choose a reports folder and scorer name. You can change these later from Workpaper.")
        intro.setWordWrap(True); layout.addWidget(intro)
        layout.addWidget(QLabel("Reports folder"))
        default_reports = Path.home() / "Documents"
        reports = QLineEdit(); reports.setText(self.store.setting("reports_root", str(default_reports if default_reports.is_dir() else Path.home()))); layout.addWidget(reports)
        layout.addWidget(self.button("Browse reports folder", lambda: reports.setText(
            QFileDialog.getExistingDirectory(dialog, "Choose reports folder", reports.text()))))
        layout.addWidget(QLabel("Scorer name"))
        scorer = QLineEdit(); scorer.setText(self.store.setting("scorer_name", "")); layout.addWidget(scorer)
        layout.addWidget(QLabel("Roster workbook (optional)"))
        roster = QLineEdit(); layout.addWidget(roster)
        layout.addWidget(self.button("Browse roster", lambda: roster.setText(
            QFileDialog.getOpenFileName(dialog, "Choose roster", "", "Excel (*.xlsx)")[0])))
        controls = QHBoxLayout(); controls.addStretch()
        controls.addWidget(self.button("Continue", dialog.accept, True)); layout.addLayout(controls)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if reports.text().strip():
            try: self.store.set_reports_root(reports.text().strip())
            except ValueError as exc: QMessageBox.warning(self, "Reports folder", str(exc))
        self.store.set_setting("scorer_name", scorer.text().strip())
        if roster.text().strip(): self.apply_roster_path(roster.text().strip())
        self.store.set_setting("first_run_complete", "1")

    def export_portable_workpaper(self):
        if not self.project_id: return QMessageBox.information(self, "Workpaper", "Select a company and fiscal year first.")
        company = self.active_company.replace("/", "-").replace("\\", "-")
        path, _ = QFileDialog.getSaveFileName(self, "Export workpaper",
            f"{company}_{self.active_year}.verdant", "Verdant workpaper (*.verdant)")
        if not path: return
        try: export_workpaper(self.store, self.project_id, path)
        except Exception as exc: return QMessageBox.warning(self, "Export failed", str(exc))
        self.statusBar().showMessage(f"Exported workpaper: {path}", 8000)

    def import_portable_workpaper(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import workpaper", "", "Verdant workpaper (*.verdant)")
        if not path: return
        if not self.store.reports_root():
            self.choose_reports_folder()
            if not self.store.reports_root(): return
        try:
            preview = import_workpaper(self.store, path)
            if preview["conflicts"]:
                details = "\n".join(f"{entry['item']}: keep {entry['winner']} (newest timestamp)" for entry in preview["conflicts"][:30])
                answer = QMessageBox.question(self, "Workpaper conflicts",
                    f"{len(preview['conflicts'])} saved item(s) differ:\n{details}\n\nImport and apply the newer decisions?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel)
                if answer != QMessageBox.StandardButton.Yes: return
                preview = import_workpaper(self.store, path, accept_newer=True)
            project = preview["project_id"]
            company, year = self.store.project_info(project)
        except Exception as exc: return QMessageBox.warning(self, "Import failed", str(exc))
        if company not in self.companies:
            self.companies.append(company); self.company.addItem(company)
        self.company.setCurrentText(company); self.year.setCurrentText(year)
        self.project_id = project; self.after_open(company, year)
        self.statusBar().showMessage(f"Imported workpaper: {company}, FY {year}", 8000)

    # ---- workpapers and reports ----------------------------------------
    def open_project(self):
        company = self.company.currentText(); year = self.year.currentText()
        if self.ocr_running or self.busy:
            self.pending_selection = (company, year)
            self.statusBar().showMessage(f"Pending workpaper: {company}, FY {year}; opens after the current task finishes.")
            return
        if company not in self.companies:
            return
        if year not in {"2022", "2023", "2024", "2025"}:
            self.statusBar().showMessage("Choose a fiscal year to open this company workpaper.", 6000)
            return
        if (company, year) == (self.active_company, self.active_year): return
        if not self.confirm_unsaved(): return
        self.project_id = self.store.project(company, year)
        self.after_open(company, year)

    def after_open(self, company, year):
        self.suggestions = {}
        self.ocr_state = ""
        self.ocr_failed_pages = set()
        self.active_company = company; self.active_year = year
        self.context_title.setText("Company Workpaper"); self.context_sub.setText(f"{company} \u00b7 FY {year}")
        self.controls_panel.hide()
        self.load_reports(); self.select_item(self.current); self.refresh_totals()
        self.review_toggle.setChecked(not bool(self.suggestions))
        self.statusBar().showMessage(f"Open: {company}, FY {year}", 4000)

    def open_saved(self):
        if self.ocr_running: return QMessageBox.information(self, "OCR in progress", "Wait for OCR to finish before changing workpapers.")
        if not self.confirm_unsaved(): return
        projects = self.store.projects()
        if not projects: return QMessageBox.information(self, "Saved workpapers", "No saved workpapers yet.")
        dialog = QDialog(self); dialog.setWindowTitle("Saved workpapers"); dialog.resize(560, 430)
        box = QVBoxLayout(dialog); box.addWidget(QLabel("Select a company-year workpaper"))
        listing = QListWidget()
        for project_id, company, year in projects:
            row = QListWidgetItem(f"{company}  ·  FY {year}")
            row.setData(Qt.ItemDataRole.UserRole, (project_id, company, year)); listing.addItem(row)
        listing.setCurrentRow(0); box.addWidget(listing)
        actions = QHBoxLayout(); open_button = self.button("Open selected", dialog.accept, True)
        delete_button = self.button("Delete selected", lambda: self.delete_saved(listing, dialog))
        close_button = self.button("Close", dialog.reject)
        actions.addWidget(open_button); actions.addWidget(delete_button); actions.addStretch(); actions.addWidget(close_button)
        box.addLayout(actions); listing.itemDoubleClicked.connect(lambda *_: dialog.accept())
        if dialog.exec() != QDialog.DialogCode.Accepted or not listing.currentItem(): return
        project_id, company, year = listing.currentItem().data(Qt.ItemDataRole.UserRole)
        self.company.setCurrentText(company); self.year.setCurrentText(year); self.project_id = project_id
        self.after_open(company, year)

    def delete_saved(self, listing, dialog):
        row = listing.currentItem()
        if not row: return
        project_id, company, year = row.data(Qt.ItemDataRole.UserRole)
        answer = QMessageBox.question(self, "Delete workpaper",
            f"Delete {company}, FY {year} and its saved scores, report references, and audit entries? Original PDF files stay on disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes: return
        self.store.delete_project(project_id)
        listing.takeItem(listing.row(row))
        if self.project_id == project_id:
            self.project_id = None; self.docs = []; self.doc_paths = {}; self.suggestions = {}
            self.active_company = None; self.active_year = None
            self.prediction_totals.hide()
            self.context_sub.setText("No workpaper open"); self.warning_panel.hide()
            self.warning_popup.hide()
            self.controls_panel.show()
            self.refresh_center(); self.refresh_totals(); self.render_items(); self.update_prediction(self.current)
        self.statusBar().showMessage(f"Deleted {company}, FY {year}", 6000)
        if not listing.count(): dialog.reject()

    def load_reports(self):
        previous_page = self.page_target
        self.pdf_model.close(); self.pdf_loaded_path = None
        if self.pdf_buffer:
            self.pdf_buffer.close(); self.pdf_buffer.deleteLater(); self.pdf_buffer = None
        self.docs = []; self.doc_paths = {}; self.suggestions = {}; self.ocr_tasks = []; self.ocr_page_refs = set()
        self.highlight_cache = {}; self.render_cache.clear(); self.render_cache_bytes = 0
        self.page_bounds_cache.clear()
        warnings = []; notes = []
        for raw_path, old_hash, _, scanned in self.store.reports(self.project_id):
            path = Path(raw_path)
            if not path.exists(): warnings.append(f"Missing: {path.name}"); continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != old_hash:
                warnings.append(f"Changed since import: {path.name}"); continue
            try:
                with fitz.open(path) as pdf: pages = [page.get_text("text") for page in pdf]
                cached = self.store.ocr_text(self.project_id, path, old_hash)
                for number, text in cached.items():
                    if 1 <= number <= len(pages) and not pages[number - 1].strip():
                        pages[number - 1] = text; self.ocr_page_refs.add((path.name, number))
                missing = [number for number, text in enumerate(pages, 1) if not text.strip()]
                if missing and self.report_matches_year(path.name): self.ocr_tasks.append((str(path), old_hash, missing))
                self.docs.append((path.name, pages)); self.doc_paths[path.name] = path
                if missing and self.report_matches_year(path.name):
                    page_list = ", ".join(str(number) for number in missing[:30])
                    if len(missing) > 30: page_list += ", ..."
                    notes.append(f"{path.name}: {len(missing)} page(s) need OCR (PDF pages {page_list}); not searched")
            except Exception as exc: warnings.append(f"{path.name}: {exc}")
        banner = [("Blocked – " + w) for w in warnings] + ["OCR – " + n for n in notes]
        if warnings: self.store.clear_predictions(self.project_id)
        else: self.suggestions = self.store.predictions(self.project_id)
        pending = sum(len(numbers) for _, _, numbers in self.ocr_tasks)
        summary = f"⚠ {pending} page(s) need OCR" if pending else "No pages need OCR"
        if warnings: summary += f" · {len(warnings)} report issue(s)"
        if self.ocr_state: summary += f" · {self.ocr_state}"
        self.ocr_summary.setText(summary)
        self.doc_warning.setText("\n".join(banner) if banner else "All imported pages have searchable text or cached OCR text.")
        self.warning_panel.setVisible(bool(banner or self.ocr_state))
        if not (banner or self.ocr_state):
            self.warning_popup.hide()
            self.warning_toggle.setChecked(False)
        self.ocr_button.setVisible(bool(self.ocr_tasks)); self.ocr_button.setEnabled(bool(self.ocr_tasks) and not self.ocr_running)
        self.ocr_selected_button.setVisible(bool(self.ocr_tasks))
        self.review_ocr_button.setVisible(bool(self.ocr_tasks))
        if warnings: QMessageBox.warning(self, "Report review", "\n".join(warnings + notes))
        self.pdf_document.blockSignals(True); self.pdf_document.clear()
        self.pdf_document.addItems([name for name, _ in self.docs])
        self.pdf_document.blockSignals(False)
        names = {name for name, _ in self.docs}
        if previous_page and previous_page[0] in names:
            count = len(next(pages for name, pages in self.docs if name == previous_page[0]))
            self.page_target = (previous_page[0], min(previous_page[1], count)) if count else None
        elif self.docs: self.page_target = (self.docs[0][0], 1)
        else: self.page_target = None
        self.search_hits()
        if self.page_target: self.render_page()
        else:
            self.page_image.setPixmap(QPixmap()); self.page_image.setText("Import a PDF to view its original pages.")
            self.page_label.setText("No page selected"); self.page_status.setText("No document")
            self.extracted_text.clear()

    def begin_background(self, worker, total, message):
        self.busy = True
        self.background_worker = worker
        self.background_project_id = self.project_id
        self.task_progress.setRange(0, max(1, total)); self.task_progress.setValue(0)
        self.task_progress.show(); self.task_cancel.show()
        self.statusBar().showMessage(message)
        worker.finished.connect(lambda: setattr(self, "background_worker", None))
        worker.start()

    def cancel_background(self):
        if self.background_worker:
            self.background_worker.requestInterruption()
            self.statusBar().showMessage("Cancel requested; finishing the current page...")

    def end_background(self):
        self.busy = False
        self.task_progress.hide(); self.task_cancel.hide()
        if self.pending_selection:
            company, year = self.pending_selection
            self.pending_selection = None
            self.company.setCurrentText(company); self.year.setCurrentText(year)
            self.open_project()

    def import_pdfs_background(self):
        if self.busy or self.ocr_running:
            return self.statusBar().showMessage("Wait for the current task to finish.", 5000)
        if not self.project_id:
            return QMessageBox.information(self, "Workpaper", "Select a company and fiscal year first.")
        paths, _ = QFileDialog.getOpenFileNames(self, "Import company reports", "", "PDF files (*.pdf)")
        if not paths: return
        worker = ImportWorker(paths)
        worker.progress.connect(lambda done, total, label: (
            self.task_progress.setMaximum(max(1, total)), self.task_progress.setValue(done),
            self.statusBar().showMessage(f"Importing {label} · {done}/{total}")))
        worker.completed.connect(self.import_background_completed)
        self.begin_background(worker, len(paths), f"Importing {len(paths)} PDF(s); you can keep reading.")

    def import_background_completed(self, records, errors, canceled):
        project = self.background_project_id
        for path, digest, count, scanned in records:
            try: self.store.add_report(project, path, digest, count, scanned)
            except Exception as exc: errors.append(f"{Path(path).name}: {exc}")
        if project == self.project_id:
            self.load_reports(); self.update_prediction(self.current); self.refresh_totals(); self.render_items()
        self.end_background()
        if errors: QMessageBox.warning(self, "Import review", "\n".join(errors))
        self.statusBar().showMessage(("Import canceled; " if canceled else "") + f"Imported {len(records)} PDF(s).", 8000)

    def import_pdfs(self):
        if self.ocr_running: return QMessageBox.information(self, "OCR in progress", "Wait for OCR to finish before importing more PDFs.")
        if not self.project_id: return QMessageBox.warning(self, "Open workpaper", "Open a company-year workpaper first.")
        if self.active_company and (self.company.currentText(), self.year.currentText()) != (self.active_company, self.active_year):
            return QMessageBox.warning(self, "Open selected workpaper", "The company or fiscal year selection changed. Click Open workpaper before importing PDFs.")
        paths, _ = QFileDialog.getOpenFileNames(self, "Import company reports", "", "PDF files (*.pdf)")
        if not paths: return
        self.ocr_state = ""
        self.busy = True
        progress = self.progress_dialog("Importing PDFs", "Reading report pages...", 1)
        warnings = []
        cancelled = False; completed = 0; total = 0
        try:
            for raw in paths:
                try:
                    with fitz.open(raw) as pdf: total += len(pdf)
                except Exception: pass
            progress.setMaximum(max(1, total))
            for raw in paths:
                path = Path(raw)
                try:
                    pages = []
                    with fitz.open(path) as pdf:
                        for number, page in enumerate(pdf, 1):
                            pages.append(page.get_text("text"))
                            completed += 1
                            progress.setLabelText(f"Reading {path.name} · page {number}/{len(pdf)}")
                            progress.setValue(completed)
                            if progress.wasCanceled(): raise OperationCancelled()
                    progress.setLabelText(f"Saving {path.name}...")
                    scanned = sum(not text.strip() for text in pages)
                    self.store.add_report(self.project_id, path, hashlib.sha256(path.read_bytes()).hexdigest(), len(pages), scanned)
                    if scanned: warnings.append(f"{path.name}: {scanned} page(s) need OCR")
                except OperationCancelled:
                    cancelled = True; break
                except Exception as exc: warnings.append(f"{path.name}: {exc}")
        finally:
            progress.close(); self.busy = False
        self.load_reports()
        self.update_prediction(self.current); self.refresh_totals(); self.render_items()
        if warnings: QMessageBox.warning(self, "Import review", "\n".join(warnings))
        self.statusBar().showMessage(("Import canceled; completed PDFs were kept. " if cancelled else "") + f"Loaded {len(self.docs)} PDF report(s)", 8000)

    def start_ocr(self, mode="all"):
        if self.ocr_running or not self.project_id or not self.ocr_tasks: return
        tasks = list(self.ocr_tasks)
        if mode in ("current", "selected"):
            name = self.page_target[0] if self.page_target else self.pdf_document.currentText()
            tasks = [task for task in tasks if Path(task[0]).name == name]
            if not tasks:
                return QMessageBox.information(self, "No OCR needed", "This PDF has no pages waiting for OCR.")
            if mode == "current":
                page = self.page_target[1] if self.page_target else self.page_number.value()
                tasks = [(path, digest, [page]) for path, digest, numbers in tasks if page in numbers]
            else:
                maximum = len(next(pages for document, pages in self.docs if document == name))
                raw, ok = QInputDialog.getText(self, "OCR selected pages",
                    f"Enter PDF page numbers for {name} (1-{maximum}), e.g. 2, 5-7:", text=str(self.page_number.value()))
                if not ok: return
                try: selected = set(parse_page_numbers(raw, maximum))
                except ValueError as exc: return QMessageBox.warning(self, "Invalid page selection", str(exc))
                tasks = [(path, digest, [number for number in numbers if number in selected]) for path, digest, numbers in tasks]
                tasks = [task for task in tasks if task[2]]
            if not tasks:
                return QMessageBox.information(self, "No OCR needed", "The selected page(s) already have searchable text or cached OCR.")
        tessdata = find_tessdata()
        if not tessdata:
            return QMessageBox.warning(self, "Tesseract language data needed",
                "English OCR data is missing. Restore Verdant\\tessdata\\eng.traineddata, "
                "or set TESSDATA_PREFIX to a folder containing eng.traineddata, then retry.")
        self.ocr_running = True; self.ocr_project_id = self.project_id
        self.ocr_state = "processing"
        self.warning_panel.show()
        self.ocr_summary.setText(f"OCR processing · 0/{sum(len(n) for _,_,n in tasks)} pages")
        self.ocr_progress_bar.show()
        self.ocr_progress_bar.setValue(0)
        self.ocr_worker = OCRWorker(tasks, tessdata)
        self.ocr_worker.progress.connect(self.ocr_progress)
        self.ocr_worker.completed.connect(self.ocr_completed)
        self.ocr_worker.finished.connect(self.ocr_finished)
        self.ocr_button.setEnabled(False)
        self.ocr_selected_button.setEnabled(False)
        self.cancel_ocr_button.show()
        total = sum(len(numbers) for _, _, numbers in tasks)
        self.statusBar().showMessage(f"OCR started: {total} image-only page(s). The original PDFs stay unchanged.")
        self.ocr_worker.start()

    def cancel_ocr(self):
        if self.ocr_running and self.ocr_worker:
            self.ocr_worker.requestInterruption()
            self.ocr_summary.setText("Stopping OCR after the current page...")

    def ocr_progress(self, done, total, name, page):
        self.ocr_current = (name, page)
        self.ocr_summary.setText(f"OCR processing · {done}/{total} pages · {name}, page {page}")
        self.ocr_progress_bar.setValue(int(done / max(1, total) * 100))
        self.statusBar().showMessage(f"OCR {done}/{total}: {name}, PDF page {page}")
        if self.page_target == (name, page): self.page_status.setText("OCR processing")

    def ocr_completed(self, results, errors):
        saved = self.store.save_ocr_pages(self.ocr_project_id, results)
        canceled = self.ocr_worker.isInterruptionRequested() if self.ocr_worker else False
        self.ocr_state = ("canceled" if canceled else "completed" if not errors else "partial success" if saved else "failed")
        for message in errors:
            match = re.match(r"(.+), page (\d+):", message)
            if match: self.ocr_failed_pages.add((match.group(1), int(match.group(2))))
        for path, _, number, _ in results: self.ocr_failed_pages.discard((Path(path).name, number))
        if self.project_id == self.ocr_project_id:
            self.load_reports()
            if saved:
                eligible, _ = self.eligible_documents()
                self.suggestions = assess_all(self.items, eligible)
                self.store.save_predictions(self.project_id, self.items, self.suggestions)
            self.update_prediction(self.current)
            self.refresh_totals(); self.render_items()
        self.statusBar().showMessage(f"OCR complete: {saved} page(s) now searchable; {len(errors)} unresolved.", 15000)
        if errors:
            QMessageBox.warning(self, "OCR review", "Some pages remain unreadable:\n" + "\n".join(errors[:10]))

    def ocr_finished(self):
        self.ocr_running = False
        self.ocr_current = None
        self.ocr_progress_bar.hide()
        self.ocr_button.setEnabled(bool(self.ocr_tasks))
        self.ocr_selected_button.setEnabled(bool(self.ocr_tasks))
        self.cancel_ocr_button.hide()
        self.ocr_worker = None
        if self.pending_selection:
            company, year = self.pending_selection
            self.pending_selection = None
            self.company.setCurrentText(company); self.year.setCurrentText(year)
            self.open_project()

    def find_leads_background(self):
        if self.busy or self.ocr_running:
            return self.statusBar().showMessage("Wait for the current task to finish.", 5000)
        if not self.project_id or not self.docs:
            return QMessageBox.information(self, "Add PDF reports", "Select a workpaper and import PDF reports first.")
        eligible, skipped = self.eligible_documents()
        if not eligible:
            return QMessageBox.information(self, "No reports for selected year", "Add a report for this fiscal year first.")
        self.background_skipped = len(skipped)
        worker = LeadWorker(self.items, eligible, self.active_company)
        worker.progress.connect(lambda done, total, code: (
            self.task_progress.setValue(done),
            self.statusBar().showMessage(f"Finding leads: {code} · {done}/{total}")))
        worker.completed.connect(self.leads_background_completed)
        self.begin_background(worker, len(self.items), "Finding leads; you can keep reading.")

    def leads_background_completed(self, results, error):
        project = self.background_project_id
        if results is not None:
            self.store.save_predictions(project, self.items, results)
            if project == self.project_id:
                self.suggestions = results; self.skipped_reports = self.background_skipped
                self.review_toggle.setChecked(False)
                self.update_prediction(self.current); self.refresh_totals(); self.render_items()
        self.end_background()
        if error and error != "canceled":
            QMessageBox.warning(self, "Find leads failed", error)
        else:
            self.statusBar().showMessage("Lead finding canceled." if error else
                f"Found {sum(result['suggestion'] for result in results.values())} items with leads.", 8000)

    def check_for_score(self):
        if self.busy: return
        if self.ocr_running: return QMessageBox.information(self, "OCR in progress", "Wait for OCR to finish before checking scores.")
        if not self.project_id:
            return QMessageBox.warning(self, "Open workpaper", "Choose a company and fiscal year, then open its workpaper.")
        if not self.docs:
            return QMessageBox.warning(self, "Add PDF reports", "Import locally downloaded PDF reports before checking for score leads.")
        if self.active_company and (self.company.currentText(), self.year.currentText()) != (self.active_company, self.active_year):
            return QMessageBox.warning(self, "Open selected workpaper", "The company or fiscal year selection changed. Click Open workpaper before checking scores.")
        fiscal_year = self.active_year or self.year.currentText()
        eligible, skipped = self.eligible_documents()
        if not eligible:
            return QMessageBox.warning(self, "No reports for selected year",
                f"The imported filenames identify other fiscal years. Add a report for FY {fiscal_year} before checking scores.")
        self.busy = True
        progress = self.progress_dialog("Checking scores", "Checking 81 rubric decisions...", len(self.items))
        try:
            def advance(done, total, code):
                progress.setLabelText(f"Checking {code} · {done}/{total}")
                progress.setValue(done)
                if progress.wasCanceled(): raise OperationCancelled()
            results = assess_all(self.items, eligible, advance, self.active_company)
        except OperationCancelled:
            self.statusBar().showMessage("Score check canceled; previous proposals were kept.", 8000)
            return
        finally:
            progress.close(); self.busy = False
        self.suggestions = results
        self.store.save_predictions(self.project_id, self.items, self.suggestions)
        leads = sum(result["suggestion"] for result in self.suggestions.values())
        self.skipped_reports = len(skipped)
        self.review_toggle.setChecked(False)
        self.update_prediction(self.current)
        self.refresh_totals(); self.render_items()
        self.statusBar().showMessage(f"Found {leads} items with leads. All decisions require reviewer approval.", 15000)

    def apply_prediction(self):
        lead = self.suggestions.get(self.current["id"])
        if not lead: return
        if lead["suggestion"] == 1:
            if not self.found.isEnabled():
                return QMessageBox.information(self, "SDG prerequisite", "Review and save the required earlier stage first.")
            best = lead["hits"][0]
            self.found.setChecked(True)
            self.store.add_evidence_pin(self.project_id, self.current["id"],
                                        best["document"], best["page"], best["excerpt"])
            self.refresh_pins(update_fields=True)
        else:
            self.absent.setChecked(True)
        self.statusBar().showMessage("Lead placed in the form. Inspect the PDF before saving.", 7000)

    # ---- saving --------------------------------------------------------
    def save(self):
        if not self.project_id:
            QMessageBox.warning(self, "Open workpaper", "Open a workpaper first."); return False
        if not (self.absent.isChecked() or self.found.isChecked()):
            QMessageBox.warning(self, "Decision required", "Choose Not supported or Supported."); return False
        score = int(self.found.isChecked()); code = self.current["id"]
        scores = self.store.scores(self.project_id)
        cascade = []
        if self.current["kind"] == "SDG":
            number, stage = self.current["number"], self.current["stage"]
            if score:
                required = PREREQ.get(stage)
                if required and scores.get(f"SDG{number}-{required}", (0,))[0] != 1:
                    QMessageBox.warning(self, "SDG sequence", f"Score {required} as supported first."); return False
            else:
                later_stages = STAGES[STAGES.index(stage) + 1:]
                cascade = [later for later in later_stages if scores.get(f"SDG{number}-{later}", (0,))[0] == 1]
                if cascade:
                    answer = QMessageBox.question(self, "Clear dependent stages",
                        f"Marking {stage} as not supported will also set {', '.join(cascade)} to not supported (0). The change is recorded in the audit log. Continue?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
                    if answer != QMessageBox.StandardButton.Yes: return False
        document = self.doc_name.text().strip(); pages = self.pages.text().strip(); excerpt = self.evidence.toPlainText().strip()
        if score and not all((document, pages)):
            QMessageBox.warning(self, "Evidence required", "Found (1) needs a document and PDF page. The reviewer note is optional."); return False
        for later in cascade:
            old = scores[f"SDG{self.current['number']}-{later}"]
            code_later = f"SDG{self.current['number']}-{later}"
            printed = self.store.score_records(self.project_id)[code_later].get("printed_pages", "")
            self.store.save_score(self.project_id, code_later, 0, old[1], old[2], old[3], printed_pages=printed)
        self.store.save_score(self.project_id, code, score, excerpt or None, document or None, pages or None,
                              printed_pages=self.printed_pages.text().strip())
        self.saved_form = self.form_state()
        self.refresh_totals(); self.render_items(); self.select_item_refresh()
        self.statusBar().showMessage(f"Saved {code} \u00b7 score {score}" + (f" \u00b7 cleared {', '.join(cascade)}" if cascade else ""), 4000)
        return True

    def update_stage_panel(self, scores):
        item = self.current; subtotal = 0
        for label, (stage, weight) in zip(self.stage_rows, RUBRIC["sdg_weights"].items()):
            value = scores.get(f"SDG{item['number']}-{stage}")
            state = "not reviewed" if value is None else "supported" if value[0] == 1 else "not supported"
            subtotal += (value[0] * weight if value else 0); active = stage == item["stage"]
            style = "color:#f2fbf5;font-weight:700;" if active else "color:#a9bbb0;"
            pointer = ARROW if active else GAP
            label.setText(f'<span style="{style}">{pointer}{stage} ({weight} pt) \u2014 {state}</span>')
        self.stage_total.setText(f"Goal subtotal: {subtotal} / 6")

    def select_item_refresh(self):
        """Redraw stage panel after a save without touching the form."""
        if self.current["kind"] == "SDG": self.update_stage_panel(self.all_scores())
        self.update_validation(); self.refresh_status()

    def save_and_next(self):
        if self.save(): self.next_unreviewed()

    def next_unreviewed(self):
        scores = self.all_scores()
        start = self.items.index(self.current)
        for offset in range(1, len(self.items) + 1):
            item = self.items[(start + offset) % len(self.items)]
            if item["id"] not in scores:
                self.select_item(item); return
        self.statusBar().showMessage("All items have been reviewed.", 5000)

    def next_with_lead(self):
        scores = self.all_scores()
        start = self.items.index(self.current)
        for offset in range(1, len(self.items) + 1):
            item = self.items[(start + offset) % len(self.items)]
            if item["id"] not in scores and self.suggestions.get(item["id"], {}).get("suggestion") == 1:
                self.select_item(item); return
        self.statusBar().showMessage("No unreviewed items with leads.", 5000)

    def bulk_mark_no_hits(self):
        if not self.project_id or len(self.suggestions) != len(self.items):
            return QMessageBox.information(self, "Find leads first", "Run Find leads before marking items with no hits.")
        scores = self.all_scores()
        targets = [item for item in self.items if item["id"] not in scores
                   and not self.suggestions[item["id"]]["hits"]]
        if not targets:
            return self.statusBar().showMessage("No unreviewed items without hits.", 5000)
        choice = QMessageBox.question(self, "Bulk Not found",
            f"Mark {len(targets)} unreviewed items with no extracted-text hits as Not found (0)? "
            "Each decision will be tagged bulk in the audit log. OCR gaps can hide evidence.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if choice != QMessageBox.StandardButton.Yes:
            return
        for item in targets:
            self.store.save_score(self.project_id, item["id"], 0, "No extracted-text hits; bulk review", "", "", source="bulk")
        self.refresh_totals(); self.render_items(); self.select_item_refresh()
        self.statusBar().showMessage(f"Marked {len(targets)} items Not found with bulk audit tags.", 8000)

    def next_item(self):
        index = self.items.index(self.current)
        if index + 1 < len(self.items): self.select_item(self.items[index + 1])

    def refresh_totals(self):
        scores = self.all_scores()
        weights = {item["id"]: item["weight"] for item in self.items}
        manual_esg = sum(value[0] for key, value in scores.items() if not key.startswith("SDG"))
        manual_sdg = sum(value[0] * weights[key] for key, value in scores.items() if key.startswith("SDG"))
        if len(self.suggestions) == len(self.items):
            self.esg_tile.set_value(sum(result["suggestion"] for result in self.suggestions.values()))
            low = sum(result["confidence"] == "low" for result in self.suggestions.values())
            skipped = f" · {self.skipped_reports} other-year PDF(s) skipped" if self.skipped_reports else ""
            unreadable = sum(len(numbers) for _, _, numbers in self.ocr_tasks)
            ocr_note = f" · {unreadable} page(s) still need OCR" if unreadable else ""
            self.prediction_totals.setText(f"Rule-based leads for this company and FY · {low} low-confidence items{skipped}{ocr_note} · Manual confirmed: ESG {manual_esg}/30, SDG {manual_sdg}/102")
            self.prediction_totals.show()
        else:
            self.esg_tile.set_value(0)
            self.prediction_totals.setText(f"Run Find leads to inspect evidence for this company and FY. Manual confirmed: ESG {manual_esg}/30, SDG {manual_sdg}/102")
            self.prediction_totals.setVisible(bool(self.project_id))
        self.reviewed_tile.set_value(len(scores))
        self.sdg_tile.set_value(sum(value[0] for value in scores.values()))
        self.review_score_strip.setText(f"Reviewed {len(scores)}/81 · Supported {self.sdg_tile.value.text()} · ESG {manual_esg}/30 · SDG {manual_sdg}/102  |  Score overview")
        if self.work_tabs.currentIndex() == 2:
            self.populate_score_tree(self.score_tree)
        self.refresh_status()

    def configure_score_tree(self, tree):
        tree.setColumnCount(5)
        tree.setHeaderLabels(["Category / scoring item", "Lead", "Confidence", "Manual", "Matched pages"])
        tree.setAlternatingRowColors(True)
        tree.setColumnWidth(0, 440); tree.setColumnWidth(1, 105)
        tree.setColumnWidth(2, 115); tree.setColumnWidth(3, 115)

    def populate_score_tree(self, tree):
        tree.clear()
        if not self.project_id: return
        scores = self.all_scores()
        def add_group(parent, label, group):
            maximum = sum(item["weight"] for item in group)
            proposed = sum(item["weight"] * self.suggestions[item["id"]]["suggestion"] for item in group if item["id"] in self.suggestions)
            confirmed = sum(item["weight"] * scores[item["id"]][0] for item in group if item["id"] in scores)
            reviewed = sum(item["id"] in scores for item in group)
            low = sum(self.suggestions[item["id"]]["confidence"] == "low" for item in group if item["id"] in self.suggestions)
            matches = sum(len(self.suggestions[item["id"]]["hits"]) for item in group if item["id"] in self.suggestions)
            row = QTreeWidgetItem(parent, [label, f"{proposed}/{maximum}" if self.suggestions else "—",
                f"{low} low" if self.suggestions else "—", f"{confirmed}/{maximum} · {reviewed}/{len(group)}", str(matches)])
            font = row.font(0); font.setBold(True)
            for column in range(5): row.setFont(column, font)
            for item in group:
                lead = self.suggestions.get(item["id"]); saved = scores.get(item["id"])
                item_row = QTreeWidgetItem(row, [f"{item['id']} · {item['title']}",
                    f"{lead['suggestion']*item['weight']}/{item['weight']}" if lead else "—",
                    lead["confidence"] if lead else "—",
                    f"{saved[0]*item['weight']}/{item['weight']}" if saved else "—",
                    str(len(lead["hits"])) if lead else "—"])
                item_row.setData(0, Qt.ItemDataRole.UserRole, item["id"])
                if lead and lead["confidence"] == "low": item_row.setForeground(2, QColor("#f3d38a"))
            return row
        esg_root = QTreeWidgetItem(tree, ["ESG · financial materiality"])
        for pillar in ("Environmental", "Social", "Governance"):
            add_group(esg_root, pillar, [item for item in self.items if item["kind"] == "ESG" and item["pillar"] == pillar])
        sdg_root = QTreeWidgetItem(tree, ["SDG · impact materiality"])
        goal_titles = {number: title for number, title, _ in RUBRIC["sdgs"]}
        for number in range(1, 18):
            add_group(sdg_root, f"SDG {number} · {goal_titles[number]}",
                [item for item in self.items if item["kind"] == "SDG" and item["number"] == number])
        tree.expandToDepth(0)

    def show_score_summary(self):
        if not self.project_id:
            return QMessageBox.information(self, "Open workpaper", "Open a company-year workpaper to view its score summary.")
        previous = getattr(self, "summary_dialog", None)
        if previous: previous.close()
        dialog = QDialog(self); dialog.setWindowTitle("Verdant · score summary"); dialog.resize(920, 680)
        box = QVBoxLayout(dialog); box.setContentsMargins(16, 16, 16, 16); box.setSpacing(10)
        title = QLabel(f"{self.active_company or self.company.currentText()} · FY {self.active_year or self.year.currentText()}")
        title.setObjectName("heading"); box.addWidget(title)
        caption = QLabel("Leads come from PDF text. Manual points count only saved reviewer decisions. Expand a category to inspect every item.")
        caption.setObjectName("muted"); caption.setWordWrap(True); box.addWidget(caption)
        tree = QTreeWidget(); self.configure_score_tree(tree)
        box.addWidget(tree, 1)
        self.populate_score_tree(tree)
        buttons = QHBoxLayout(); buttons.addStretch()
        buttons.addWidget(self.button("Expand all", tree.expandAll))
        buttons.addWidget(self.button("Collapse all", tree.collapseAll))
        buttons.addWidget(self.button("Close", dialog.close))
        box.addLayout(buttons)
        self.summary_dialog = dialog; dialog.show()

    def configure_reviewer(self):
        name, accepted = QInputDialog.getText(self, "Scorer name", "Name for the Scorer/Ticker column:",
            text=self.store.setting("scorer_name", ""))
        if not accepted:
            return
        self.store.set_setting("scorer_name", name.strip())
        choices = ["PDF", "Printed"]
        current = self.store.setting("evidence_page_type", "PDF")
        page_type, accepted = QInputDialog.getItem(self, "Evidence page type",
            "Page reference in exports:", choices, choices.index(current) if current in choices else 0, False)
        if accepted:
            self.store.set_setting("evidence_page_type", page_type)

    def export_sheets(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export consolidated sheets",
            "Verdant_Consolidated_Scores.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            output = export_general_workbook(self.store, path)
        except Exception as exc:
            return QMessageBox.critical(self, "Export failed", str(exc))
        self.statusBar().showMessage(f"Exported consolidated workbook: {output}", 8000)

    def export_excel(self):
        if not self.project_id: return QMessageBox.warning(self, "Open workpaper", "Open a workpaper first.")
        from openpyxl import Workbook
        company = self.active_company or self.company.currentText(); year = self.active_year or self.year.currentText()
        path, _ = QFileDialog.getSaveFileName(self, "Export scores", f"{company}_{year}_scoring.xlsx", "Excel (*.xlsx)")
        if not path: return
        workbook = Workbook(); sheet = workbook.active; sheet.title = "Scores"
        sheet.append(["Company", "Fiscal year", "Framework", "Item", "Score", "Weight", "Weighted points", "Document name", "PDF page(s)", "Evidence excerpt", "Printed page(s)", "Scorer"])
        scores = self.store.scores(self.project_id)
        for item in self.items:
            value = scores.get(item["id"])
            sheet.append([company, year, item["kind"], item["id"],
                          value[0] if value else None, item["weight"], value[0] * item["weight"] if value else None,
                          value[2] if value else "", value[3] if value else "", value[1] if value else "",
                          self.store.score_records(self.project_id).get(item["id"], {}).get("printed_pages", ""),
                          self.store.setting("scorer_name", "")])
        sheet.freeze_panes = "A2"; sheet.auto_filter.ref = sheet.dimensions
        for column, width in {"A":30, "B":15, "C":14, "D":22, "E":10, "F":10, "G":18, "H":45, "I":15, "J":90}.items():
            sheet.column_dimensions[column].width = width
        pins_sheet = workbook.create_sheet("Evidence_Pins")
        pins_sheet.append(["Company", "Fiscal year", "Item", "Document name", "PDF page", "Printed page", "Pinned passage"])
        for pin in self.store.evidence_pins(self.project_id):
            pins_sheet.append([company, year, pin["item_id"], pin["document"], pin["page"],
                               pin["printed_page"] or None, pin["excerpt"]])
        pins_sheet.freeze_panes = "A2"; pins_sheet.auto_filter.ref = pins_sheet.dimensions
        pins_sheet.column_dimensions["D"].width = 45; pins_sheet.column_dimensions["G"].width = 90
        try: workbook.save(path)
        except OSError as exc: return QMessageBox.critical(self, "Export failed", str(exc))
        self.statusBar().showMessage(f"Exported {path}", 6000)

    def export_for_master_workbook(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export for master workbook",
            "Verdant_Master_Export.xlsx", "Excel (*.xlsx)")
        if not path: return
        try:
            export_master_workbook(self.store, path)
        except Exception as exc:
            return QMessageBox.critical(self, "Master export failed", str(exc))
        self.statusBar().showMessage(f"Exported {path}", 6000)


def main():
    application = QApplication(sys.argv)
    application.setStyleSheet(STYLE)
    window = Workbench(); window.show(); window.first_run_setup()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
