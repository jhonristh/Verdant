import tempfile
import unittest
import sys
from pathlib import Path
from zipfile import ZipFile

if sys.platform == "win32":
    import installer


@unittest.skipUnless(sys.platform == "win32", "Windows installer tests")
class InstallerTests(unittest.TestCase):
    def test_update_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "Installed Verdant"
            data = target / "data"
            data.mkdir(parents=True)
            (data / "pdf_scorer.db").write_bytes(b"existing work")
            package = root / "payload.zip"
            with ZipFile(package, "w") as archive:
                archive.writestr(installer.EXE_NAME, b"version 2")
                archive.writestr("_internal/rubric.json", b"{}")
            self.assertEqual(installer.install_payload(package, target), 2)
            self.assertEqual((target / installer.EXE_NAME).read_bytes(), b"version 2")
            self.assertEqual((data / "pdf_scorer.db").read_bytes(), b"existing work")

    def test_rejects_data_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "payload.zip"
            with ZipFile(package, "w") as archive:
                archive.writestr(installer.EXE_NAME, b"exe")
                archive.writestr("data/pdf_scorer.db", b"do not ship")
            with self.assertRaises(ValueError):
                installer.install_payload(package, root / "target")
            self.assertFalse((root / "target").exists())
        for name in ("../outside", "/rooted", "C:/drive", "a\\..\\outside"):
            with self.assertRaises(ValueError):
                installer._safe_member(name)
