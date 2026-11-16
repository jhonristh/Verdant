"""Locate every occurrence of the selected rubric item's terms on a PDF page."""
import re

import pymupdf as fitz


def word_rects(page, term):
    """Fallback for PDFs whose extractable words are missed by search_for."""
    tokens = re.findall(r"\w+", term.casefold())
    if not tokens:
        return []
    words = page.get_text("words")
    found = []
    for start in range(len(words) - len(tokens) + 1):
        group = words[start:start + len(tokens)]
        if [re.sub(r"^\W+|\W+$", "", word[4].casefold()) for word in group] != tokens:
            continue
        # Avoid joining unrelated columns or blocks into a false phrase.
        if len(tokens) > 1 and len({(word[5], word[6]) for word in group}) != 1:
            continue
        rect = fitz.Rect(group[0][:4])
        for word in group[1:]:
            rect |= fitz.Rect(word[:4])
        found.append(rect)
    return found


def keyword_rects(page, terms, *, ocr=False, tessdata=None):
    textpage=page.get_textpage_ocr(language="eng",dpi=200,full=True,tessdata=str(tessdata)) if ocr else None
    rectangles=[]; seen=set()
    for term in terms:
        matches=page.search_for(term,textpage=textpage) if textpage is not None else page.search_for(term)
        if not matches and not ocr:
            matches=word_rects(page,term)
        for rect in matches:
            key=tuple(round(value,2) for value in (rect.x0,rect.y0,rect.x1,rect.y1))
            if key not in seen:
                seen.add(key); rectangles.append(rect)
    return rectangles
