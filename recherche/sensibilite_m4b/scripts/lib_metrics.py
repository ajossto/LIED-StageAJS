"""Extraction des grandeurs de réponse d'un run M4B.

Chaque fonction lit uniquement les données primaires du run (series.csv,
avalanches.csv, deaths.csv, snapshots) et produit des scalaires documentés
dans le protocole.  Les ajustements de lois se font toujours par run (donc
par graine) ; l'agrégation inter-graines relève de l'analyse, pas d'ici.

Conventions :
- une fenêtre est notée [lo, hi] en pas inclus ;
- burn-in par défaut T/4 ; la robustesse à ce choix est vérifiée en
  calculant les mêmes grandeurs pour d'autres burn-ins et deux demi-fenêtres ;
- un ajustement de loi n'est tenté que si l'effectif est suffisant
  (N_MIN_FIT tailles >= 2), sinon la métrique est marquée non identifiable.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import optimize, special, stats

N_MIN_FIT = 100          # effectif minimal (tailles >= 2) pour ajuster une loi
S_MIN = 2                # seuil bas des ajustements de tailles d'avalanches
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

def fit_powerlaw_discrete(sizes: np.ndarray) -> dict | None:
    """MLE de p(s) = s^-alpha / zeta(alpha, S_MIN) sur s >= S_MIN."""
    sizes = np.asarray(sizes[sizes >= S_MIN], dtype=float)
    n = len(sizes)
    if n < N_MIN_FIT:
        return None
    log_sum = float(np.log(sizes).sum())

    def nll(alpha: float) -> float:
        if alpha <= 1.0001:
            return 1e100
        z = float(special.zeta(alpha, S_MIN))
        if not np.isfinite(z) or z <= 0:
            return 1e100
        return n * math.log(z) + alpha * log_sum

    result = optimize.minimize_scalar(nll, bounds=(1.01, 8.0), method="bounded")
    alpha = float(result.x)
    step = 1e-4
    second = (nll(alpha + step) - 2 * nll(alpha) + nll(alpha - step)) / step**2
    se = 1.0 / math.sqrt(second) if second > 0 else float("nan")
    return {"alpha": alpha, "se": se, "n_tail": n, "loglik": -float(result.fun)}


def _support(sizes: np.ndarray) -> np.ndarray:
    upper = max(int(sizes.max()) * 4, 500)
    return np.arange(S_MIN, upper + 1, dtype=float)


def fit_powerlaw_cutoff(sizes: np.ndarray) -> dict | None:
    """MLE de p(s) ∝ s^-alpha exp(-s/s_c) sur s >= S_MIN (support étendu)."""
    sizes = np.asarray(sizes[sizes >= S_MIN], dtype=float)
    n = len(sizes)
    if n < N_MIN_FIT:
        return None
    support = _support(sizes)
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
            "loglik": -float(best.fun), "n_tail": n}


def _pointwise_loglik_powerlaw(sizes: np.ndarray, alpha: float) -> np.ndarray:
    z = float(special.zeta(alpha, S_MIN))
    return -alpha * np.log(sizes) - math.log(z)


def fit_lognormal_discrete(sizes: np.ndarray) -> dict | None:
    """MLE de la log-normale discrète renormalisée sur s >= S_MIN."""
    sizes = np.asarray(sizes[sizes >= S_MIN], dtype=float)
    n = len(sizes)
    if n < N_MIN_FIT:
        return None
    support = _support(sizes)
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
            "pointwise": pointwise, "n_tail": n}


def compare_laws(sizes: np.ndarray) -> dict:
    """Ajuste les trois lois et calcule les comparaisons de vraisemblance.

    Retourne aussi le test de Vuong loi de puissance contre log-normale
    (z > 0 : la loi de puissance est favorisée).
    """
    sizes = np.asarray(sizes, dtype=int)
    tail = sizes[sizes >= S_MIN].astype(float)
    out: dict = {"n_events": int(len(sizes)), "n_tail": int(len(tail))}
    if len(tail) < N_MIN_FIT:
        out["identifiable"] = False
        return out
    out["identifiable"] = True

    pl = fit_powerlaw_discrete(tail)
    cut = fit_powerlaw_cutoff(tail)
    ln = fit_lognormal_discrete(tail)
    out["powerlaw"] = {k: pl[k] for k in ("alpha", "se", "n_tail", "loglik")} if pl else None
    out["powerlaw_cutoff"] = cut
    if ln:
        out["lognormal"] = {k: ln[k] for k in ("mu", "sd", "loglik", "n_tail")}

    if pl and cut:
        lam_stat = 2.0 * (cut["loglik"] - pl["loglik"])
        out["lrt_cutoff_vs_pure"] = {
            "statistic": float(lam_stat),
            # borne du paramètre : p conservatrice = 0.5 * chi2(1)
            "p_value": float(0.5 * stats.chi2.sf(max(lam_stat, 0.0), df=1)),
        }
    if pl and ln:
        pointwise_pl = _pointwise_loglik_powerlaw(tail, pl["alpha"])
        ratio = pointwise_pl - ln["pointwise"]
        n = len(ratio)
        sd = float(ratio.std(ddof=1))
        z = float(ratio.mean() * math.sqrt(n) / sd) if sd > 0 else float("nan")
        out["vuong_pl_vs_ln"] = {"z": z, "mean_lr": float(ratio.mean()), "n": n}
    return out


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
                "claim_losses", "destroyed", "n_avalanches", "cascade_iters"):
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
        }
    return out


def window_avalanche_metrics(av: dict, lo: int, hi: int, pop_mean: float) -> dict:
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
        "frac_size_ge2": float((sizes >= 2).mean()),
        "roots_per_avalanche": float(roots.mean()),
        "volume_mean_j": float(volume.mean()),
        "volume_max_j": float(volume.max()),
    })
    out.update(compare_laws(sizes))
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


def compute_run_metrics(directory: Path) -> dict:
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
            block["avalanches"] = window_avalanche_metrics(avalanches, lo, hi, pop_mean)
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
