# QA report — Verdant

## Intel macOS Big Sur build kit (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Windows regression suite | 44 tests passed with `QT_QPA_PLATFORM=offscreen` after the Mac path and PDF loading changes. |
| PASS | Mac data path unit check | Packaged Mac data resolves to `~/Library/Application Support/Verdant/data`; Windows and source paths retain their prior locations. |
| PASS | Mac dependency research | Qt for Python 6.5.3 Addons lists QtPdf and QtPdfWidgets and supplies a macOS 11 universal2 wheel; PyMuPDF 1.24.14 supplies an Intel macOS wheel. |
| NOT RUN | Native Mac build and runtime | No macOS machine is connected to this Windows workspace. `build_mac.sh`, application launch, PDF rendering, OCR and exports need verification on the target Mac. |

The Big Sur transfer kit excludes the existing database, imported reports,
Windows virtual environment, and Windows executables.

## Branded Windows installer (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Full source suite | 41 tests passed with `QT_QPA_PLATFORM=offscreen` and unittest discovery; includes two installer payload/data-preservation tests. |
| PASS | Setup build | `build_installer.ps1` rebuilt the current Qt application and created a branded, single-file `dist/Verdant_Setup.exe` with a verified data-free payload. |
| PASS | Isolated installation | Setup CLI installed into a fresh temporary folder and exited 0; the installed application launched and created SQLite data. |
| PASS | Upgrade preservation | Re-running the final setup over the isolated installation exited 0 and left the database SHA-256 unchanged. The upgraded app launched. |
| PASS | Setup window startup | The setup GUI process stayed running during a hidden-window launch check without an exception. |
| PASS | Shortcut creation | The Windows shortcut helper created a `.lnk` in an isolated temporary folder. |
| NOT RUN | Clean second PC | Installation, Start Menu creation, Installed apps registration/uninstall, OCR, and display scaling still need validation on a separate Windows machine. |

The setup EXE is unsigned. Windows may show a publisher warning. The installer does not contain user research data or imported PDFs.

## PDF reader layout and panel bug fixes (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Offscreen regression suite | 39 passed (0 failures, 0 errors) with `QT_QPA_PLATFORM=offscreen; & .\.venv\Scripts\python.exe -m unittest discover -s tests -v`. |
| PASS | Layout budgets & proportions | Verified 58%/42% splitter split, left pane vertical budget (>400px at 720p, >500px at 864p, >640px at 1080p), and hit list >=120px via `test_v3_layout.py`. |
| PASS | Non-modal OCR popup | Verified `OCRDetailsPopup` uses `Qt.WindowType.Popup` without resizing the PDF viewing area (`test_ocr_popup_does_not_resize_pdf`). |
| PASS | Zoom & continuous mode safety | Verified continuous PDF mode does not perform redundant synchronous pixmap renders and zoom operations do not division-by-zero on hidden widgets (`test_zoom_when_continuous_active_does_not_crash`). |
| PASS | Visual screenshots across 3 resolutions | 15 PNG screenshots captured across 1920x1080, 1536x864 (125% scale), and 1280x720 (150% scale) under `qa_screens/`. All layouts verified clean and legible with visible dividers and no clipped action buttons. |
| NOT RUN | Interactive desktop inspection | Manual mouse interactions, physical DPI monitor scaling, and smooth continuous scrolling on hardware GPU display. |
| NOT RUN | Clean-machine test | Startup and execution on a secondary Windows machine without local Python development tools installed. |

## Windows package (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | PyInstaller build | One-directory `Verdant_Disclosure_Scorer.exe` built using Verdant's Python environment and the updated `build_qt_exe.ps1`. |
| PASS | Local EXE startup | Hidden startup smoke check kept the EXE running for 12 seconds and created a new 49 KB SQLite database beside it. The test-created database is excluded from the ZIP. |
| PASS | Qt DLL resolution | Removed a transitive ICU 78 DLL whose versioned exports conflicted with Qt's Windows ICU imports; local startup then passed. |
| NOT RUN | Clean-machine test | The ZIP has not been launched on a second Windows PC. |

The packaged app uses a fresh database. It does not include the existing development workpapers or imported report PDFs; report references still depend on the original local PDF paths.

## Document-first reader (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Continuous PDF mode | Qt test opens a two-page image-only PDF before OCR and verifies `QPdfView.PageMode.MultiPage`, two loaded pages, and the All PDF pages tab. |
| PASS | Work tabs | Qt test verifies PDF reader, Checklist & decisions, Score overview, and navigation from a score item into its decision. |
| PASS | Windows report-file release | Test suite creates and removes temporary PDF reports after the reader closes; the full run completed without file-lock errors after loading through an in-memory buffer. |
| PASS | Regression suite | 30 tests passed with `QT_QPA_PLATFORM=offscreen` and `.venv\Scripts\python.exe -m unittest discover -s tests -q`. |
| NOT RUN | Visible Windows pass | Continuous scrolling, display scaling, and very large report performance need interactive inspection. |

The continuous All PDF pages mode shows the original report. Keyword overlays remain in the separate Highlighted page mode.

## Work area navigation and readability (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Review and score tabs | A new Qt test opens Score overview, checks ESG/SDG roots, activates E2, and returns to Review workpaper. |
| PASS | Focus PDF | The same test hides and restores the checklist column without losing the selected item. |
| PASS | Regression suite | 30 offscreen Qt/Python tests passed with `.venv\Scripts\python.exe -m unittest discover -s tests -q`. |
| NOT RUN | Visible Windows review | Actual display scaling, PDF legibility, and scrollbar behavior should be checked interactively on the user's monitor. |

The Score overview shows proposed and manually saved values separately. Its item rows provide navigation back into the review workflow; they do not save decisions.

## V3 PDF and OCR foundation (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Database preservation | Created `data/backups/pdf_scorer_before_v3_20261116_164035.db` with SQLite online backup; integrity check returned `ok`. Tests use temporary databases. |
| PASS | Original-page access | Offscreen Qt tests open image-only PDF pages before OCR, navigate pages, and switch reader modes. |
| PASS | Warning and OCR controls | Tests cover collapsed/expanded warning, page-range parsing, current-page OCR, safe cancellation between pages, and worker progress while the warning is collapsed. |
| PASS | Score workflow | Tests cover import/scoring progress and cancellation, score-summary grouping, and rendered-page keyword highlights. |
| PASS | Full regression suite | `QT_QPA_PLATFORM=offscreen` and `.venv\Scripts\python.exe -m unittest discover -s tests -q`: 29 tests passed. |
| NOT RUN | Real report accuracy and performance | OCR accuracy, keyword proposal quality, and very long or complex PDF rendering need measurement on representative company reports. |
| NOT RUN | Visible desktop and packaged EXE | Display scaling, keyboard/scroll interaction, and a clean-machine executable were not verified in this run. |

Scope: V3 Phase 1 foundation and the requested progress, summary, and highlighting changes. Later V3 phases remain listed in `docs/V3_DEVELOPMENT_CHECKLIST.md`. The original PDF viewer renders one page synchronously, so unusually complex pages can briefly pause the UI. Historical results below describe earlier builds and are not the current test count.

## On-demand OCR integration (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | OCR engine | A synthetic image-only PDF had zero extractable characters; PyMuPDF OCR with bundled English data recovered its text. |
| PASS | UI workflow | Offscreen Qt test ran the OCR button's background worker, cached page text, removed the pending-page warning, and used OCR text to propose E1=1. |
| PASS | Cache and invalidation | Tests verified cached text enters matching pages and a changed report hash does not reuse that text. |
| PASS | Regression suite | 22 tests passed from the consolidated Verdant root. |
| NOT RUN | Real company scans | Accuracy, speed on long reports, and tables require review with the user's PDFs. OCR text is not overlaid as highlights on the original image page. |

The bundled `tessdata_fast/eng.traineddata` is Apache-2.0 licensed; `tessdata/LICENSE` is included. SHA-256: `7D4322BD2A7749724879683FC3912CB542F19906C83BCC1A52132556427170B2`.

## Company-year automated score display (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Automated cards | Regression tests verify proposed ESG total on the main card and manual review remaining separate. |
| PASS | Persistence | Reopening a company-year with an intact PDF restores 81 proposals and the ESG card value. |
| PASS | CSV mirror | Tests verify 81 proposal rows and manual score update in the readable CSV. |
| PASS | Manual-only CSV | A manually scored item appears in the CSV even before an automated run, with blank proposal fields. |
| PASS | Fiscal-year boundary | Changing the toolbar FY without opening that workpaper blocks scoring. |
| PASS | Numbered hits | Test checks the first matching row starts with `1.`. |
| PASS | Regression suite | 17 offscreen Qt tests passed after the layout and CSV changes. |
| LIMITED | Visual check | Offscreen capture confirmed pane and border placement; its Windows font rendering showed placeholder boxes, so final text appearance at the user's display scaling was not verified. |
| NOT RUN | Prediction accuracy | Keyword/context rules are not calibrated against annotated reports; low-confidence proposed zeros still require inspection. |

## Consolidated Verdant root (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Bundled environment | `.venv\Scripts\python.exe` imported PySide6, PyMuPDF, openpyxl, and CustomTkinter from the new root. |
| PASS | Workbook and database | Local workbook yielded 60 company names; new `data\pdf_scorer.db` had 0 projects, reports, scores, and audit rows. |
| PASS | Regression suite | 15 tests passed from `Verdant` with offscreen Qt. |
| PASS | App startup | Offscreen Qt created and showed the workbench with 60 companies and no saved workspaces. |
| NOT RUN | Interactive Windows display | `run.cmd` was not clicked in a visible desktop session. |

## V2.1 provisional scoring and workspace management (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Automated predictions | 15 tests passed; strong contextual hit proposes 1 with source, weak/no hit proposes low-confidence 0, and SDG stages follow prerequisite proposals. |
| PASS | Reviewer gate | Applying a proposed 1 fills the form with source/page/excerpt but does not save or increase official reviewed count. |
| PASS | Fiscal year | A filename explicitly marked FY2023 is skipped during FY2022 prediction. |
| PASS | Workspace deletion | Test confirms one project and its reports, scores, and audit rows are removed. Original PDFs are not deleted by the store method. |
| NOT RUN | Research accuracy | Prediction precision/recall against annotated company reports has not been measured. Weak/no-hit zeros remain low confidence, especially with OCR gaps. |

## V2.1 readability fix (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Minimum-window layout | Offscreen Qt test at 1100 × 700 with 12 OCR notices confirms warning height ≤108 px, reader ≥170 px, and evidence editor ≥145 px. |
| PASS | Regression suite | 12 tests passed with `QT_QPA_PLATFORM=offscreen`; previous workflow and scoring tests remain green. |
| NOT RUN | Windows visual inspection | A live review at the user's display scaling remains to be done. |

## V2.1 workflow update (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Prototype reset | `data/pdf_scorer.db` has 0 projects, reports, scores, and audit events after initialization. The shared AppData file was not changed. |
| PASS | Rule-based check | 11 isolated tests passed, including candidate 1, generic/no-hit undetermined, and no score saved by Check for score. |
| NOT RUN | Long real annual reports | Search speed and false-positive rate require review on actual company reports. |
| NOT RUN | Windows visual pass | The new toolbar and filter have not yet been manually inspected at 125-200% DPI. |

The check is a retrieval aid, not a validated automatic research score.

Date: 2026-11-16 (Asia/Manila)

## Source inventory and authority

Present: creator guide, consolidated V2 spec, README, four project docs, revised workbook, rubric JSON, Qt and legacy Tk sources, build scripts, SVG mark, local Python environment. No pre-existing test suite was present. The older PDF is present but is superseded on disputed scoring rules by the revised workbook.

Workbook parity check: 30 ESG keyword lists and 17 SDG titles/keyword lists matched runtime JSON; weights are Identified 1, Managed 2, Reported 3. The workbook contains 60 company rows. The two exclusions needed for the stated 58-company research target remain unresolved.

## Verification

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Python syntax | `.venv\Scripts\python.exe -m py_compile app.py app_qt.py` exited 0 before implementation; subsequent test import of updated Qt source passed. |
| PASS | Qt foundation tests | `QT_QPA_PLATFORM=offscreen` with `.venv\Scripts\python.exe -m unittest discover -s tests -v`: 4 tests passed. |
| PASS | 30/102/81 contract | Test asserts 81 decisions, 102 total SDG weights, and saved 0 counts toward reviewed but earns no ESG points. |
| PASS | Dirty guard | Test verifies Cancel blocks selection and Discard proceeds. |
| PASS | Grouped filter | Test verifies SDG13 search yields one nonselectable group header and three stage rows. |
| PASS | Qt initialization | Offscreen `Workbench()` opened with 81 items and Reviewed 0 / 81. |
| PASS | Isolated workpaper reopen and legacy export | Temporary SQLite database reopened with saved 0 and 1; exported Scores preserved 0, weighted 1, and blank unreviewed cell. |
| NOT RUN | Actual user workpaper reopen | Tests deliberately used a temporary database; no user research record was modified. |
| NOT RUN | Clean-PC executable | PyInstaller build and deployment to another PC were not attempted. |
| NOT RUN | Manual DPI and keyboard-only visual review | No visual review session was performed at 125–200% Windows scaling. |

## Data safety and rollback

No schema migration or direct edit of existing SQLite rows was performed. Rollback is to restore the prior `app_qt.py`; the SQLite database, original PDFs, rubric, and flat export format remain compatible. Tests create and remove a temporary database. The real database was not copied because this phase did not migrate it.

## Known limitations

The center pane displays extracted passages rather than rendered PDF pages. OCR, evidence registry, multi-evidence rows, sign-off, cloud sync, and a tested distributable executable remain outside this phase. The Qt entrypoint still imports shared logic from the Tk module, causing harmless font and `fitz` deprecation warnings. An entered document/page/excerpt is required for a supported decision, but this phase does not prove typed evidence matches the imported PDF text.


## V2.1 UI pass (2026-11-16)

| Result | Check | Evidence |
| --- | --- | --- |
| PASS | Offscreen tests | 7 tests pass (metrics, dirty guard, grouped filter, reopen/export blanks, status chip and empty state, evidence validation and prerequisite lock, cascade with audit). Run in a sandbox with tkinter stubbed. |
| PASS | Offscreen render | Screenshots with a generated sample PDF show tiles, panes, hit list and highlighted page render. |
| NOT RUN | Windows, Segoe UI, 125-200% DPI, keyboard-only pass | Needs manual review on your machine. |
| NOT RUN | Real workpaper and real report PDFs | Only a temporary database was used. |
| NOT RUN | Clean-PC executable | No build attempted. |

Not implemented: Overview and Evidence Registry tabs, audit viewer, structured export sheets, OCR, multi-evidence.
