$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& ".\.venv\Scripts\python.exe" -m PyInstaller --noconsole --onedir --name ESG_SDG_PDF_Scorer --add-data "scoring_rubric.json;." --add-data "ESG_SDG_Scoring_Consolidated.xlsx;." app.py
