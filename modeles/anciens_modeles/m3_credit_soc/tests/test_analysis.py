"""Tests des estimateurs statistiques (analysis.py, dpln.py) sur données
synthétiques à vérité connue, seeds fixes. Assertions simples — pas de pytest."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from m3.analysis import (fit_body, fit_tail_csn, fit_tail_fixed_xmin,
                         lr_powerlaw_vs_lognormal, fit_full_families,
                         gini, hhi, top_shares, transition_matrix,
                         avalanche_size_distribution, network_default_auc)
from m3.dpln import dpln_rvs, fit_dpln


def _pareto_sample(alpha_pdf, n, rng, x_min=1.0):
    """Pareto pure : pdf ~ x^-alpha_pdf pour x >= x_min (CSN alpha = pdf)."""
    u = rng.uniform(0.0, 1.0, size=n)
    return x_min * (1.0 - u) ** (-1.0 / (alpha_pdf - 1.0))


def test_fit_body_expon():
    """fit_body sur exponentielle pure (n=5000) : expon gagne ou dAIC <= 2."""
    rng = np.random.default_rng(101)
    v = rng.exponential(2.0, size=5000)
    out = fit_body(v)
    assert out is not None
    assert out["best"] == "expon" or out["delta_aic_expon"] <= 2.0, \
        (out["best"], out["delta_aic_expon"])


def test_fit_body_gamma():
    """fit_body sur gamma(shape=2) : best == "gamma"."""
    rng = np.random.default_rng(102)
    v = rng.gamma(2.0, 1.5, size=5000)
    out = fit_body(v)
    assert out is not None
    assert out["best"] == "gamma", (out["best"],
                                    {k: f["aic"] for k, f in out["fits"].items()})


def test_fit_tail_csn_pareto():
    """fit_tail_csn sur Pareto pure alpha=2.5 (n=5000) : alpha dans [2.3, 2.7]."""
    rng = np.random.default_rng(103)
    v = _pareto_sample(2.5, 5000, rng)
    fit = fit_tail_csn(v)
    assert fit is not None
    assert 2.3 <= fit["alpha"] <= 2.7, fit


def test_lr_lognormal_negative():
    """LR corrigé (lognormale tronquée) sur lognormale pure : R < 0."""
    rng = np.random.default_rng(104)
    v = rng.lognormal(0.0, 1.0, size=5000)
    tail_fit = fit_tail_csn(v)
    assert tail_fit is not None
    out = lr_powerlaw_vs_lognormal(v, tail_fit["x_min"], tail_fit["alpha"],
                                   truncated=True)
    assert out is not None
    assert out["R"] < 0.0, out


def test_lr_pareto_inconclusive():
    """LR corrigé sur Pareto pure : |z| < 2 (le test ne conclut pas
    anti-Pareto sur une vraie loi de puissance)."""
    rng = np.random.default_rng(105)
    v = _pareto_sample(2.5, 5000, rng)
    tail_fit = fit_tail_fixed_xmin(v, x_min=1.0)
    assert tail_fit is not None
    out = lr_powerlaw_vs_lognormal(v, 1.0, tail_fit["alpha"], truncated=True)
    assert out is not None
    assert abs(out["z"]) < 2.0, out


def test_fit_dpln_recovery():
    """fit_dpln sur dpln_rvs(nu=1, tau=0.5, a=1.8, b=2.5, n=8000) :
    a dans [1.5, 2.2], b dans [1.9, 3.3]."""
    rng = np.random.default_rng(106)
    x = dpln_rvs(1.0, 0.5, 1.8, 2.5, 8000, rng)
    fit = fit_dpln(x)
    assert fit is not None
    a_hat = fit["params"]["a"]
    b_hat = fit["params"]["b"]
    assert 1.5 <= a_hat <= 2.2, fit["params"]
    assert 1.9 <= b_hat <= 3.3, fit["params"]
    assert abs(fit["tail_alpha_pdf"] - (a_hat + 1.0)) < 1e-12


def test_full_families_lognorm():
    """fit_full_families sur lognormale pure : lognorm gagne ou dAIC < 6
    (la dPlN imbrique la lognormale : quasi-égalité possible)."""
    rng = np.random.default_rng(107)
    v = rng.lognormal(0.0, 1.0, size=4000)
    out = fit_full_families(v)
    assert out is not None
    d_aic = out["fits"]["lognorm"]["aic"] - out["fits"][out["best"]]["aic"]
    assert out["best"] == "lognorm" or d_aic < 6.0, (out["best"], d_aic)


def test_full_families_dpln():
    """fit_full_families sur dPlN à queues marquées (a=1.5) : best == "dpln"."""
    rng = np.random.default_rng(108)
    x = dpln_rvs(0.0, 0.4, 1.5, 2.0, 8000, rng)
    out = fit_full_families(x)
    assert out is not None
    assert out["best"] == "dpln", (out["best"],
                                   {k: f["aic"] for k, f in out["fits"].items()})


def test_gini():
    """Gini : valeurs égales -> ~0 ; un seul détenteur sur n=100 -> ~0.99."""
    g_eq = gini([5.0] * 100)
    assert abs(g_eq) < 1e-12, g_eq
    g_one = gini([0.0] * 99 + [10.0])
    assert abs(g_one - 0.99) < 1e-12, g_one


def test_hhi():
    """HHI : parts égales n=10 -> 0.1."""
    h = hhi([3.0] * 10)
    assert abs(h - 0.1) < 1e-12, h
    h_mono = hhi([0.0, 0.0, 7.0])   # un seul détenteur -> 1
    assert abs(h_mono - 1.0) < 1e-12, h_mono


def test_top_shares():
    """top_shares cohérents sur 1..100 : top1 = 100/5050, top10 = 955/5050."""
    v = list(range(1, 101))
    out = top_shares(v)
    total = 5050.0
    assert abs(out["top1"] - 100.0 / total) < 1e-12, out
    top10_sum = float(sum(range(91, 101)))   # 955
    assert abs(out["top10"] - top10_sum / total) < 1e-12, out


def test_transition_matrix_rows():
    """transition_matrix : chaque ligne somme à 1 (colonne mort incluse)."""
    rng = np.random.default_rng(109)
    snap_a = {"id": np.arange(100), "nw": rng.normal(10.0, 5.0, size=100)}
    survivors = np.sort(rng.choice(100, size=70, replace=False))
    snap_b = {"id": survivors, "nw": rng.normal(12.0, 6.0, size=70)}
    mat = transition_matrix(snap_a, snap_b, var="nw", n_q=5)
    assert mat.shape == (5, 6)               # 5 quantiles + colonne mort
    row_sums = mat.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-9), row_sums
    assert mat[:, 5].sum() > 0.0             # des morts sont bien comptées


def test_avalanche_size_distribution():
    """Moyenne/max corrects sur une liste construite ; t < t_min exclu."""
    avalanches = ([dict(t=100, size=50)]          # exclu (t < 500)
                  + [dict(t=600, size=1)] * 6
                  + [dict(t=700, size=2)] * 2
                  + [dict(t=800, size=5), dict(t=900, size=9)])
    out = avalanche_size_distribution(avalanches, t_min=500)
    assert out is not None
    assert out["n"] == 10
    assert out["max"] == 9
    expected_mean = (6 * 1 + 2 * 2 + 5 + 9) / 10.0   # 2.4
    assert abs(out["mean"] - expected_mean) < 1e-12, out["mean"]
    assert abs(out["frac_multi"] - 0.4) < 1e-12
    assert out["sizes"] == [1, 2, 5, 9]
    assert out["counts"] == [6, 2, 1, 1]


def test_network_default_auc():
    """Si les mortes sont exactement les plus endettées -> AUC(debts) ~ 1."""
    n = 60
    rng = np.random.default_rng(110)
    snap = {
        "id": np.arange(n),
        "debts": np.arange(n, dtype=float),          # dette croissante avec id
        "deg_in": rng.integers(0, 4, size=n),
        "claims": rng.uniform(0.0, 10.0, size=n),
        "nw": np.ones(n),
    }
    deaths_after = set(range(50, 60))                # les 10 plus endettées
    out = network_default_auc(None, snap, deaths_after)
    assert out is not None
    assert out["debts"] > 0.95, out
    assert out["leverage"] > 0.95, out               # nw constant : même ordre


def _main():
    mod = sys.modules[__name__]
    names = sorted(n for n in dir(mod) if n.startswith("test_"))
    for name in names:
        getattr(mod, name)()
        print(f"OK {name}")
    return len(names)


if __name__ == "__main__":
    _main()
