"""Read-only inventory of the client PDF corpus and native text/search coverage."""
import csv
import json
import sys
import time
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT.parent / "Sample Companies"
OUTPUT = ROOT / "output" / "qa"
OUTPUT.mkdir(parents=True, exist_ok=True)
TERMS = ("climate risk", "scenario analysis", "sustainability", "SDG")


def audit(path):
    record = {"path": str(path.relative_to(CORPUS)), "bytes": path.stat().st_size,
              "pages": 0, "blank_pages": 0, "sparse_pages": 0,
              "search_mismatches": 0, "error": ""}
    try:
        with fitz.open(path) as pdf:
            record["pages"] = len(pdf)
            for page in pdf:
                text = page.get_text("text")
                if not text.strip():
                    record["blank_pages"] += 1
                elif len(text.strip()) < 30:
                    record["sparse_pages"] += 1
                # Test native text and PDF geometry on one representative term per page.
                for term in TERMS:
                    if term.casefold() in text.casefold():
                        if not page.search_for(term):
                            record["search_mismatches"] += 1
                        break
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def main():
    started = time.monotonic()
    paths = sorted(CORPUS.rglob("*.pdf"))
    fields = ("path", "bytes", "pages", "blank_pages", "sparse_pages", "search_mismatches", "error")
    totals = {"files": len(paths), "pages": 0, "blank_pages": 0,
              "sparse_pages": 0, "search_mismatches": 0, "errors": 0}
    with (OUTPUT / "corpus_audit.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index, path in enumerate(paths, 1):
            row = audit(path)
            writer.writerow(row)
            stream.flush()
            for key in ("pages", "blank_pages", "sparse_pages", "search_mismatches"):
                totals[key] += row[key]
            totals["errors"] += bool(row["error"])
            if index % 25 == 0 or index == len(paths):
                print(f"Audited {index}/{len(paths)} PDFs; {totals['pages']} pages", flush=True)
    totals["elapsed_seconds"] = round(time.monotonic() - started, 1)
    (OUTPUT / "corpus_audit_summary.json").write_text(json.dumps(totals, indent=2), encoding="utf-8")
    print(json.dumps(totals), flush=True)
    return int(totals["errors"] > 0)


if __name__ == "__main__":
    sys.exit(main())
