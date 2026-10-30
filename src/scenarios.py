"""Scenario figures quoted in the README ('What this means for decision-makers').
Illustrations of scale, not targets. Run: python -m src.scenarios"""
from src.analysis import load
from src.stats import flag_practices

df = load()
nat = df.newer_items.sum() / df.non_insulin_items.sum()
total_newer = df.newer_items.sum()

q = df.groupby("imd_quintile")[["newer_items", "non_insulin_items"]].sum()
q["share"] = q.newer_items / q.non_insulin_items
dep = (q.loc[5, "share"] - q.loc[1, "share"]) * q.loc[1, "non_insulin_items"]
print(f"Deprivation scenario: {dep:,.0f} items, {100*dep/q.loc[1,'newer_items']:.1f}% more than Q1 issued, "
      f"{100*dep/total_newer:.1f}% of national newer-drug items")

icb = df.groupby("icb_code")[["newer_items", "non_insulin_items"]].sum()
icb["share"] = icb.newer_items / icb.non_insulin_items
below = icb[icb.share < nat].copy()
below["gap"] = (nat - below.share) * below.non_insulin_items
print(f"ICB scenario: {below.gap.sum():,.0f} items across {len(below)} ICBs, "
      f"{100*below.gap.sum()/total_newer:.1f}% of national newer-drug items")
london = below.loc[below.index.intersection(["QMF", "QKK", "QWE"]), "gap"].sum()
print(f"North East, South East and South West London: {100*london/below.gap.sum():.0f}% of the ICB gap")
print(below.sort_values("gap", ascending=False).head(5)[["share", "gap"]])

flagged, _, _ = flag_practices(df, "newer_items", "non_insulin_items")
out = flagged[flagged.funnel_flag.str.contains("99.8")]
n_by_icb = out.groupby("icb_code").size().sort_values(ascending=False)
print(f"{len(out)} outliers; top 6 ICBs hold {100*n_by_icb.head(6).sum()/len(out):.0f}%; "
      f"{len(n_by_icb)} of {df.icb_code.nunique()} ICBs have at least one")