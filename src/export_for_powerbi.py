"""Export marts to CSV for Power BI (use when you want a file-based, publishable model)."""
import pandas as pd

from src.config import EXPORT_DIR, OUTPUT_DIR
from src.db import get_engine

TABLES = ["dim_practice", "dim_drug", "fact_prescribing_month", "mart_practice_window",
          "mart_class_trend", "mart_icb_summary"]


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    eng = get_engine()
    flags = OUTPUT_DIR / "results" / "funnel_flags.csv"
    for t in TABLES:
        df = pd.read_sql(f"SELECT * FROM marts.{t}", eng)
        if t == "mart_practice_window" and flags.exists():
            df = df.merge(pd.read_csv(flags)[["practice_code", "funnel_flag"]], on="practice_code", how="left")
        df.to_csv(EXPORT_DIR / f"{t}.csv", index=False)
        print(f"{t}: {len(df):,} rows")


if __name__ == "__main__":
    main()
