"""SQLite repository. This module contains no UI or scoring dependencies."""
import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path


class Store:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.database_path)
        self._create_schema()

    def _create_schema(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, company TEXT NOT NULL, fiscal_year TEXT NOT NULL, UNIQUE(company, fiscal_year));
            CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, project_id INTEGER, path TEXT NOT NULL, sha256 TEXT NOT NULL, page_count INTEGER NOT NULL, scanned_pages INTEGER NOT NULL, UNIQUE(project_id, path));
            CREATE TABLE IF NOT EXISTS scores (project_id INTEGER, item_id TEXT, score INTEGER DEFAULT 0, evidence TEXT DEFAULT '', document_name TEXT DEFAULT '', pages TEXT DEFAULT '', PRIMARY KEY(project_id,item_id));
            CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY, project_id INTEGER, item_id TEXT, changed_at TEXT, old_score INTEGER, new_score INTEGER, document_name TEXT, pages TEXT);
            CREATE TABLE IF NOT EXISTS predictions (project_id INTEGER NOT NULL, item_id TEXT NOT NULL, framework TEXT NOT NULL, weight INTEGER NOT NULL, proposed_score INTEGER NOT NULL, confidence TEXT NOT NULL, result_json TEXT NOT NULL, checked_at TEXT NOT NULL, PRIMARY KEY(project_id,item_id));
            CREATE TABLE IF NOT EXISTS ocr_pages (project_id INTEGER NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL, page_number INTEGER NOT NULL, text TEXT NOT NULL, PRIMARY KEY(project_id,path,page_number));
        """)
        self.db.commit()

    def project(self, company, year):
        row = self.db.execute("SELECT id FROM projects WHERE company=? AND fiscal_year=?", (company, year)).fetchone()
        if row is None:
            with self.db:
                self.db.execute("INSERT INTO projects(company,fiscal_year) VALUES (?,?)", (company, year))
            row = self.db.execute("SELECT id FROM projects WHERE company=? AND fiscal_year=?", (company, year)).fetchone()
        return row[0]

    def projects(self):
        return list(self.db.execute("SELECT id,company,fiscal_year FROM projects ORDER BY company,fiscal_year"))

    def delete_project(self, project_id):
        with self.db:
            for table in ("audit_log", "scores", "reports", "predictions", "ocr_pages"):
                self.db.execute(f"DELETE FROM {table} WHERE project_id=?", (project_id,))
            self.db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        self.sync_csv()

    def save_score(self, project_id, item, score, evidence, document, pages):
        previous = self.db.execute("SELECT score FROM scores WHERE project_id=? AND item_id=?", (project_id, item)).fetchone()
        with self.db:
            self.db.execute("INSERT INTO scores VALUES (?,?,?,?,?,?) ON CONFLICT(project_id,item_id) DO UPDATE SET score=excluded.score,evidence=excluded.evidence,document_name=excluded.document_name,pages=excluded.pages", (project_id, item, score, evidence, document, pages))
            self.db.execute("INSERT INTO audit_log(project_id,item_id,changed_at,old_score,new_score,document_name,pages) VALUES (?,?,?,?,?,?,?)", (project_id, item, datetime.now().isoformat(timespec="seconds"), previous[0] if previous else None, score, document, pages))
        self.sync_csv()

    def scores(self, project_id):
        return {row[0]: row[1:] for row in self.db.execute("SELECT item_id,score,evidence,document_name,pages FROM scores WHERE project_id=?", (project_id,))}

    def add_report(self, project_id, path, digest, page_count, scanned_pages):
        path = str(path)
        previous = self.db.execute("SELECT sha256 FROM reports WHERE project_id=? AND path=?", (project_id, path)).fetchone()
        with self.db:
            self.db.execute("INSERT INTO reports(project_id,path,sha256,page_count,scanned_pages) VALUES (?,?,?,?,?) ON CONFLICT(project_id,path) DO UPDATE SET sha256=excluded.sha256,page_count=excluded.page_count,scanned_pages=excluded.scanned_pages", (project_id, path, digest, page_count, scanned_pages))
            if previous and previous[0] != digest:
                self.db.execute("DELETE FROM ocr_pages WHERE project_id=? AND path=?", (project_id, path))
        self.clear_predictions(project_id)

    def reports(self, project_id):
        return list(self.db.execute("SELECT path,sha256,page_count,scanned_pages FROM reports WHERE project_id=? ORDER BY path", (project_id,)))

    def save_predictions(self, project_id, items, results):
        checked_at = datetime.now().isoformat(timespec="seconds")
        with self.db:
            self.db.execute("DELETE FROM predictions WHERE project_id=?", (project_id,))
            self.db.executemany("INSERT INTO predictions (project_id,item_id,framework,weight,proposed_score,confidence,result_json,checked_at) VALUES (?,?,?,?,?,?,?,?)", [(project_id, item["id"], item["kind"], item["weight"], results[item["id"]]["suggestion"], results[item["id"]]["confidence"], json.dumps(results[item["id"]]), checked_at) for item in items])
        self.sync_csv()

    def clear_predictions(self, project_id):
        with self.db:
            self.db.execute("DELETE FROM predictions WHERE project_id=?", (project_id,))
        self.sync_csv()

    def predictions(self, project_id):
        return {item_id: json.loads(payload) for item_id, payload in self.db.execute("SELECT item_id,result_json FROM predictions WHERE project_id=?", (project_id,))}

    def ocr_text(self, project_id, path, digest):
        return {number: text for number, text in self.db.execute("SELECT page_number,text FROM ocr_pages WHERE project_id=? AND path=? AND sha256=?", (project_id, str(path), digest))}

    def save_ocr_pages(self, project_id, results):
        valid = {(path, digest) for path, digest, _, _ in self.reports(project_id)}
        kept = [(project_id, str(path), digest, number, text) for path, digest, number, text in results if (str(path), digest) in valid and text.strip()]
        if not kept:
            return 0
        with self.db:
            self.db.executemany("INSERT INTO ocr_pages(project_id,path,sha256,page_number,text) VALUES (?,?,?,?,?) ON CONFLICT(project_id,path,page_number) DO UPDATE SET sha256=excluded.sha256,text=excluded.text", kept)
        self.clear_predictions(project_id)
        return len(kept)

    def sync_csv(self):
        output = self.database_path.parent / "scores_readable.csv"
        temporary = output.with_suffix(".csv.tmp")
        query = """SELECT p.company,p.fiscal_year,ids.item_id,r.framework,r.weight,r.proposed_score,r.confidence,r.result_json,r.checked_at,s.score,s.document_name,s.pages,s.evidence FROM projects p JOIN (SELECT project_id,item_id FROM predictions UNION SELECT project_id,item_id FROM scores) ids ON ids.project_id=p.id LEFT JOIN predictions r ON r.project_id=ids.project_id AND r.item_id=ids.item_id LEFT JOIN scores s ON s.project_id=ids.project_id AND s.item_id=ids.item_id ORDER BY p.company,p.fiscal_year,ids.item_id"""
        def safe(value):
            return "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value
        with temporary.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(("company","fiscal_year","item_id","framework","weight","proposed_score","proposed_points","confidence","best_document","best_pdf_page","reason","manual_score","manual_document","manual_page","manual_excerpt","checked_at"))
            for company, year, item_id, framework, weight, score, confidence, payload, checked_at, manual, document, page, evidence in self.db.execute(query):
                result = json.loads(payload) if payload else {}; best = (result.get("hits") or [{}])[0]
                framework = framework or ("SDG" if item_id.startswith("SDG") else "ESG"); weight = weight or {"Identified": 1, "Managed": 2, "Reported": 3}.get(item_id.rsplit("-", 1)[-1], 1)
                writer.writerow([safe(value) for value in (company,year,item_id,framework,weight,"" if score is None else score,"" if score is None else score * weight,confidence or "",best.get("document", ""),best.get("page", ""),result.get("reason", ""),"" if manual is None else manual,document or "",page or "",evidence or "",checked_at or "")])
        temporary.replace(output)
