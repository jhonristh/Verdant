"""Central paths and file names for the Verdant application."""
from pathlib import Path

from runtime_paths import data_directory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCES_DIR = PROJECT_ROOT / "resources"
DATA_DIR = data_directory(source_root=PROJECT_ROOT)
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "pdf_scorer.db"
RUBRIC_PATH = RESOURCES_DIR / "scoring_rubric.json"
ROSTER_NAME = "ESG_SDG_Scoring_Consolidated.xlsx"
ROSTER_PATHS = (RESOURCES_DIR / ROSTER_NAME, PROJECT_ROOT / ROSTER_NAME, PROJECT_ROOT.parent / ROSTER_NAME)
