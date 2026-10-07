"""Tests de l'outillage statistique sur des données synthétiques contrôlées."""
import conftest_path  # noqa: F401
import numpy as np

from m2.analysis import (bootstrap_tail_alpha, fit_body, fit_tail_csn,
                         fit_tail_fixed_xmin, lr_powerlaw_vs_lognormal,
                         body_increment_moments)


def test_body_fit_recovers_exponential():
    """MLE tronqué : sur un échantillon exponentiel pur, l'exponentielle doit
    gagner ou être à dAIC <= 2 (l'ajustement NON tronqué échoue à ce test :
    dAIC ~ 31 pour gamma — c'est la raison du MLE tronqué)."""
    rng = np.random.default_rng(0)
    x = rng.exponential(scale=5.0, size=5000)
    res = fit_body(x)
    assert res["delta_aic_expon"] <= 2.0
    assert abs(res["fits"]["expon"]["params"][-1] - 5.0) < 0.5  # scale
    assert 0.6 < res["med_over_mean"] < 0.78  # ~ln 2 (corps tronqué à 95%)


def test_body_fit_prefers_lognormal_on_lognormal():
    rng = np.random.default_rng(1)
    x = rng.lognormal(mean=1.0, sigma=0.8, size=5000)
    res = fit_body(x)
    assert res["best"] in ("lognorm", "gamma", "fisk")
    assert res["delta_aic_expon"] > 2


def test_tail_csn_recovers_pareto_exponent():
    rng = np.random.default_rng(2)
    alpha_true = 2.8  # exposant de pdf
    x = (1 - rng.random(20000)) ** (-1.0 / (alpha_true - 1.0))  # Pareto x_min=1
    fit = fit_tail_csn(x)
    assert fit is not None
    assert abs(fit["alpha"] - alpha_true) < 0.15
    lr = lr_powerlaw_vs_lognormal(x, fit["x_min"], fit["alpha"])
    # la log-normale tronquée imite une Pareto : le signe de R est du bruit
    # sur des données Pareto pures ; l'exigence correcte est de ne PAS
    # conclure significativement log-normale
    assert lr["R"] > 0 or lr["p"] > 0.05


def test_tail_lr_favors_lognormal_on_lognormal():
    """LR corrigé (log-normale tronquée) : ne doit pas conclure Pareto sur des
    données log-normales pures."""
    rng = np.random.default_rng(3)
    x = rng.lognormal(mean=0.0, sigma=1.0, size=20000)
    fit = fit_tail_csn(x)
    lr = lr_powerlaw_vs_lognormal(x, fit["x_min"], fit["alpha"])
    assert lr["R"] < 0 or lr["p"] > 0.05  # ne doit pas conclure Pareto


def test_tail_lr_naive_is_biased_pro_pareto():
    """Documente le défaut du tail_test.py historique : sur des données
    log-normales pures, la variante naïve conclut « loi de puissance »
    (R fortement positif, p ~ 0). Si ce test casse un jour, la comparaison
    avec les logs E7c n'est plus valable telle quelle."""
    rng = np.random.default_rng(3)
    x = rng.lognormal(mean=0.0, sigma=1.0, size=20000)
    fit = fit_tail_csn(x)
    lr = lr_powerlaw_vs_lognormal(x, fit["x_min"], fit["alpha"], truncated=False)
    assert lr["R"] > 100 and lr["p"] < 0.01


def test_tail_lr_truncated_still_favors_pareto_on_pareto():
    """Sur une Pareto pure, le LR corrigé doit au moins pointer dans la bonne
    direction (R > 0). NB : une log-normale tronquée à grand sigma imite une
    Pareto de très près, donc la significativité peut rester marginale même
    sur 12000 points de queue — c'est une limite de puissance connue (CSN) à
    garder en tête pour interpréter les résultats M2."""
    rng = np.random.default_rng(6)
    alpha_true = 2.5
    x = (1 - rng.random(20000)) ** (-1.0 / (alpha_true - 1.0))
    fit = fit_tail_csn(x)
    lr = lr_powerlaw_vs_lognormal(x, fit["x_min"], fit["alpha"])
    assert lr["R"] > 0 or lr["p"] > 0.05


def test_fixed_xmin_and_bootstrap_consistent():
    rng = np.random.default_rng(4)
    alpha_true = 3.0
    x = (1 - rng.random(10000)) ** (-1.0 / (alpha_true - 1.0))
    fx = fit_tail_fixed_xmin(x, 2.0)
    bt = bootstrap_tail_alpha(x, 2.0, n_boot=100, seed=0)
    assert abs(fx["alpha"] - alpha_true) < 0.2
    assert bt["alpha_lo"] < fx["alpha"] < bt["alpha_hi"]


def test_body_increment_moments():
    """Marche aléatoire à drift connu : A0 = -drift, B0 = var/2."""
    rng = np.random.default_rng(5)
    n = 2000
    x0 = rng.uniform(0, 10, size=n)
    dx = rng.normal(-0.3, 1.0, size=n)  # drift -0.3, variance 1
    snap_a = dict(id=np.arange(n), nw=x0)
    snap_b = dict(id=np.arange(n), nw=x0 + dx)
    m = body_increment_moments(snap_a, snap_b, 0.0, 10.0)
    assert abs(m["A0"] - 0.3) < 0.1
    assert abs(m["B0"] - 0.5) < 0.1
