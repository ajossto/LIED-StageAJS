"""Tests des estimateurs SOC (experiments/m4/soc_stats.py) sur données
synthétiques : récupération de l'exposant zêta, signe du LR de Vuong,
régression log-log. Assertions Python simples — pas de pytest."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent / "experiments" / "m4"))

from soc_stats import (fit_tail_discrete, loglog_regression,  # noqa: E402
                       lr_discrete_pl_vs_lognormal)


def _zeta_sample(alpha, n, rng, x_max=100000):
    """Tirage exact d'une loi zêta tronquée à x_max (pmf ~ x^-alpha)."""
    xs = np.arange(1, x_max + 1, dtype=float)
    pmf = xs ** (-alpha)
    pmf /= pmf.sum()
    return rng.choice(xs, size=n, p=pmf).astype(np.int64)


def _discrete_lognormal_sample(mu, s, n, rng):
    return np.maximum(1, np.round(rng.lognormal(mu, s, size=n))).astype(np.int64)


def test_zeta_alpha_recovery():
    """MLE discret : alpha récupéré à ±0.15 sur un vrai échantillon zêta."""
    rng = np.random.default_rng(1)
    for alpha_true in (1.8, 2.5):
        sizes = _zeta_sample(alpha_true, 20000, rng)
        fit = fit_tail_discrete(sizes)
        assert fit is not None
        assert abs(fit["alpha"] - alpha_true) < 0.15, (alpha_true, fit)


def test_lr_favors_powerlaw_on_zeta():
    """LR > 0 (z > 2) sur un vrai échantillon zêta."""
    rng = np.random.default_rng(2)
    sizes = _zeta_sample(2.0, 20000, rng)
    fit = fit_tail_discrete(sizes)
    lr = lr_discrete_pl_vs_lognormal(sizes, fit["s_min"], fit["alpha"])
    assert lr is not None and lr["z"] > 2.0, lr


def test_lr_rejects_powerlaw_on_lognormal():
    """LR < 0 (z < -2) sur une lognormale discrète large — le piège n°1
    (pro-Pareto par non-renormalisation) ne se reproduit pas."""
    rng = np.random.default_rng(3)
    sizes = _discrete_lognormal_sample(2.0, 1.2, 20000, rng)
    fit = fit_tail_discrete(sizes)
    assert fit is not None
    lr = lr_discrete_pl_vs_lognormal(sizes, fit["s_min"], fit["alpha"])
    assert lr is not None and lr["z"] < -2.0, lr


def test_loglog_regression_slope():
    """Régression log-binnée : pente ≈ -alpha sur un échantillon zêta dense,
    et r² élevé hors taille 1."""
    rng = np.random.default_rng(4)
    sizes = _zeta_sample(2.2, 50000, rng)
    reg = loglog_regression(sizes, exclude_one=True)
    assert reg is not None
    assert abs(reg["slope"] + 2.2) < 0.35, reg
    assert reg["r2"] > 0.95, reg


def test_regression_none_on_degenerate():
    """Toutes les tailles à 1 : pas de régression (None), pas d'exception."""
    sizes = np.ones(500, dtype=np.int64)
    assert loglog_regression(sizes, exclude_one=False) is None
    assert fit_tail_discrete(sizes) is None


def _main():
    mod = sys.modules[__name__]
    names = sorted(n for n in dir(mod) if n.startswith("test_"))
    for name in names:
        getattr(mod, name)()
        print(f"OK {name}")
    return len(names)


if __name__ == "__main__":
    _main()
