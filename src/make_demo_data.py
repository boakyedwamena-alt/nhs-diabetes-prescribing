"""Generate SYNTHETIC data in the same shape as the real NHS/ONS files.

Purpose: let anyone run and test the full pipeline without downloading anything.
Relationships in this data (e.g. between deprivation and prescribing) are arbitrary and
are NOT findings. Never publish results from demo data as if they were real.
"""
import numpy as np
import pandas as pd

from src.config import ROOT

OUT = ROOT / "data" / "demo"
rng = np.random.default_rng(42)

REGIONS = ["NORTH EAST AND YORKSHIRE", "NORTH WEST", "MIDLANDS", "EAST OF ENGLAND",
           "LONDON", "SOUTH EAST", "SOUTH WEST"]
N_PRACTICES, N_LSOA, MONTHS = 420, 2500, [202401 + i for i in range(12)]

# (substance, bnf prefix, class key, within-class weight)
SUBSTANCES = [
    ("Metformin hydrochloride", "0601022B0", "metformin", 1.0),
    ("Gliclazide", "0601021M0", "su", 0.8), ("Glimepiride", "0601021H0", "su", 0.2),
    ("Pioglitazone", "0601023B0", "pio", 1.0),
    ("Sitagliptin", "0601023X0", "dpp4", 0.5), ("Linagliptin", "0601023AM", "dpp4", 0.35),
    ("Alogliptin", "0601023AJ", "dpp4", 0.15),
    ("Dapagliflozin", "0601023AG", "sglt2", 0.5), ("Empagliflozin", "0601023AN", "sglt2", 0.5),
    ("Semaglutide", "0601023AW", "glp1", 0.6), ("Dulaglutide", "0601023AX", "glp1", 0.35),
    ("Tirzepatide", "0601023AZ", "glp1", 0.05),  # brand-only presentation name (Mounjaro)
    ("Insulin glargine", "0601012V0", "insulin", 0.5), ("Insulin aspart", "0601012AB", "insulin", 0.5),
    ("Sitagliptin/metformin hydrochloride", "0601023AA", "dpp4", 0.1),  # combination product: must classify as DPP-4, not metformin
]
BASE_MIX = {"metformin": 0.40, "su": 0.12, "pio": 0.03, "dpp4": 0.10, "insulin": 0.0,
            "sglt2": 0.0, "glp1": 0.0}


def main() -> None:
    (OUT / "epd").mkdir(parents=True, exist_ok=True)

    # --- geography: 21 ICBs across 7 regions
    icbs = []
    for ri, region in enumerate(REGIONS):
        for k in range(3):
            icbs.append((f"Q{ri}{k}", f"NHS DEMO ICB {ri}{k}", region, rng.normal(0, 0.25)))

    # --- LSOAs with deprivation scores (right-skewed like IMD)
    lsoas = [f"E01{i:06d}" for i in range(N_LSOA)]
    lsoa_imd = np.clip(rng.gamma(2.2, 9.5, N_LSOA), 1.5, 90)
    imd = pd.DataFrame({
        "LSOA code (2011)": lsoas,
        "Index of Multiple Deprivation (IMD) Score": lsoa_imd.round(3),
        "Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOAs)":
            (11 - pd.qcut(lsoa_imd, 10, labels=False) - 1).astype(int),
    })
    imd.to_csv(OUT / "imd.csv", index=False)

    # --- practices
    order = np.argsort(lsoa_imd)
    prac_rows, lsoa_rows, qof_rows, epd_meta = [], [], [], []
    for i in range(N_PRACTICES):
        code = f"Y{i:05d}"
        icb = icbs[rng.integers(len(icbs))]
        list_size = int(np.clip(rng.lognormal(8.9, 0.55), 900, 30000))
        # practices draw patients from a deprivation neighbourhood
        centre = rng.integers(0, N_LSOA)
        pool = order[np.clip(np.arange(centre - 120, centre + 120), 0, N_LSOA - 1)]
        chosen = rng.choice(pool, size=6, replace=False)
        w = rng.dirichlet(np.ones(6))
        counts = np.maximum((w * list_size).round().astype(int), 5)
        for l, c in zip(chosen, counts):
            lsoa_rows.append((code, lsoas[l], int(c)))
        prac_imd = float(np.average(lsoa_imd[chosen], weights=counts))
        prev = np.clip(0.055 + 0.0007 * prac_imd + rng.normal(0, 0.008), 0.02, 0.2)
        reg = int(counts.sum() * 0.8 * prev)
        qof_rows.append((code, "DM", reg, int(counts.sum() * 0.8)))
        epd_meta.append(dict(code=code, name=f"DEMO SURGERY {i:03d}", pc=f"ZZ{i%90:02d} 1AA",
                             icb=icb, reg=reg, imd=prac_imd))

    pd.DataFrame(lsoa_rows, columns=["PRACTICE_CODE", "LSOA_CODE", "NUMBER_OF_PATIENTS"]).assign(
        EXTRACT_DATE="2024-01-01").to_csv(OUT / "gp_lsoa.csv", index=False)
    pd.DataFrame(qof_rows, columns=["PRACTICE_CODE", "GROUP_CODE", "REGISTER", "PATIENT_LIST_SIZE"]).to_csv(
        OUT / "qof_diabetes.csv", index=False)

    # --- prescribing
    by_class = {}
    for s in SUBSTANCES:
        by_class.setdefault(s[2], []).append(s)

    for mi, ym in enumerate(MONTHS):
        rows = []
        for p in epd_meta:
            # newer-drug share: arbitrary demo relationship + ICB effect + upward drift
            logit = -1.7 - 0.008 * (p["imd"] - 25) + p["icb"][3] + 0.04 * mi + rng.normal(0, 0.35)
            newer = 1 / (1 + np.exp(-logit))
            mix = dict(BASE_MIX)
            mix["sglt2"], mix["glp1"] = newer * 0.7, newer * 0.3
            total_non_ins = sum(mix.values())
            mix = {k: v / total_non_ins for k, v in mix.items() if k != "insulin"}
            n_items = rng.poisson(p["reg"] * rng.normal(1.9, 0.25))
            n_ins = rng.poisson(p["reg"] * 0.35)
            for cls, share in mix.items():
                n_cls = rng.binomial(n_items, share)
                subs = [s for s in by_class[cls] if s[3] > 0]
                ws = np.array([s[3] for s in subs]) / sum(s[3] for s in subs)
                for s, k in zip(subs, rng.multinomial(n_cls, ws)):
                    if k:
                        rows.append((s, p, k))
            subs = by_class["insulin"]
            for s, k in zip(subs, rng.multinomial(n_ins, [0.5, 0.5])):
                if k:
                    rows.append((s, p, k))
            if rng.random() < 0.6:  # hypoglycaemia item that must be filtered out (BNF 060104)
                rows.append((("Glucagon", "0601040G0", "x", 1), p, int(rng.integers(1, 6))))

        df = pd.DataFrame([{
            "YEAR_MONTH": f"{ym // 100}-{ym % 100:02d}", "REGIONAL_OFFICE_NAME": p["icb"][2], "ICB_NAME": p["icb"][1],
            "ICB_CODE": p["icb"][0], "PRACTICE_NAME": p["name"], "PRACTICE_CODE": p["code"],
            "POSTCODE": p["pc"], "BNF_CHEMICAL_SUBSTANCE_CODE": s[1], "BNF_PRESENTATION_CODE": s[1] + "AA",
            "BNF_PRESENTATION_NAME": ("Mounjaro KwikPen 5mg/0.5ml solution for injection" if s[0] == "Tirzepatide" else s[0] + " 10mg tablets"),
            "BNF_CHEMICAL_SUBSTANCE": s[1], "ITEMS": k, "TOTAL_QUANTITY": k * 56,
            "NIC": round(k * rng.uniform(1.5, 40), 2), "ACTUAL_COST": 0.0,
        } for s, p, k in rows])
        df["ACTUAL_COST"] = (df["NIC"] * 0.93).round(2)
        df.to_csv(OUT / "epd" / f"epd_{ym}.csv", index=False)
        print(f"{ym}: {len(df):,} rows")

    # a few EPD practices with no denominators (simulates mergers/closures)
    extra = df.head(30).copy()
    extra["PRACTICE_CODE"] = [f"Z{i%8:05d}" for i in range(len(extra))]
    extra["PRACTICE_NAME"] = "DEMO CLOSED PRACTICE"
    extra.to_csv(OUT / "epd" / f"epd_{MONTHS[-1]}.csv", mode="a", header=False, index=False)
    print("Demo data written to", OUT)


if __name__ == "__main__":
    main()
