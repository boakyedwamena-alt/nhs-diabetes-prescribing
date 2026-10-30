import numpy as np
import pandas as pd

from src.stats import flag_practices, funnel_limits, icc_anova, overdispersion_factor

def test_limits_narrow_as_n_grows():
    lo, hi = funnel_limits(0.2, np.array([100, 10000]), 1.0, 3.09)
    assert (hi - lo)[0] > (hi - lo)[1]


def test_phi_near_one_for_binomial_noise():
    rng = np.random.default_rng(0)
    n = rng.integers(500, 5000, 800)
    p = rng.binomial(n, 0.2) / n
    assert 0.8 <= overdispersion_factor(p, n, 0.2) <= 1.3


def test_obvious_outlier_flagged():
    rng = np.random.default_rng(1)
    n = np.full(300, 2000)
    ev = rng.binomial(n, 0.2)
    ev[0] = 900  # 45% against a ~20% norm
    df = pd.DataFrame({"events": ev, "trials": n})
    out, p0, phi = flag_practices(df, "events", "trials")
    assert out.iloc[0]["funnel_flag"].startswith("High outlier")
    assert 0.19 < p0 < 0.22


def test_icc_recovers_known_value():
    rng = np.random.default_rng(0)
    k, m = 200, 30
    g = np.repeat(np.arange(k), m)
    y = rng.normal(0, 1, k)[g] + rng.normal(0, 1, k * m)  # true ICC = 0.5
    assert abs(icc_anova(y, g) - 0.5) < 0.1


def test_icc_near_zero_without_group_effect():
    rng = np.random.default_rng(2)
    g = np.repeat(np.arange(100), 20)
    assert icc_anova(rng.normal(size=2000), g) < 0.05
