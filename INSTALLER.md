# Verdant Windows setup

`dist\Verdant_Setup.exe` is a standalone per-user Windows installer. Send that
single file for installation; recipients do not need Python. Double-click it,
choose a folder, and click **Install**. The default location is
`%LOCALAPPDATA%\Programs\Verdant Disclosure Scorer`. Setup adds a Start Menu
shortcut and an entry in Windows Installed apps for the current user.

Setup installs the app EXE and its required `_internal` folder. It does not
include research workpapers or PDF reports. The installed app creates its
`data` folder beside its EXE. On an update, setup replaces program files while
leaving `data` unchanged. Close Verdant before updating. Uninstall removes the
program and Start Menu shortcut but leaves `data` for recovery. Imported PDF
files remain at their original paths.

To rebuild from source on a Windows PC with Python 3.13:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_installer.ps1
```

The script rebuilds the onedir app, creates a data-free payload, then creates
`dist\Verdant_Setup.exe`. Build and startup were tested locally. The setup EXE
is unsigned; Windows may show a publisher warning. A clean second-PC install
has not been verified.
