from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = ROOT_DIR / "sql"
OUTPUT_DIR = ROOT_DIR / "outputs"
REPORTS_DIR = OUTPUT_DIR / "reports"
FIGURES_DIR = OUTPUT_DIR / "figures"
DB_PATH = PROCESSED_DATA_DIR / "retail_demand.sqlite"


def ensure_directories():
    for path in [
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        REPORTS_DIR,
        FIGURES_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)

