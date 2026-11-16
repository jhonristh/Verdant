$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& ".\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --noconsole --onedir --name Verdant_Disclosure_Scorer --icon "resources\brand_mark.ico" --hidden-import PySide6.QtPdf --hidden-import PySide6.QtPdfWidgets --add-data "resources;resources" app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
$internal = Join-Path $PSScriptRoot 'dist\Verdant_Disclosure_Scorer\_internal'
# Use the Qt wheel's matching VC runtime beside Python's bundled DLLs.
foreach ($name in @('VCRUNTIME140.dll', 'VCRUNTIME140_1.dll')) {
    $qtRuntime = Join-Path $internal "PySide6\$name"
    if (Test-Path -LiteralPath $qtRuntime) {
        Copy-Item -LiteralPath $qtRuntime -Destination (Join-Path $internal $name) -Force
    }
}
# A transitive package supplies ICU 78 with versioned exports. Qt imports the
# Windows ICU API by unversioned names, so that copy must not shadow System32.
$conflictingIcu = Join-Path $internal 'icuuc.dll'
if (Test-Path -LiteralPath $conflictingIcu) { Remove-Item -LiteralPath $conflictingIcu }
