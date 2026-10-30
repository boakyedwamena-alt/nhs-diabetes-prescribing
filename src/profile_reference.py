"""Profile the reference data (GP patients by LSOA, IMD 2019, QOF diabetes) before prescribing is added.

Needs only `python -m src.ingest --reference-only`. Writes outputs/results/reference_profile.json
and outputs/figures/00_prevalence_vs_deprivation.png.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.config import FIG_DIR, MIN_DIABETES_REGISTER, MIN_LIST_SIZE, OUTPUT_DIR
from src.db import get_engine

SQL = """
WITH p AS (
  SELECT g.practice_code,
         SUM(g.number_of_patients) AS list_size,
         SUM(g.number_of_patients * i.imd_score)
           / NULLIF(SUM(g.number_of_patients) FILTER (WHERE i.imd_score IS NOT NULL), 0) AS imd_score,
         (SUM(g.number_of_patients) FILTER (WHERE i.imd_score IS NOT NULL))::numeric
           / NULLIF(SUM(g.number_of_patients), 0) AS imd_coverage
  FROM raw.gp_lsoa g LEFT JOIN raw.imd i USING (lsoa_code)
  GROUP BY g.practice_code)
SELECT p.*, q.register, q.list_size AS qof_list_size
FROM p LEFT JOIN raw.qof_diabetes q USING (practice_code)
"""


def main() -> None:
    d = pd.read_sql(SQL, get_engine())
    for c in ["list_size", "imd_score", "imd_coverage", "register", "qof_list_size"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["prevalence_pct"] = 100 * d["register"] / d["qof_list_size"]
    inc = d[(d.list_size >= MIN_LIST_SIZE) & (d.register >= MIN_DIABETES_REGISTER)
            & d.imd_score.notna() & d.prevalence_pct.notna()].copy()
    inc["imd_quintile"] = pd.qcut(inc.imd_score.rank(method="first", ascending=False), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    quint = inc.groupby("imd_quintile").apply(lambda g: pd.Series({
        "practices": len(g), "patients_17plus": int(g.qof_list_size.sum()),
        "crude_prevalence_pct": 100 * g.register.sum() / g.qof_list_size.sum(),
        "mean_imd_score": g.imd_score.mean()}), include_groups=False)
    rho, p = stats.spearmanr(inc.imd_score, inc.prevalence_pct)
    out = {
        "practices_in_gp_file": int(len(d)),
        "practices_with_qof_diabetes_register": int(d.register.notna().sum()),
        "practices_included": int(len(inc)),
        "excluded_no_qof_or_small": int(len(d) - len(inc)),
        "excluded_no_qof_record": int(d.register.isna().sum()),
        "excluded_other_size_or_imd": int(len(d) - len(inc) - d.register.isna().sum()),
        "median_imd_coverage": float(d.imd_coverage.median()),
        "practices_imd_coverage_below_95pct": int((d.imd_coverage < 0.95).sum()),
        "national_crude_prevalence_pct_included": float(100 * inc.register.sum() / inc.qof_list_size.sum()),
        "spearman_rho_prevalence_vs_imd": float(rho), "spearman_p": float(p),
        "qof_list_vs_lsoa_list_median_ratio": float((inc.qof_list_size / inc.list_size).median()),
    }
    (OUTPUT_DIR / "results").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "results" / "reference_profile.json").write_text(json.dumps(out, indent=2))
    quint.round(2).to_csv(OUTPUT_DIR / "results" / "prevalence_by_deprivation_quintile.csv")
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.scatter(inc.imd_score, inc.prevalence_pct, s=5, alpha=.3, color="#2a6f97")
    z = np.polyfit(inc.imd_score, inc.prevalence_pct, 1)
    xs = np.linspace(inc.imd_score.min(), inc.imd_score.max(), 50)
    ax.plot(xs, np.polyval(z, xs), color="#d62828", lw=2)
    ax.set(xlabel="Practice deprivation (patient-weighted IMD 2019 score; higher = more deprived)",
           ylabel="Crude diabetes prevalence, aged 17+ (%)",
           title="QOF diabetes prevalence vs practice deprivation, England 2023-24")
    fig.tight_layout(); fig.savefig(FIG_DIR / "00_prevalence_vs_deprivation.png", dpi=130); plt.close(fig)
    print(json.dumps(out, indent=2)); print(quint.round(2).to_string())


if __name__ == "__main__":
    main()
