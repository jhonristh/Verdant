# Changelog

## macOS Big Sur build track — 2026-11-16

- Added an Intel Big Sur dependency set, Mac build script and transfer kit.
- Packaged Mac workpapers now save under the user's Application Support folder.
- Mac PDF viewer loads report files from disk to reduce peak memory usage.
- Added path tests. Native Mac build and runtime verification remain pending.

## Per-user Windows installer — 2026-11-16

- Added a branded single-file `Verdant_Setup.exe` builder. It embeds a clean
  one-directory app build and installs under the current user's Local AppData
  by default, with a Start Menu entry and Installed apps registration.
- Installer upgrades preserve the installed `data` folder and reject payloads
  containing a database. Uninstall removes program files while retaining user
  data. The current setup EXE is unsigned.

## PDF reader layout rebuild and panel fixes — 2026-11-16

- Rebuilt PDF reader as side-by-side panes: 58% left pane for PDF viewing with full height, 42% right pane for search hits, evidence context, extracted text, and Pin action, separated by a visible 7px divider handle.
- Compact single-row reader toolbar combining page navigation, zoom, and OCR controls; eliminated redundant and misaligned toolbar rows.
- Converted OCR warning strip to a non-intrusive 34px bar with popup details (`OCRDetailsPopup`), preventing PDF viewing canvas compression.
- Moved score summary badge into the `work_tabs` top-right corner widget, saving 54px header vertical space.
- Fixed keyboard mnemonic underscore on "Checklist and decisions" tab.
- Removed duplicate dropdown arrow glyph on "Workpaper ▾" menu button.
- Fixed status bar message persistence and page jump feedback loops with `_navigating` guard.
- Bound zoom and fit calculations strictly to visible reader tabs, resolving zero-dimension scaling bugs on continuous view.
- Eliminated redundant page rendering when switching to continuous PDF mode, dramatically reducing UI thread lag.
- Guaranteed 120px minimum height for hits list and capped warning scroll at 96px, ensuring bottom action buttons never clip off-screen.
- Set default window dimensions to 92% available screen geometry (min 1024x640) and validated layouts at 1920x1080, 1536x864 (125%), and 1280x720 (150%).
- Expanded offscreen automated test suite from 30 to 39 tests covering layout proportions, vertical budgets, popup dialogs, and zoom safety.

## Windows executable package — 2026-11-16

- Built a one-directory Windows EXE from the current Qt app with the workbook, rubric, Verdant mark, English OCR data, and Qt PDF reader.
- Put packaged SQLite data beside the EXE, leaving the development database outside the release. Added a repeatable build cleanup for a conflicting ICU DLL discovered during startup verification.

## Document-first reader and workpaper menu — 2026-11-16

- Made the main PDF reader a continuous multi-page view using Qt PDF; all pages, including image-only pages, are readable without OCR.
- Moved checklist and manual decisions into their own work tab, leaving the PDF reader the full work area. The separate highlighted-page mode still shows current-keyword marks; extracted text and evidence context remain available.
- Collapsed evidence search by default and added a Verdant **Workpaper ▾** menu for company/year selection, workspaces, import, scoring, and export. The selector remains visible before a workpaper is opened and folds away afterward.
- Loaded the selected PDF into the Qt reader from memory, avoiding a persistent Windows file lock on the original report.

## Work area navigation and readability — 2026-11-16

- Moved the large score cards and full 81-item breakdown into a persistent **Score overview** tab. The **Review workpaper** tab uses the freed height for checklist, PDF evidence, and decisions.
- Kept a compact proposed ESG/SDG strip on the review tab; selecting it opens the score overview. Double-clicking or activating a scoring item in the overview returns to that item in review.
- Added **Focus PDF** in the evidence pane to temporarily hide checklist and decision columns, giving long pages and report controls more width. The same control restores the three-pane review layout.
- Kept the existing original PDF, extracted text, and evidence context tabs inside the evidence pane.

## V3 PDF and OCR foundation — 2026-11-16

- Made the OCR notice compact by default, expandable without covering the reader, and persistent across sessions in `data/viewer.ini`. It lists pages needing OCR and offers review, all-page, selected-page, and cancel actions.
- Added original-PDF viewing independent of text extraction, with document choice, page navigation and entry, fit/zoom controls, and separate original-page, extracted-text, and evidence-context modes.
- Added per-page OCR status and selective OCR. Cancellation stops after the current page and retains completed OCR results. Original PDFs are not modified.
- Bounded the rendered-page image cache and retained current-criterion keyword highlights on rendered pages, including available OCR text geometry.
- Added import and scoring progress with cancellation, plus a score-summary dialog grouped by ESG pillar and SDG goal. A canceled scoring run keeps the previous proposals.
- Recorded the V3 roadmap and remaining work in `docs/V3_DEVELOPMENT_CHECKLIST.md`; this release does not complete all V3 phases.

## On-demand OCR — 2026-11-16

- Added **OCR missing pages** in the Evidence viewer for image-only pages in the open company-year's reports.
- Bundled English Tesseract language data, used by PyMuPDF's integrated OCR engine; original PDFs remain unchanged.
- Runs OCR in a background Qt thread and caches recognized text per report hash and page in SQLite.
- OCR text enters search hits and automated score predictions; successful OCR invalidates older proposals until Check for score runs again.
- Marks OCR hits and explains that keyword highlighting is unavailable on the source image page.

## Company-year automated score display — 2026-11-16

- Main ESG and SDG cards now show saved automated proposed totals; a separate card counts optional manual reviews.
- Added a `predictions` SQLite table keyed by company-year workpaper and item. Predictions reload when reopening a workpaper and are invalidated after report import or integrity failure.
- Added `data/scores_readable.csv`, regenerated from SQLite after scoring, manual saving, or workspace deletion.
- Collapsed the manual decision form after an automated run behind **Review / adjust manually**.
- Numbered matching page rows and simplified the checklist border and scrollbars.
- Blocked scoring/import when the toolbar company or year differs from the opened workpaper.

## Consolidated root — 2026-11-16

- Copied the latest Qt prototype, revised company workbook, empty SQLite database, tests, documentation, and working Python environment into one `Verdant` root.
- Added `run.cmd` as a stable launch entrypoint from any working directory.
- Made the bundled workbook the first roster lookup and updated build scripts to reference it locally.
- Omitted the older how-to-use PDF from this root as requested.

## V2.1 provisional scoring and workspace management — 2026-11-16

- Check for score now proposes 0/1 for all 81 items, displays provisional ESG/SDG totals, and shows best source hit and confidence in the Decision panel.
- Added Use proposed score to populate the decision form; final scores still require reviewer save and supported evidence.
- Excluded PDFs whose filenames explicitly indicate another fiscal year from the prediction run.
- Added Workspaces dialog with confirmed deletion of one company-year and its local report references, scores, and audit records. Original PDFs remain on disk.
- Kept 30/102/81 scoring and SDG prerequisites unchanged.

## V2.1 readability fix — 2026-11-16

- Constrained long OCR notices to a scrollable area so they cannot displace the evidence viewer.
- Gave the context/PDF reader and evidence excerpt usable minimum heights; the evidence viewer scrolls when the window is short.
- Made the decision form vertically scrollable at smaller window sizes so its fields and Save button remain reachable.
- Added a minimum-window layout regression check.

## V2.1 workflow update — 2026-11-16

- Isolated this prototype's SQLite database at `data/pdf_scorer.db`, starting with no saved workpapers; the earlier shared AppData database remains untouched.
- Added Check for score after PDF import. It produces rule-based candidate 1 leads and never writes a score or turns no-hit into 0.
- Added a word/phrase filter for matching PDF pages and candidate markers in the checklist.
- Updated user-facing workflow documentation and regression tests.

## V2.1 UI pass — 2026-11-16

- Rebuilt the Qt shell to the V2 spec: compact brand header with workpaper context and a status chip (No workpaper / Ready / Unsaved edits / Review in progress / Complete), toolbar, and three separate metric tiles (ESG n/30, SDG n/102, Reviewed n/81) with progress bars and captions.
- Three labelled panes (Checklist, Evidence viewer, Decision) at roughly 22/50/28; wrapped checklist titles with colour-coded status markers and a legend.
- Evidence viewer: explicit empty states ("Open a workpaper to begin", "Import PDFs to begin"), separate missing/changed-PDF and OCR banners, "no keyword matches is not proof of absence" message, and a rendered PDF page tab with amber keyword highlights, page stepping, and PDF-versus-printed page label.
- Decision pane: ESG/SDG perspective label, SDG stage panel with weights and goal subtotal, Supported locked until its prerequisite stage is supported, Save disabled until a supported decision has document, page and excerpt (drafting stays enabled).
- Marking an upstream SDG stage not supported now offers to clear dependent stages, each recorded in the audit log, instead of blocking.
- Visible focus rings, 14 px body text. Schema, rubric, export format and shortcuts unchanged.

## V2.0 foundation — 2026-11-16

- Separated ESG points (out of 30), SDG weighted points (out of 102), and reviewed decisions (out of 81) in the Qt header.
- Grouped the searchable checklist by ESG pillar and SDG goal, with reviewed counts, status markers, and full-title tooltips. The checklist no longer shows a horizontal scrollbar.
- Added saved SDG stage statuses, weights, and per-goal subtotal beside the selected decision.
- Added Save/Discard/Cancel protection when changing item or workpaper and when closing the Qt window. Failed save validation does not advance.
- Persisted Qt splitter proportions in local application settings.
- Preserved the SQLite schema, rubric, report integrity checks, legacy flat Scores export, and keyboard shortcuts.
- Added isolated Qt foundation tests and updated project documentation.
