import tempfile
import unittest
from pathlib import Path

from runtime_paths import data_directory


class RuntimePathsTests(unittest.TestCase):
    def test_mac_bundle_data_is_outside_read_only_app(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            result = data_directory(
                source_root=home / "Verdant.app" / "Contents" / "Resources",
                executable=home / "Verdant.app" / "Contents" / "MacOS" / "Verdant",
                frozen=True, platform="darwin", home=home,
            )
            self.assertEqual(result, home / "Library" / "Application Support" / "Verdant" / "data")

    def test_windows_bundle_keeps_existing_data_location(self):
        with tempfile.TemporaryDirectory() as root:
            executable = Path(root) / "Verdant" / "Verdant.exe"
            result = data_directory(executable=executable, frozen=True, platform="win32")
            self.assertEqual(result, executable.parent / "data")

    def test_source_uses_local_data(self):
        root = Path("/example/Verdant")
        self.assertEqual(data_directory(source_root=root, frozen=False), root / "data")


if __name__ == "__main__":
    unittest.main()
