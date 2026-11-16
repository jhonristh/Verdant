"""Explainable provisional scores. Official scores still require reviewer approval."""
import re

from app import keyword_pattern

NUMBER = re.compile(r"\b\d+(?:[,.]\d+)?(?:\s*%|\s*(?:tons?|people|employees|sites|million|billion))?\b", re.I)
ESG_CUES = re.compile(r"\b(risk|cost|expense|investment|compliance|committee|policy|audit|training|penalt(?:y|ies)|program)\b", re.I)
SDG_CUES = {
    "Identified": re.compile(r"\b(SDG|sustainable development goal)\s*\d{1,2}\b", re.I),
    "Managed": re.compile(r"\b(target|KPI|program|initiative|budget|team|committee)\b", re.I),
    "Reported": re.compile(r"\b(reduced|reached|trained|provided|achieved|completed|benefited|served)\b", re.I),
}


def assess_item(item, documents):
    """Return a provisional 0/1 and the passage behind it, never a saved decision."""
    hits=[]
    for name,pages in documents:
        for page_number,text in enumerate(pages,1):
            matched=[word for word in item["keywords"] if keyword_pattern(word).search(text)]
            if not matched: continue
            first=keyword_pattern(matched[0]).search(text)
            passage=text[max(0,first.start()-250):min(len(text),first.end()+550)].replace("\n"," ")
            if item["kind"]=="ESG":
                cues=bool(ESG_CUES.search(passage)) and (bool(NUMBER.search(passage)) or len(matched)>=2)
            else:
                cue=SDG_CUES[item["stage"]]
                if item["stage"]=="Identified":
                    cues=bool(re.search(rf"\b(?:SDG|sustainable development goal)\s*{item['number']}\b",passage,re.I))
                else:
                    cues=bool(cue.search(passage)) and (item["stage"]!="Reported" or bool(NUMBER.search(passage)))
            hits.append({"document":name,"page":page_number,"terms":matched,"excerpt":passage,"strong":cues})
    hits.sort(key=lambda hit:(not hit["strong"],-len(hit["terms"]),hit["document"],hit["page"]))
    if not hits:
        return {"suggestion":0,"label":"Proposed 0 · low confidence","reason":"No rubric keyword found in extractable text. Check OCR gaps and synonyms before accepting.","hits":[],"confidence":"low"}
    best=hits[0]
    if best["strong"]:
        return {"suggestion":1,"label":"Proposed 1 · review evidence","reason":"Rubric keyword and contextual cue found. Check company specificity and the full criterion.","hits":hits,"confidence":"medium"}
    return {"suggestion":0,"label":"Proposed 0 · low confidence","reason":"Keywords found, but no qualifying contextual cue was detected. Read the passage before accepting.","hits":hits,"confidence":"low"}


def assess_all(items, documents, progress=None):
    results={}
    for count,item in enumerate(items,1):
        results[item["id"]]=assess_item(item,documents)
        if progress: progress(count,len(items),item["id"])
    for item in items:
        if item["kind"]!="SDG" or item["stage"]=="Identified": continue
        prerequisite="Identified" if item["stage"]=="Managed" else "Managed"
        if results[f"SDG{item['number']}-{prerequisite}"]["suggestion"]!=1:
            result=results[item["id"]]
            result.update(suggestion=0,label="Proposed 0 · prerequisite",confidence="low",
                          reason=f"{prerequisite} is not proposed as supported. Review both stages before accepting.")
    return results
