import unittest

from app_qt import make_items
from scoring_assist import assess_item
from verdant.domain.rubric import build_items, keyword_pattern, load_rubric


class SDGKeywordTests(unittest.TestCase):
    def test_all_seventeen_goals_include_number_title_and_topic_terms(self):
        rubric = load_rubric()
        domain = build_items(rubric)
        ui = make_items()
        self.assertEqual(len(domain), 81)
        self.assertEqual([item["keywords"] for item in domain],
                         [item["keywords"] for item in ui])
        for number, title, terms in rubric["sdgs"]:
            stages = [item for item in domain if item.get("number") == number]
            self.assertEqual(len(stages), 3)
            for item in stages:
                self.assertIn(f"SDG {number}", item["keywords"])
                self.assertIn(title, item["keywords"])
                for term in terms.split(","):
                    self.assertIn(term.strip(), item["keywords"])
                self.assertTrue(keyword_pattern(f"SDG {number}").search(f"SDG{number}"))
                self.assertTrue(keyword_pattern(f"SDG {number}").search(f"SDG {number}"))
                self.assertTrue(keyword_pattern(title).search(title.replace(" ", "\n")))
        self.assertFalse(keyword_pattern("SDG 1").search("SDG 10"))

    def test_title_and_number_can_find_company_specific_leads(self):
        items = make_items()
        poverty = next(item for item in items if item["id"] == "SDG1-Identified")
        by_title = assess_item(poverty, [("report.pdf", ["Our No Poverty program served 200 people."])])
        by_number = assess_item(poverty, [("report.pdf", ["Our SDG1 program served 200 people."])])
        self.assertEqual(by_title["suggestion"], 1)
        self.assertEqual(by_number["suggestion"], 1)
        self.assertEqual(by_title["hits"][0]["page"], 1)


if __name__ == "__main__":
    unittest.main()
