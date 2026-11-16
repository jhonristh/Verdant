$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Rebuild the application before embedding it into the standalone installer.
& "$PSScriptRoot\build_qt_exe.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Verdant application build failed' }

& '.\.venv\Scripts\python.exe' '.\tools\create_installer_payload.py'
if ($LASTEXITCODE -ne 0) { throw 'Installer payload build failed' }

& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name Verdant_Setup --icon 'brand_mark.ico' --add-data 'build\installer_payload.zip;.' installer.py
if ($LASTEXITCODE -ne 0) { throw 'Verdant setup EXE build failed' }

Write-Output "Installer: $PSScriptRoot\dist\Verdant_Setup.exe"
