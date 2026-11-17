import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from verdant.domain.rubric import build_items
from verdant.services.workspace_export import export_workspace_workbook
from verdant.storage.repository import Store


class WorkspaceExportTests(unittest.TestCase):
    def test_only_current_workspace_with_decisions_leads_and_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root / "scores.db")
            current = store.project("Alpha PLC", "2022")
            other = store.project("Beta PLC", "2023")
            store.save_score(current, "E1", 1, None, "annual.pdf", "4")
            store.add_evidence_pin(current, "E1", "annual.pdf", 4, "=company-specific evidence")
            store.save_score(current, "E2", 0, None, None, None)
            store.save_score(other, "E1", 1, "Other company", "other.pdf", "8")
            items = build_items()
            results = {item["id"]: {"suggestion": 0, "confidence": "low", "label": "No lead",
                                    "reason": "No hit", "hits": []} for item in items}
            results["E1"] = {"suggestion": 1, "confidence": "high", "label": "Lead found",
                             "reason": "Company-specific evidence", "hits": [{"document": "annual.pdf", "page": 4}]}
            store.save_predictions(current, items, results)
            output = export_workspace_workbook(store, current, items, root / "alpha.xlsx")
            book = load_workbook(output, read_only=True, data_only=False)
            self.assertEqual(book.sheetnames, ["Summary", "Decisions", "Evidence pins"])
            self.assertEqual(book["Summary"]["B2"].value, "Alpha PLC")
            self.assertEqual(book["Summary"]["B3"].value, "2022")
            self.assertEqual(book["Summary"]["B5"].value, "1 / 30")
            decisions = book["Decisions"]
            self.assertEqual(decisions.max_row, 82)
            self.assertEqual([decisions.cell(2, column).value for column in (2, 5, 6, 7, 10, 11, 15)],
                             ["E1", "Supported", 1, "Lead found", "annual.pdf", 4, None])
            self.assertEqual(decisions["E3"].value, "Not supported")
            self.assertEqual(decisions["F3"].value, 0)
            self.assertEqual(decisions["E4"].value, "Not reviewed")
            self.assertEqual(decisions["F4"].value, None)
            self.assertEqual(book["Evidence pins"]["E2"].value, "'=company-specific evidence")
            self.assertNotIn("Other company", str(list(decisions.values)))
            book.close(); store.db.close()


if __name__ == "__main__":
    unittest.main()
