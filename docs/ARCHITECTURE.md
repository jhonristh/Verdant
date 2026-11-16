# Architecture

## Entrypoints and dependencies

`app_qt.py` is the active PySide6 interface. It imports the `Store`, `RUBRIC`, `keyword_pattern`, and `load_companies` functions from `app.py`, which also contains the earlier CustomTkinter interface. This shared-module arrangement is temporary; a later refactor can move common logic to independent modules without changing saved data.

`scoring_rubric.json` contains 30 ESG items and 17 SDG titles/keyword sets. `brand_mark.svg` is the Qt window icon. `requirements.txt` declares PySide6, CustomTkinter, PyMuPDF, and openpyxl.

## Data flow

1. The company selector loads names from the parent workbook’s `Companies` sheet. Year is selected from 2022–2025.
2. Opening a workpaper gets or creates a `(company, fiscal_year)` project in SQLite.
3. Importing PDFs records their absolute paths, SHA-256 hashes, page counts, and count of pages without text.
4. Reopening verifies each file hash. Changed or missing files are not silently used.
5. PyMuPDF extracts page text. Each item’s keyword patterns search the text; hits are ranked by distinct matching terms.
6. The reviewer pins a hit or enters evidence, chooses 0/1, and saves. A score of 1 requires document, page, and excerpt. A new audit event records the prior and new score.
7. ESG and SDG totals are computed from saved decisions. Excel export leaves unreviewed scores blank.

V2.0 keeps the database schema unchanged. The Qt workbench compares the current decision form with its last loaded/saved snapshot before item switches, workpaper switches, or window close. It prompts Save/Discard/Cancel, and only a successful `save()` permits a guarded transition. Splitter geometry is kept in local `QSettings`.

## SQLite tables

- `projects`: company and fiscal year, unique together.
- `reports`: PDF path, hash, page count, and scanned-page count per project.
- `scores`: one latest decision/evidence record per project and checklist item.
- `audit_log`: timestamped score changes, old/new values, document, and pages.

In this v2.1 prototype folder, the database is stored at `data\pdf_scorer.db`. The previously shared `%APPDATA%\ESGScorer\pdf_scorer.db` remains untouched. PDF files are referenced in place, not copied into the database.

Current consolidated root: `Verdant/data/pdf_scorer.db`. The `(company, fiscal_year)` pair uniquely identifies a workpaper. `predictions` stores all 81 automated proposals, weights, confidence, full result JSON, and check time per workpaper. Existing `scores` and `audit_log` remain separate for optional manual decisions. Predictions are restored when a workpaper is reopened and invalidated when an imported report changes or disappears. `scores_readable.csv` is regenerated from SQLite after prediction, manual save, or deletion; it is a human-readable mirror rather than a second authoritative database.

`ocr_support.py` invokes PyMuPDF's integrated Tesseract OCR on image-only pages in a Qt worker thread. The bundled `tessdata/eng.traineddata` enables English OCR without installing a separate executable. `ocr_pages` caches extracted words by workpaper, report path/hash, and 1-based PDF page; `load_reports()` merges valid cached text into search and prediction. Report changes invalidate OCR cache for that path and predictions. OCR remains limited to pages with no extractable text; embedded images on otherwise searchable pages are not processed.

V3 viewer: `data/viewer.ini` stores splitter and OCR-warning expansion. The warning has one compact header and bounded scrollable details. The original PDF tab selects any imported report/page independently of search hits or OCR. Extracted text and evidence context are separate tabs. Rendered page images are cached with an 80 MB cap and keyed by file modification time, page, rubric item, and scale. OCR runs in a QThread with cancellation checks between pages; import and score calculation use modal progress dialogs and pump Qt events between pages/items. Exceptionally complex single-page rendering and OCR highlight geometry can still pause the main thread briefly; background page rendering remains open V3 work.

`scoring_assist.py` produces provisional 0/1 predictions over imported text pages, with a best hit and confidence. Contextual matches propose 1; weak or absent matches propose 0 with low confidence. SDG proposals respect stage order. Predictions remain in memory and never enter SQLite or official totals until the reviewer chooses and saves a decision. Workspace deletion removes dependent rows transactionally and leaves original PDFs untouched.

## Search and evidence limitations

Search is literal and uses whole-word boundaries. Short uppercase acronyms are case-sensitive. A hit is contextual text, not a semantic judgment. The displayed page is the PDF’s 1-based page index; printed page numbering inside a report may differ. Only one document/page/excerpt is stored per scored item in this version. OCR text is searchable after processing, while PDF image pages do not show keyword highlight overlays. Multiple evidence records per item remain a later enhancement.
