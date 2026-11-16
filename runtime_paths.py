"""Writable application data paths for source and packaged builds."""
import sys
from pathlib import Path


def data_directory(source_root=None, executable=None, frozen=None, platform=None, home=None):
    source_root = Path(source_root or Path(__file__).resolve().parent)
    executable = Path(executable or sys.executable)
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else Path(home)
    if frozen and platform == "darwin":
        return home / "Library" / "Application Support" / "Verdant" / "data"
    return (executable.resolve().parent if frozen else source_root) / "data"
