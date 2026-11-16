# Replicate Verdant from source

This source package has code, the scoring workbook and rubric, English OCR data,
tests, and documentation. It has no saved workpapers, imported PDFs, virtual
environment, or EXE. Use Windows with Python 3.13 (64-bit) installed.

In PowerShell, open this folder and run:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
& .\run.cmd
```

To check the source and build the EXE:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& .\.venv\Scripts\python.exe -m unittest discover -s tests -q
Remove-Item Env:\QT_QPA_PLATFORM
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_qt_exe.ps1
```

To create the single-file installer instead, run
`powershell -NoProfile -ExecutionPolicy Bypass -File .\build_installer.ps1`.
See `INSTALLER.md` for the install and update behavior.

The executable folder appears at `dist\Verdant_Disclosure_Scorer`. Keep that
entire folder together. `data\pdf_scorer.db` and `data\scores_readable.csv`
are created when needed. Keep `data` when updating to preserve scores. Imported
PDFs remain at their original locations; moving them breaks their references.

The tested development environment used PySide6 6.12.0, PySide6_Pdf
6.12.0.140, PyMuPDF 2.1, openpyxl 3.1.5, CustomTkinter 6.0.0, and
PyInstaller 6.21.0. Newer dependency versions need a fresh test run.
