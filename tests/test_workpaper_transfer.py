import hashlib
import tempfile
import unittest
from pathlib import Path

from verdant.services.workpaper_transfer import export_workpaper, import_workpaper
from verdant.storage.repository import Store


class WorkpaperTransferTests(unittest.TestCase):
    def test_export_import_and_newer_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports"; reports.mkdir()
            report = reports / "annual.pdf"; report.write_bytes(b"sample PDF bytes")
            digest = hashlib.sha256(report.read_bytes()).hexdigest()
            first = Store(root / "a" / "work.db")
            first.set_reports_root(reports)
            project = first.project("Alpha PLC", "2023")
            first.add_report(project, report, digest, 1, 1)
            first.save_score(project, "E1", 1, "A specific risk", "annual.pdf", "1")
            first.save_score(project, "SDG1-Identified", 0, "", "", "")
            first.save_ocr_pages(project, [(str(report), digest, 1, "Recognized text")])
            self.assertEqual(first.db.execute("SELECT path FROM reports").fetchone()[0], "annual.pdf")
            archive = root / "workpaper.verdant"
            export_workpaper(first, project, archive)

            moved = root / "moved"; moved.mkdir()
            moved_report = moved / "annual.pdf"; moved_report.write_bytes(report.read_bytes())
            second = Store(root / "b" / "work.db")
            second.set_reports_root(moved)
            result = import_workpaper(second, archive)
            self.assertTrue(result["imported"])
            target = result["project_id"]
            self.assertEqual(second.scores(target), first.scores(project))
            self.assertEqual(second.ocr_text(target, moved_report, digest), {1: "Recognized text"})
            self.assertEqual(Path(second.reports(target)[0][0]), moved_report)
            self.assertEqual(second.db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0], 2)

            second.save_score(target, "E1", 0, "", "", "")
            with second.db:
                second.db.execute("UPDATE scores SET updated_at='2020-01-01T00:00:00' WHERE item_id='E1'")
            preview = import_workpaper(second, archive)
            self.assertFalse(preview["imported"])
            self.assertEqual(preview["conflicts"][0]["winner"], "incoming")
            self.assertEqual(second.scores(target)["E1"][0], 0)
            applied = import_workpaper(second, archive, accept_newer=True)
            self.assertTrue(applied["imported"])
            self.assertEqual(second.scores(target)["E1"][0], 1)
            first.db.close(); second.db.close()

    def test_relink_by_hash_preserves_ocr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); a = root / "a"; b = root / "b"
            a.mkdir(); b.mkdir()
            original = a / "annual.pdf"; original.write_bytes(b"same report")
            moved = b / "annual.pdf"; moved.write_bytes(original.read_bytes())
            digest = hashlib.sha256(original.read_bytes()).hexdigest()
            store = Store(root / "work.db")
            project = store.project("Alpha PLC", "2023")
            store.add_report(project, original, digest, 1, 1)
            store.save_ocr_pages(project, [(str(original), digest, 1, "OCR")])
            original.unlink()
            self.assertEqual(store.relink_report(project, original, moved), "hash")
            self.assertEqual(store.ocr_text(project, moved, digest), {1: "OCR"})
            store.db.close()


if __name__ == "__main__":
    unittest.main()
