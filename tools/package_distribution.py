"""Package the verified Windows build and complete Mac source build kits."""
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


SOURCE = Path(__file__).resolve().parents[1]
ROOT = SOURCE.parent
OUTPUT = ROOT / "Zip Files for Distribution"
DOCS = ROOT / "Verdant_Final_Handoff" / "Documentation"
FEATURES = ROOT / "Verdant_Final_Handoff" / "FEATURES_AND_HOW_TO_USE.txt"
WINDOWS_APP = SOURCE / "dist" / "Verdant_Disclosure_Scorer"

SOURCE_FILES = ["app.py", "app_qt.py", "scoring_assist.py", "ocr_support.py",
                "pdf_highlights.py", "runtime_paths.py", "installer.py"]

WINDOWS_START = """VERDANT WINDOWS PORTABLE - 17 NOVEMBER 2026

1. Extract this entire folder to a writable location such as Documents.
2. Double-click Verdant_Disclosure_Scorer.exe. Keep _internal beside it.
3. Choose a reports folder, optional roster, company and fiscal year.
4. Read FEATURES_AND_HOW_TO_USE.txt for the workflow.

UPDATING: Close Verdant. Back up your old data folder and PDF reports. Extract
the new ZIP to a separate folder, copy the old data folder into it while the
app is closed, then inspect the workpapers before removing the old folder.
This is a portable app, not a setup installer. The earlier setup EXE is stale.
"""

INTEL_REQUIREMENTS = """# Intel macOS Big Sur 11.x, Python 3.11
PySide6==6.5.3
PyMuPDF==1.24.14
openpyxl==3.1.5
PyInstaller==6.21.0
"""

M4_REQUIREMENTS = """# Apple silicon M4, macOS 14 or newer, Python 3.12
PySide6==6.12.0
PySide6_Pdf==6.12.0.140
PyMuPDF==2.1
openpyxl==3.1.5
PyInstaller==6.21.0
"""


def mac_scripts(architecture):
    intel = architecture == "intel"
    arch = "x86_64" if intel else "arm64"
    os_check = ('[[ "$major" == "11" ]]' if intel else '[[ "$major" -ge 14 ]]')
    python = ('python3.11' if intel else 'python3.12')
    build = f'''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "{arch}" ]]; then
  echo "This kit must run on a {arch} Mac." >&2; exit 1
fi
major="$(sw_vers -productVersion | cut -d. -f1)"
if ! {os_check}; then
  echo "Unsupported macOS version: $(sw_vers -productVersion)" >&2; exit 1
fi
if ! command -v {python} >/dev/null 2>&1; then
  echo "Install {python} from python.org, then retry." >&2; exit 1
fi
{python} -m venv .venv-mac
PY=".venv-mac/bin/python"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements-mac.txt
"$PY" -c 'from PySide6.QtPdfWidgets import QPdfView; import pymupdf, openpyxl; print("Imports pass")'
QT_QPA_PLATFORM=offscreen "$PY" -m unittest discover -s tests -q
"$PY" -m PyInstaller --noconfirm --clean --windowed --onedir \\
  --name Verdant --target-arch {arch} \\
  --osx-bundle-identifier org.verdant.disclosure-scorer \\
  --hidden-import PySide6.QtPdf --hidden-import PySide6.QtPdfWidgets \\
  --add-data "resources:resources" app.py
test -d dist/Verdant.app
ditto -c -k --sequesterRsrc --keepParent dist/Verdant.app Verdant_{arch}_Mac.zip
echo "Built: $(pwd)/dist/Verdant.app"
echo "Client ZIP: $(pwd)/Verdant_{arch}_Mac.zip"
'''
    launcher = '#!/bin/bash\ncd "$(dirname "$0")"\nbash ./build_macos.sh\n'
    run = f'''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "{arch}" ]]; then
  echo "Use this kit on a {arch} Mac." >&2; exit 1
fi
if [[ ! -x .venv-mac/bin/python ]]; then
  {python} -m venv .venv-mac
  .venv-mac/bin/python -m pip install -r requirements-mac.txt
fi
.venv-mac/bin/python app.py
'''
    return build, launcher, run


def _zip_write(archive, path, name, executable=False):
    info = ZipInfo(name)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = ((0o755 if executable else 0o644) & 0xffff) << 16
    info.create_system = 3
    archive.writestr(info, path.read_bytes())


def _zip_text(archive, text, name, executable=False):
    info = ZipInfo(name)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = ((0o755 if executable else 0o644) & 0xffff) << 16
    info.create_system = 3
    archive.writestr(info, text.encode("utf-8"))


def _atomic_zip(destination, writer):
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix=".verdant_package_", suffix=".zip", dir=destination.parent)
    os.close(handle)
    try:
        with ZipFile(temp, "w", ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            writer(archive)
        with ZipFile(temp) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Corrupt member in {destination.name}: {bad}")
            if len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError(f"Duplicate entries in {destination.name}")
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def windows_zip(destination):
    executable = WINDOWS_APP / "Verdant_Disclosure_Scorer.exe"
    if not executable.is_file() or not (WINDOWS_APP / "_internal").is_dir():
        raise FileNotFoundError("Build the current Windows app before packaging.")
    def write(archive):
        base = "Verdant_Disclosure_Scorer/"
        for path in sorted(WINDOWS_APP.rglob("*")):
            if path.is_file() and "data" not in path.relative_to(WINDOWS_APP).parts:
                _zip_write(archive, path, base + path.relative_to(WINDOWS_APP).as_posix())
        _zip_text(archive, WINDOWS_START, base + "START_HERE.txt")
        _zip_write(archive, FEATURES, base + FEATURES.name)
        _zip_write(archive, DOCS / "Verdant_Operator_Guide.pdf", base + "Verdant_Operator_Guide.pdf")
    _atomic_zip(destination, write)


def mac_kit(destination, architecture):
    base = "Verdant-Intel-Big-Sur/" if architecture == "intel" else "Verdant-M4/"
    arch_name = "Intel macOS Big Sur 11" if architecture == "intel" else "Apple silicon M4 macOS 14+"
    requirements = INTEL_REQUIREMENTS if architecture == "intel" else M4_REQUIREMENTS
    build, launcher, run = mac_scripts(architecture)
    start = f'''VERDANT {arch_name.upper()} BUILD KIT - 17 NOVEMBER 2026

This ZIP contains COMPLETE CURRENT SOURCE, not a compiled Mac app.
Use only on the matching Mac with Python installed and internet access.

1. Extract the entire ZIP.
2. In Terminal, enter the extracted folder and run: bash ./build_macos.sh
   (Build_Verdant.command performs the same build if macOS allows opening it.)
3. The script installs dependencies, runs the full test suite, builds Verdant.app,
   and creates a separate Verdant_*.zip for clients. Do not send this build kit
   as if it were the ready-made app.
4. Launch dist/Verdant.app on that Mac. Import a PDF, run OCR, save a score,
   pin evidence, and export sheets. Only then distribute the generated Mac ZIP.

Optional source test: bash ./run.command (installs dependencies if needed).
App data for compiled Mac apps: ~/Library/Application Support/Verdant/data
The ZIP does not include workpapers or client PDFs.
'''
    def write(archive):
        for name in SOURCE_FILES:
            _zip_write(archive, SOURCE / name, base + name)
        for folder in ("verdant", "resources", "tests"):
            for path in sorted((SOURCE / folder).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo"):
                    _zip_write(archive, path, base + path.relative_to(SOURCE).as_posix())
        _zip_text(archive, requirements, base + "requirements-mac.txt")
        _zip_text(archive, build, base + "build_macos.sh", True)
        _zip_text(archive, launcher, base + "Build_Verdant.command", True)
        _zip_text(archive, run, base + "run.command", True)
        _zip_text(archive, start, base + "START_HERE.txt")
        _zip_write(archive, FEATURES, base + FEATURES.name)
        _zip_write(archive, DOCS / "Verdant_Operator_Guide.pdf", base + "Verdant_Operator_Guide.pdf")
    _atomic_zip(destination, write)


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    release_docs = OUTPUT / "Documentation"
    release_docs.mkdir(exist_ok=True)
    for pdf in DOCS.glob("*.pdf"):
        shutil.copy2(pdf, release_docs / pdf.name)
    shutil.copy2(FEATURES, OUTPUT / FEATURES.name)
    windows = OUTPUT / "Verdant_Disclosure_Scorer_Windows.zip"
    intel = OUTPUT / "MAC Files" / "Verdant_Intel_BigSur_Build_Kit.zip"
    m4 = OUTPUT / "MAC Files" / "Verdant_M4_MacBook_Air_Build_Kit.zip"
    windows_zip(windows)
    mac_kit(intel, "intel")
    mac_kit(m4, "m4")
    readme = """VERDANT CURRENT DISTRIBUTION - 17 NOVEMBER 2026

Windows: Verdant_Disclosure_Scorer_Windows.zip is a ready-to-run portable app.
Intel Big Sur: MAC Files/Verdant_Intel_BigSur_Build_Kit.zip is a source build kit.
M4: MAC Files/Verdant_M4_MacBook_Air_Build_Kit.zip is a source build kit.

Mac client apps still require build and verification on each matching Mac.
The older setup EXE and older handoff ZIP are superseded by this distribution.
Read FEATURES_AND_HOW_TO_USE.txt and Documentation/Verdant_Operator_Guide.pdf.
No package contains client data or company PDF reports.
"""
    (OUTPUT / "CURRENT_RELEASE_README.txt").write_text(readme, encoding="utf-8")
    (OUTPUT / "MAC Files" / "README_FIRST.txt").write_text(readme, encoding="utf-8")
    checks = []
    for path in [windows, intel, m4, OUTPUT / FEATURES.name, OUTPUT / "CURRENT_RELEASE_README.txt", *sorted(release_docs.glob("*.pdf"))]:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checks.append(f"{digest}  {path.relative_to(OUTPUT).as_posix()}")
    (OUTPUT / "SHA256SUMS.txt").write_text("\n".join(checks) + "\n", encoding="utf-8")
    combined = OUTPUT / "Verdant_Final_Handoff.zip"
    def write_combined(archive):
        for path in [windows, intel, m4, OUTPUT / FEATURES.name, OUTPUT / "CURRENT_RELEASE_README.txt", OUTPUT / "SHA256SUMS.txt", *sorted(release_docs.glob("*.pdf"))]:
            _zip_write(archive, path, "Verdant_Final_Handoff/" + path.relative_to(OUTPUT).as_posix())
    _atomic_zip(combined, write_combined)
    (OUTPUT / "Verdant_Final_Handoff.zip.sha256").write_text(
        f"{hashlib.sha256(combined.read_bytes()).hexdigest()}  {combined.name}\n", encoding="ascii")
    return [windows, intel, m4, combined]


if __name__ == "__main__":
    for path in build():
        print(path, path.stat().st_size)
