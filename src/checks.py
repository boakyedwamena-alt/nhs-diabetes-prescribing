"""Data-quality assertions on the marts. Exits non-zero if any fail (used in CI)."""
import sys

import pandas as pd

from src.db import get_engine

CHECKS = {
    "fact has no duplicate grain rows":
        "SELECT COUNT(*) FROM (SELECT 1 FROM marts.fact_prescribing_month "
        "GROUP BY practice_code, month_start, drug_class HAVING COUNT(*) > 1) d",
    "no negative items in fact":
        "SELECT COUNT(*) FROM marts.fact_prescribing_month WHERE items <= 0",
    "unclassified drugs are under 0.5% of diabetes items":
        "SELECT CASE WHEN COALESCE(SUM(items) FILTER (WHERE drug_class = 'Unclassified'), 0) < 0.005 * SUM(items) "
        "THEN 0 ELSE 1 END FROM marts.fact_prescribing_month",
    "every newer-drug class has prescribing (classifier is working)":
        "SELECT 2 - COUNT(DISTINCT drug_class) FROM marts.fact_prescribing_month "
        "WHERE drug_class IN ('SGLT2 inhibitor', 'GLP-1 / GIP agonist')",
    "newer_share within [0,1]":
        "SELECT COUNT(*) FROM marts.mart_practice_window WHERE newer_share < 0 OR newer_share > 1",
    "included practices have list size and IMD":
        "SELECT COUNT(*) FROM marts.dim_practice WHERE include_in_analysis AND (list_size IS NULL OR imd_score IS NULL)",
    "IMD scores in plausible range (0-100)":
        "SELECT COUNT(*) FROM marts.dim_practice WHERE imd_score < 0 OR imd_score > 100",
    "five IMD quintiles present":
        "SELECT 5 - COUNT(DISTINCT imd_quintile) FROM marts.dim_practice WHERE include_in_analysis",
    "median practice IMD coverage >= 95% (LSOA vintages match)":
        "SELECT CASE WHEN percentile_cont(0.5) WITHIN GROUP (ORDER BY imd_coverage) >= 0.95 THEN 0 ELSE 1 END "
        "FROM marts.dim_practice WHERE imd_coverage IS NOT NULL",
    "included practices account for at least 98% of diabetes items":
        "SELECT CASE WHEN SUM(total_items) FILTER (WHERE include_in_analysis) >= 0.98 * SUM(total_items) "
        "THEN 0 ELSE 1 END FROM marts.mart_practice_window",
}


def main() -> int:
    eng = get_engine()
    failed = 0
    for name, sql in CHECKS.items():
        val = pd.read_sql(sql, eng).iloc[0, 0]
        ok = val == 0
        failed += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name} (value={val})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
