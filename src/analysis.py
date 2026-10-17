"""Practice-level analysis of newer diabetes drug prescribing in relation to deprivation.

Outcome: share of non-insulin diabetes items that are SGLT2 inhibitors or GLP-1/GIP agonists
(latest 12 months in the data). Unit: GP practice. Ecological, observational.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.nonparametric.smoothers_lowess import lowess

from src.config import FIG_DIR, OUTPUT_DIR
from src.db import get_engine
from src.stats import flag_practices

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
RES = OUTPUT_DIR / "results"


def load() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM marts.mart_practice_window WHERE include_in_analysis", get_engine())
    df = df[df["non_insulin_items"] > 0].copy()
    df["imd_per10"] = df["imd_score"].astype(float) / 10
    df["log_list_size"] = np.log(df["list_size"].astype(float))
    for c in ["newer_share", "diabetes_prevalence_pct", "items_per_register_patient"]:
        df[c] = df[c].astype(float)
    df["region_name"] = df["region_name"].astype("category")
    return df


def binomial_model(df: pd.DataFrame) -> dict:
    """Quasi-binomial-style GLM on (newer, other non-insulin) items, ICB-clustered robust SEs."""
    X = pd.concat([df[["imd_per10", "diabetes_prevalence_pct", "log_list_size"]],
                   pd.get_dummies(df["region_name"], drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)
    y = np.column_stack([df["newer_items"], df["non_insulin_items"] - df["newer_items"]])
    groups = pd.factorize(df["icb_code"])[0]
    fit = sm.GLM(y, X, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": groups})
    ci = fit.conf_int().loc["imd_per10"]
    return {
        "n_practices": int(len(df)), "n_icbs": int(df["icb_code"].nunique()),
        "odds_ratio_per_10_imd_points": float(np.exp(fit.params["imd_per10"])),
        "or_ci_low": float(np.exp(ci[0])), "or_ci_high": float(np.exp(ci[1])),
        "p_value": float(fit.pvalues["imd_per10"]),
    }


def volume_model(df: pd.DataFrame) -> dict:
    d = df[df["items_per_register_patient"] > 0]
    fit = smf.ols("np.log(items_per_register_patient) ~ imd_per10 + diabetes_prevalence_pct "
                  "+ log_list_size + C(region_name)", data=d).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d["icb_code"])[0]})
    ci = fit.conf_int().loc["imd_per10"]
    return {"pct_change_items_per_patient_per_10_imd": float((np.exp(fit.params["imd_per10"]) - 1) * 100),
            "ci_low_pct": float((np.exp(ci[0]) - 1) * 100), "ci_high_pct": float((np.exp(ci[1]) - 1) * 100),
            "p_value": float(fit.pvalues["imd_per10"]), "r_squared": float(fit.rsquared)}


def icc_anova(y: np.ndarray, g: np.ndarray) -> float:
    """Intraclass correlation from a one-way ANOVA: the share of variance lying between groups (ICBs).
    Always converges, unlike a mixed model; unbalanced group sizes are handled through n0."""
    d = pd.DataFrame({"y": y, "g": g})
    grp = d.groupby("g")["y"]
    n, means = grp.size(), grp.mean()
    k, N, grand = len(n), n.sum(), d["y"].mean()
    msb = (n * (means - grand) ** 2).sum() / (k - 1)
    msw = ((d["y"] - d["g"].map(means)) ** 2).sum() / (N - k)
    n0 = (N - (n ** 2).sum() / N) / (k - 1)
    var_b = max((msb - msw) / n0, 0.0)
    return float(var_b / (var_b + msw))


def icb_variation(df: pd.DataFrame, n_boot: int = 500, seed: int = 1) -> dict:
    """Share of practice-level variance in newer-drug share that sits between ICBs, before and after
    adjusting for deprivation, prevalence and list size, with a bootstrap (resampling ICBs) 95% interval."""
    ols = smf.ols("newer_share ~ imd_per10 + diabetes_prevalence_pct + log_list_size", df).fit()
    series = {"unadjusted": df["newer_share"].to_numpy(), "adjusted": ols.resid.to_numpy()}
    groups = df["icb_code"].to_numpy()
    ids = pd.unique(groups)
    rng = np.random.default_rng(seed)
    by_icb = {i: np.where(groups == i)[0] for i in ids}
    out = {}
    for tag, y in series.items():
        out[f"icc_{tag}"] = icc_anova(y, groups)
        boots = []
        for _ in range(n_boot):
            pick = rng.choice(ids, size=len(ids), replace=True)
            idx = np.concatenate([by_icb[i] for i in pick])
            lab = np.concatenate([np.full(len(by_icb[i]), j) for j, i in enumerate(pick)])
            boots.append(icc_anova(y[idx], lab))
        out[f"icc_{tag}_ci"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    return out


def fig_scatter(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.scatter(df["imd_score"], df["newer_share"] * 100, s=10, alpha=.45, color="#2a6f97")
    lw = lowess(df["newer_share"] * 100, df["imd_score"].astype(float), frac=.5)
    ax.plot(lw[:, 0], lw[:, 1], color="#d62828", lw=2, label="LOWESS trend")
    ax.set(xlabel="Practice deprivation (patient-weighted IMD 2019 score; higher = more deprived)",
           ylabel="SGLT2 + GLP-1 share of non-insulin items (%)",
           title="Newer diabetes drug share vs practice deprivation")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIG_DIR / "01_newer_share_vs_deprivation.png"); plt.close(fig)


def fig_funnel(d: pd.DataFrame, p0: float) -> None:
    d = d.sort_values("non_insulin_items")
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.scatter(d["non_insulin_items"], d["p"] * 100, s=10, alpha=.45, color="#6c757d")
    out = d[d["funnel_flag"].str.contains("99.8")]
    ax.scatter(out["non_insulin_items"], out["p"] * 100, s=18, color="#d62828", label="Outside 99.8% limits")
    ax.plot(d["non_insulin_items"], d["hi_998"] * 100, "--", color="#d62828", lw=1)
    ax.plot(d["non_insulin_items"], d["lo_998"] * 100, "--", color="#d62828", lw=1)
    ax.plot(d["non_insulin_items"], d["hi_95"] * 100, ":", color="#444", lw=1)
    ax.plot(d["non_insulin_items"], d["lo_95"] * 100, ":", color="#444", lw=1)
    ax.axhline(p0 * 100, color="#2a6f97", lw=1.2, label=f"National {p0*100:.1f}%")
    ax.set(xlabel="Non-insulin diabetes items in 12 months", ylabel="Newer-drug share (%)",
           title="Funnel plot (overdispersion-adjusted)")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIG_DIR / "02_funnel_plot.png"); plt.close(fig)


def fig_trend() -> None:
    t = pd.read_sql("SELECT month_start, imd_quintile, is_newer_class, SUM(items) AS items "
                    "FROM marts.mart_class_trend WHERE drug_class <> 'Insulin' "
                    "GROUP BY 1,2,3", get_engine())
    tot = t.groupby(["month_start", "imd_quintile"])["items"].sum().rename("tot").reset_index()
    n = t[t["is_newer_class"]].groupby(["month_start", "imd_quintile"])["items"].sum().reset_index()
    m = n.merge(tot, on=["month_start", "imd_quintile"])
    m["share"] = m["items"].astype(float) / m["tot"].astype(float) * 100
    fig, ax = plt.subplots(figsize=(7, 4.6))
    for q, g in m.groupby("imd_quintile"):
        lab = {1: "Q1 most deprived", 5: "Q5 least deprived"}.get(q, f"Q{q}")
        ax.plot(g["month_start"], g["share"], label=lab, lw=2 if q in (1, 5) else 1,
                color=plt.cm.viridis((q - 1) / 4))
    ax.set(ylabel="Newer-drug share of non-insulin items (%)", title="Monthly trend by deprivation quintile")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout(); fig.savefig(FIG_DIR / "03_trend_by_quintile.png"); plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    df = load()
    quint = (df.groupby("imd_quintile").apply(
        lambda g: pd.Series({"practices": len(g),
                             "newer_share_pct": g["newer_items"].sum() / g["non_insulin_items"].sum() * 100,
                             "items_per_register_patient": g["total_items"].sum() / g["diabetes_register"].sum()}),
        include_groups=False).round(2))
    quint.to_csv(RES / "by_deprivation_quintile.csv")
    flagged, p0, phi = flag_practices(df, "newer_items", "non_insulin_items")
    flagged[["practice_code", "practice_name", "icb_name", "non_insulin_items", "newer_items", "p",
             "funnel_flag"]].sort_values("p").to_csv(RES / "funnel_flags.csv", index=False)
    results = {
        "window": pd.read_sql("SELECT * FROM marts.v_window", get_engine()).astype(str).iloc[0].to_dict(),
        "national_newer_share": p0, "overdispersion_phi": phi,
        "practices_outside_99_8": int(flagged["funnel_flag"].str.contains("99.8").sum()),
        "binomial_model": binomial_model(df), "volume_model": volume_model(df),
        "icb_variation": icb_variation(df),
    }
    (RES / "results.json").write_text(json.dumps(results, indent=2, default=str))
    fig_scatter(df); fig_funnel(flagged, p0); fig_trend()
    print(quint.to_string()); print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
