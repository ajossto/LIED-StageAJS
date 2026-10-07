"""
run_simulation.py — Cœur de l'étude de sensibilité.

Fournit :
  run_and_collect(params_override, n_steps, seed) → dict de métriques
  detect_regime(n_alive_series) → int (step de début du régime permanent)
  compute_distribution_stats(values) → dict de statistiques de distribution

Conçu pour être appelé en parallèle via multiprocessing.Pool.
Chaque appel est stateless (pas de globals mutables).
"""

from __future__ import annotations

import importlib
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "modele-27-04-WIP" / "src"

# Paramètres fixes pour toute l'étude (alpha homogène, pas d'amortissement)
FIXED_PARAMS = {
    "alpha_min": 1.0,
    "alpha_max": 1.0,
    "alpha_sigma_brownien": 0.0,
    "taux_amortissement": 0.0,
    "log_events": False,
    "freq_snapshot": 50,
}

# Baseline (point central de l'étude)
BASELINE = {
    "theta": 0.35,
    "mu": 0.05,
    "lambda_creation": 2.0,
    "n_candidats_pool": 3,
    "fraction_taux_emprunteur": 0.2,
    "seuil_ratio_endettement": 1.0,
    "seuil_ratio_liquide_passif": 0.05,
    "taux_depreciation_endo": 0.05,
    "taux_depreciation_exo": 0.05,
    "fraction_auto_investissement": 0.5,
    "coefficient_reliquefaction": 0.5,
    "actif_liquide_initial": 200.0,
    "passif_inne_initial": 190.0,
    "n_entites_initiales": 100,
}


def _load_sim_modules():
    """Charge config + simulation depuis src/ en isolant les modules."""
    sys.path.insert(0, str(SRC))
    try:
        for mod in ("config", "models", "statistics", "simulation"):
            sys.modules.pop(mod, None)
        config_mod = importlib.import_module("config")
        importlib.import_module("models")
        importlib.import_module("statistics")
        sim_mod = importlib.import_module("simulation")
    finally:
        if str(SRC) in sys.path:
            sys.path.remove(str(SRC))
    return config_mod.SimulationConfig, sim_mod.Simulation


def detect_regime(n_alive_series: list[int], n_min_window: int = 100) -> tuple[int, bool]:
    """
    Détecte le début du régime permanent.

    Returns (t_regime, is_genuine) :
      t_regime   — premier pas considéré comme appartenant au régime permanent
      is_genuine — True si une vraie descente a été détectée,
                   False si on a utilisé le fallback (30 % finaux)

    Algorithme :
      1. Ignorer les 50 premiers pas (phase transitoire)
      2. Trouver le pic global de n_alive après le transitoire
      3. Chercher la première descente à < 75 % du pic
      4. Régime = drop + 100 pas de stabilisation
    """
    n = len(n_alive_series)
    skip = min(50, n // 6)

    if n < skip + n_min_window + 20:
        return max(0, n - n_min_window), False

    post_skip = n_alive_series[skip:]
    peak = max(post_skip)
    if peak == 0:
        return int(0.7 * n), False

    t_peak = post_skip.index(peak) + skip
    threshold = 0.75 * peak

    t_drop = None
    for t in range(t_peak, n):
        if n_alive_series[t] < threshold:
            t_drop = t
            break

    if t_drop is None:
        return int(0.70 * n), False

    t_regime = t_drop + n_min_window
    if t_regime >= n - 30:
        t_regime = max(t_drop + 20, n - 30)

    return t_regime, True


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _safe_mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def _linear_slope(values: list[float]) -> float:
    """Pente OLS par pas de temps, avec x=0..n-1."""
    n = len(values)
    if n < 2:
        return 0.0
    mx = (n - 1) / 2.0
    my = _safe_mean(values)
    denom = sum((i - mx) ** 2 for i in range(n))
    if denom <= 0:
        return 0.0
    return sum((i - mx) * (y - my) for i, y in enumerate(values)) / denom


def _relative_tail_slope(values: list[float]) -> float:
    """
    Variation lineaire attendue sur toute la fenetre, rapportee a la moyenne.
    0.10 signifie environ +10 % ou -10 % sur la fenetre de mesure.
    """
    if len(values) < 2:
        return 0.0
    m = _safe_mean(values)
    if abs(m) <= 1e-12:
        return 0.0
    return _linear_slope(values) * len(values) / m


def _relative_iqr(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    v = sorted(values)
    n = len(v)

    def q(p: float) -> float:
        idx = p * (n - 1)
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return v[lo] + (idx - lo) * (v[hi] - v[lo])

    med = q(0.5)
    if abs(med) <= 1e-12:
        return 0.0
    return (q(0.9) - q(0.1)) / med


def _pearson(x: list[float], y: list[float]) -> float:
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    xs = x[:n]
    ys = y[:n]
    mx = _safe_mean(xs)
    my = _safe_mean(ys)
    dx = math.sqrt(sum((v - mx) ** 2 for v in xs))
    dy = math.sqrt(sum((v - my) ** 2 for v in ys))
    if dx <= 0 or dy <= 0:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (dx * dy)


def detect_regime_diagnostics(
    n_alive_series: list[int],
    actif_series: list[float],
    n_loans_series: list[int],
    failures_series: list[int],
    densite_fin_series: list[float],
) -> dict[str, float | int | bool | None]:
    """
    Diagnostics plus souples que l'ancien critere de chute de 25 %.

    L'objectif est de distinguer :
      - une chute visible, meme faible (5 %),
      - une queue approximativement bornee sur la duree simulee,
      - un regime peut-etre non atteint mais dont les faillites montent encore.
    """
    n = len(n_alive_series)
    if n == 0:
        return {
            "t_drop_5": None,
            "drop_5_detected": False,
            "bounded_tail": False,
            "tail_start": None,
        }

    skip = min(50, max(5, n // 20))
    post = n_alive_series[skip:]
    peak_alive = max(post) if post else max(n_alive_series)
    t_peak_alive = n_alive_series.index(peak_alive)

    t_drop_5 = None
    threshold = 0.95 * peak_alive
    for t in range(t_peak_alive + 1, n):
        if n_alive_series[t] <= threshold:
            t_drop_5 = t
            break

    tail_start = max(int(0.6 * n), (t_drop_5 + 100) if t_drop_5 is not None else 0)
    tail_start = min(tail_start, max(0, n - max(30, n // 5)))

    alive_tail = [float(x) for x in n_alive_series[tail_start:]]
    actif_tail = [float(x) for x in actif_series[tail_start:]]
    failures_tail = [float(x) for x in failures_series[tail_start:]]
    dens_tail = [float(x) for x in densite_fin_series[tail_start:]]
    loans_tail = [float(x) for x in n_loans_series[tail_start:]]

    alive_slope_rel = _relative_tail_slope(alive_tail)
    actif_slope_rel = _relative_tail_slope(actif_tail)
    dens_slope_rel = _relative_tail_slope(dens_tail)
    failures_slope_abs = _linear_slope(failures_tail)
    failures_slope_rel = _relative_tail_slope(failures_tail)
    alive_iqr_rel = _relative_iqr(alive_tail)
    actif_iqr_rel = _relative_iqr(actif_tail)

    # Critere operationnel, volontairement descriptif : sur la queue observee,
    # les stocks ne doivent pas continuer une derive de grande amplitude.
    bounded_tail = (
        abs(alive_slope_rel) <= 0.20
        and abs(actif_slope_rel) <= 0.20
        and alive_iqr_rel <= 0.70
        and actif_iqr_rel <= 0.80
    )

    return {
        "t_drop_5": t_drop_5,
        "drop_5_detected": t_drop_5 is not None,
        "peak_alive": peak_alive,
        "t_peak_alive": t_peak_alive,
        "tail_start": tail_start,
        "bounded_tail": bounded_tail,
        "alive_tail_slope_rel": alive_slope_rel,
        "actif_tail_slope_rel": actif_slope_rel,
        "densite_fin_tail_slope_rel": dens_slope_rel,
        "failures_tail_slope_abs": failures_slope_abs,
        "failures_tail_slope_rel": failures_slope_rel,
        "alive_tail_iqr_rel": alive_iqr_rel,
        "actif_tail_iqr_rel": actif_iqr_rel,
        "tail_failure_rate": _safe_mean(failures_tail),
        "corr_alive_actif_tail": _pearson(alive_tail, actif_tail),
        "corr_alive_loans_tail": _pearson(alive_tail, loans_tail),
        "corr_actif_loans_tail": _pearson(actif_tail, loans_tail),
        "corr_alive_failures_tail": _pearson(alive_tail, failures_tail),
        "corr_actif_failures_tail": _pearson(actif_tail, failures_tail),
    }


def compute_distribution_stats(values: list[float]) -> dict[str, float]:
    """
    Calcule des statistiques descriptives d'une distribution.
    Inclut : moyenne, médiane, std, Gini, quantiles, estimateur de pente log-log (Pareto).
    """
    if not values:
        return {}
    v = sorted(values)
    n = len(v)

    mean_v = sum(v) / n
    var_v = sum((x - mean_v) ** 2 for x in v) / n
    std_v = math.sqrt(var_v)

    def quantile(p: float) -> float:
        idx = p * (n - 1)
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return v[lo] + (idx - lo) * (v[hi] - v[lo])

    # Gini en O(n) sur valeurs triées.
    if mean_v > 0:
        weighted = sum((i + 1) * x for i, x in enumerate(v))
        gini = (2 * weighted) / (n * sum(v)) - (n + 1) / n
    else:
        gini = 0.0

    # Estimateur de pente log-log (rang vs valeur, méthode OLS sur log-log)
    # Utilise les 10 % supérieurs pour estimer la queue
    tail_start = int(0.5 * n)
    tail = v[tail_start:]
    power_slope = float("nan")
    if len(tail) >= 5 and tail[0] > 0:
        try:
            xs = [math.log(x) for x in tail if x > 0]
            ys = [math.log(len(tail) - i) for i in range(len(xs))]
            n_t = len(xs)
            sx = sum(xs); sy = sum(ys)
            sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
            denom = n_t * sxx - sx * sx
            if denom != 0:
                power_slope = (n_t * sxy - sx * sy) / denom
        except Exception:
            pass

    # Log-normal quality : compare log(values) to a normal distribution
    log_vals = [math.log(x) for x in v if x > 0]
    lognormal_sigma = 0.0
    lognormal_mu = 0.0
    if log_vals:
        lognormal_mu = sum(log_vals) / len(log_vals)
        lognormal_sigma = math.sqrt(sum((x - lognormal_mu) ** 2 for x in log_vals) / len(log_vals))

    return {
        "n": n,
        "mean": mean_v,
        "median": quantile(0.5),
        "std": std_v,
        "cv": std_v / mean_v if mean_v > 0 else 0.0,
        "p10": quantile(0.10),
        "p25": quantile(0.25),
        "p75": quantile(0.75),
        "p90": quantile(0.90),
        "p99": quantile(0.99),
        "gini": gini,
        "power_slope": power_slope,   # pente log-log (Pareto) ; négatif = queue lourde
        "lognormal_mu": lognormal_mu,
        "lognormal_sigma": lognormal_sigma,
        "max": v[-1],
        "min": v[0],
    }


def run_and_collect(
    params_override: dict[str, Any],
    n_steps: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Lance une simulation et retourne un dict compact de métriques.

    params_override : surcharges du BASELINE (ex. {"theta": 0.5})
    n_steps        : durée de la simulation
    seed           : graine RNG

    Retour :
      {
        'params'         : dict complet des paramètres utilisés,
        'seed'           : int,
        'n_steps'        : int,
        'converged'      : bool (True si vraie descente détectée),
        't_regime'       : int,
        # Métriques régime permanent :
        'n_alive_mean'   : float,
        'n_alive_std'    : float,
        'n_alive_cv'     : float,
        'actif_mean'     : float,
        'actif_std'      : float,
        'actif_cv'       : float,
        'n_loans_mean'   : float,
        'loan_density_mean' : float,  # n_loans / n_alive
        'densite_fin_mean'  : float,  # volume_prets / actif
        'gini_actif_mean'   : float,
        'failure_rate_mean' : float,  # faillites / pas
        'failure_lambda_ratio': float,
        'levier_mean'    : float,
        # Distribution shape (dernière snapshot en régime) :
        'dist_stats'     : dict,
        # Séries temporelles compactes (pour tracé) :
        'ts_n_alive'     : list[int],
        'ts_actif'       : list[float],
        'ts_n_loans'     : list[int],
        'ts_failures'    : list[int],
        'ts_densite_fin' : list[float],
        'ts_gini'        : list[float],
      }
    """
    executed_at_utc = datetime.now(timezone.utc)
    executed_at_local = executed_at_utc.astimezone()
    SimulationConfig, Simulation = _load_sim_modules()

    # Construction du dict de paramètres complet
    params = {**BASELINE, **FIXED_PARAMS, **params_override, "seed": seed, "duree_simulation": n_steps}

    # Si actif_liquide_initial est surchargé sans passif_inne_initial explicite,
    # maintenir NW=10
    if "actif_liquide_initial" in params_override and "passif_inne_initial" not in params_override:
        params["passif_inne_initial"] = params["actif_liquide_initial"] - 10.0

    cfg = SimulationConfig(**params)
    sim = Simulation(cfg)
    sim.run(verbose=False)

    # --- Extraction des séries temporelles ---
    stats = sim.stats
    indicators = sim.collector.indicators

    ts_n_alive = [s["n_entities_alive"] for s in stats]
    ts_actif = [s["actif_total_systeme"] for s in stats]
    ts_n_loans = [s["n_prets_actifs"] for s in stats]
    ts_failures = [s["n_failures"] for s in stats]
    ts_densite_fin = [
        ind.densite_financiere for ind in indicators
    ]
    ts_gini = [ind.gini_actif_total for ind in indicators]

    # --- Détection du régime permanent ---
    t_regime, converged = detect_regime(ts_n_alive)
    regime_diag = detect_regime_diagnostics(ts_n_alive, ts_actif, ts_n_loans, ts_failures, ts_densite_fin)
    # Pour les nouvelles analyses, on mesure a partir de la queue bornee si le
    # critere strict 25 % n'est pas informatif. Les anciens champs restent
    # compatibles avec les scripts deja produits.
    t_measure = int(regime_diag.get("tail_start") or t_regime)
    window = slice(t_regime, n_steps)
    measure_window = slice(t_measure, n_steps)

    n_alive_w = ts_n_alive[window]
    actif_w = ts_actif[window]
    loans_w = ts_n_loans[window]
    failures_w = ts_failures[window]
    gini_w = ts_gini[window]
    densite_w = ts_densite_fin[window]

    n_alive_mean = _safe_mean(n_alive_w)
    n_alive_std = _safe_std(n_alive_w)
    actif_mean = _safe_mean(actif_w)
    actif_std = _safe_std(actif_w)
    n_loans_mean = _safe_mean(loans_w)
    failure_rate = _safe_mean(failures_w)
    gini_mean = _safe_mean(gini_w)
    densite_fin_mean = _safe_mean(densite_w)

    n_alive_m = ts_n_alive[measure_window]
    actif_m = ts_actif[measure_window]
    loans_m = ts_n_loans[measure_window]
    failures_m = ts_failures[measure_window]
    gini_m = ts_gini[measure_window]
    densite_m = ts_densite_fin[measure_window]

    # loan_density = n_loans / n_alive (moyen)
    loan_densities = [
        l / n if n > 0 else 0.0
        for l, n in zip(loans_w, n_alive_w)
    ]
    loan_density_mean = _safe_mean(loan_densities)

    loan_densities_m = [
        l / n if n > 0 else 0.0
        for l, n in zip(loans_m, n_alive_m)
    ]

    # levier moyen (indicateurs dans la fenêtre de régime)
    ind_w = indicators[t_regime:n_steps]
    levier_mean = _safe_mean([ind.levier_systeme for ind in ind_w])

    # Cascades dans la fenetre de mesure.
    cascades_m = [c for c in sim.collector.cascades if c.step >= t_measure]
    cascade_sizes = [c.nb_entites_faillie for c in cascades_m]
    cascade_destructions = [c.ratio_destruction for c in cascades_m]
    cascade_contagions = [c.ratio_contagion for c in cascades_m]

    # --- Distribution des tailles en régime ---
    # Chercher le dernier snapshot dans la fenêtre de régime
    raw_dist = sim.collector.raw_distributions.get("actif_total", [])
    regime_dist = []
    for (step, vals) in raw_dist:
        if step >= t_regime:
            regime_dist = vals
    # Si aucun snapshot en régime, prendre le dernier disponible
    if not regime_dist and raw_dist:
        regime_dist = raw_dist[-1][1]

    dist_stats = compute_distribution_stats(regime_dist)
    # Les distributions complètes peuvent être volumineuses dans les campagnes
    # longues ; on conserve néanmoins le dernier snapshot utile pour les pilotes
    # et les diagnostics de forme.
    dist_values_regime = list(regime_dist)

    lambda_c = params.get("lambda_creation", 2.0)

    return {
        "executed_at_utc": executed_at_utc.isoformat(),
        "executed_at_local": executed_at_local.isoformat(),
        "params": {k: v for k, v in params.items() if k not in ("seed", "duree_simulation", "log_events", "freq_snapshot")},
        "seed": seed,
        "n_steps": n_steps,
        "converged": converged,
        "t_regime": t_regime,
        "t_measure": t_measure,
        "regime_diagnostics": regime_diag,
        # Métriques régime permanent
        "n_alive_mean": n_alive_mean,
        "n_alive_std": n_alive_std,
        "n_alive_cv": n_alive_std / n_alive_mean if n_alive_mean > 0 else 0.0,
        "actif_mean": actif_mean,
        "actif_std": actif_std,
        "actif_cv": actif_std / actif_mean if actif_mean > 0 else 0.0,
        "n_loans_mean": n_loans_mean,
        "loan_density_mean": loan_density_mean,
        "densite_fin_mean": densite_fin_mean,
        "gini_actif_mean": gini_mean,
        "failure_rate_mean": failure_rate,
        "failure_lambda_ratio": failure_rate / lambda_c if lambda_c > 0 else 0.0,
        "levier_mean": levier_mean,
        # Meme famille de metriques sur la fenetre souple de queue observee.
        "measure_n_alive_mean": _safe_mean(n_alive_m),
        "measure_n_alive_cv": _safe_std(n_alive_m) / _safe_mean(n_alive_m) if _safe_mean(n_alive_m) > 0 else 0.0,
        "measure_actif_mean": _safe_mean(actif_m),
        "measure_actif_cv": _safe_std(actif_m) / _safe_mean(actif_m) if _safe_mean(actif_m) > 0 else 0.0,
        "measure_n_loans_mean": _safe_mean(loans_m),
        "measure_loan_density_mean": _safe_mean(loan_densities_m),
        "measure_densite_fin_mean": _safe_mean(densite_m),
        "measure_gini_actif_mean": _safe_mean(gini_m),
        "measure_failure_rate_mean": _safe_mean(failures_m),
        "measure_failure_lambda_ratio": _safe_mean(failures_m) / lambda_c if lambda_c > 0 else 0.0,
        # Critère de convergence flux : faillites ≈ naissances (|ratio - 1| < 0.15).
        # flow_balanced = True signifie que le flux de faillites est en équilibre
        # avec le flux de naissances, indiquant un régime permanent réel.
        "flow_balanced": abs(_safe_mean(failures_m) / lambda_c - 1.0) < 0.15 if lambda_c > 0 else False,
        "stationary": bool((regime_diag or {}).get("bounded_tail")) and (abs(_safe_mean(failures_m) / lambda_c - 1.0) < 0.15 if lambda_c > 0 else False),
        # Cascades de faillites.
        "cascade_event_rate": len(cascades_m) / max(1, n_steps - t_measure),
        "cascade_size_mean": _safe_mean(cascade_sizes),
        "cascade_size_max": max(cascade_sizes) if cascade_sizes else 0,
        "cascade_ratio_destruction_mean": _safe_mean(cascade_destructions),
        "cascade_ratio_contagion_mean": _safe_mean(cascade_contagions),
        "dist_stats": dist_stats,
        "dist_values_regime": dist_values_regime,
        # Séries temporelles (compactes)
        "ts_n_alive": ts_n_alive,
        "ts_actif": ts_actif,
        "ts_n_loans": ts_n_loans,
        "ts_failures": ts_failures,
        "ts_densite_fin": ts_densite_fin,
        "ts_gini": ts_gini,
    }
