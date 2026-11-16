# Operations

## Setup

The consolidated `Verdant` folder includes its own Python 3.13 environment and `ESG_SDG_Scoring_Consolidated.xlsx`. Run it from PowerShell at any location:

```powershell
& "C:\Users\acer\Documents\ECA - Projs\26-11 Kuya\Verdant\run.cmd"
```

From Command Prompt, run the same quoted path without `&`. If the environment needs rebuilding later, use a Windows Python installation with Tcl/Tk, create `.venv`, and install `requirements.txt`.

## Daily review

1. Select a company and FY, then open the workpaper. Use **Workspaces** to return to prior work.
2. Add the annual, sustainability, or SEC PDF reports for that company-year. If Verdant flags pages with no text, click **OCR missing pages** in the Evidence viewer and wait for completion. OCR text is cached in SQLite; original PDFs are unchanged.
3. Click **Check for score** after OCR. Automated ESG and SDG totals appear in the main cards and are saved for this company-year. The readable mirror is `data\scores_readable.csv`.
4. Select an ESG or SDG item and a numbered matching page to inspect the proposal. Low-confidence zeros need special care where OCR gaps exist.
5. For a correction or confirmation, click **Review / adjust manually**, use or override the proposal, and save. Supported decisions require document, PDF page, and excerpt. `Ctrl+S` saves the current item; `Alt+Right` moves to the next.
6. Export Excel and check any remaining unreviewed rows before using totals in research.

### PDF and OCR viewer

The warning is collapsed by default; its Expand/Collapse state is saved in `data/viewer.ini`. Expand it for missing page numbers and OCR actions. **Review pages** opens the first missing-text page before OCR. Use **Workpaper ▾** to reveal the company/year selector or reach import, score check, workspaces, and export. **PDF reader → All PDF pages** scrolls continuously through the original document, including scanned pages without a text layer. Choose another imported report in the document picker, enter a 1-based PDF page and click **Go**, or use Previous/Next. Fit width, Fit page, and zoom controls change the display. **Highlighted page** shows the current criterion's marks on a single page; **Extracted text** shows native or cached OCR text; **Evidence context** shows the selected search hit. Open **Find evidence** for the matching-page list. Selecting a numbered hit opens the highlighted page. The **Checklist & decisions** and **Score overview** tabs keep scoring information available without narrowing the main PDF reader.

**OCR current** processes the displayed missing-text page. **OCR selected pages** accepts numbers or ranges such as `2, 5-7`; **OCR all missing** processes every pending page for the open fiscal year. **Cancel OCR** stops after the current page where safe; completed pages stay cached. After OCR, run **Check for score** again. The original PDF is never rewritten.

Import and score checking display progress with a Cancel button. Canceling import keeps fully imported reports and discards the partly read report. Canceling score checking keeps the previous saved proposals.

The app saves decisions in SQLite. When you switch items or workpapers, or close the window with unfinished changes, choose Save, Discard, or Cancel. A failed validation leaves you on the current item.

This root's authoritative database is `data\pdf_scorer.db`. The CSV mirror is `data\scores_readable.csv`; it is rebuilt after prediction and manual changes. Earlier databases are separate.

## Run foundation tests

From `Verdant` in PowerShell:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests use an isolated temporary SQLite database.

## Build

Install PyInstaller into `.venv` and run `build_qt_exe.ps1` from PowerShell. The script includes the rubric, icon, and workbook in a one-directory Windows package. A distributable build has not yet been verified on another machine.

## Troubleshooting

- `python.exe not recognized`: `.venv` is missing or the path is wrong. Recreate it with the installed Python and reinstall `requirements.txt`.
- `No installed Python found`: the `py` launcher cannot locate Python; use the full Python path shown above.
- `Can't find a usable init.tcl`: the environment was created from a Python runtime without Tk. Recreate `.venv` using a normal Windows Python installation with Tk.
- `FutureWarning` for `fitz`: a deprecation warning from PyMuPDF’s old import name; current PDF extraction still works.
- A PDF has no keyword hits: verify it has a text layer; the app warns when pages need OCR.
- OCR still shows no text: inspect scan quality and confirm the bundled `tessdata\eng.traineddata` exists. The model is English-only; non-English reports need matching language data and a code setting change.
- Changed or missing report warning: restore the original PDF path/file or reimport the report after confirming it is the intended version.
- `KeyboardInterrupt` after `Ctrl+C`: the user stopped the GUI process. Close the window normally to exit.
