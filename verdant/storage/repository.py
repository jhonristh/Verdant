"""SQLite repository. This module contains no UI or scoring dependencies."""
import csv
import hashlib
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
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(scores)")}
        if "updated_at" not in columns:
            self.db.execute("ALTER TABLE scores ADD COLUMN updated_at TEXT")
            self.db.execute("""UPDATE scores SET updated_at=COALESCE(
                (SELECT MAX(changed_at) FROM audit_log a WHERE a.project_id=scores.project_id AND a.item_id=scores.item_id),
                '1970-01-01T00:00:00')""")
        if "printed_pages" not in columns:
            self.db.execute("ALTER TABLE scores ADD COLUMN printed_pages TEXT DEFAULT ''")
        audit_columns = {row[1] for row in self.db.execute("PRAGMA table_info(audit_log)")}
        if "source" not in audit_columns:
            self.db.execute("ALTER TABLE audit_log ADD COLUMN source TEXT DEFAULT 'manual'")
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

    def project_info(self, project_id):
        return self.db.execute("SELECT company,fiscal_year FROM projects WHERE id=?", (project_id,)).fetchone()

    def delete_project(self, project_id):
        with self.db:
            for table in ("audit_log", "scores", "reports", "predictions", "ocr_pages"):
                self.db.execute(f"DELETE FROM {table} WHERE project_id=?", (project_id,))
            self.db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        self.sync_csv()

    def save_score(self, project_id, item, score, evidence, document, pages, source="manual", printed_pages=""):
        previous = self.db.execute("SELECT score FROM scores WHERE project_id=? AND item_id=?", (project_id, item)).fetchone()
        changed_at = datetime.now().isoformat(timespec="microseconds")
        with self.db:
            self.db.execute("INSERT INTO scores(project_id,item_id,score,evidence,document_name,pages,updated_at,printed_pages) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(project_id,item_id) DO UPDATE SET score=excluded.score,evidence=excluded.evidence,document_name=excluded.document_name,pages=excluded.pages,updated_at=excluded.updated_at,printed_pages=excluded.printed_pages", (project_id, item, score, evidence, document, pages, changed_at, printed_pages))
            self.db.execute("INSERT INTO audit_log(project_id,item_id,changed_at,old_score,new_score,document_name,pages,source) VALUES (?,?,?,?,?,?,?,?)", (project_id, item, changed_at, previous[0] if previous else None, score, document, pages, source))
        self.sync_csv()

    def scores(self, project_id):
        return {row[0]: row[1:] for row in self.db.execute("SELECT item_id,score,evidence,document_name,pages FROM scores WHERE project_id=?", (project_id,))}

    def score_records(self, project_id):
        return {row[0]: {"score": row[1], "evidence": row[2], "document": row[3],
                         "pages": row[4], "updated_at": row[5] or "1970-01-01T00:00:00", "printed_pages": row[6] or ""}
                for row in self.db.execute("SELECT item_id,score,evidence,document_name,pages,updated_at,printed_pages FROM scores WHERE project_id=?", (project_id,))}

    def setting(self, key, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        with self.db:
            self.db.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    def add_report(self, project_id, path, digest, page_count, scanned_pages):
        path = self._stored_path(path)
        previous = self.db.execute("SELECT sha256 FROM reports WHERE project_id=? AND path=?", (project_id, path)).fetchone()
        with self.db:
            self.db.execute("INSERT INTO reports(project_id,path,sha256,page_count,scanned_pages) VALUES (?,?,?,?,?) ON CONFLICT(project_id,path) DO UPDATE SET sha256=excluded.sha256,page_count=excluded.page_count,scanned_pages=excluded.scanned_pages", (project_id, path, digest, page_count, scanned_pages))
            if previous and previous[0] != digest:
                self.db.execute("DELETE FROM ocr_pages WHERE project_id=? AND path=?", (project_id, path))
        self.clear_predictions(project_id)

    def reports(self, project_id):
        return [(str(self._resolved_path(path)), digest, count, scanned)
                for path, digest, count, scanned in self.db.execute(
                    "SELECT path,sha256,page_count,scanned_pages FROM reports WHERE project_id=? ORDER BY path", (project_id,))]

    def reports_root(self):
        value = self.setting("reports_root")
        return Path(value) if value else None

    def _stored_path(self, path):
        path = Path(path)
        if not path.is_absolute():
            return path.as_posix()
        path = path.resolve()
        root = self.reports_root()
        if root:
            try:
                return path.relative_to(root.resolve()).as_posix()
            except ValueError:
                pass
        return str(path)

    def _resolved_path(self, stored):
        path = Path(stored)
        return path if path.is_absolute() else (self.reports_root() or self.database_path.parent) / path

    def set_reports_root(self, root):
        root = Path(root).resolve()
        if not root.is_dir():
            raise ValueError("Choose an existing reports folder.")
        with self.db:
            for project_id, old in self.db.execute("SELECT project_id,path FROM reports").fetchall():
                old_path = self._resolved_path(old).resolve()
                try:
                    relative = old_path.relative_to(root).as_posix()
                except ValueError:
                    continue
                if old != relative:
                    self.db.execute("UPDATE reports SET path=? WHERE project_id=? AND path=?", (relative, project_id, old))
                    self.db.execute("UPDATE ocr_pages SET path=? WHERE project_id=? AND path=?", (relative, project_id, old))
            self.db.execute("INSERT INTO settings(key,value) VALUES ('reports_root',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(root),))

    def relink_report(self, project_id, old_path, new_path, allow_filename=False):
        old = self._stored_path(old_path)
        row = self.db.execute("SELECT sha256 FROM reports WHERE project_id=? AND path=?", (project_id, old)).fetchone()
        if not row:
            raise ValueError("The missing report is no longer in this workpaper.")
        new_path = Path(new_path).resolve()
        digest = hashlib.sha256(new_path.read_bytes()).hexdigest()
        same_hash = digest == row[0]
        if not same_hash and not (allow_filename and new_path.name.casefold() == Path(old).name.casefold()):
            raise ValueError("The selected PDF does not match by SHA-256 or filename.")
        new = self._stored_path(new_path)
        with self.db:
            self.db.execute("UPDATE reports SET path=?,sha256=? WHERE project_id=? AND path=?", (new, digest, project_id, old))
            if same_hash:
                self.db.execute("UPDATE ocr_pages SET path=? WHERE project_id=? AND path=?", (new, project_id, old))
            else:
                self.db.execute("DELETE FROM ocr_pages WHERE project_id=? AND path=?", (project_id, old))
        self.clear_predictions(project_id)
        return "hash" if same_hash else "filename"

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
        return {number: text for number, text in self.db.execute("SELECT page_number,text FROM ocr_pages WHERE project_id=? AND path=? AND sha256=?", (project_id, self._stored_path(path), digest))}

    def save_ocr_pages(self, project_id, results):
        valid = {(self._stored_path(path), digest) for path, digest, _, _ in self.reports(project_id)}
        kept = [(project_id, self._stored_path(path), digest, number, text) for path, digest, number, text in results if (self._stored_path(path), digest) in valid and text.strip()]
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
