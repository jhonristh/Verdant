"""Rule-based evidence leads; only reviewers save decisions."""
import re

from app import keyword_pattern

FIGURE = re.compile(r"(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:%(?!\w)|(?:percent|tonnes?|tons?|tco2e|co2e|employees|people|sites|million|billion|php|₱|mw|mwh)\b)", re.I)
PROGRAM = re.compile(r"\b(?:[A-Za-z][\w&-]+\s+){1,4}(?:Program|Programme|Committee|Board|Policy|Initiative|Team|Department|Division|Fund)\b", re.I)
COMPANY_CUE = re.compile(r"\b(?:the company|we|our|us|the group|our group)\b", re.I)
CONTENTS = re.compile(r"\b(?:table of contents|contents|index)\b", re.I)
SDG_LIST = re.compile(r"\bSDGs?[\s-]*\d{1,2}(?:\s*[,/&]|\s+and\s+)\s*\d{1,2}", re.I)
SDG_CUES = {
    "Identified": re.compile(r"\b(?:SDG|sustainable development goal)\s*\d{1,2}\b", re.I),
    "Managed": re.compile(r"\b(?:target|KPI|program|initiative|budget|team|committee)\b", re.I),
    "Reported": re.compile(r"\b(?:reduced|reached|trained|provided|achieved|completed|benefited|served)\b", re.I),
}


def _company_cue(passage, company_name):
    if COMPANY_CUE.search(passage):
        return True
    tokens = [word for word in re.findall(r"[A-Za-z]{4,}", company_name or "")
              if word.lower() not in {"incorporated", "corporation", "company", "limited", "holdings"}]
    return bool(tokens and re.search(rf"\b{re.escape(tokens[0])}\b", passage, re.I))


def assess_item(item, documents, company_name=""):
    """Return a lead and source passage; never save a score."""
    hits = []
    for name, pages in documents:
        for page_number, text in enumerate(pages, 1):
            matched = [word for word in item["keywords"] if keyword_pattern(word).search(text)]
            if not matched:
                continue
            first = keyword_pattern(matched[0]).search(text)
            passage = text[max(0, first.start()-250):min(len(text), first.end()+550)].replace("\n", " ")
            specific = _company_cue(passage, company_name)
            concrete = bool(FIGURE.search(passage) or PROGRAM.search(passage))
            list_only = item["kind"] == "SDG" and bool(SDG_LIST.search(passage)) and not concrete
            index_page = bool(CONTENTS.search(text[:300])) or (len(text) < 600 and text.count("...") >= 3)
            stage_cue = True
            if item["kind"] == "SDG":
                stage_cue = bool(SDG_CUES[item["stage"]].search(passage))
                if item["stage"] == "Identified":
                    number_cue = bool(re.search(rf"\b(?:SDG|sustainable development goal)[\s-]*{item['number']}\b", passage, re.I))
                    title = item.get("title", "").rsplit(": ", 1)[0]
                    title_cue = bool(title and keyword_pattern(title).search(passage))
                    stage_cue = number_cue or title_cue
            strong = specific and concrete and stage_cue and not list_only and not index_page
            reason = ("Company-specific passage with a figure or named program/body." if strong else
                      "Contents or index page." if index_page else
                      "SDG list without company-specific action." if list_only else
                      "No company cue." if not specific else
                      "No figure or named program/body." if not concrete else
                      "No stage-specific action.")
            hits.append({"document": name, "page": page_number, "terms": matched,
                         "excerpt": passage, "strong": strong, "reason": reason})
    hits.sort(key=lambda hit: (not hit["strong"], -len(hit["terms"]), hit["document"], hit["page"]))
    if not hits:
        return {"suggestion": 0, "label": "No lead", "reason": "No rubric keyword in extracted text. Check OCR and synonyms.", "hits": [], "confidence": "low"}
    best = hits[0]
    if best["strong"]:
        confidence = "high" if len(best["terms"]) >= 2 else "medium"
        return {"suggestion": 1, "label": "Lead found", "reason": best["reason"] + " Verify the full criterion.", "hits": hits, "confidence": confidence}
    return {"suggestion": 0, "label": "No strong lead", "reason": best["reason"] + " Review the passage manually.", "hits": hits, "confidence": "low"}


def assess_all(items, documents, progress=None, company_name=""):
    results = {}
    for count, item in enumerate(items, 1):
        results[item["id"]] = assess_item(item, documents, company_name)
        if progress:
            progress(count, len(items), item["id"])
    for item in items:
        if item["kind"] != "SDG" or item["stage"] == "Identified":
            continue
        prerequisite = "Identified" if item["stage"] == "Managed" else "Managed"
        if results[f"SDG{item['number']}-{prerequisite}"]["suggestion"] != 1:
            results[item["id"]].update(suggestion=0, label="Prerequisite needs review", confidence="low",
                                       reason=f"Review {prerequisite} first; this lead cannot support the later stage yet.")
    return results
