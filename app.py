"""Verdant application entry point and compatibility facade."""
from openpyxl import load_workbook

from verdant.config import DATA_DIR, DATABASE_PATH, ROSTER_PATHS
from verdant.domain.rubric import keyword_pattern, load_rubric
from verdant.storage.repository import Store as RepositoryStore

RUBRIC = load_rubric()
DB_PATH = DATABASE_PATH


def load_companies():
    roster_path = next((path for path in ROSTER_PATHS if path.exists()), None)
    if roster_path is None:
        return []
    workbook = load_workbook(roster_path, read_only=True, data_only=True)
    try:
        sheet = workbook["Companies"]
        names = []
        for row in sheet.iter_rows(min_row=4, max_col=3, values_only=True):
            name = row[2]
            if isinstance(name, str) and name.strip() and name.strip() not in names:
                names.append(name.strip())
        return names
    finally:
        workbook.close()


class Store(RepositoryStore):
    """Repository initialized from the public database setting."""
    def __init__(self):
        super().__init__(DB_PATH)


def main():
    from app_qt import main as launch
    launch()


if __name__ == "__main__":
    main()
