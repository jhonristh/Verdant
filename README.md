# Verdant Disclosure Scorer

Verdant is a local Windows desktop workbench for reviewing company PDF disclosures against ESG and SDG criteria. It does not send reports or scores to a cloud service.

## Run

Double-click `run.cmd`, or run `app.py` with the project Python environment. The application opens with a fresh local database in `data/`.

## Windows testing ZIP

Unzip the complete `Verdant_Disclosure_Scorer` folder to a writable location such as `Documents` or `Desktop`, then run `Verdant_Disclosure_Scorer.exe` inside it. Do not put the extracted folder under `Program Files`; Verdant saves local workpapers next to the application. If Windows SmartScreen warns about an unsigned test build, choose **More info > Run anyway** only if the ZIP came from the expected project owner.

The first-run setup asks for a reports folder, scorer name, and optional roster workbook. PDF paths are saved relative to the chosen reports folder when possible. Use **Workpaper > Relink missing PDF** if reports move. Keep the PDFs and `data/` folder together in your backups. `data/pdf_scorer.db` holds decisions, evidence, OCR text, and audit history; `data/roster.xlsx` is an imported roster. Copy both while Verdant is closed. A `.verdant` export moves one company-year workpaper between machines; it contains report references and OCR text, but not PDF binaries.

Choose both a company and a fiscal year to open a workpaper; no fiscal year is preselected. Hover over buttons or Workpaper menu actions for brief guidance, or click **? Help** for a searchable button guide.

**Find leads** offers rule-based passages for review. It does not assign confirmed points. Each Found (1) decision needs a document and PDF page. In the Workpaper menu, choose **Scorer name and evidence page setting** to select PDF or printed page references for exports. The workbook export creates a new file; it does not modify the supplied consolidated workbook.

The reviewer note is optional and stays blank in saved data and exports when left empty. **Pin selected passage** adds passages from different PDF pages or reports to the currently selected score item; the pinned list appears in both the PDF reader and decision form. **Export sheets** creates one new copy of the consolidated workbook template with saved decisions and one evidence row per pinned passage. The template itself is never overwritten.

## Project layout

```
app.py                 application entry point
app_qt.py              Qt workbench
verdant/               application package
  config.py            central paths and settings
  domain/              rubric and domain construction
  services/            explainable scoring services
  storage/             SQLite repository
resources/             rubric, roster, branding, OCR language data
data/                  generated local workpapers only (not source)
tests/                 automated checks
docs/                  product and operating documentation
```

`app.py`, `scoring_assist.py`, and the existing support modules keep small compatibility facades while the Qt screen is incrementally decomposed. New domain, scoring, and storage work belongs in `verdant/`; UI code must not access SQLite directly.

## Local data

`data/` has intentionally been reset. It is recreated as you open workpapers. It contains the local SQLite database, readable score export, and viewer preferences; do not treat it as source code.

## Verification

Run the test suite from this directory:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
