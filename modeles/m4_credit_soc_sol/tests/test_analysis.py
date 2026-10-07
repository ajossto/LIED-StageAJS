import numpy as np

from m4.analysis import (fit_discrete_powerlaw,
                         lr_discrete_powerlaw_vs_lognormal,
                         avalanche_powerlaw_diagnostics)


def test_discrete_powerlaw_recovers_zipf():
    rng = np.random.default_rng(101)
    x = rng.zipf(2.4, size=12000)
    fit = fit_discrete_powerlaw(x, min_tail=100)
    assert fit is not None
    assert 2.2 < fit["alpha"] < 2.6
    lr = lr_discrete_powerlaw_vs_lognormal(x, fit["x_min"], fit["alpha"])
    assert lr is not None
    assert lr["R"] > 0


def test_truncated_lognormal_alternative_not_biased_to_powerlaw():
    rng = np.random.default_rng(102)
    x = np.maximum(1, np.rint(rng.lognormal(1.0, 1.0, size=12000))).astype(int)
    fit = fit_discrete_powerlaw(x, min_tail=100)
    assert fit is not None
    lr = lr_discrete_powerlaw_vs_lognormal(x, fit["x_min"], fit["alpha"])
    assert lr is not None
    assert lr["R"] < 0


def test_double_regression_is_reported():
    avalanches = []
    for size, count in ((1, 1000), (2, 120), (3, 55), (4, 30), (5, 18)):
        avalanches.extend(dict(t=700, size=size) for _ in range(count))
    out = avalanche_powerlaw_diagnostics(avalanches, t_min=500)
    assert out["regression_all"] is not None
    assert out["regression_no_singletons"] is not None
    assert out["regression_no_singletons"]["size_min"] == 2

