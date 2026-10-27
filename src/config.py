import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://nhs:nhs@127.0.0.1:5433/nhs_diabetes"
)
SQL_DIR = ROOT / "sql"
# Override with env vars (the demo does this so it cannot overwrite real results).
EXPORT_DIR = ROOT / os.getenv("EXPORT_DIR", "data/exports")
OUTPUT_DIR = ROOT / os.getenv("OUTPUT_DIR", "outputs")
FIG_DIR = OUTPUT_DIR / "figures"

# Practice inclusion rules (documented in the README)
MIN_LIST_SIZE = 1000
MIN_DIABETES_REGISTER = 20
