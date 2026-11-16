"""Rubric loading and item construction, independent of any UI toolkit."""
import json
import re

from verdant.config import RUBRIC_PATH


def load_rubric(path=RUBRIC_PATH):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def keyword_pattern(keyword):
    escaped = re.escape(keyword)
    flags = 0 if keyword.isupper() and len(keyword) <= 5 else re.I
    return re.compile(rf"(?<!\w){escaped}(?!\w)", flags)


def build_items(rubric=None):
    rubric = rubric or load_rubric()
    items = [{**item, "kind": "ESG", "weight": 1} for item in rubric["esg"]]
    for number, title, terms in rubric["sdgs"]:
        for stage, weight in rubric["sdg_weights"].items():
            items.append({"id": f"SDG{number}-{stage}", "kind": "SDG", "pillar": f"SDG {number}",
                          "title": f"{title}: {stage}",
                          "keywords": [part.strip() for part in terms.split(",")],
                          "weight": weight, "stage": stage, "number": number})
    return items
