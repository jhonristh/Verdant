import unittest

from scoring_assist import assess_item, assess_all


class SuggestionTests(unittest.TestCase):
    def test_contents_bare_mention_and_strong_passage(self):
        item = {"id": "E1", "kind": "ESG", "keywords": ["electricity"]}
        pages = ["Table of contents electricity ................ 12",
                 "Electricity is important in the industry in 2022. See page 13.",
                 "Our electricity reduction program saved 12% of use this year."]
        result = assess_item(item, [("report.pdf", pages)])
        self.assertEqual(result["suggestion"], 1)
        self.assertEqual(result["hits"][0]["page"], 3)
        self.assertFalse(result["hits"][1]["strong"])

    def test_sdg_list_is_not_a_lead(self):
        item = {"id": "SDG3-Identified", "kind": "SDG", "stage": "Identified", "number": 3, "keywords": ["SDG 3"]}
        result = assess_item(item, [("report.pdf", ["Our SDGs 3, 4 and 8 are shown on page 3."])])
        self.assertEqual(result["suggestion"], 0)
    def test_no_hit_proposes_low_confidence_zero(self):
        item={"id":"E2","kind":"ESG","keywords":["energy cost"]}
        result=assess_item(item,[("report.pdf",["Nothing relevant here."])])
        self.assertEqual(result["suggestion"],0)
        self.assertEqual(result["confidence"],"low")
        self.assertEqual(result["hits"],[])

    def test_contextual_esg_proposes_one_with_evidence(self):
        item={"id":"E2","kind":"ESG","keywords":["energy cost","electricity cost"]}
        result=assess_item(item,[("report.pdf",["The company reported electricity cost of PHP 14 million and a fuel cost risk."])])
        self.assertEqual(result["suggestion"],1)
        self.assertEqual(result["hits"][0]["page"],1)

    def test_generic_keyword_requires_review(self):
        item={"id":"S3","kind":"ESG","keywords":["training"]}
        result=assess_item(item,[("report.pdf",["Training is important for everyone."])])
        self.assertEqual(result["suggestion"],0)

    def test_sdg_stage_proposal_respects_prerequisite(self):
        items=[{"id":f"SDG1-{stage}","kind":"SDG","stage":stage,"number":1,"keywords":["poverty"]}
               for stage in ("Identified","Managed","Reported")]
        result=assess_all(items,[("report.pdf",["Our poverty program reached 100 people in 2022."])])
        self.assertEqual(result["SDG1-Identified"]["suggestion"],0)
        self.assertEqual(result["SDG1-Managed"]["suggestion"],0)
        self.assertEqual(result["SDG1-Reported"]["suggestion"],0)


if __name__=="__main__":
    unittest.main()
