"""Turn the mart exports into small, clean, dashboard-ready CSVs for Power BI.

Reads  data/exports/{mart_practice_window,mart_icb_summary,mart_class_trend}.csv
Writes data/exports/dashboard_{practice,icb,trend,class}.csv

Why: Power BI guesses column types from the first rows of a CSV. The raw marts start with practices that
have blank values and store whole numbers as 1.0, which made Power BI read a number column as text.
These files hold only analysed practices, whole numbers as integers, readable labels, and no blanks, so
they load with no repair steps. Run with:  python -m src.make_dashboard_files
"""
import argparse
from pathlib import Path

import pandas as pd

from src.config import EXPORT_DIR

IMD_LABELS = {1: "Q1 most deprived", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5 least deprived"}

# Source ICB names are cut at 40 characters, so labels are set by ICB code.
ICB_SHORT = {
    "QOX": "Bath, Swindon and Wiltshire", "QHG": "Bedfordshire, Luton and Milton Keynes",
    "QHL": "Birmingham and Solihull", "QUA": "Black Country", "QUY": "Bristol, North Somerset and South Glos",
    "QU9": "Bucks, Oxfordshire and Berkshire West", "QUE": "Cambridgeshire and Peterborough",
    "QYG": "Cheshire and Merseyside", "QT6": "Cornwall and Isles of Scilly", "QWU": "Coventry and Warwickshire",
    "QJ2": "Derby and Derbyshire", "QJK": "Devon", "QVV": "Dorset", "QNQ": "Frimley",
    "QR1": "Gloucestershire", "QOP": "Greater Manchester", "QRL": "Hampshire and Isle of Wight",
    "QGH": "Herefordshire and Worcestershire", "QM7": "Hertfordshire and West Essex",
    "QOQ": "Humber and North Yorkshire", "QKS": "Kent and Medway", "QE1": "Lancashire and South Cumbria",
    "QK1": "Leicester, Leics and Rutland", "QJM": "Lincolnshire", "QH8": "Mid and South Essex",
    "QMM": "Norfolk and Waveney", "QMJ": "North Central London", "QHM": "North East and North Cumbria",
    "QMF": "North East London", "QRV": "North West London", "QPM": "Northamptonshire",
    "QT1": "Nottingham and Notts", "QOC": "Shropshire, Telford and Wrekin", "QSL": "Somerset",
    "QKK": "South East London", "QWE": "South West London", "QF7": "South Yorkshire",
    "QNC": "Staffordshire and Stoke-on-Trent", "QJG": "Suffolk and North East Essex",
    "QXU": "Surrey Heartlands", "QNX": "Sussex", "QWO": "West Yorkshire",
}
REGION_LABELS = {"NORTH EAST AND YORKSHIRE": "North East and Yorkshire", "NORTH WEST": "North West",
                 "MIDLANDS": "Midlands", "EAST OF ENGLAND": "East of England", "LONDON": "London",
                 "SOUTH EAST": "South East", "SOUTH WEST": "South West"}


def nice_name(s: str) -> str:
    t = str(s).title().replace("'S", "'s")
    for small in [" And ", " Of ", " The ", " At "]:
        t = t.replace(small, small.lower())
    return t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=EXPORT_DIR)
    d = ap.parse_args().dir

    p = pd.read_csv(d / "mart_practice_window.csv")
    p = p[p["include_in_analysis"].astype(str).str.lower() == "true"].copy()
    p["imd_quintile"] = p["imd_quintile"].astype(int)
    p["icb_short"] = p["icb_code"].map(ICB_SHORT).fillna(p["icb_name"].map(nice_name))
    p["region"] = p["region_name"].map(REGION_LABELS).fillna(p["region_name"].map(nice_name))
    p["outlier_status"] = p["funnel_flag"].map(
        lambda f: "High outlier" if str(f).startswith("High outlier")
        else "Low outlier" if str(f).startswith("Low outlier") else "Not an outlier")
    practice = pd.DataFrame({
        "practice_code": p["practice_code"], "practice_name": p["practice_name"].map(nice_name),
        "icb_code": p["icb_code"], "icb_short": p["icb_short"], "region": p["region"],
        "list_size": p["list_size"].astype(int), "diabetes_register": p["diabetes_register"].astype(int),
        "prevalence_pct": p["diabetes_prevalence_pct"].round(2), "imd_score": p["imd_score"].round(2),
        "imd_quintile": p["imd_quintile"], "imd_group": p["imd_quintile"].map(IMD_LABELS),
        "total_items": p["total_items"].astype(int), "non_insulin_items": p["non_insulin_items"].astype(int),
        "newer_items": p["newer_items"].astype(int), "newer_share": p["newer_share"].round(4),
        "items_per_register_patient": p["items_per_register_patient"].round(2),
        "funnel_flag": p["funnel_flag"], "outlier_status": p["outlier_status"],
    })
    national = practice["newer_items"].sum() / practice["non_insulin_items"].sum()

    i = pd.read_csv(d / "mart_icb_summary.csv")
    icb = pd.DataFrame({
        "icb_code": i["icb_code"], "icb_short": i["icb_code"].map(ICB_SHORT).fillna(i["icb_name"].map(nice_name)),
        "region": i["region_name"].map(REGION_LABELS), "practices": i["practices"].astype(int),
        "patients": i["patients"].astype(int), "items_per_1000_patients": i["items_per_1000_patients"].round(1),
        "newer_share": i["newer_share"].round(4), "mean_imd_score": i["mean_imd_score"].round(1),
        "crude_prevalence_pct": i["crude_prevalence_pct"].round(2),
        "vs_national_pp": ((i["newer_share"] - national) * 100).round(2),
    })

    c = pd.read_csv(d / "mart_class_trend.csv")
    c["imd_quintile"] = c["imd_quintile"].astype(int)
    c["imd_group"] = c["imd_quintile"].map(IMD_LABELS)
    c["is_newer_class"] = c["is_newer_class"].astype(str).str.lower() == "true"
    cls = pd.DataFrame({
        "month_start": c["month_start"], "imd_quintile": c["imd_quintile"], "imd_group": c["imd_group"],
        "drug_class": c["drug_class"], "is_newer_class": c["is_newer_class"].map({True: "True", False: "False"}),
        "items": c["items"].round().astype(int), "items_per_1000_patients": c["items_per_1000_patients"].round(2),
    })
    g = c.groupby(["month_start", "imd_quintile", "imd_group"])
    trend = g.apply(lambda x: pd.Series({
        "newer_items": int(round(x.loc[x["is_newer_class"], "items"].sum())),
        "non_insulin_items": int(round(x.loc[x["drug_class"] != "Insulin", "items"].sum()))}),
        include_groups=False).reset_index()
    trend["newer_share"] = (trend["newer_items"] / trend["non_insulin_items"]).round(4)

    for name, df in [("practice", practice), ("icb", icb), ("trend", trend), ("class", cls)]:
        df.to_csv(d / f"dashboard_{name}.csv", index=False)
        print(f"dashboard_{name}.csv: {len(df):,} rows, {df.shape[1]} columns")


if __name__ == "__main__":
    main()
