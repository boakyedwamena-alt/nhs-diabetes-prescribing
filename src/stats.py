"""Statistics helpers: funnel-plot limits (Spiegelhalter 2005, overdispersed proportions) and the ANOVA intraclass correlation."""
import numpy as np
import pandas as pd

Z_95, Z_998 = 1.96, 3.09


def overdispersion_factor(p: np.ndarray, n: np.ndarray, p0: float, trim: float = 0.1) -> float:
    """phi = mean of squared winsorised z-scores. phi > 1 means more between-practice
    variation than chance alone would give. Floored at 1."""
    z = (p - p0) / np.sqrt(p0 * (1 - p0) / n)
    lo, hi = np.quantile(z, [trim, 1 - trim])
    return float(max(1.0, np.mean(np.clip(z, lo, hi) ** 2)))


def funnel_limits(p0: float, n: np.ndarray, phi: float, z: float) -> tuple[np.ndarray, np.ndarray]:
    se = np.sqrt(phi * p0 * (1 - p0) / n)
    return np.clip(p0 - z * se, 0, 1), np.clip(p0 + z * se, 0, 1)


def flag_practices(df: pd.DataFrame, events: str, trials: str) -> tuple[pd.DataFrame, float, float]:
    """Return df with funnel columns, the national proportion and phi."""
    d = df[df[trials] > 0].copy()
    p0 = d[events].sum() / d[trials].sum()
    d["p"] = d[events] / d[trials]
    phi = overdispersion_factor(d["p"].to_numpy(), d[trials].to_numpy(), p0)
    for z, tag in [(Z_95, "95"), (Z_998, "998")]:
        lo, hi = funnel_limits(p0, d[trials].to_numpy(), phi, z)
        d[f"lo_{tag}"], d[f"hi_{tag}"] = lo, hi
    d["funnel_flag"] = np.where(d["p"] > d["hi_998"], "High outlier (99.8%)",
                        np.where(d["p"] < d["lo_998"], "Low outlier (99.8%)",
                        np.where(d["p"] > d["hi_95"], "High (95%)",
                        np.where(d["p"] < d["lo_95"], "Low (95%)", "Within limits"))))
    return d, float(p0), phi


def icc_anova(y: np.ndarray, g: np.ndarray) -> float:
    """Intraclass correlation from a one-way ANOVA: the share of variance lying between groups (ICBs).
    Needs no iterative fit, unlike a mixed model; unbalanced group sizes are handled through n0.
    The between-group variance is floored at zero."""
    d = pd.DataFrame({"y": y, "g": g})
    grp = d.groupby("g")["y"]
    n, means = grp.size(), grp.mean()
    k, N, grand = len(n), n.sum(), d["y"].mean()
    msb = (n * (means - grand) ** 2).sum() / (k - 1)
    msw = ((d["y"] - d["g"].map(means)) ** 2).sum() / (N - k)
    n0 = (N - (n ** 2).sum() / N) / (k - 1)
    var_b = max((msb - msw) / n0, 0.0)
    return float(var_b / (var_b + msw))
