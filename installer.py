"""Per-user Windows installer for Verdant's verified one-directory package."""
from __future__ import annotations

import argparse
import ctypes
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import winreg
from zipfile import ZipFile


APP_NAME = "Verdant Disclosure Scorer"
EXE_NAME = "Verdant_Disclosure_Scorer.exe"
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\VerdantDisclosureScorer"
DEFAULT_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / APP_NAME


def payload_path() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "installer_payload.zip"


def _safe_member(name: str) -> Path:
    if name.startswith(("/", "\\")) or "\\" in name:
        raise ValueError(f"Unsafe package path: {name}")
    parts = PurePosixPath(name).parts
    if not parts or any(part in ("", ".", "..") for part in parts) or ":" in parts[0]:
        raise ValueError(f"Unsafe package path: {name}")
    return Path(*parts)


def _check_app_closed(target: Path) -> None:
    """Windows exclusive open catches a running packaged EXE before updating."""
    executable = target / EXE_NAME
    if not executable.exists():
        return
    kernel = ctypes.windll.kernel32
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                   ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                   ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    handle = kernel.CreateFileW(str(executable), 0x80000000, 0, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise RuntimeError("Close Verdant before installing an update.")
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle(handle)


def install_payload(package: Path, target: Path, progress=None) -> int:
    """Extract known package files while preserving target/data on upgrades."""
    target = target.expanduser().resolve()
    if target == Path(target.anchor) or not target.is_absolute():
        raise ValueError("Choose an application folder, not a drive root.")
    _check_app_closed(target)
    with ZipFile(package) as archive:
        members = [(entry, _safe_member(entry.filename)) for entry in archive.infolist()
                   if not entry.is_dir()]
        if not any(relative.name == EXE_NAME and len(relative.parts) == 1
                   for _, relative in members):
            raise ValueError("The setup package does not contain Verdant's EXE.")
        if any(relative.parts[0].casefold() == "data" for _, relative in members):
            raise ValueError("The setup package must not contain saved user data.")
        target.mkdir(parents=True, exist_ok=True)
        for index, (entry, relative) in enumerate(members, 1):
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_name(output.name + ".verdant-new")
            try:
                with archive.open(entry) as source, temporary.open("wb") as destination:
                    while chunk := source.read(1024 * 1024):
                        destination.write(chunk)
                os.replace(temporary, output)
            finally:
                if temporary.exists():
                    temporary.unlink()
            if progress and (index == 1 or index % 25 == 0 or index == len(members)):
                progress(index, len(members), relative.name)
    return len(members)


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _start_menu_link() -> Path:
    return (Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" /
            "Programs" / f"{APP_NAME}.lnk")


def create_shortcut(target: Path) -> Path:
    link = _start_menu_link()
    link.parent.mkdir(parents=True, exist_ok=True)
    command = ("$s=New-Object -ComObject WScript.Shell; "
               f"$l=$s.CreateShortcut({_powershell_quote(str(link))}); "
               f"$l.TargetPath={_powershell_quote(str(target / EXE_NAME))}; "
               f"$l.WorkingDirectory={_powershell_quote(str(target))}; "
               "$l.Description='Verdant Disclosure Scorer'; $l.Save()")
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                   check=True, capture_output=True, text=True)
    return link


UNINSTALL_SCRIPT = r'''$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($PSScriptRoot)
$internal = [IO.Path]::GetFullPath((Join-Path $root '_internal'))
if (-not $internal.StartsWith($root + [IO.Path]::DirectorySeparatorChar,
    [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid install path' }
$app = Join-Path $root 'Verdant_Disclosure_Scorer.exe'
if (Get-Process -Name 'Verdant_Disclosure_Scorer' -ErrorAction SilentlyContinue) {
    throw 'Close Verdant before uninstalling.'
}
if (Test-Path -LiteralPath $internal) { Remove-Item -LiteralPath $internal -Recurse -Force }
foreach ($name in @('Verdant_Disclosure_Scorer.exe', 'START_HERE.txt')) {
    $path = Join-Path $root $name
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
}
$link = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Verdant Disclosure Scorer.lnk'
if (Test-Path -LiteralPath $link) { Remove-Item -LiteralPath $link -Force }
reg.exe delete 'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\VerdantDisclosureScorer' /f | Out-Null
Write-Host "Verdant program files removed. Saved work remains in $root\data"
'''


def register_uninstaller(target: Path) -> None:
    script = target / "Uninstall_Verdant.ps1"
    script.write_text(UNINSTALL_SCRIPT, encoding="utf-8-sig")
    command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{script}"'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "3.0-prototype")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Verdant")
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(target))
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(target / EXE_NAME))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, command)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Verdant for the current Windows user")
    parser.add_argument("--install-dir", type=Path, help="Install destination; defaults to Local AppData")
    parser.add_argument("--no-shortcut", action="store_true", help="Do not create a Start Menu shortcut")
    parser.add_argument("--no-registry", action="store_true", help="Do not register in Windows Apps")
    parser.add_argument("--quiet", action="store_true", help="Install without a dialog")
    args = parser.parse_args()
    package = payload_path()
    if not package.is_file():
        raise FileNotFoundError(f"Missing installer payload: {package}")

    def do_install(target: Path, update=None):
        count = install_payload(package, target, update)
        if not args.no_shortcut:
            create_shortcut(target)
        if not args.no_registry:
            register_uninstaller(target)
        return count

    if args.quiet:
        do_install(args.install_dir or DEFAULT_DIR)
        return 0

    window = tk.Tk()
    window.title("Verdant Setup")
    window.geometry("560x260")
    window.resizable(False, False)
    window.configure(bg="#eff5ef")
    destination = tk.StringVar(value=str(args.install_dir or DEFAULT_DIR))
    status = tk.StringVar(value="Install Verdant for this Windows user. Saved work is preserved on updates.")
    frame = ttk.Frame(window, padding=22)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="verdant.  /  Disclosure Scorer", font=("Segoe UI", 16, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Choose where the application files will be installed.").pack(anchor="w", pady=(12, 8))
    row = ttk.Frame(frame)
    row.pack(fill="x")
    ttk.Entry(row, textvariable=destination).pack(side="left", fill="x", expand=True)
    ttk.Button(row, text="Browse", command=lambda: destination.set(
        filedialog.askdirectory(initialdir=destination.get()) or destination.get())).pack(side="left", padx=(8, 0))
    bar = ttk.Progressbar(frame, maximum=100)
    bar.pack(fill="x", pady=(18, 6))
    ttk.Label(frame, textvariable=status, wraplength=510).pack(anchor="w")
    actions = ttk.Frame(frame)
    actions.pack(fill="x", pady=(18, 0))

    def start():
        target = Path(destination.get().strip())
        install_button.configure(state="disabled")
        window.update_idletasks()
        try:
            count = do_install(target, lambda done, total, name: (
                bar.configure(value=100 * done / total),
                status.set(f"Installing {done}/{total}: {name}"),
                window.update_idletasks()))
        except Exception as exc:
            install_button.configure(state="normal")
            status.set("Installation did not finish.")
            messagebox.showerror("Verdant Setup", str(exc))
            return
        status.set(f"Installed {count} files. Your saved data folder was not overwritten.")
        install_button.configure(text="Open Verdant", state="normal",
                                 command=lambda: (subprocess.Popen([str(target / EXE_NAME)]), window.destroy()))
        messagebox.showinfo("Verdant Setup", f"Verdant is ready in:\n{target}")

    ttk.Button(actions, text="Cancel", command=window.destroy).pack(side="right")
    install_button = ttk.Button(actions, text="Install", command=start)
    install_button.pack(side="right", padx=(0, 8))
    window.mainloop()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        if "--quiet" not in sys.argv:
            try:
                messagebox.showerror("Verdant Setup", str(error))
            except Exception:
                pass
        raise
