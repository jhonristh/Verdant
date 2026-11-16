# Verdant Disclosure Scorer

Verdant is a local Windows desktop workbench for reviewing company PDF disclosures against ESG and SDG criteria. It does not send reports or scores to a cloud service.

## Run

Double-click `run.cmd`, or run `app.py` with the project Python environment. The application opens with a fresh local database in `data/`.

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
