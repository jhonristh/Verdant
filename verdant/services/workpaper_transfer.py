"""Portable, data-only workpaper exchange with explicit score conflicts."""
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def _portable_report_path(store, stored):
    path = Path(stored)
    if not path.is_absolute():
        return path.as_posix()
    root = store.reports_root()
    if root:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return path.name


def export_workpaper(store, project_id, destination):
    project = store.db.execute("SELECT company,fiscal_year FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        raise ValueError("Workpaper not found.")
    stored_reports = list(store.db.execute(
        "SELECT path,sha256,page_count,scanned_pages FROM reports WHERE project_id=?", (project_id,)))
    reports = [{"path": _portable_report_path(store, path), "sha256": digest,
                "page_count": count, "scanned_pages": scanned}
               for path, digest, count, scanned in stored_reports]
    path_map = {row[0]: report["path"] for row, report in zip(stored_reports, reports)}
    audit = [dict(zip(("item_id", "changed_at", "old_score", "new_score", "document", "pages"), row))
             for row in store.db.execute("SELECT item_id,changed_at,old_score,new_score,document_name,pages FROM audit_log WHERE project_id=?", (project_id,))]
    ocr = [{"path": path_map.get(path, _portable_report_path(store, path)), "sha256": digest,
            "page": number, "text": text}
           for path, digest, number, text in store.db.execute(
               "SELECT path,sha256,page_number,text FROM ocr_pages WHERE project_id=?", (project_id,))]
    payload = {"format": 1, "company": project[0], "fiscal_year": project[1],
               "scores": store.score_records(project_id), "reports": reports,
               "audit": audit, "ocr": ocr}
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        archive.writestr("workpaper.json", json.dumps(payload, ensure_ascii=False))
    return Path(destination)


def read_workpaper(path):
    with ZipFile(path) as archive:
        names = archive.namelist()
        if names != ["workpaper.json"]:
            raise ValueError("Invalid workpaper package.")
        payload = json.loads(archive.read("workpaper.json"))
    if payload.get("format") != 1 or not payload.get("company") or not payload.get("fiscal_year"):
        raise ValueError("Unsupported workpaper format.")
    for report in payload.get("reports", []):
        path = Path(report["path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Workpaper contains an unsafe report path.")
    return payload


def import_workpaper(store, source, accept_newer=False):
    """Return conflicts without mutation; apply newer remote values only after approval."""
    payload = read_workpaper(source)
    existing = store.db.execute("SELECT id FROM projects WHERE company=? AND fiscal_year=?",
                                (payload["company"], str(payload["fiscal_year"]))).fetchone()
    current = store.score_records(existing[0]) if existing else {}
    conflicts = []
    for item, incoming in payload.get("scores", {}).items():
        local = current.get(item)
        if local and any(local[key] != incoming[key] for key in ("score", "evidence", "document", "pages")):
            conflicts.append({"item": item, "local": local, "incoming": incoming,
                              "winner": "incoming" if incoming["updated_at"] > local["updated_at"] else "local"})
    if conflicts and not accept_newer:
        return {"imported": False, "conflicts": conflicts}
    project_id = store.project(payload["company"], str(payload["fiscal_year"]))
    with store.db:
        for item, incoming in payload.get("scores", {}).items():
            local = current.get(item)
            if local and incoming["updated_at"] <= local["updated_at"]:
                continue
            if local and local != incoming:
                store.db.execute("INSERT INTO audit_log(project_id,item_id,changed_at,old_score,new_score,document_name,pages) VALUES (?,?,?,?,?,?,?)",
                                 (project_id, item, datetime.now().isoformat(timespec="microseconds"), local["score"], incoming["score"], incoming["document"], incoming["pages"]))
            store.db.execute("""INSERT INTO scores(project_id,item_id,score,evidence,document_name,pages,updated_at)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(project_id,item_id) DO UPDATE SET score=excluded.score,
                evidence=excluded.evidence,document_name=excluded.document_name,pages=excluded.pages,updated_at=excluded.updated_at""",
                (project_id, item, incoming["score"], incoming["evidence"], incoming["document"], incoming["pages"], incoming["updated_at"]))
        existing_audit = set(store.db.execute(
            "SELECT item_id,changed_at,old_score,new_score,document_name,pages FROM audit_log WHERE project_id=?", (project_id,)))
        for row in payload.get("audit", []):
            values = (row["item_id"], row["changed_at"], row["old_score"], row["new_score"], row["document"], row["pages"])
            if values not in existing_audit:
                store.db.execute("INSERT INTO audit_log(project_id,item_id,changed_at,old_score,new_score,document_name,pages) VALUES (?,?,?,?,?,?,?)", (project_id, *values))
        for report in payload.get("reports", []):
            store.db.execute("""INSERT OR IGNORE INTO reports(project_id,path,sha256,page_count,scanned_pages)
                VALUES (?,?,?,?,?)""", (project_id, report["path"], report["sha256"], report["page_count"], report["scanned_pages"]))
        for page in payload.get("ocr", []):
            store.db.execute("""INSERT OR IGNORE INTO ocr_pages(project_id,path,sha256,page_number,text)
                VALUES (?,?,?,?,?)""", (project_id, page["path"], page["sha256"], page["page"], page["text"]))
    store.clear_predictions(project_id)
    store.sync_csv()
    return {"imported": True, "project_id": project_id, "conflicts": conflicts}
