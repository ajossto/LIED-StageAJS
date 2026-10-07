"""Point 14 : validité des estimateurs statistiques sur données synthétiques.

Les échantillons sont tirés par inversion exacte de la CDF discrète sur un
support tronqué très au-delà de la région utile ; la troncature induit un
biais négligeable devant les tolérances testées.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import lib_metrics  # noqa: E402
from lib_metrics import (  # noqa: E402
    compare_laws,
    fit_lognormal_discrete,
    fit_powerlaw_cutoff,
    fit_powerlaw_cutoff_fixed_sc,
    fit_powerlaw_discrete,
    fit_tail_discrete,
    vuong_trunc_vs_ln,
)


def _sample_discrete(pmf_weights: np.ndarray, support: np.ndarray, n: int,
                     rng: np.random.Generator) -> np.ndarray:
    cdf = np.cumsum(pmf_weights / pmf_weights.sum())
    return support[np.searchsorted(cdf, rng.random(n))]


def sample_powerlaw(tau: float, n: int, rng: np.random.Generator,
                    s_min: int = 2, s_max: int = 1_000_000) -> np.ndarray:
    support = np.arange(s_min, s_max + 1, dtype=np.int64)
    return _sample_discrete(support.astype(float) ** (-tau), support, n, rng)


def sample_powerlaw_cutoff(tau: float, s_c: float, n: int,
                           rng: np.random.Generator, s_min: int = 2) -> np.ndarray:
    s_max = int(max(50 * s_c, 500))
    support = np.arange(s_min, s_max + 1, dtype=np.int64)
    weights = support.astype(float) ** (-tau) * np.exp(-support / s_c)
    return _sample_discrete(weights, support, n, rng)


def sample_lognormal_discrete(mu: float, sd: float, n: int,
                              rng: np.random.Generator, s_min: int = 2) -> np.ndarray:
    s_max = int(np.exp(mu + 8 * sd)) + 10
    support = np.arange(s_min, s_max + 1, dtype=np.int64)
    log_support = np.log(support.astype(float))
    weights = np.exp(-((log_support - mu) ** 2) / (2 * sd * sd)) / support
    return _sample_discrete(weights, support, n, rng)


def test_powerlaw_mle_recovers_tau() -> None:
    rng = np.random.default_rng(101)
    for tau in (1.8, 2.2, 2.6):
        sizes = sample_powerlaw(tau, 5000, rng).astype(float)
        fit = fit_powerlaw_discrete(sizes)
        assert fit is not None
        assert abs(fit["alpha"] - tau) <= 3.0 * fit["se"], (tau, fit)

    # Biais moyen sur 20 réplicats indépendants.
    errors = []
    for _ in range(20):
        sizes = sample_powerlaw(2.2, 2000, rng).astype(float)
        fit = fit_powerlaw_discrete(sizes)
        assert fit is not None
        errors.append(fit["alpha"] - 2.2)
    assert abs(float(np.mean(errors))) < 0.05, np.mean(errors)

    # Le paramètre s_min est bien pris en compte (données à support s >= 3).
    sizes3 = sample_powerlaw(2.0, 5000, rng, s_min=3).astype(float)
    fit3 = fit_powerlaw_discrete(sizes3, s_min=3)
    assert fit3 is not None
    assert abs(fit3["alpha"] - 2.0) <= 3.0 * fit3["se"], fit3


def test_cutoff_mle_recovers_tau_and_sc() -> None:
    rng = np.random.default_rng(202)
    for s_c in (30.0, 200.0):
        sizes = sample_powerlaw_cutoff(2.0, s_c, 5000, rng).astype(float)
        fit = fit_powerlaw_cutoff(sizes)
        assert fit is not None
        assert abs(fit["alpha"] - 2.0) <= 0.15, (s_c, fit)
        assert abs(fit["cutoff"] - s_c) <= 0.30 * s_c, (s_c, fit)


def test_smin_scan_finds_threshold() -> None:
    """Queue en loi de puissance pure pour s >= 5, tête contaminée."""
    rng = np.random.default_rng(303)
    tail = sample_powerlaw(2.2, 4000, rng, s_min=5)
    head = rng.integers(2, 5, size=1500)  # contamination uniforme sur {2,3,4}
    sizes = np.concatenate([tail, head])
    rng.shuffle(sizes)
    fit = fit_tail_discrete(sizes)
    assert fit is not None
    assert fit["s_min"] in (4, 5, 6), fit
    assert abs(fit["alpha"] - 2.2) <= 0.15, fit


def test_compare_laws_prefers_generating_family() -> None:
    rng = np.random.default_rng(404)

    # Données tronquées : le LRT doit rejeter la loi pure.
    truncated = sample_powerlaw_cutoff(2.0, 50.0, 3000, rng)
    out = compare_laws(truncated)
    assert out["identifiable"]
    assert out["lrt_cutoff_vs_pure"]["p_value"] < 0.01, out["lrt_cutoff_vs_pure"]

    # Données pures : le LRT ne doit pas rejeter la loi pure (contrôle du
    # taux d'erreur sur 5 réplicats — au plus un rejet à 5 %).
    rejections = 0
    vuong_positive = 0
    for _ in range(5):
        pure = sample_powerlaw(2.2, 3000, rng)
        out = compare_laws(pure)
        assert out["identifiable"]
        if out["lrt_cutoff_vs_pure"]["p_value"] < 0.05:
            rejections += 1
        if out["vuong_pl_vs_ln"]["z"] > 0:
            vuong_positive += 1
    assert rejections <= 1, rejections
    # Sur données en loi de puissance pure, Vuong doit favoriser la loi de
    # puissance contre la log-normale dans la majorité des réplicats.
    assert vuong_positive >= 4, vuong_positive


def test_lognormal_fit_on_lognormal_data() -> None:
    rng = np.random.default_rng(505)
    sizes = sample_lognormal_discrete(1.5, 0.8, 3000, rng).astype(float)
    ln = fit_lognormal_discrete(sizes)
    pl = fit_powerlaw_discrete(sizes)
    assert ln is not None and pl is not None
    assert ln["loglik"] > pl["loglik"], (ln["loglik"], pl["loglik"])
    out = compare_laws(sizes.astype(int))
    assert out["vuong_pl_vs_ln"]["z"] < 0, out["vuong_pl_vs_ln"]


def test_out_of_range_cutoff_falls_back_to_pure() -> None:
    """Convention « s_c hors portée » (protocole §6) : sur données pures, si
    la coupure ajustée dépasse 10·s_max, tau_hat est lu sur la loi pure."""
    rng = np.random.default_rng(707)
    pure = sample_powerlaw(2.2, 3000, rng)
    out = compare_laws(pure)
    assert out["identifiable"]
    assert "tau_hat" in out and "s_c_out_of_range" in out
    if out["s_c_out_of_range"]:
        assert out["tau_hat"] == out["powerlaw"]["alpha"]
        assert out["tau_hat_source"] == "powerlaw_pure"
    else:
        assert out["tau_hat"] == out["powerlaw_cutoff"]["alpha"]
    # Sur données franchement tronquées, la coupure est dans la portée.
    truncated = sample_powerlaw_cutoff(2.0, 30.0, 3000, rng)
    out_trunc = compare_laws(truncated)
    assert out_trunc["s_c_out_of_range"] is False
    assert out_trunc["tau_hat_source"] == "powerlaw_cutoff"


def test_fixed_sc_profile_recovers_tau() -> None:
    """Profil de vraisemblance à s_c fixé (critère de confirmation n°4)."""
    rng = np.random.default_rng(808)
    sizes = sample_powerlaw_cutoff(2.0, 50.0, 5000, rng).astype(float)
    fit = fit_powerlaw_cutoff_fixed_sc(sizes, cutoff=50.0)
    assert fit is not None
    assert abs(fit["alpha"] - 2.0) <= 0.15, fit
    # À la coupure ajustée librement, le profil redonne le même alpha.
    free = fit_powerlaw_cutoff(sizes)
    profiled = fit_powerlaw_cutoff_fixed_sc(sizes, cutoff=free["cutoff"])
    assert abs(profiled["alpha"] - free["alpha"]) <= 0.02


def test_vuong_trunc_vs_ln_prefers_generating_family() -> None:
    """Correction post-audit (27/07) : le Vuong tronquée/log-normale doit
    favoriser chaque modèle sur ses propres données. À taille d'échantillon
    modeste, tronquée et log-normale peuvent être statistiquement proches
    (fait connu) : le test utilise n=20000, l'ordre de grandeur réel des
    runs confirmatoires de la campagne (8300 à 34000 avalanches s>=2)."""
    rng = np.random.default_rng(909)
    truncated = sample_powerlaw_cutoff(2.0, 30.0, 20000, rng)
    result = vuong_trunc_vs_ln(truncated)
    assert result is not None
    assert result["z"] > 2, result

    lognormal = sample_lognormal_discrete(1.5, 0.8, 20000, rng)
    result_ln = vuong_trunc_vs_ln(lognormal)
    assert result_ln is not None
    assert result_ln["z"] < -2, result_ln


def test_bootstrap_returns_calibrated_intervals() -> None:
    rng = np.random.default_rng(606)
    sizes = sample_powerlaw_cutoff(2.0, 50.0, 2000, rng)
    boot = lib_metrics.bootstrap_avalanche_fits(sizes, n_boot=60, seed=1)
    assert boot is not None
    assert boot["alpha_pure"] is not None
    assert boot["alpha_cutoff"] is not None
    interval = boot["alpha_cutoff"]
    assert interval["q025"] <= 2.0 <= interval["q975"], interval
    cutoff_interval = boot["cutoff"]
    assert cutoff_interval["q025"] <= 50.0 <= cutoff_interval["q975"], cutoff_interval


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
