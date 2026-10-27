"""Idempotent loader: CSVs in --source go into the raw schema.

Expected files in the source folder:
  epd/*.csv          monthly English Prescribing Dataset extracts (BNF 0601 rows)
  gp_lsoa.csv        NHS Digital 'Patients Registered at a GP Practice' LSOA file (one extract date)
  imd.csv            IMD 2019 'File 7' scores/ranks/deciles by LSOA
  qof_diabetes.csv   QOF diabetes register and list size by practice

Re-running replaces data rather than appending: EPD partitions are truncated per month,
reference tables are truncated before load.
"""
import argparse
import io
import logging
from pathlib import Path

import pandas as pd

from src import colmap
from src.config import SQL_DIR
from src.db import get_engine, run_sql_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")

EPD_COLS = ["year_month", "practice_code", "practice_name", "postcode", "icb_code", "icb_name",
            "region_name", "bnf_code", "bnf_description", "chemical_substance", "items",
            "quantity", "nic", "actual_cost"]


def copy_df(conn, df: pd.DataFrame, table: str, columns: list[str]) -> None:
    buf = io.StringIO()
    df[columns].to_csv(buf, index=False, header=False)
    buf.seek(0)
    with conn.cursor() as cur:
        cur.copy_expert(f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv)", buf)


def log_load(conn, source: str, n: int) -> None:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO raw.ingest_log (source, row_count) VALUES (%s, %s)", (source, n))


def load_epd(conn, folder: Path) -> None:
    files = sorted((folder / "epd").glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No EPD files found in {folder / 'epd'}")
    for f in files:
        df = colmap.apply_map(pd.read_csv(f, dtype=str, low_memory=False),
                              colmap.EPD_MAP, colmap.EPD_REQUIRED, f.name)
        for c in EPD_COLS:
            if c not in df:
                df[c] = None
        df["year_month"] = df["year_month"].astype(str).str.replace(r"\D", "", regex=True)  # '2024-03' -> '202403'
        for c in ["year_month", "items"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        for c in ["quantity", "nic", "actual_cost"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["year_month", "practice_code", "bnf_code"])
        df["year_month"] = df["year_month"].astype(int)
        df["items"] = df["items"].fillna(0).astype(int)
        for ym, part in df.groupby("year_month"):
            name = f"raw.epd_{ym}"
            with conn.cursor() as cur:
                cur.execute(f"CREATE TABLE IF NOT EXISTS {name} PARTITION OF raw.epd FOR VALUES IN ({int(ym)})")
                cur.execute(f"TRUNCATE {name}")
            copy_df(conn, part, "raw.epd", EPD_COLS)
            log_load(conn, f"{f.name}:{ym}", len(part))
            log.info("EPD %s: %s rows", ym, f"{len(part):,}")


def load_reference(conn, folder: Path) -> None:
    # Patients by practice and LSOA (also gives list size)
    g = colmap.apply_map(pd.read_csv(folder / "gp_lsoa.csv", dtype=str), colmap.GP_LSOA_MAP,
                         colmap.GP_LSOA_REQUIRED, "gp_lsoa.csv")
    if "extract_date" in g:
        latest = g["extract_date"].max()
        g = g[g["extract_date"] == latest]
        log.info("GP LSOA file: using extract date %s", latest)
    g["number_of_patients"] = pd.to_numeric(g["number_of_patients"], errors="coerce").fillna(0).astype(int)
    imd = colmap.apply_map(pd.read_csv(folder / "imd.csv", dtype=str), colmap.IMD_MAP,
                           colmap.IMD_REQUIRED, "imd.csv")
    imd["imd_score"] = pd.to_numeric(imd["imd_score"], errors="coerce")
    imd["imd_decile"] = pd.to_numeric(imd.get("imd_decile"), errors="coerce")
    imd = imd.drop_duplicates("lsoa_code")
    q = colmap.apply_map(pd.read_csv(folder / "qof_diabetes.csv", dtype=str), colmap.QOF_MAP,
                         colmap.QOF_REQUIRED, "qof_diabetes.csv")
    if "group_code" in q:
        q = q[q["group_code"].str.upper() == "DM"]
    q["register"] = pd.to_numeric(q["register"], errors="coerce")
    q["list_size"] = pd.to_numeric(q.get("list_size"), errors="coerce")
    q = q.dropna(subset=["register"]).drop_duplicates("practice_code")
    for c in ["register", "list_size"]:
        q[c] = q[c].astype("Int64")
    imd["imd_decile"] = imd["imd_decile"].astype("Int64")

    with conn.cursor() as cur:
        cur.execute("TRUNCATE raw.gp_lsoa, raw.imd, raw.qof_diabetes")
    copy_df(conn, g, "raw.gp_lsoa", ["practice_code", "lsoa_code", "number_of_patients"])
    copy_df(conn, imd, "raw.imd", ["lsoa_code", "imd_score", "imd_decile"])
    copy_df(conn, q, "raw.qof_diabetes", ["practice_code", "register", "list_size"])
    for name, d in [("gp_lsoa", g), ("imd", imd), ("qof_diabetes", q)]:
        log_load(conn, name, len(d))
        log.info("%s: %s rows", name, f"{len(d):,}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="data/raw", help="folder containing the input files")
    ap.add_argument("--reference-only", action="store_true",
                    help="load only GP/LSOA, IMD and QOF files (skip prescribing)")
    args = ap.parse_args()
    folder = Path(args.source)
    run_sql_file(SQL_DIR / "01_schema.sql")
    conn = get_engine().raw_connection()
    try:
        if not args.reference_only:
            load_epd(conn, folder)
        load_reference(conn, folder)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    log.info("Ingestion complete")


if __name__ == "__main__":
    main()
