"""On-demand OCR for PDF pages without an extractable text layer."""
import os
from pathlib import Path

import pymupdf as fitz
from verdant.config import RESOURCES_DIR


def find_tessdata():
    """Find English Tesseract language data without changing global environment."""
    configured=os.environ.get("TESSDATA_PREFIX")
    candidates=[Path(configured)] if configured else []
    candidates.extend((RESOURCES_DIR / "tessdata", Path(__file__).resolve().parent / "tessdata"))
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        root=os.environ.get(variable)
        if root: candidates.append(Path(root) / "Tesseract-OCR" / "tessdata")
    local=os.environ.get("LOCALAPPDATA")
    if local: candidates.append(Path(local) / "Programs" / "Tesseract-OCR" / "tessdata")
    return next((path for path in candidates if (path / "eng.traineddata").is_file()),None)


def parse_page_numbers(raw, maximum):
    """Parse 1-based page numbers and inclusive ranges such as 2,5-7."""
    selected=set()
    for part in raw.split(","):
        part=part.strip()
        if not part: raise ValueError("Enter PDF page numbers, for example 2, 5-7.")
        ends=part.split("-")
        if len(ends)>2 or not all(end.strip().isdigit() for end in ends):
            raise ValueError("Use page numbers or ranges such as 2, 5-7.")
        first=int(ends[0]); last=int(ends[-1])
        if first<1 or last>maximum or first>last:
            raise ValueError(f"Pages must be within 1-{maximum}, with range start before end.")
        selected.update(range(first,last+1))
    return sorted(selected)


def extract_missing_pages(tasks, tessdata, progress=None, should_cancel=None):
    """OCR (path, SHA-256, page numbers) tasks; return results and per-page errors."""
    results=[]; errors=[]; total=sum(len(numbers) for _,_,numbers in tasks); done=0
    for path,digest,numbers in tasks:
        if should_cancel and should_cancel(): break
        try:
            with fitz.open(path) as pdf:
                for number in numbers:
                    if should_cancel and should_cancel(): return results,errors
                    try:
                        page=pdf[number-1]
                        textpage=page.get_textpage_ocr(language="eng",dpi=200,full=True,tessdata=str(tessdata))
                        text=page.get_text("text",textpage=textpage).strip()
                        if text: results.append((str(path),digest,number,text))
                        else: errors.append(f"{Path(path).name}, page {number}: OCR found no text")
                    except Exception as exc:
                        errors.append(f"{Path(path).name}, page {number}: {exc}")
                    done+=1
                    if progress: progress(done,total,Path(path).name,number)
        except Exception as exc:
            errors.append(f"{Path(path).name}: {exc}")
            done+=len(numbers)
            if progress: progress(done,total,Path(path).name,0)
    return results,errors
