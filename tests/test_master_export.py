import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

from verdant.services.master_export import ESG_IDS, export_master_workbook
from verdant.storage.repository import Store


class MasterExportTests(unittest.TestCase):
    def test_three_company_years_match_master_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            roster = Workbook(); sheet = roster.active; sheet.title = "Companies"
            sheet.append(["Companies"]); sheet.append([])
            sheet.append(["No.", "Ticker", "Company name"])
            sheet.append([1, "Ana", "Alpha PLC"])
            sheet.append([2, "Ben", "Beta PLC"])
            roster_path = root / "roster.xlsx"; roster.save(roster_path)
            store = Store(root / "work.db")
            alpha22 = store.project("Alpha PLC", "2022")
            alpha23 = store.project("Alpha PLC", "2023")
            beta22 = store.project("Beta PLC", "2022")
            store.save_score(alpha22, "E1", 1, "Site-specific policy", "alpha.pdf", "5")
            store.save_score(alpha22, "E2", 0, "", "", "")
            for stage in ("Identified", "Managed", "Reported"):
                store.save_score(alpha22, f"SDG1-{stage}", 1, stage, "alpha.pdf", "7")
            store.save_score(alpha23, "S10", 1, "Training at site", "alpha23.pdf", "12")
            store.save_score(beta22, "G10", 0, "", "", "")
            output = root / "export.xlsx"
            export_master_workbook(store, output, roster_path)
            book = load_workbook(output, data_only=False)
            esg, sdg, evidence = (book[name] for name in ("ESG_Scores", "SDG_Scores", "Evidence_Log"))
            self.assertEqual([esg.cell(4, col).value for col in range(1, 7)],
                             [1, "Ana", "Alpha PLC", 2022, 1, 0])
            self.assertEqual([esg.cell(5, col).value for col in range(1, 6)],
                             [1, "Ana", "Alpha PLC", 2023, None])
            self.assertEqual(esg["X5"].value, 1)  # S10
            self.assertEqual([esg.cell(8, col).value for col in range(1, 5)],
                             [2, "Ben", "Beta PLC", 2022])
            self.assertEqual(esg["AH8"].value, 0)
            self.assertTrue(all(esg.cell(4, 5 + i).value is None for i in range(2, len(ESG_IDS))))
            self.assertEqual([sdg.cell(4, col).value for col in range(5, 8)], [1, 1, 1])
            self.assertEqual(sdg["H4"].value,
                             '=IF(COUNT(E4:G4)<3,"",E4+2*E4*F4+3*E4*F4*G4)')
            self.assertTrue(sdg["BU4"].value.startswith("=IF(COUNT("))
            self.assertEqual([evidence.cell(4, col).value for col in range(1, 9)],
                             ["Ana", 2022, "ESG", "E1", "alpha.pdf", "5", "Site-specific policy", "Alpha PLC"])
            self.assertEqual(evidence.max_row, 8)  # E1, SDG1 x3, S10
            self.assertIn("master workbook", book["README"]["A1"].value)
            store.db.close()


if __name__ == "__main__":
    unittest.main()
