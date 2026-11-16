#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "x86_64" ]]; then
  echo "Build this edition on the Intel MacBook Air running macOS Big Sur." >&2
  exit 1
fi
if [[ "$(sw_vers -productVersion)" != 11.* ]]; then
  echo "This package targets macOS Big Sur 11.x; this Mac runs $(sw_vers -productVersion)." >&2
  exit 1
fi
if ! command -v python3.11 >/dev/null 2>&1; then
  echo "Install Python 3.11 for macOS from python.org, then rerun this script." >&2
  exit 1
fi
python3.11 -m venv .venv-mac
PY=".venv-mac/bin/python"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements-mac-big-sur.txt
"$PY" -c 'from PySide6.QtPdfWidgets import QPdfView; import fitz, openpyxl; print("Mac dependencies import successfully")'
QT_QPA_PLATFORM=offscreen "$PY" -m unittest discover -s tests -v
"$PY" -m PyInstaller --noconfirm --clean --windowed --onedir \
  --name Verdant --target-arch x86_64 \
  --osx-bundle-identifier org.verdant.disclosure-scorer \
  --hidden-import PySide6.QtPdf --hidden-import PySide6.QtPdfWidgets \
  --add-data "scoring_rubric.json:." \
  --add-data "brand_mark.svg:." \
  --add-data "tessdata:tessdata" \
  --add-data "ESG_SDG_Scoring_Consolidated.xlsx:." \
  app_qt.py
test -d dist/Verdant.app
echo "Built: $(pwd)/dist/Verdant.app"
echo "Open it with: open dist/Verdant.app"
