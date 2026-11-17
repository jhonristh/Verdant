import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook, load_workbook

from verdant.services.master_export import export_master_workbook
from verdant.services.workpaper_transfer import export_workpaper, import_workpaper
from verdant.services.template_export import BENCHMARK_PATH, TEMPLATE_PATH, export_general_workbook
from verdant.storage.repository import Store


class EvidencePinsTests(unittest.TestCase):
    def test_general_output_uses_template_copy_and_keeps_all_pins(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_hash = hashlib.sha256(TEMPLATE_PATH.read_bytes()).hexdigest()
            store = Store(root / "scores.db")
            project = store.project("Aboitiz Power Corporation", "2022")
            store.add_evidence_pin(project, "E1", "one.pdf", 3, "First passage", "iv")
            store.add_evidence_pin(project, "E1", "two.pdf", 8, "Second passage")
            store.save_score(project, "E1", 1, None, "one.pdf; two.pdf", "3, 8")
            store.set_setting("evidence_page_type", "Printed")
            output = root / "consolidated.xlsx"
            export_general_workbook(store, output)
            book = load_workbook(output, read_only=True, data_only=False)
            self.assertEqual(len(book.sheetnames), 9)
            self.assertEqual(book["ESG_Scores"]["E4"].value, 1)
            self.assertEqual(book["ESG_Scores"]["D4"].value, 2022)
            self.assertEqual(book["Evidence_Log"]["E4"].value, "one.pdf")
            self.assertEqual(book["Evidence_Log"]["F4"].value, "iv")
            self.assertEqual(book["Evidence_Log"]["E5"].value, "two.pdf")
            self.assertEqual(book["Evidence_Log"]["F5"].value, 8)
            self.assertEqual(book["Evidence_Log"]["G5"].value, "Second passage")
            with ZipFile(TEMPLATE_PATH) as original_zip, ZipFile(output) as output_zip:
                for member in ("xl/worksheets/sheet4.xml", "xl/worksheets/sheet5.xml", "xl/worksheets/sheet7.xml"):
                    self.assertEqual(original_zip.read(member).count(b"<extLst"),
                                     output_zip.read(member).count(b"<extLst"))
                self.assertIn(b'forceFullCalc="1"', output_zip.read("xl/workbook.xml"))
            self.assertEqual(hashlib.sha256(TEMPLATE_PATH.read_bytes()).hexdigest(), original_hash)
            with self.assertRaises(ValueError):
                export_general_workbook(store, TEMPLATE_PATH)
            with self.assertRaises(ValueError):
                export_general_workbook(store, BENCHMARK_PATH)
            book.close(); store.db.close()

    def test_null_note_multiple_pins_export_and_transfer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            roster = Workbook(); companies = roster.active; companies.title = "Companies"
            companies.append(["Companies"]); companies.append([])
            companies.append(["No.", "Ticker", "Company"])
            companies.append([1, "Reviewer", "Alpha PLC"])
            roster_path = root / "roster.xlsx"; roster.save(roster_path)
            source = Store(root / "source.db")
            project = source.project("Alpha PLC", "2022")
            source.add_evidence_pin(project, "E1", "annual.pdf", 4, "First company passage", "iv")
            source.add_evidence_pin(project, "E1", "integrated.pdf", 12, "Second company passage")
            source.save_score(project, "E1", 1, None, "annual.pdf; integrated.pdf", "4, 12")
            self.assertIsNone(source.score_records(project)["E1"]["evidence"])
            self.assertEqual(len(source.evidence_pins(project, "E1")), 2)

            exported = root / "master.xlsx"
            export_master_workbook(source, exported, roster_path)
            book = load_workbook(exported, data_only=False)
            rows = list(book["Evidence_Log"].iter_rows(min_row=4, max_col=8, values_only=True))
            self.assertEqual(len(rows), 2)
            self.assertEqual([(row[3], row[4], row[5], row[6]) for row in rows],
                             [("E1", "annual.pdf", 4, "First company passage"),
                              ("E1", "integrated.pdf", 12, "Second company passage")])
            archive = root / "transfer.verdant"
            export_workpaper(source, project, archive)
            target = Store(root / "target.db")
            imported = import_workpaper(target, archive)
            self.assertTrue(imported["imported"])
            self.assertEqual(len(target.evidence_pins(imported["project_id"], "E1")), 2)
            self.assertEqual(target.evidence_pins(imported["project_id"], "E1")[0]["printed_page"], "iv")
            self.assertIsNone(target.score_records(imported["project_id"])["E1"]["evidence"])
            source.db.close(); target.db.close()


if __name__ == "__main__":
    unittest.main()
