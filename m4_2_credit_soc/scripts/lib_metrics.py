"""Extraction des grandeurs de réponse d'un run M4.2.

Copié de recherche/sensibilite_m4b/scripts/lib_metrics.py, adapté pour M4.2 :
- le seuil bas ``s_min`` des ajustements est un paramètre (défaut 2, comme la
  campagne M4B) au lieu d'une constante figée ;
- intégration de l'estimateur CSN discret avec scan de s_min par distance KS
  (copié de m4_credit_soc_fable/experiments/m4/soc_stats.py::fit_tail_discrete) ;
- bootstrap par run des paramètres (tau, s_c, s_min) ;
- métriques de fonctionnement du marché η (colonnes mkt_* de series.csv).

Chaque fonction lit uniquement les données primaires du run (series.csv,
avalanches.csv, deaths.csv, snapshots) et produit des scalaires documentés
dans le protocole.  Les ajustements de lois se font toujours par run (donc
par graine) ; l'agrégation inter-graines relève de l'analyse, pas d'ici.

Conventions :
- une fenêtre est notée [lo, hi] en pas inclus ;
- burn-in par défaut T/4 ; la robustesse à ce choix est vérifiée en
  calculant les mêmes grandeurs pour d'autres burn-ins et deux demi-fenêtres ;
- un ajustement de loi n'est tenté que si l'effectif est suffisant
  (N_MIN_FIT tailles >= s_min), sinon la métrique est marquée non identifiable.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import optimize, special, stats

N_MIN_FIT = 100          # effectif minimal (tailles >= s_min) pour ajuster une loi
DEFAULT_S_MIN = 2        # seuil bas primaire (comparabilité avec la campagne M4B)
BURN_FRACTIONS = (0.125, 0.25, 0.5)


# ---------------------------------------------------------------- lecture

def read_series(directory: Path) -> dict[str, np.ndarray]:
    with (directory / "series.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        return {}
    keys = rows[0].keys()
    return {key: np.array([float(row[key]) for row in rows]) for key in keys}


def read_avalanches(directory: Path) -> dict[str, np.ndarray]:
    path = directory / "avalanches.csv"
    if not path.exists():
        return {}
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        return {"t": np.array([]), "size": np.array([]), "depth": np.array([]),
                "n_roots": np.array([]), "volume_j": np.array([])}
    return {
        "t": np.array([int(row["t"]) for row in rows]),
        "size": np.array([int(row["size"]) for row in rows]),
        "depth": np.array([int(row["depth"]) for row in rows]),
        "n_roots": np.array([int(row["n_roots"]) for row in rows]),
        "volume_j": np.array([float(row.get("volume_j", "nan") or "nan") for row in rows]),
    }


def read_deaths(directory: Path) -> list[dict]:
    path = directory / "deaths.csv"
    if not path.exists():
        return []
    with path.open() as stream:
        return list(csv.DictReader(stream))


def final_snapshot(directory: Path) -> dict[str, np.ndarray] | None:
    snaps = sorted((directory / "snapshots").glob("entities_t*.npz"))
    if not snaps:
        return None
    with np.load(snaps[-1]) as data:
        return {key: data[key].copy() for key in data.files}


def final_network(directory: Path) -> dict[str, np.ndarray] | None:
    snaps = sorted((directory / "snapshots").glob("network_t*.npz"))
    if not snaps:
        return None
    with np.load(snaps[-1]) as data:
        return {key: data[key].copy() for key in data.files}


# ---------------------------------------------------------- outils de série

def integrated_autocorr(values: np.ndarray, max_lag: int | None = None) -> float:
    """Temps d'autocorrélation intégré (somme des rho jusqu'au premier négatif)."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 10:
        return float("nan")
    centred = values - values.mean()
    variance = float(np.dot(centred, centred) / n)
    if variance <= 0:
        return 1.0
    tau = 1.0
    limit = max_lag or n // 4
    for lag in range(1, limit):
        rho = float(np.dot(centred[:-lag], centred[lag:]) / ((n - lag) * variance))
        if rho <= 0:
            break
        tau += 2.0 * rho
    return tau


def slope_per_step(t: np.ndarray, values: np.ndarray) -> tuple[float, float]:
    """Pente OLS et son erreur type corrigée par l'autocorrélation."""
    if len(t) < 10:
        return float("nan"), float("nan")
    slope, _, _, _, stderr = stats.linregress(t, values)
    tau = integrated_autocorr(values)
    correction = math.sqrt(tau) if np.isfinite(tau) and tau > 1 else 1.0
    return float(slope), float(stderr * correction)


# ------------------------------------------------------ lois des avalanches

def fit_powerlaw_discrete(sizes: np.ndarray, s_min: int = DEFAULT_S_MIN) -> dict | None:
    """MLE de p(s) = s^-alpha / zeta(alpha, s_min) sur s >= s_min."""
    sizes = np.asarray(sizes, dtype=float)
    sizes = sizes[sizes >= s_min]
    n = len(sizes)
    if n < N_MIN_FIT:
        return None
    log_sum = float(np.log(sizes).sum())

    def nll(alpha: float) -> float:
        if alpha <= 1.0001:
            return 1e100
        z = float(special.zeta(alpha, s_min))
        if not np.isfinite(z) or z <= 0:
            return 1e100
        return n * math.log(z) + alpha * log_sum

    result = optimize.minimize_scalar(nll, bounds=(1.01, 8.0), method="bounded")
    alpha = float(result.x)
    step = 1e-4
    second = (nll(alpha + step) - 2 * nll(alpha) + nll(alpha - step)) / step**2
    se = 1.0 / math.sqrt(second) if second > 0 else float("nan")
    return {"alpha": alpha, "se": se, "n_tail": n, "s_min": int(s_min),
            "loglik": -float(result.fun)}


def _support(sizes: np.ndarray, s_min: int) -> np.ndarray:
    upper = max(int(sizes.max()) * 4, 500)
    return np.arange(s_min, upper + 1, dtype=float)


def fit_powerlaw_cutoff(sizes: np.ndarray, s_min: int = DEFAULT_S_MIN) -> dict | None:
    """MLE de p(s) ∝ s^-alpha exp(-s/s_c) sur s >= s_min (support étendu)."""
    sizes = np.asarray(sizes, dtype=float)
    sizes = sizes[sizes >= s_min]
    n = len(sizes)
    if n < N_MIN_FIT:
        return None
    support = _support(sizes, s_min)
    log_support = np.log(support)
    log_sizes = np.log(sizes)

    def nll(theta) -> float:
        alpha, log_cutoff = theta
        if not (0 < alpha < 8) or not (-1 < log_cutoff < 20):
            return 1e100
        logw = -alpha * log_support - support * math.exp(-log_cutoff)
        logz = float(np.logaddexp.reduce(logw))
        value = n * logz + alpha * float(log_sizes.sum()) + float(sizes.sum()) * math.exp(-log_cutoff)
        return value if np.isfinite(value) else 1e100

    best = None
    for start in ((1.5, math.log(max(sizes.max(), 4))), (1.0, 3.0), (2.0, 5.0)):
        result = optimize.minimize(nll, start, method="Nelder-Mead",
                                   options={"maxiter": 2000, "xatol": 1e-6, "fatol": 1e-9})
        if best is None or result.fun < best.fun:
            best = result
    if best is None or not np.isfinite(best.fun) or best.fun >= 1e99:
        return None
    alpha, log_cutoff = best.x
    return {"alpha": float(alpha), "cutoff": float(math.exp(log_cutoff)),
            "loglik": -float(best.fun), "n_tail": n, "s_min": int(s_min)}


def fit_powerlaw_cutoff_fixed_sc(
    sizes: np.ndarray, cutoff: float, s_min: int = DEFAULT_S_MIN
) -> dict | None:
    """MLE de alpha seul, coupure s_c fixée (profil de vraisemblance).

    Sert au critère de confirmation n°4 du protocole : ré-ajuster tau à
    coupure commune pour séparer un effet de pente d'un effet de coupure.
    """
    sizes = np.asarray(sizes, dtype=float)
    sizes = sizes[sizes >= s_min]
    n = len(sizes)
    if n < N_MIN_FIT or cutoff <= 0:
        return None
    support = _support(sizes, s_min)
    log_support = np.log(support)
    log_sum = float(np.log(sizes).sum())
    penalty = float(sizes.sum()) / cutoff

    def nll(alpha: float) -> float:
        if not (0 < alpha < 8):
            return 1e100
        logw = -alpha * log_support - support / cutoff
        logz = float(np.logaddexp.reduce(logw))
        value = n * logz + alpha * log_sum + penalty
        return value if np.isfinite(value) else 1e100

    result = optimize.minimize_scalar(nll, bounds=(0.01, 8.0), method="bounded")
    if not np.isfinite(result.fun) or result.fun >= 1e99:
        return None
    return {"alpha": float(result.x), "cutoff": float(cutoff),
            "loglik": -float(result.fun), "n_tail": n, "s_min": int(s_min)}


def _pointwise_loglik_powerlaw(sizes: np.ndarray, alpha: float, s_min: int) -> np.ndarray:
    z = float(special.zeta(alpha, s_min))
    return -alpha * np.log(sizes) - math.log(z)


def _pointwise_loglik_cutoff(
    sizes: np.ndarray, alpha: float, cutoff: float, s_min: int
) -> np.ndarray:
    support = _support(sizes, s_min)
    logw = -alpha * np.log(support) - support / cutoff
    logz = float(np.logaddexp.reduce(logw))
    return -alpha * np.log(sizes) - sizes / cutoff - logz


def vuong_trunc_vs_ln(sizes: np.ndarray, s_min: int = DEFAULT_S_MIN) -> dict | None:
    """Test de Vuong loi tronquée (modèle primaire) contre log-normale.

    Contrairement à ``vuong_pl_vs_ln`` (qui compare la loi PURE, déjà
    rejetée par LRT dès que la coupure est significative — comparaison non
    informative sur le modèle primaire), ce test compare directement la
    tronquée à la log-normale. Les deux modèles ont deux paramètres libres
    chacun et sont normalisés sur le même support fini
    ``[s_min, max(4·s_max, 500)]`` : la statistique de Vuong (test non
    emboîté, variance de la différence de vraisemblances point par point)
    s'applique sans correction de degrés de liberté supplémentaire.
    z > 0 : la tronquée est favorisée.
    """
    sizes = np.asarray(sizes, dtype=int)
    tail = sizes[sizes >= s_min].astype(float)
    if len(tail) < N_MIN_FIT:
        return None
    cut = fit_powerlaw_cutoff(tail, s_min=s_min)
    ln = fit_lognormal_discrete(tail, s_min=s_min)
    if not cut or not ln:
        return None
    pointwise_cut = _pointwise_loglik_cutoff(tail, cut["alpha"], cut["cutoff"], s_min)
    ratio = pointwise_cut - ln["pointwise"]
    n = len(ratio)
    sd = float(ratio.std(ddof=1))
    z = float(ratio.mean() * math.sqrt(n) / sd) if sd > 0 else float("nan")
    return {"z": z, "mean_lr": float(ratio.mean()), "n": n}


def fit_lognormal_discrete(sizes: np.ndarray, s_min: int = DEFAULT_S_MIN) -> dict | None:
    """MLE de la log-normale discrète renormalisée sur s >= s_min."""
    sizes = np.asarray(sizes, dtype=float)
    sizes = sizes[sizes >= s_min]
    n = len(sizes)
    if n < N_MIN_FIT:
        return None
    support = _support(sizes, s_min)
    log_support = np.log(support)
    log_sizes = np.log(sizes)

    def logpmf_terms(mu: float, sd: float):
        logw = -((log_support - mu) ** 2) / (2 * sd * sd) - log_support
        logz = float(np.logaddexp.reduce(logw))
        return logz

    def nll(theta) -> float:
        mu, log_sd = theta
        sd = math.exp(log_sd)
        if sd > 50 or abs(mu) > 30:
            return 1e100
        logz = logpmf_terms(mu, sd)
        ll = (-((log_sizes - mu) ** 2) / (2 * sd * sd) - log_sizes - logz).sum()
        return -float(ll) if np.isfinite(ll) else 1e100

    mean, sd0 = float(log_sizes.mean()), max(float(log_sizes.std()), 0.05)
    best = None
    for start in ((mean, math.log(sd0)), (mean - 1, math.log(2 * sd0)), (0.0, 0.0)):
        result = optimize.minimize(nll, start, method="Nelder-Mead",
                                   options={"maxiter": 2000})
        if best is None or result.fun < best.fun:
            best = result
    if best is None or not np.isfinite(best.fun) or best.fun >= 1e99:
        return None
    mu, log_sd = best.x
    sd = math.exp(log_sd)
    logz = logpmf_terms(mu, sd)
    pointwise = -((log_sizes - mu) ** 2) / (2 * sd * sd) - log_sizes - logz
    return {"mu": float(mu), "sd": float(sd), "loglik": -float(best.fun),
            "pointwise": pointwise, "n_tail": n, "s_min": int(s_min)}


# ------------------- estimateur CSN discret avec scan de s_min (soc_stats)

def _discrete_pl_negll(alpha: float, sizes: np.ndarray, s_min: int) -> float:
    if alpha <= 1.0:
        return 1e12
    z = float(special.zeta(alpha, s_min))
    if not (z > 0 and math.isfinite(z)):
        return 1e12
    return len(sizes) * math.log(z) + alpha * float(np.sum(np.log(sizes)))


def _fit_alpha_discrete(sizes: np.ndarray, s_min: int) -> float | None:
    """MLE de alpha par recherche ternaire sur [1.01, 20]."""
    lo, hi = 1.01, 20.0
    for _ in range(200):
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        if _discrete_pl_negll(m1, sizes, s_min) < _discrete_pl_negll(m2, sizes, s_min):
            hi = m2
        else:
            lo = m1
    alpha = 0.5 * (lo + hi)
    if alpha >= 19.5:
        return None  # bord : pas une loi de puissance identifiable
    return alpha


def _discrete_pl_cdf(xs: np.ndarray, alpha: float, s_min: int) -> np.ndarray:
    z = float(special.zeta(alpha, s_min))
    pmf_support = np.arange(s_min, xs.max() + 1, dtype=float) ** (-alpha) / z
    cum = np.cumsum(pmf_support)
    return cum[(xs - s_min).astype(int)]


def fit_tail_discrete(sizes: np.ndarray, s_min_max: int = 10,
                      min_tail: int = 50) -> dict | None:
    """Scan de s_min (1..s_min_max), MLE zêta, choix par KS minimal (CSN
    discret). sizes : entiers >= 1."""
    sizes = np.asarray(sizes, dtype=int)
    best = None
    for s_min in range(1, s_min_max + 1):
        tail = sizes[sizes >= s_min]
        if len(tail) < min_tail or tail.max() <= s_min:
            continue
        alpha = _fit_alpha_discrete(tail, s_min)
        if alpha is None:
            continue
        xs = np.sort(np.unique(tail))
        cdf_fit = _discrete_pl_cdf(xs, alpha, s_min)
        cdf_emp = np.searchsorted(np.sort(tail), xs, side="right") / len(tail)
        ks = float(np.max(np.abs(cdf_emp - cdf_fit)))
        if best is None or ks < best["ks"]:
            best = dict(s_min=s_min, alpha=float(alpha), ks=ks,
                        n_tail=int(len(tail)))
    return best


def compare_laws(sizes: np.ndarray, s_min: int = DEFAULT_S_MIN) -> dict:
    """Ajuste les trois lois et calcule les comparaisons de vraisemblance.

    Retourne aussi le test de Vuong loi de puissance contre log-normale
    (z > 0 : la loi de puissance est favorisée) et le fit secondaire avec
    scan de s_min (tail_scan) demandé par le protocole M4.2.
    """
    sizes = np.asarray(sizes, dtype=int)
    tail = sizes[sizes >= s_min].astype(float)
    out: dict = {"n_events": int(len(sizes)), "n_tail": int(len(tail)),
                 "s_min": int(s_min)}
    if len(tail) < N_MIN_FIT:
        out["identifiable"] = False
        return out
    out["identifiable"] = True

    pl = fit_powerlaw_discrete(tail, s_min=s_min)
    cut = fit_powerlaw_cutoff(tail, s_min=s_min)
    ln = fit_lognormal_discrete(tail, s_min=s_min)
    out["powerlaw"] = {k: pl[k] for k in ("alpha", "se", "n_tail", "loglik")} if pl else None
    out["powerlaw_cutoff"] = cut
    if ln:
        out["lognormal"] = {k: ln[k] for k in ("mu", "sd", "loglik", "n_tail")}

    # Convention pré-enregistrée « coupure hors portée » (protocole §6) :
    # si s_c > 10·s_max, la tronquée dégénère en pure ; tau_hat (métrique
    # primaire) est alors lu sur la loi pure et le drapeau est levé.
    size_max = float(tail.max())
    if cut:
        out["s_c_out_of_range"] = bool(cut["cutoff"] > 10.0 * size_max)
        out["tau_hat"] = (
            pl["alpha"] if (out["s_c_out_of_range"] and pl) else cut["alpha"]
        )
        out["tau_hat_source"] = (
            "powerlaw_pure" if out["s_c_out_of_range"] else "powerlaw_cutoff"
        )
    elif pl:
        out["s_c_out_of_range"] = None
        out["tau_hat"] = pl["alpha"]
        out["tau_hat_source"] = "powerlaw_pure"

    if pl and cut:
        lam_stat = 2.0 * (cut["loglik"] - pl["loglik"])
        out["lrt_cutoff_vs_pure"] = {
            "statistic": float(lam_stat),
            # borne du paramètre : p conservatrice = 0.5 * chi2(1)
            "p_value": float(0.5 * stats.chi2.sf(max(lam_stat, 0.0), df=1)),
        }
    if pl and ln:
        pointwise_pl = _pointwise_loglik_powerlaw(tail, pl["alpha"], s_min)
        ratio = pointwise_pl - ln["pointwise"]
        n = len(ratio)
        sd = float(ratio.std(ddof=1))
        z = float(ratio.mean() * math.sqrt(n) / sd) if sd > 0 else float("nan")
        out["vuong_pl_vs_ln"] = {"z": z, "mean_lr": float(ratio.mean()), "n": n}

    out["tail_scan"] = fit_tail_discrete(sizes)
    return out


def bootstrap_avalanche_fits(
    sizes: np.ndarray,
    n_boot: int = 200,
    seed: int = 0,
    s_min: int = DEFAULT_S_MIN,
    scan: bool = True,
) -> dict | None:
    """IC bootstrap (percentile) par run des paramètres d'avalanches.

    Rééchantillonne les tailles avec remise (toutes tailles, y compris les
    singletons, pour que le scan de s_min soit refait par réplicat), puis
    réajuste : loi pure (alpha), loi tronquée (alpha, s_c) et scan de s_min.
    """
    rng = np.random.default_rng(seed)
    sizes = np.asarray(sizes, dtype=int)
    if len(sizes[sizes >= s_min]) < N_MIN_FIT:
        return None
    alphas: list[float] = []
    alphas_cut: list[float] = []
    cutoffs: list[float] = []
    smins: list[float] = []
    for _ in range(n_boot):
        resample = rng.choice(sizes, size=len(sizes), replace=True)
        tail = resample[resample >= s_min].astype(float)
        if len(tail) < N_MIN_FIT:
            continue
        pl = fit_powerlaw_discrete(tail, s_min=s_min)
        if pl:
            alphas.append(pl["alpha"])
        cut = fit_powerlaw_cutoff(tail, s_min=s_min)
        if cut:
            alphas_cut.append(cut["alpha"])
            cutoffs.append(cut["cutoff"])
        if scan:
            scanned = fit_tail_discrete(resample)
            if scanned:
                smins.append(float(scanned["s_min"]))

    def _ci(values: list[float]) -> dict | None:
        if len(values) < max(20, n_boot // 4):
            return None
        arr = np.asarray(values, dtype=float)
        return {
            "mean": float(arr.mean()),
            "sd": float(arr.std(ddof=1)),
            "q025": float(np.quantile(arr, 0.025)),
            "q975": float(np.quantile(arr, 0.975)),
            "n": int(len(arr)),
        }

    return {
        "n_boot": int(n_boot),
        "alpha_pure": _ci(alphas),
        "alpha_cutoff": _ci(alphas_cut),
        "cutoff": _ci(cutoffs),
        "smin_scan": _ci(smins),
    }


# ------------------------------------------------------- métriques fenêtre

def window_series_metrics(series: dict, lo: int, hi: int) -> dict:
    mask = (series["t"] >= lo) & (series["t"] <= hi)
    n = int(mask.sum())
    if n < 30:
        return {"valid": False, "n_steps": n}
    t = series["t"][mask]
    pop = series["pop"][mask]
    out: dict = {"valid": True, "n_steps": n, "window": [int(lo), int(hi)]}

    slope, slope_se = slope_per_step(t, pop)
    tau = integrated_autocorr(pop)
    pop_mean = float(pop.mean())
    out["pop"] = {
        "mean": pop_mean,
        "std": float(pop.std()),
        "cv": float(pop.std() / pop_mean) if pop_mean > 0 else float("nan"),
        "slope_per_step": slope,
        "slope_se": slope_se,
        "rel_drift_window": float(slope * (hi - lo) / pop_mean) if pop_mean > 0 else float("nan"),
        "tau_int": float(tau),
        "ess": float(n / tau) if np.isfinite(tau) and tau > 0 else float("nan"),
    }
    for key in ("births", "deaths", "K_tot", "nw_tot", "prod_tot", "n_loans",
                "new_loans", "loan_volume", "interest_paid", "defaults",
                "claim_losses", "destroyed", "n_avalanches", "cascade_iters",
                "mkt_pool", "mkt_rounds", "mkt_new_edges", "mkt_merges"):
        out[key + "_mean"] = float(series[key][mask].mean())
    out["max_avalanche_window"] = float(series["max_avalanche"][mask].max())

    if pop_mean > 0:
        out["intensive"] = {
            "K_per_capita": out["K_tot_mean"] / pop_mean,
            "loans_per_capita": out["n_loans_mean"] / pop_mean,
            "prod_per_capita": out["prod_tot_mean"] / pop_mean,
            "loan_volume_per_capita": out["loan_volume_mean"] / pop_mean,
            "deaths_rate": out["deaths_mean"] / pop_mean,
        }
        kt = out["K_tot_mean"]
        out["ratios"] = {
            "interest_to_K": out["interest_paid_mean"] / kt if kt > 0 else float("nan"),
            "new_credit_to_K": out["loan_volume_mean"] / kt if kt > 0 else float("nan"),
            "losses_to_K": out["claim_losses_mean"] / kt if kt > 0 else float("nan"),
            "interest_to_prod": out["interest_paid_mean"] / out["prod_tot_mean"]
            if out["prod_tot_mean"] > 0 else float("nan"),
        }
        # Fonctionnement de η : succès des tentatives et part des fusions.
        rounds_mean = out["mkt_rounds_mean"]
        tx_mean = out["new_loans_mean"]
        out["market"] = {
            "tx_success_rate": tx_mean / rounds_mean if rounds_mean > 0 else float("nan"),
            "merge_share": out["mkt_merges_mean"] / tx_mean if tx_mean > 0 else float("nan"),
            "pool_over_pop": out["mkt_pool_mean"] / pop_mean,
        }
    return out


def window_avalanche_metrics(av: dict, lo: int, hi: int, pop_mean: float,
                             s_min: int = DEFAULT_S_MIN) -> dict:
    if not av or len(av.get("t", ())) == 0:
        return {"n_events": 0, "identifiable": False}
    mask = (av["t"] >= lo) & (av["t"] <= hi)
    sizes = av["size"][mask]
    out: dict = {"n_events": int(len(sizes))}
    if len(sizes) == 0:
        out["identifiable"] = False
        return out
    depth = av["depth"][mask]
    roots = av["n_roots"][mask]
    volume = av["volume_j"][mask]
    total_size = int(sizes.sum())
    out.update({
        "rate_per_step": float(len(sizes) / max(1, hi - lo + 1)),
        "size_mean": float(sizes.mean()),
        "size_q50": float(np.quantile(sizes, 0.5)),
        "size_q90": float(np.quantile(sizes, 0.9)),
        "size_q99": float(np.quantile(sizes, 0.99)),
        "size_max": int(sizes.max()),
        "size_max_over_pop": float(sizes.max() / pop_mean) if pop_mean > 0 else float("nan"),
        "susceptibility": float((sizes.astype(float) ** 2).mean() / sizes.mean()),
        "branching_ratio": float(1.0 - roots.sum() / total_size) if total_size else float("nan"),
        "induced_fraction": float((sizes - roots).sum() / total_size) if total_size else float("nan"),
        "depth_mean": float(depth.mean()),
        "depth_max": int(depth.max()),
        "singleton_rate": float((sizes == 1).mean()),
        "frac_size_ge2": float((sizes >= 2).mean()),
        "roots_per_avalanche": float(roots.mean()),
        "volume_mean_j": float(volume.mean()),
        "volume_max_j": float(volume.max()),
    })
    out.update(compare_laws(sizes, s_min=s_min))
    return out


def death_metrics(deaths: list[dict], lo: int, hi: int) -> dict:
    rows = [row for row in deaths if lo <= int(row["t"]) <= hi]
    if not rows:
        return {"n_deaths": 0}
    ages = np.array([int(row["age"]) for row in rows])
    causes = [row["cause"] for row in rows]
    n = len(rows)
    return {
        "n_deaths": n,
        "age_mean": float(ages.mean()),
        "age_median": float(np.median(ages)),
        "age_q90": float(np.quantile(ages, 0.9)),
        "cause_shares": {
            cause: causes.count(cause) / n
            for cause in ("liquidity", "insolvency", "both", "cascade")
        },
    }


def snapshot_metrics(snap: dict | None, network: dict | None) -> dict:
    if snap is None or len(snap.get("id", ())) == 0:
        return {"available": False}
    K = snap["K"]
    nw = snap["nw"]
    income = snap["income"]
    debts = snap["debts"]
    claims = snap["claims"]
    out = {
        "available": True,
        "n_entities": int(len(K)),
        "K": _dist_stats(K),
        "nw": _dist_stats(nw),
        "income": _dist_stats(income),
        "income_net": _dist_stats(snap["income_net"]),
        "age_K_spearman": float(stats.spearmanr(snap["age"], K).statistic)
        if len(K) > 10 else float("nan"),
        "debt_to_K": float(debts.sum() / K.sum()) if K.sum() > 0 else float("nan"),
        "frac_borrowers": float((debts > 0).mean()),
        "frac_lenders": float((claims > 0).mean()),
        "deg_in_mean": float(snap["deg_in"].mean()),
        "deg_out_mean": float(snap["deg_out"].mean()),
        "deg_in_max": int(snap["deg_in"].max()),
        "deg_out_max": int(snap["deg_out"].max()),
        "nw_negative_frac": float((nw < 0).mean()),
    }
    if network is not None and len(network.get("q", ())) > 0:
        q = network["q"]
        q_sorted = np.sort(q)[::-1]
        top = max(1, int(0.01 * len(q)))
        out["network"] = {
            "n_loans": int(len(q)),
            "principal_gini": _gini(q),
            "principal_top1pct_share": float(q_sorted[:top].sum() / q.sum()),
            "rate_mean": float(network["r"].mean()),
            "rate_median": float(np.median(network["r"])),
            "rate_q90": float(np.quantile(network["r"], 0.9)),
        }
    return out


def _gini(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values >= 0)]
    if len(values) == 0 or values.sum() <= 0:
        return 0.0
    values = np.sort(values)
    n = len(values)
    return float((2 * np.dot(np.arange(1, n + 1), values) / values.sum() - n - 1) / n)


def _dist_stats(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return {}
    positive = finite[finite > 0]
    sorted_desc = np.sort(finite)[::-1]
    top10 = max(1, int(0.10 * len(finite)))
    total = finite.sum()
    return {
        "mean": float(finite.mean()),
        "median": float(np.median(finite)),
        "q90": float(np.quantile(finite, 0.9)),
        "q99": float(np.quantile(finite, 0.99)),
        "max": float(finite.max()),
        "gini_nonneg": _gini(finite),
        "top10_share": float(sorted_desc[:top10].sum() / total) if total > 0 else float("nan"),
        "log_std": float(np.log(positive).std()) if len(positive) > 10 else float("nan"),
    }


def integrity_metrics(series: dict, summary: dict) -> dict:
    if not series:
        return {"balance_max_rel_residual": float("nan"),
                "book_errors": summary.get("book_errors", [])}
    change = np.diff(np.r_[0.0, series["K_tot"]])
    flows = (series["injected"] + series["shock_gain"] + series["prod_tot"]
             - series["depreciated"] - series["destroyed"])
    scale = np.maximum(1.0, np.abs(series["K_tot"]))
    residual = np.abs(change - flows) / scale
    return {
        "balance_max_rel_residual": float(residual.max()),
        "book_errors": summary.get("book_errors", []),
        "K_tot_min": float(series["K_tot"].min()),
    }


# --------------------------------------------------------------- pilotage

def _load_manifest(directory: Path) -> dict:
    """Manifeste de campagne, ou équivalent synthétisé pour un run
    Simulation Lab (config.json du moteur + run.json du lab)."""
    path = directory / "manifest.json"
    if path.exists():
        return json.loads(path.read_text())
    config = json.loads((directory / "config.json").read_text())
    lab = {}
    lab_path = directory / "run.json"
    if lab_path.exists():
        lab = json.loads(lab_path.read_text())
    return {
        "run_id": lab.get("run_id", directory.name),
        "engine_hash": "lab:" + config.get("model_version", "?"),
        "parameters": config["parameters"],
        "recording": config.get("recording", {}),
    }


def compute_run_metrics(directory: Path, s_min: int = DEFAULT_S_MIN) -> dict:
    """Toutes les métriques d'un run, pour plusieurs fenêtres."""
    manifest = _load_manifest(directory)
    summary = json.loads((directory / "summary.json").read_text())
    series = read_series(directory)
    avalanches = read_avalanches(directory)
    deaths = read_deaths(directory)
    T = manifest["parameters"]["T"]
    t_final = summary["t_final"]

    out = {
        "run_id": manifest["run_id"],
        "engine_hash": manifest["engine_hash"],
        "parameters": manifest["parameters"],
        "recording": manifest["recording"],
        "model_status": summary["status"],
        "t_final": t_final,
        "population_final": summary["population_final"],
        "censored_by_pop_max": summary["status"] == "explosion",
        "extinct": summary["status"] == "extinction",
        "integrity": integrity_metrics(series, summary),
        "windows": {},
    }
    if summary["status"] == "extinction":
        out["extinction_time"] = t_final

    if not series:
        return out

    pop_mean_ref = None
    for fraction in BURN_FRACTIONS:
        lo = int(fraction * T)
        hi = t_final
        name = f"burn{fraction}"
        block = {"series": window_series_metrics(series, lo, hi)}
        if block["series"].get("valid"):
            pop_mean = block["series"]["pop"]["mean"]
            if fraction == 0.25:
                pop_mean_ref = pop_mean
            block["avalanches"] = window_avalanche_metrics(
                avalanches, lo, hi, pop_mean, s_min=s_min
            )
            block["deaths"] = death_metrics(deaths, lo, hi)
        out["windows"][name] = block

    # Demi-fenêtres de la fenêtre par défaut : contrôle de stationnarité.
    lo = int(0.25 * T)
    mid = (lo + t_final) // 2
    first = window_series_metrics(series, lo, mid)
    second = window_series_metrics(series, mid + 1, t_final)
    if first.get("valid") and second.get("valid"):
        p1, p2 = first["pop"]["mean"], second["pop"]["mean"]
        pooled_sd = math.sqrt(0.5 * (first["pop"]["std"] ** 2 + second["pop"]["std"] ** 2))
        out["stationarity"] = {
            "pop_mean_first_half": p1,
            "pop_mean_second_half": p2,
            "rel_diff": (p2 - p1) / p1 if p1 > 0 else float("nan"),
            "diff_in_sd": (p2 - p1) / pooled_sd if pooled_sd > 0 else float("nan"),
            "K_rel_diff": (second["K_tot_mean"] - first["K_tot_mean"]) / first["K_tot_mean"]
            if first["K_tot_mean"] > 0 else float("nan"),
        }

    snap = final_snapshot(directory)
    network = final_network(directory)
    out["final_snapshot"] = snapshot_metrics(snap, network)

    if pop_mean_ref is not None:
        out["N_over_lambda"] = pop_mean_ref / manifest["parameters"]["lam"] \
            if manifest["parameters"]["lam"] > 0 else float("nan")
    return out


def _to_jsonable(obj):
    if isinstance(obj, dict):
        return {key: _to_jsonable(value) for key, value in obj.items()
                if key != "pointwise"}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(item) for item in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def save_run_metrics(directory: Path, output_dir: Path) -> Path:
    metrics = _to_jsonable(compute_run_metrics(directory))
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{metrics['run_id']}.json"
    path.write_text(json.dumps(metrics, indent=1, ensure_ascii=False))
    return path
