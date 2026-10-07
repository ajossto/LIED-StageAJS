"""
analysis.py — Analyse statistique et visualisation des résultats de simulation.

Graphiques produits dans <simu>/figures/ :
  1. macro_overview.png
  2. cascades_rank_size.png          — taille (X) vs fréquence (Y), log-log
  3. entity_size_histos.png          — histogrammes bâtons aux pas fixes
  4. extraction_power.png            — Π médiane, moyenne, max, Q10, Q90
  5. destruction_moving_avg.png      — destruction + puissance extraction totale
  6. internal_rate_evolution.png     — r* : max, min, moy, med, D1, D9
  7. gini_evolution.png              — inégalités de stocks et revenus
  8. gini_lorenz_snapshots.png       — courbes de Lorenz par snapshot
  9. revenue_distributions.png       — distributions des revenus
 10. entity_lives_overview.png       — 10 entités comparables, 3 graphes par entité
 11. detail_vie_entites/entity_{id}.png — vie individuelle des entités surveillées
 12. loan_network_final.png          — réseau final des prêts actifs
 13. lifespan_analysis.png           — espérance de vie vs taille / levier

Les CSV sont lus dans <simu>/csv/
"""

import csv
import json
import math
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
    import numpy as np
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False
    print("matplotlib non disponible.")


# ============================================================
# CONSTANTES
# ============================================================

FIXED_STEPS = [10, 50, 100, 200, 500, 1000, 2000]


# ============================================================
# LECTURE DES DONNÉES
# ============================================================

def read_csv(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                lines.append(line)
    if not lines:
        return []
    reader = csv.DictReader(lines)
    result = []
    for row in reader:
        converted = {}
        for k, v in row.items():
            if v is None or v == "" or v == "None":
                converted[k] = None
                continue
            try:
                if "." in v or "e" in v.lower():
                    converted[k] = float(v)
                else:
                    converted[k] = int(v)
            except (ValueError, TypeError):
                converted[k] = v
        result.append(converted)
    return result


def read_raw_distribution(csv_dir: str, name: str) -> Dict[int, List[float]]:
    path = os.path.join(csv_dir, f"distrib_brute_{name}.csv")
    rows = read_csv(path)
    data = defaultdict(list)
    for r in rows:
        data[int(r["step"])].append(float(r["value"]))
    return dict(data)


def read_meta(folder: str) -> dict:
    path = os.path.join(folder, "meta.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# UTILITAIRES
# ============================================================

def _paths(folder: str) -> Tuple[str, str]:
    """Retourne (csv_dir, fig_dir) et crée fig_dir si nécessaire."""
    csv_dir = os.path.join(folder, "csv")
    fig_dir = os.path.join(folder, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    return csv_dir, fig_dir


def _save(fig, path: str):
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {path}")


def _log_binned_histogram(values: List[float], n_bins: int = 30) -> Tuple:
    pos = [v for v in values if v > 0]
    if len(pos) < 2:
        return None, None, None
    vmin, vmax = min(pos), max(pos)
    if vmin <= 0 or vmax <= vmin:
        return None, None, None
    log_min, log_max = math.log10(vmin), math.log10(vmax)
    if log_max == log_min:
        return None, None, None
    step = (log_max - log_min) / n_bins
    edges = [10 ** (log_min + i * step) for i in range(n_bins + 1)]
    counts = [0] * n_bins
    for v in pos:
        idx = int((math.log10(v) - log_min) / step)
        idx = min(max(idx, 0), n_bins - 1)
        counts[idx] += 1
    total = len(pos)
    centres, densities = [], []
    for i in range(n_bins):
        if counts[i] > 0:
            centre = math.sqrt(edges[i] * edges[i + 1])
            width = edges[i + 1] - edges[i]
            centres.append(centre)
            densities.append(counts[i] / (total * width))
    return centres, densities, edges


def _adaptive_log_histogram(values, min_per_bin: int = 8, max_bins: int = 40):
    """Histogramme log à bins adaptatifs (quantiles).

    Zones denses → bins plus étroits → meilleure résolution.
    Retourne (centres, densities, edges, counts, poisson_errs) ou Nones si échec.
    """
    pos = np.array([v for v in values if v is not None and v > 0], dtype=float)
    n = len(pos)
    if n < 4:
        return None, None, None, None, None

    n_bins = max(3, min(max_bins, n // min_per_bin))
    log_pos = np.log10(pos)

    # Edges quantiles dans l'espace log
    quantiles = np.linspace(0, 100, n_bins + 1)
    log_edges_raw = np.percentile(log_pos, quantiles)

    # Dédupliquer (valeurs identiques aux bords de bins → largeur nulle)
    unique_log_edges = [log_edges_raw[0]]
    for e in log_edges_raw[1:]:
        if e > unique_log_edges[-1] + 1e-9:
            unique_log_edges.append(e)
    if len(unique_log_edges) < 3:
        return None, None, None, None, None

    log_edges = np.array(unique_log_edges)
    n_bins = len(log_edges) - 1
    edges = 10.0 ** log_edges

    # Compter dans chaque bin via searchsorted sur les arêtes intérieures
    bin_idx = np.searchsorted(log_edges[1:-1], log_pos, side="right")
    counts_arr = np.bincount(bin_idx, minlength=n_bins)
    total = n

    centres, densities, poisson_errs, counts_out = [], [], [], []
    for i in range(n_bins):
        cnt = int(counts_arr[i])
        if cnt == 0:
            continue
        width = edges[i + 1] - edges[i]
        if width <= 0:
            continue
        centre = math.sqrt(edges[i] * edges[i + 1])
        d = cnt / (total * width)
        e = math.sqrt(cnt) / (total * width)
        centres.append(centre)
        densities.append(d)
        poisson_errs.append(e)
        counts_out.append(cnt)

    return centres, densities, list(edges), counts_out, poisson_errs


def _fit_lognormal_mixture(values):
    """Ajuste D = λ·LN(μ₁,σ₁) + (1-λ)·LN(μ₂,σ₂) par MLE.

    Paramètres en log naturel (convention scipy.stats.lognorm).
    Retourne (lam, mu1, s1, mu2, s2) avec mu1 ≤ mu2, ou None si échec.
    """
    try:
        from scipy.stats import lognorm as _lognorm
        from scipy.optimize import minimize as _minimize
    except ImportError:
        return None

    pos = np.array([v for v in values if v is not None and v > 0], dtype=float)
    if len(pos) < 20:
        return None

    log_pos = np.log(pos)

    def neg_ll(p):
        lam, mu1, s1, mu2, s2 = p
        if s1 < 1e-6 or s2 < 1e-6 or lam <= 0 or lam >= 1:
            return 1e12
        pdf1 = _lognorm.pdf(pos, s=s1, scale=np.exp(mu1))
        pdf2 = _lognorm.pdf(pos, s=s2, scale=np.exp(mu2))
        return -np.sum(np.log(np.maximum(lam * pdf1 + (1 - lam) * pdf2, 1e-300)))

    bounds = [(1e-3, 1 - 1e-3), (None, None), (1e-3, None), (None, None), (1e-3, None)]
    best = None

    for q_split in (30, 50, 65):
        cut = np.percentile(log_pos, q_split)
        low = log_pos[log_pos <= cut]
        high = log_pos[log_pos > cut]
        mu1_0 = float(np.mean(low)) if len(low) > 1 else float(np.mean(log_pos)) - 1
        s1_0 = max(float(np.std(low)), 0.15) if len(low) > 1 else 0.5
        mu2_0 = float(np.mean(high)) if len(high) > 1 else float(np.mean(log_pos)) + 1
        s2_0 = max(float(np.std(high)), 0.15) if len(high) > 1 else 0.5
        try:
            res = _minimize(neg_ll, [q_split / 100.0, mu1_0, s1_0, mu2_0, s2_0],
                            method="L-BFGS-B", bounds=bounds,
                            options={"maxiter": 2000, "ftol": 1e-12})
            if best is None or res.fun < best.fun:
                best = res
        except Exception:
            continue

    if best is None:
        return None

    lam, mu1, s1, mu2, s2 = best.x
    if mu1 > mu2:
        lam, mu1, s1, mu2, s2 = 1.0 - lam, mu2, s2, mu1, s1
    return float(np.clip(lam, 1e-4, 1 - 1e-4)), float(mu1), float(s1), float(mu2), float(s2)


def _mixture_r2(centres, counts, edges, lam, mu1, s1, mu2, s2):
    """R² en espace log-densité (plus robuste que R² linéaire pour les queues lourdes)."""
    return _mixture_r2_generic(centres, counts, edges, "ln+ln", (lam, mu1, s1, mu2, s2))


def _mixture_r2_generic(centres, counts, edges, model_type, params):
    """R² en espace log-densité générique pour ln+ln et ln+pareto."""
    try:
        from scipy.stats import lognorm as _lognorm, pareto as _spareto
    except ImportError:
        return float("nan")
    total = sum(counts)
    if total == 0:
        return float("nan")
    log_obs, log_pred = [], []
    for i, (c, ctr) in enumerate(zip(counts, centres)):
        if c <= 0:
            continue
        w = edges[i + 1] - edges[i]
        if w <= 0:
            continue
        d_obs = c / (total * w)
        if model_type == "ln+ln":
            lam, mu1, s1, mu2, s2 = params
            d_pred = (lam * _lognorm.pdf(ctr, s=s1, scale=np.exp(mu1))
                      + (1 - lam) * _lognorm.pdf(ctr, s=s2, scale=np.exp(mu2)))
        elif model_type == "ln+pareto":
            lam, mu, s, alpha, x_min = params
            d_pred = (lam * _lognorm.pdf(ctr, s=s, scale=np.exp(mu))
                      + (1 - lam) * _spareto.pdf(ctr, b=alpha, scale=x_min))
        else:
            continue
        if d_pred > 0:
            log_obs.append(math.log(d_obs))
            log_pred.append(math.log(d_pred))
    if len(log_obs) < 3:
        return float("nan")
    lo = np.array(log_obs)
    lp = np.array(log_pred)
    ss_tot = float(np.sum((lo - lo.mean()) ** 2))
    return float(1.0 - np.sum((lo - lp) ** 2) / max(ss_tot, 1e-300))


def _fit_lognormal_pareto(values):
    """Ajuste D = λ·LN(μ,σ) + (1-λ)·Pareto(x_min,α) par MLE.

    x_min estimé par grille (percentiles 40–90), L-BFGS-B sur (λ, μ, σ, α).
    Retourne (lam, mu, s, alpha, x_min) avec LN=Pop.1 petits, Pareto=Pop.2 grands, ou None.
    """
    try:
        from scipy.stats import lognorm as _lognorm, pareto as _spareto
        from scipy.optimize import minimize as _minimize
    except ImportError:
        return None

    pos = np.array([v for v in values if v is not None and v > 0], dtype=float)
    if len(pos) < 20:
        return None

    log_pos = np.log(pos)
    best_ll = -np.inf
    best_params = None

    for q in range(40, 91, 5):
        x_min = float(np.percentile(pos, q))
        if x_min <= 0:
            continue

        def neg_ll(p, xm=x_min):
            lam, mu, s, alpha = p
            if s < 1e-6 or alpha < 0.05 or lam <= 0 or lam >= 1:
                return 1e12
            f1 = _lognorm.pdf(pos, s=s, scale=np.exp(mu))
            f2 = _spareto.pdf(pos, b=alpha, scale=xm)
            return -np.sum(np.log(np.maximum(lam * f1 + (1 - lam) * f2, 1e-300)))

        below = log_pos[pos < x_min]
        mu0 = float(np.mean(below)) if len(below) > 1 else float(np.mean(log_pos)) - 1
        s0 = max(float(np.std(below)), 0.2) if len(below) > 1 else 0.5
        lam0 = float(np.clip(np.mean(pos < x_min), 0.1, 0.9))
        bounds = [(1e-3, 1 - 1e-3), (None, None), (1e-3, None), (0.05, None)]
        try:
            res = _minimize(neg_ll, [lam0, mu0, s0, 2.0],
                            method="L-BFGS-B", bounds=bounds,
                            options={"maxiter": 1000, "ftol": 1e-11})
            ll = -res.fun
            if ll > best_ll:
                best_ll = ll
                best_params = (res.x, x_min)
        except Exception:
            continue

    if best_params is None:
        return None
    p, x_min = best_params
    lam, mu, s, alpha = p
    return (float(np.clip(lam, 1e-4, 1 - 1e-4)), float(mu), float(s),
            float(max(alpha, 0.05)), float(x_min))


def _fit_single_best(values):
    """Compare LN vs Pareto (composantes uniques) par AIC.

    Retourne dict {'model': 'ln'|'pareto', 'params': tuple, 'aic': float} ou None.
      ln     → (mu, sigma)  en log naturel  [scipy lognorm: s=sigma, scale=exp(mu)]
      pareto → (alpha, x_min)               [scipy pareto:  b=alpha, scale=x_min]
    """
    try:
        from scipy.stats import lognorm as _lognorm, pareto as _spareto
    except ImportError:
        return None

    pos = np.array([v for v in values if v is not None and v > 0], dtype=float)
    if len(pos) < 10:
        return None

    results = {}
    # Log-normale MLE
    try:
        s, _, scale = _lognorm.fit(pos, floc=0)
        neg_ll = float(-np.sum(_lognorm.logpdf(pos, s=s, scale=scale)))
        results["ln"] = {"params": (math.log(scale), s), "aic": 4 + 2 * neg_ll}
    except Exception:
        pass
    # Pareto MLE (x_min fixé au minimum des données)
    try:
        x_min = float(np.min(pos))
        alpha = float(len(pos) / np.sum(np.log(pos / x_min)))
        alpha = max(alpha, 0.05)
        neg_ll = float(-np.sum(_spareto.logpdf(pos, b=alpha, scale=x_min)))
        if math.isfinite(neg_ll):
            results["pareto"] = {"params": (alpha, x_min), "aic": 4 + 2 * neg_ll}
    except Exception:
        pass

    if not results:
        return None
    best = min(results, key=lambda k: results[k]["aic"])
    return {"model": best, "params": results[best]["params"], "aic": results[best]["aic"]}


def _fit_best_mixture(values):
    """Compare LN+LN et LN+Pareto, retourne le meilleur modèle selon l'AIC.

    Retourne dict :
      'model'  : 'ln+ln' | 'ln+pareto'
      'params' : (lam,mu1,s1,mu2,s2)  ou  (lam,mu,s,alpha,x_min)
      'aic'    : float
      'all'    : dict modèle→{params, aic, neg_ll}
    ou None si les deux échouent.
    """
    try:
        from scipy.stats import lognorm as _lognorm, pareto as _spareto
    except ImportError:
        return None

    pos = np.array([v for v in values if v is not None and v > 0], dtype=float)
    if len(pos) < 20:
        return None

    results = {}

    fit_lnln = _fit_lognormal_mixture(values)
    if fit_lnln is not None:
        lam, mu1, s1, mu2, s2 = fit_lnln
        try:
            f1 = _lognorm.pdf(pos, s=s1, scale=np.exp(mu1))
            f2 = _lognorm.pdf(pos, s=s2, scale=np.exp(mu2))
            neg_ll = float(-np.sum(np.log(np.maximum(lam * f1 + (1 - lam) * f2, 1e-300))))
            results["ln+ln"] = {"params": fit_lnln, "neg_ll": neg_ll, "aic": 10 + 2 * neg_ll}
        except Exception:
            pass

    fit_lnp = _fit_lognormal_pareto(values)
    if fit_lnp is not None:
        lam, mu, s, alpha, x_min = fit_lnp
        try:
            f1 = _lognorm.pdf(pos, s=s, scale=np.exp(mu))
            f2 = _spareto.pdf(pos, b=alpha, scale=x_min)
            neg_ll = float(-np.sum(np.log(np.maximum(lam * f1 + (1 - lam) * f2, 1e-300))))
            results["ln+pareto"] = {"params": fit_lnp, "neg_ll": neg_ll, "aic": 10 + 2 * neg_ll}
        except Exception:
            pass

    if not results:
        return None
    best = min(results, key=lambda k: results[k]["aic"])
    return {"model": best, "params": results[best]["params"],
            "aic": results[best]["aic"], "all": results}


def _posterior_pop2(x_vals, model_type, params):
    """P(Pop.2 | x) = (1-λ)·f2(x) / (λ·f1(x) + (1-λ)·f2(x)).

    Formule de Bayes standard — non-monotone quand σ1 ≠ σ2.
    Utiliser _mixture_threshold pour une frontière de décision monotone.
    """
    try:
        from scipy.stats import lognorm as _lognorm, pareto as _spareto
    except ImportError:
        return np.full(len(x_vals), 0.5)

    x = np.asarray(x_vals, dtype=float)
    if model_type == "ln+ln":
        lam, mu1, s1, mu2, s2 = params
        f1 = _lognorm.pdf(x, s=s1, scale=np.exp(mu1))
        f2 = _lognorm.pdf(x, s=s2, scale=np.exp(mu2))
        denom = lam * f1 + (1 - lam) * f2
        return np.clip(np.where(denom > 1e-300, (1 - lam) * f2 / denom, 0.5), 0.0, 1.0)
    elif model_type == "ln+pareto":
        lam, mu, s, alpha, x_min = params
        f1 = _lognorm.pdf(x, s=s, scale=np.exp(mu))
        f2 = _spareto.pdf(x, b=alpha, scale=x_min)
        denom = lam * f1 + (1 - lam) * f2
        return np.clip(np.where(denom > 1e-300, (1 - lam) * f2 / denom, 0.0), 0.0, 1.0)
    return np.full(len(x), 0.5)


def _mixture_threshold(model_type, params) -> float:
    """Seuil x* entre les deux centres où λ·f1(x*) = (1-λ)·f2(x*).

    Classification monotone : Pop.1 si actif ≤ x*, Pop.2 si actif > x*.
    Évite les cas non-monotones du postérieur de Bayes quand σ1 ≪ σ2.
    """
    try:
        from scipy.stats import lognorm as _lognorm, pareto as _spareto
        from scipy.optimize import brentq as _brentq
    except ImportError:
        if model_type == "ln+ln":
            lam, mu1, s1, mu2, s2 = params
            return float(np.exp((mu1 + mu2) / 2))
        return float(params[4]) if model_type == "ln+pareto" else 1.0

    if model_type == "ln+ln":
        lam, mu1, s1, mu2, s2 = params
        score = lambda x: (lam * _lognorm.pdf(x, s=s1, scale=np.exp(mu1))
                           - (1 - lam) * _lognorm.pdf(x, s=s2, scale=np.exp(mu2)))
        lo, hi = float(np.exp(mu1)), float(np.exp(mu2))
        try:
            return float(_brentq(score, lo, hi))
        except ValueError:
            return float(np.exp((mu1 + mu2) / 2))

    elif model_type == "ln+pareto":
        lam, mu, s, alpha, x_min = params
        score = lambda x: (lam * _lognorm.pdf(x, s=s, scale=np.exp(mu))
                           - (1 - lam) * _spareto.pdf(x, b=alpha, scale=x_min))
        lo = float(np.exp(mu))
        hi = float(x_min * (1 + alpha) * 2)  # bien au-delà du mode de Pareto
        try:
            # Chercher un changement de signe dans [lo, hi]
            xs = np.logspace(np.log10(max(lo, x_min * 0.5)), np.log10(hi), 200)
            vals = np.array([score(x) for x in xs])
            idx = np.where(np.diff(np.sign(vals)))[0]
            if len(idx) > 0:
                return float(_brentq(score, xs[idx[0]], xs[idx[0] + 1]))
        except Exception:
            pass
        return float(x_min)

    return 1.0


def _linear_regression(xs, ys) -> Tuple[float, float]:
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.0, 0.0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def _weighted_linear_regression(xs, ys, weights) -> Tuple[float, float]:
    wsum = sum(weights)
    if wsum <= 0:
        return _linear_regression(xs, ys)
    mx = sum(w * x for w, x in zip(weights, xs)) / wsum
    my = sum(w * y for w, y in zip(weights, ys)) / wsum
    denom = sum(w * (x - mx) ** 2 for w, x in zip(weights, xs))
    if abs(denom) < 1e-12:
        return 0.0, my
    slope = sum(w * (x - mx) * (y - my) for w, x, y in zip(weights, xs, ys)) / denom
    intercept = my - slope * mx
    return slope, intercept


def _gini(values: List[float]) -> float:
    xs = sorted(v for v in values if math.isfinite(v) and v >= 0)
    n = len(xs)
    if n == 0:
        return 0.0
    total = sum(xs)
    if total <= 0:
        return 0.0
    weighted = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * weighted) / (n * total) - (n + 1) / n


def _rolling_mean(values: List[float], window: int) -> List[float]:
    result = []
    for i in range(len(values)):
        lo = max(0, i - window // 2)
        hi = min(len(values), i + window // 2 + 1)
        result.append(sum(values[lo:hi]) / (hi - lo))
    return result


def _select_plot_steps(all_steps: List[int], n_total: Optional[int] = None) -> List[int]:
    """Sélectionne les pas à afficher parmi FIXED_STEPS + mi-parcours + final."""
    if not all_steps:
        return []
    max_step = all_steps[-1]
    target = set(FIXED_STEPS)
    if n_total is not None:
        target.add(n_total // 2)
        target.add(n_total)
    target.add(max_step)  # always include final
    step_set = set(all_steps)
    selected = []
    for t in sorted(target):
        if t > max_step:
            continue
        # Find closest available step
        closest = min(all_steps, key=lambda s: abs(s - t))
        if closest not in selected:
            selected.append(closest)
    return sorted(selected)


# ============================================================
# 1. VUE MACRO
# ============================================================

def plot_macro_overview(folder: str, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    rows = read_csv(os.path.join(csv_dir, "indicateurs_systemiques.csv"))
    if not rows:
        print("  Pas d'indicateurs_systemiques.csv")
        return
    steps = [r["step"] for r in rows]
    actifs = [r["actif_total"] for r in rows]
    prets = [r["volume_prets"] for r in rows]
    entites = [r["nb_entites"] for r in rows]

    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()
    ax1.plot(steps, actifs, color="#1f77b4", linewidth=1.6, label="Actifs cumulés")
    ax1.plot(steps, prets, color="#9C27B0", linewidth=1.4, linestyle="--", label="Prêts cumulés")
    ax1.set_xlabel("Pas de simulation", fontsize=11)
    ax1.set_ylabel("Joules", fontsize=11)
    ax2.plot(steps, entites, color="#e67e22", linewidth=1.3, label="Entités vivantes")
    ax2.set_ylabel("Nombre d'entités vivantes", fontsize=11)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="upper left")
    title = "Actifs agrégés, prêts et population vivante"
    if title_extra:
        title += f" — {title_extra}"
    ax1.set_title(title, fontsize=12)
    ax1.grid(True, alpha=0.25)
    _save(fig, os.path.join(fig_dir, "macro_overview.png"))


# ============================================================
# 2. CASCADES : TAILLE (X) vs FRÉQUENCE (Y)
# ============================================================

def plot_cascades_rank_size(folder: str, title_extra: str = "", n_bins: int = 25):
    """
    Graphique taille-fréquence des cascades.

    Méthode statistique :
      - les points gris montrent la CCDF empirique brute P(X >= x);
      - les points rouges sont une densité log-binnée;
      - l'incertitude verticale vient du comptage Poisson sqrt(n_bin);
      - la régression est une régression log-log pondérée par n_bin.

    Cette lecture évite de donner le même poids aux bins pauvres qu'aux bins
    bien renseignés, ce qui était la principale faiblesse de l'ancienne figure.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    rows = read_csv(os.path.join(csv_dir, "tailles_cascades_brutes.csv"))
    if not rows:
        print("  Pas de données de cascade")
        return
    volumes_desc = sorted(
        [float(r["volume_joules"]) for r in rows if float(r["volume_joules"]) > 0],
        reverse=True,
    )
    n = len(volumes_desc)
    if n < 5:
        print("  Trop peu de cascades pour un graphique rang-taille")
        return

    volumes = sorted(volumes_desc)
    ccdf_x = volumes_desc
    ccdf_y = [(i + 1) / n for i in range(n)]

    vmin, vmax = min(volumes), max(volumes)
    log_min = math.log10(vmin)
    log_max = math.log10(vmax)
    if log_max <= log_min:
        return
    effective_bins = min(n_bins, max(4, int(math.sqrt(n)) * 2))
    bin_edges = [
        10 ** (log_min + i * (log_max - log_min) / effective_bins)
        for i in range(effective_bins + 1)
    ]

    binned_x, binned_y, yerr_low, yerr_high, counts = [], [], [], [], []
    for i in range(effective_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        in_bin = [v for v in volumes if lo <= v < hi or (i == effective_bins - 1 and lo <= v <= hi)]
        count = len(in_bin)
        if count == 0:
            continue
        width = hi - lo
        density = count / (n * width)
        sigma_count = math.sqrt(count)
        sigma_density = sigma_count / (n * width)
        x_rep = 10 ** (sum(math.log10(v) for v in in_bin) / count)
        binned_x.append(x_rep)
        binned_y.append(density)
        yerr_low.append(min(density * 0.95, sigma_density))
        yerr_high.append(sigma_density)
        counts.append(count)

    if len(binned_x) < 3:
        print("  Trop peu de bins non vides pour cascades_rank_size")
        return

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(ccdf_x, ccdf_y, s=10, alpha=0.18, color="gray", label="CCDF empirique brute")

    ax.errorbar(
        binned_x,
        binned_y,
        yerr=[yerr_low, yerr_high],
        fmt="o",
        markersize=5,
        linewidth=1.1,
        capsize=3,
        color="#d62728",
        ecolor="#d62728",
        alpha=0.9,
        label="Densité log-binnée ± sqrt(n_bin)",
    )
    for x, y, count in zip(binned_x, binned_y, counts):
        ax.annotate(str(count), (x, y), textcoords="offset points", xytext=(3, 4),
                    fontsize=7, alpha=0.7)

    # Ajustement sur les bins non triviaux, pondéré par le nombre de points.
    fit_points = [(x, y, c) for x, y, c in zip(binned_x, binned_y, counts) if c >= 2 and y > 0]
    if len(fit_points) < 3:
        fit_points = [(x, y, c) for x, y, c in zip(binned_x, binned_y, counts) if y > 0]
    log_fx = [math.log10(x) for x, _, _ in fit_points]
    log_vy = [math.log10(y) for _, y, _ in fit_points]
    weights = [c for _, _, c in fit_points]
    slope, intercept = _weighted_linear_regression(log_fx, log_vy, weights)
    fit_x = [min(x for x, _, _ in fit_points), max(x for x, _, _ in fit_points)]
    fit_y = [10 ** (intercept + slope * math.log10(x)) for x in fit_x]
    ax.plot(fit_x, fit_y, "k--", linewidth=1.2, alpha=0.8,
            label=f"Pente pondérée ≈ {slope:.2f}")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Taille de la cascade (joules)", fontsize=11)
    ax.set_ylabel("Densité log-binnée / CCDF brute", fontsize=11)
    title = "Cascades de faillite : taille, fréquence et incertitude"
    if title_extra:
        title += f"\n{title_extra}"
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.3)
    _save(fig, os.path.join(fig_dir, "cascades_rank_size.png"))


# ============================================================
# 3. HISTOGRAMMES DES TAILLES D'ENTITÉS — PAS FIXES, BÂTONS
# ============================================================

def plot_entity_size_histograms(folder: str, title_extra: str = ""):
    """
    Histogrammes en bâtons de la distribution des tailles d'entités aux pas fixes.
    X : actif total (log), Y : effectif.
    Un subplot par pas de temps.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    data = read_raw_distribution(csv_dir, "actif_total")
    if not data:
        print("  Pas de distribution brute pour actif_total")
        return

    all_steps = sorted(data.keys())
    max_step = all_steps[-1]
    selected = _select_plot_steps(all_steps, max_step)
    # Filter to steps with enough data
    selected = [s for s in selected if len([v for v in data[s] if v > 0]) >= 5]
    if not selected:
        return

    n = len(selected)
    ncols = min(n, 4)
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows), squeeze=False)

    cmap = plt.cm.viridis
    colors = [cmap(i / max(n - 1, 1)) for i in range(n)]

    for idx, (step, color) in enumerate(zip(selected, colors)):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]
        values = [v for v in data[step] if v > 0]
        if len(values) < 5:
            ax.set_visible(False)
            continue

        vmin, vmax = min(values), max(values)
        n_bins = min(20, max(5, len(values) // 3))
        log_min = math.log10(vmin)
        log_max = math.log10(vmax)
        if log_max <= log_min:
            ax.set_visible(False)
            continue

        edges = [10 ** (log_min + i * (log_max - log_min) / n_bins) for i in range(n_bins + 1)]
        counts = [0] * n_bins
        for v in values:
            idx_b = int((math.log10(v) - log_min) / (log_max - log_min) * n_bins)
            idx_b = max(0, min(n_bins - 1, idx_b))
            counts[idx_b] += 1

        # Vertical bars with log X axis: use Rectangle patches + count annotation
        centres_step = []
        count_max = max(counts) if max(counts) > 0 else 1
        for i in range(n_bins):
            centre = math.sqrt(edges[i] * edges[i + 1])
            centres_step.append(centre)
            if counts[i] > 0:
                rect = mpatches.Rectangle(
                    (edges[i], 0), edges[i + 1] - edges[i], counts[i],
                    facecolor=color, alpha=0.75, edgecolor="white", linewidth=0.5
                )
                ax.add_patch(rect)
                ax.text(centre, counts[i] + count_max * 0.025, str(counts[i]),
                        ha="center", va="bottom", fontsize=5.5, color="black",
                        clip_on=True)

        # Fit mélange (LN+LN ou LN+Pareto) et overlay du meilleur modèle
        fit_result = _fit_best_mixture(values)
        ylim_top = max(counts) * 1.3
        if fit_result is not None:
            try:
                from scipy.stats import lognorm as _lognorm, pareto as _spareto
                model_type = fit_result["model"]
                params = fit_result["params"]
                r2 = _mixture_r2_generic(centres_step, counts, edges, model_type, params)
                mean_dlog = (log_max - log_min) / n_bins
                scale = len(values) * math.log(10) * mean_dlog
                x_dense = np.logspace(log_min, log_max, 500)
                ln10 = math.log(10)
                r2_str = f"{r2:.3f}" if math.isfinite(r2) else "n/a"
                if model_type == "ln+ln":
                    lam, mu1, s1, mu2, s2 = params
                    y1 = lam * _lognorm.pdf(x_dense, s=s1, scale=np.exp(mu1)) * x_dense * scale
                    y2 = (1 - lam) * _lognorm.pdf(x_dense, s=s2, scale=np.exp(mu2)) * x_dense * scale
                    lbl1 = f"Pop.1 λ={lam:.2f} μ={mu1/ln10:.2f} σ={s1/ln10:.2f}"
                    lbl2 = f"Pop.2 λ={1-lam:.2f} μ={mu2/ln10:.2f} σ={s2/ln10:.2f}"
                else:  # ln+pareto
                    lam, mu, s, alpha, x_min = params
                    y1 = lam * _lognorm.pdf(x_dense, s=s, scale=np.exp(mu)) * x_dense * scale
                    y2 = (1 - lam) * _spareto.pdf(x_dense, b=alpha, scale=x_min) * x_dense * scale
                    lbl1 = f"Pop.1 λ={lam:.2f} μ={mu/ln10:.2f} σ={s/ln10:.2f}"
                    lbl2 = f"Pop.2 λ={1-lam:.2f} α={alpha:.2f} x_min={x_min:.1e}"
                model_tag = "LN+Par" if model_type == "ln+pareto" else "LN+LN"
                ax.fill_between(x_dense, y1, alpha=0.25, color="steelblue")
                ax.fill_between(x_dense, y2, alpha=0.25, color="tomato")
                ax.plot(x_dense, y1, color="steelblue", linewidth=1.1, alpha=0.8, label=lbl1)
                ax.plot(x_dense, y2, color="tomato", linewidth=1.1, alpha=0.8, label=lbl2)
                ax.plot([], [], " ", label=f"R²={r2_str} [{model_tag}]")
                ylim_top = max(max(counts) * 1.6, float(np.max(y1 + y2)) * 1.2)
                ax.legend(fontsize=6, loc="upper left")
            except Exception:
                pass

        ax.set_xlim(edges[0] * 0.9, edges[-1] * 1.1)
        ax.set_ylim(0, ylim_top)
        ax.set_xscale("log")
        ax.set_title(f"Pas {step} (n={len(values)})", fontsize=9)
        ax.set_xlabel("Actif total (J)", fontsize=8)
        ax.set_ylabel("Effectif", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, which="both", alpha=0.2)

    # Hide unused subplots
    for idx in range(n, nrows * ncols):
        row, col = divmod(idx, ncols)
        axes[row][col].set_visible(False)

    title = "Histogrammes des tailles d'entités"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12, y=1.01)
    fig.tight_layout()
    _save(fig, os.path.join(fig_dir, "entity_size_histos.png"))


# ============================================================
# 4. PUISSANCE EXTRACTRICE
# ============================================================

def plot_extraction_power(folder: str, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    meta = read_meta(folder)
    alpha = meta.get("config", {}).get("alpha", 1.0)

    passif_data = read_raw_distribution(csv_dir, "passif_total")
    if not passif_data:
        print("  Pas de distribution brute pour passif_total")
        return

    steps_sorted = sorted(passif_data.keys())
    steps_out, means, medians, maxs, q10s, q90s = [], [], [], [], [], []
    for step in steps_sorted:
        p_vals = sorted([v for v in passif_data[step] if v > 0])
        if not p_vals:
            continue
        pi_vals = sorted(alpha * math.sqrt(p) for p in p_vals)
        n = len(pi_vals)
        steps_out.append(step)
        means.append(sum(pi_vals) / n)
        medians.append(pi_vals[n // 2])
        maxs.append(pi_vals[-1])
        q10s.append(pi_vals[max(0, int(0.1 * n))])
        q90s.append(pi_vals[min(n - 1, int(0.9 * n))])
    if not steps_out:
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.fill_between(steps_out, q10s, q90s, alpha=0.15, color="#1f77b4", label="Q10–Q90")
    ax.plot(steps_out, medians, color="#1f77b4", linewidth=1.8, label="Médiane")
    ax.plot(steps_out, means,   color="#ff7f0e", linewidth=1.4, linestyle="--", label="Moyenne")
    ax.plot(steps_out, maxs,    color="#d62728", linewidth=1.0, linestyle=":",  label="Maximum")
    ax.plot(steps_out, q10s,    color="#2ca02c", linewidth=1.0, linestyle="-.", label="Q10")
    ax.plot(steps_out, q90s,    color="#9467bd", linewidth=1.0, linestyle="-.", label="Q90")
    ax.set_xlabel("Pas de simulation", fontsize=11)
    ax.set_ylabel(f"Puissance extractrice Π = α√P  (α = {alpha})", fontsize=11)
    title = "Puissance extractrice des entités"
    if title_extra:
        title += f" — {title_extra}"
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.25)
    _save(fig, os.path.join(fig_dir, "extraction_power.png"))


# ============================================================
# 5. DESTRUCTION DE CAPITAL + PUISSANCE D'EXTRACTION TOTALE
# ============================================================

def plot_destruction_moving_average(folder: str, window: int = 100, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    rows = read_csv(os.path.join(csv_dir, "indicateurs_systemiques.csv"))
    stats_rows = read_csv(os.path.join(csv_dir, "stats_legeres.csv"))
    if not rows:
        return

    steps = [r["step"] for r in rows]
    destroyed = [r.get("volume_faillites", 0.0) or 0.0 for r in rows]
    moving = _rolling_mean(destroyed, window)

    # Extraction totale depuis stats_legeres
    extr_by_step = {r["step"]: r.get("extraction_total", 0.0) or 0.0 for r in stats_rows}
    extraction = [extr_by_step.get(s, 0.0) for s in steps]
    extr_smooth = _rolling_mean(extraction, window)

    fig, ax = plt.subplots(figsize=(12, 5))
    # Extraction power total en bleu clair transparent (fond)
    ax.fill_between(steps, 0, extr_smooth, alpha=0.18, color="#4fc3f7",
                    label=f"Extraction totale (moy. {window})")
    ax.plot(steps, extr_smooth, linewidth=1.0, alpha=0.5, color="#0288d1")

    ax.plot(steps, destroyed, linewidth=0.8, alpha=0.25, color="#d62728", label="Destruction brute")
    ax.plot(steps, moving, linewidth=2.0, color="black", label=f"Destruction (moy. {window})")

    ax.set_xlabel("Pas de simulation", fontsize=11)
    ax.set_ylabel("Joules par pas", fontsize=11)
    title = "Destruction de capital vs puissance d'extraction"
    if title_extra:
        title += f" — {title_extra}"
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.25)
    _save(fig, os.path.join(fig_dir, "destruction_moving_avg.png"))


# ============================================================
# 6. DISTRIBUTION DES ACTIFS TOTAUX — LOG-LOG, AXES INVERSÉS
# ============================================================

def plot_actif_total_distribution(folder: str, title_extra: str = ""):
    """
    Histogrammes de la distribution de l'actif total aux pas fixes.
    Axes inversés : X = densité (log), Y = taille (log).
    Un subplot par pas de temps.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    data = read_raw_distribution(csv_dir, "actif_total")
    if not data:
        print("  Pas de distribution brute pour actif_total")
        return

    all_steps = sorted(data.keys())
    max_step = all_steps[-1]
    selected = _select_plot_steps(all_steps, max_step)
    selected = [s for s in selected if len([v for v in data[s] if v > 0]) >= 5]
    if not selected:
        return

    n = len(selected)
    ncols = min(n, 3)
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 5 * nrows), squeeze=False)

    cmap = plt.cm.plasma
    colors = [cmap(i / max(n - 1, 1)) for i in range(n)]

    for plot_idx, (step, color) in enumerate(zip(selected, colors)):
        row, col = divmod(plot_idx, ncols)
        ax = axes[row][col]
        values = [v for v in data[step] if v > 0]
        if len(values) < 5:
            ax.set_visible(False)
            continue

        vmin, vmax = min(values), max(values)
        n_bins = min(25, max(5, len(values) // 3))
        log_min = math.log10(vmin)
        log_max = math.log10(vmax)
        if log_max <= log_min:
            ax.set_visible(False)
            continue

        log_step = (log_max - log_min) / n_bins
        edges = [10 ** (log_min + i * log_step) for i in range(n_bins + 1)]
        counts = [0] * n_bins
        for v in values:
            idx_b = int((math.log10(v) - log_min) / log_step)
            idx_b = max(0, min(n_bins - 1, idx_b))
            counts[idx_b] += 1

        total = len(values)
        # density = count / (total * bin_width_linéaire)  — normalisation correcte
        centres = [math.sqrt(edges[i] * edges[i + 1]) for i in range(n_bins)]
        densities = []
        poisson_errors = []
        for i in range(n_bins):
            width = edges[i + 1] - edges[i]
            if total * width > 0 and counts[i] > 0:
                d = counts[i] / (total * width)
                e = math.sqrt(counts[i]) / (total * width)
            else:
                d, e = 0.0, 0.0
            densities.append(d)
            poisson_errors.append(e)

        # Horizontal bars: Y = taille (log), X = densité (log)
        valid = [(centres[i], edges[i], edges[i + 1], densities[i], counts[i], poisson_errors[i])
                 for i in range(n_bins) if densities[i] > 0]
        for (centre, e_lo, e_hi, dens, cnt, err) in valid:
            ax.fill_betweenx([e_lo, e_hi], 1e-300, dens, alpha=0.7, color=color)

        # Ligne de connexion des centres
        ctr_vals = [c for c, *_ in valid]
        dens_vals = [d for _, _, _, d, _, _ in valid]
        if len(ctr_vals) > 1:
            ax.plot(dens_vals, ctr_vals, color=color, linewidth=1.0, alpha=0.9)

        # Barres d'incertitude Poisson horizontales : xerr = sigma_density
        for (centre, e_lo, e_hi, dens, cnt, err) in valid:
            ax.errorbar(
                dens, centre, xerr=err,
                fmt="none", color="black", capsize=2, linewidth=0.8, alpha=0.6,
            )

        ax.set_yscale("log")
        ax.set_xscale("log")
        ax.set_ylabel("Actif total (J)", fontsize=8)
        ax.set_xlabel("Densité", fontsize=8)
        ax.set_title(f"Pas {step} (n={total})", fontsize=9)
        ax.tick_params(labelsize=7)
        ax.grid(True, which="both", alpha=0.2)

        # Zoom inset sur la queue haute (grands actifs — potentielle loi de puissance)
        if len(valid) >= 6:
            log_y_vals = [math.log10(c) for c, *_ in valid]
            y_thresh_log = min(log_y_vals) + 0.55 * (max(log_y_vals) - min(log_y_vals))
            tail_data = [(c, lo, hi, d, cnt, e) for c, lo, hi, d, cnt, e in valid
                         if math.log10(c) >= y_thresh_log]
            if len(tail_data) >= 3:
                tail_dens = [d for _, _, _, d, _, _ in tail_data]
                d_min = min(tail_dens) * 0.4
                d_max = max(tail_dens) * 2.5
                y_lo = 10 ** y_thresh_log * 0.9
                y_hi = max(hi for _, _, hi, *_ in tail_data) * 1.2
                axins = inset_axes(ax, width="48%", height="38%", loc="upper left")
                axins.set_xlim(d_min, d_max)
                axins.set_ylim(y_lo, y_hi)
                axins.set_xscale("log")
                axins.set_yscale("log")
                axins.tick_params(labelsize=6)
                axins.grid(True, which="both", alpha=0.2)
                for (c, lo, hi, d, cnt, e) in tail_data:
                    axins.fill_betweenx([lo, hi], 1e-300, d, alpha=0.7, color=color)
                    axins.errorbar(d, c, xerr=e, fmt="none", color="black",
                                   capsize=2, linewidth=0.8, alpha=0.6)
                try:
                    mark_inset(ax, axins, loc1=1, loc2=3, fc="none", ec="0.5", linewidth=0.8)
                except Exception:
                    pass

    for plot_idx in range(n, nrows * ncols):
        row, col = divmod(plot_idx, ncols)
        axes[row][col].set_visible(False)

    title = "Distribution des actifs totaux (log-log)"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12, y=1.01)
    fig.tight_layout()
    _save(fig, os.path.join(fig_dir, "actif_total_distribution.png"))


# ============================================================
# 7. ÉVOLUTION DU TAUX INTERNE MARGINAL r*
# ============================================================

def plot_internal_rate_evolution(folder: str, title_extra: str = ""):
    """
    Évolution de r* = α/(2√P) : max, min, moyenne, médiane, D1, D9.
    Lit les statistiques pré-calculées dans snapshots_distributions.csv.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    rows = read_csv(os.path.join(csv_dir, "snapshots_distributions.csv"))
    if not rows:
        print("  Pas de snapshots_distributions.csv")
        return
    taux_rows = sorted(
        [r for r in rows if r.get("name") == "taux_interne"],
        key=lambda r: r["step"]
    )
    if not taux_rows:
        print("  Pas de données taux_interne dans snapshots_distributions.csv")
        return

    steps   = [r["step"]   for r in taux_rows]
    means   = [r["mean"]   for r in taux_rows]
    medians = [r["median"] for r in taux_rows]
    maxs    = [r["max"]    for r in taux_rows]
    mins    = [r["min"]    for r in taux_rows]
    d1s     = [r["q10"]    for r in taux_rows]
    d9s     = [r["q90"]    for r in taux_rows]

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.fill_between(steps, d1s, d9s, alpha=0.15, color="#1f77b4", label="D1–D9")
    ax.plot(steps, medians, color="#1f77b4", linewidth=2.0, label="Médiane")
    ax.plot(steps, means,   color="#ff7f0e", linewidth=1.4, linestyle="--", label="Moyenne")
    ax.plot(steps, maxs,    color="#d62728", linewidth=1.0, linestyle=":",  label="Maximum")
    ax.plot(steps, mins,    color="#2ca02c", linewidth=1.0, linestyle=":",  label="Minimum")
    ax.plot(steps, d1s,     color="#9467bd", linewidth=1.0, linestyle="-.", label="D1 (10e pct)")
    ax.plot(steps, d9s,     color="#8c564b", linewidth=1.0, linestyle="-.", label="D9 (90e pct)")

    ax.set_xlabel("Pas de simulation", fontsize=11)
    ax.set_ylabel("Taux interne marginal r* = α/(2√P)", fontsize=11)
    title = "Évolution du taux interne marginal r*"
    if title_extra:
        title += f" — {title_extra}"
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.25)
    _save(fig, os.path.join(fig_dir, "internal_rate_evolution.png"))


# ============================================================
# 8. GINI ET DISTRIBUTIONS DES REVENUS
# ============================================================

def plot_gini_evolution(folder: str, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    rows = read_csv(os.path.join(csv_dir, "indicateurs_systemiques.csv"))
    if not rows:
        print("  Pas d'indicateurs_systemiques.csv pour Gini")
        return
    steps = [r["step"] for r in rows]
    series = [
        ("Capital / actif total", "gini_actif_total", "#1f77b4"),
        ("Revenu total", "gini_revenu_total", "#ff7f0e"),
    ]
    fig, ax = plt.subplots(figsize=(12, 5))
    for label, key, color in series:
        values = [r.get(key, 0.0) or 0.0 for r in rows]
        if any(v > 0 for v in values):
            ax.plot(steps, values, linewidth=1.5, color=color, label=label)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Pas de simulation", fontsize=11)
    ax.set_ylabel("Coefficient de Gini", fontsize=11)
    title = "Inégalités : capital et revenus"
    if title_extra:
        title += f" — {title_extra}"
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.25)
    _save(fig, os.path.join(fig_dir, "gini_evolution.png"))


def _lorenz_curve(values: List[float]) -> Tuple[List[float], List[float], float]:
    xs = sorted(v for v in values if isinstance(v, (int, float)) and math.isfinite(v) and v >= 0)
    if not xs or sum(xs) <= 0:
        return [], [], 0.0
    total = sum(xs)
    cum_pop = [0.0]
    cum_val = [0.0]
    running = 0.0
    n = len(xs)
    for i, value in enumerate(xs, start=1):
        running += value
        cum_pop.append(i / n)
        cum_val.append(running / total)
    return cum_pop, cum_val, _gini(xs)


def plot_gini_lorenz_snapshots(folder: str, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    datasets = [
        ("Capital / actif total", read_raw_distribution(csv_dir, "actif_total"), "#1f77b4"),
        ("Revenu total", read_raw_distribution(csv_dir, "revenu_total"), "#ff7f0e"),
    ]
    datasets = [(label, data, color) for label, data, color in datasets if data]
    if not datasets:
        print("  Pas de distributions brutes pour les courbes de Lorenz")
        return

    all_steps = sorted(set().union(*[set(data.keys()) for _, data, _ in datasets]))
    selected = _select_plot_steps(all_steps, all_steps[-1])
    selected = selected[-6:] if len(selected) > 6 else selected
    if not selected:
        return

    fig, axes = plt.subplots(len(selected), len(datasets), figsize=(5.2 * len(datasets), 3.6 * len(selected)), squeeze=False)
    for row_idx, step in enumerate(selected):
        for col_idx, (label, data, color) in enumerate(datasets):
            ax = axes[row_idx][col_idx]
            values = data.get(step, [])
            pop, share, gini = _lorenz_curve(values)
            ax.plot([0, 1], [0, 1], color="gray", linewidth=0.9, linestyle="--", alpha=0.55, label="Égalité parfaite")
            if pop:
                ax.plot(pop, share, color=color, linewidth=2.0, label=f"Gini = {gini:.3f}")
                ax.fill_between(pop, pop, share, color=color, alpha=0.12)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_title(f"{label} — pas {step}", fontsize=10)
            ax.set_xlabel("Part cumulée des entités", fontsize=9)
            ax.set_ylabel("Part cumulée de la grandeur", fontsize=9)
            ax.grid(True, alpha=0.25)
            ax.legend(fontsize=8, loc="upper left")

    title = "Courbes de Lorenz par snapshot"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12, y=1.01)
    fig.tight_layout()
    _save(fig, os.path.join(fig_dir, "gini_lorenz_snapshots.png"))


def plot_revenue_distributions(folder: str, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    candidates = [
        ("revenu_extraction", "Extraction naturelle", "#2ca02c"),
        ("revenu_interets", "Intérêts reçus", "#1f77b4"),
        ("charges_interets", "Intérêts payés", "#d62728"),
        ("revenu_total", "Revenu total brut", "#ff7f0e"),
        ("revenu_net", "Revenu net", "#9467bd"),
    ]
    raw = [(name, label, color, read_raw_distribution(csv_dir, name)) for name, label, color in candidates]
    raw = [(name, label, color, data) for name, label, color, data in raw if data]
    if not raw:
        print("  Pas de distributions de revenus")
        return

    all_steps = sorted(set().union(*[set(data.keys()) for _, _, _, data in raw]))
    selected = _select_plot_steps(all_steps, all_steps[-1])
    selected = selected[-4:] if len(selected) > 4 else selected
    if not selected:
        return

    n_rows = len(selected)
    fig, axes = plt.subplots(n_rows, 2, figsize=(30, 3.4 * n_rows), squeeze=False)

    for row_idx, step in enumerate(selected):
        ax_full = axes[row_idx][0]
        ax_zoom = axes[row_idx][1]

        all_values_step: list = []
        series_pts: list = []  # (centres, densities) par série pour calcul Y zoom

        for _, label, color, data in raw:
            values = [v for v in data.get(step, []) if v > 0]
            if len(values) < 5:
                continue
            centres, densities, _, bin_counts, _ = _adaptive_log_histogram(values)
            if not centres:
                continue

            all_values_step.extend(values)
            series_pts.append((centres, densities))
            median_count = int(sorted(bin_counts)[len(bin_counts) // 2])
            legend_label = f"{label}  (méd. {median_count} ind./bin)"

            for ax in (ax_full, ax_zoom):
                ax.plot(
                    centres, densities,
                    marker="o", markersize=3, linewidth=0.9,
                    alpha=0.85, color=color, label=legend_label,
                )

            # Fit LN vs Pareto sur cette série (distribution générale)
            fit_s = _fit_single_best(values)
            if fit_s is not None:
                try:
                    from scipy.stats import lognorm as _lnorm, pareto as _spar
                    x_d = np.logspace(math.log10(min(values)), math.log10(max(values)), 300)
                    if fit_s["model"] == "ln":
                        mu, sigma = fit_s["params"]
                        y_f = _lnorm.pdf(x_d, s=sigma, scale=math.exp(mu))
                        tag = f"LN μ={mu/math.log(10):.2f}"
                    else:
                        al, xm = fit_s["params"]
                        y_f = _spar.pdf(x_d, b=al, scale=xm)
                        tag = f"Par α={al:.2f}"
                    for ax in (ax_full, ax_zoom):
                        ax.plot(x_d, y_f, color=color, linewidth=1.1,
                                linestyle="--", alpha=0.6, label=f"  fit {tag}")
                except Exception:
                    pass

        # Plage X du zoom : P10–P100
        zoom_lo = zoom_hi = None
        if all_values_step:
            log_all = np.log10(all_values_step)
            zoom_lo = 10 ** float(np.percentile(log_all, 10))
            zoom_hi = float(np.max(10 ** log_all))

        # Plage Y du zoom : densités dans la fenêtre X
        zoom_y_lo = zoom_y_hi = None
        if zoom_lo is not None:
            dens_in_zoom = [d for (cs, ds) in series_pts
                            for c, d in zip(cs, ds) if zoom_lo <= c <= zoom_hi and d > 0]
            if dens_in_zoom:
                zoom_y_lo = min(dens_in_zoom) / 3.0
                zoom_y_hi = max(dens_in_zoom) * 3.0

        for ax, is_zoom in ((ax_full, False), (ax_zoom, True)):
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel("Flux (valeurs positives)", fontsize=9)
            ax.set_ylabel("Densité", fontsize=9)
            ax.grid(True, which="both", alpha=0.2)
            ax.legend(fontsize=7, ncols=1)
            if is_zoom and zoom_lo is not None and zoom_hi is not None and zoom_hi > zoom_lo:
                ax.set_xlim(zoom_lo, zoom_hi)
                if zoom_y_lo is not None:
                    ax.set_ylim(zoom_y_lo, zoom_y_hi)
                ax.set_title(f"Pas {step} — zoom P10–P100", fontsize=10)
            elif is_zoom:
                ax.set_visible(False)
            else:
                ax.set_title(f"Pas {step} — vue complète", fontsize=10)
                # Rectangle 2D délimitant la fenêtre de zoom (X et Y)
                if (zoom_lo is not None and zoom_hi is not None
                        and zoom_y_lo is not None and zoom_y_hi is not None
                        and zoom_hi > zoom_lo and zoom_y_hi > zoom_y_lo):
                    ax.fill_between(
                        [zoom_lo, zoom_hi], [zoom_y_lo, zoom_y_lo], [zoom_y_hi, zoom_y_hi],
                        alpha=0.10, color="#888888", zorder=0,
                    )
                    ax.plot(
                        [zoom_lo, zoom_hi, zoom_hi, zoom_lo, zoom_lo],
                        [zoom_y_lo, zoom_y_lo, zoom_y_hi, zoom_y_hi, zoom_y_lo],
                        color="#555555", linewidth=0.9, linestyle="--", alpha=0.6, zorder=1,
                    )

    title = "Distributions des revenus et charges financières"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12, y=1.01)
    fig.tight_layout()
    _save(fig, os.path.join(fig_dir, "revenue_distributions.png"))


# ============================================================
# 9. VIE DES ENTITÉS INDIVIDUELLES
# ============================================================

def _load_entity_histories(csv_dir: str) -> Dict[int, List[dict]]:
    """Charge entity_histories.csv et groupe par entity_id."""
    rows = read_csv(os.path.join(csv_dir, "entity_histories.csv"))
    if not rows:
        return {}
    histories = defaultdict(list)
    for r in rows:
        histories[int(r["entity_id"])].append(r)
    # Sort each entity's records by step
    for eid in histories:
        histories[eid].sort(key=lambda r: r["step"])
    return dict(histories)


def _select_entities_to_plot(histories: Dict[int, List[dict]]) -> List[int]:
    """
    Sélectionne les entités à tracer :
    - Entités initiales (creation_step == 0) : jusqu'à 5
    - Entité qui a eu le plus grand actif_total : 1
    - Entités nées pendant la simulation : jusqu'à 5 (espacées)
    """
    if not histories:
        return []

    initial = [eid for eid, recs in histories.items()
               if recs and recs[0].get("creation_step", 1) == 0][:5]

    # Largest ever
    max_actif = -1
    largest_eid = None
    for eid, recs in histories.items():
        m = max((r.get("actif_total", 0) or 0) for r in recs)
        if m > max_actif:
            max_actif = m
            largest_eid = eid

    born_during = sorted(
        [eid for eid, recs in histories.items()
         if recs and (recs[0].get("creation_step", 0) or 0) > 0 and eid != largest_eid],
        key=lambda eid: histories[eid][0].get("creation_step", 0)
    )
    # Pick 5 spread across the simulation
    if born_during:
        step = max(1, len(born_during) // 5)
        born_selected = [born_during[i] for i in range(0, len(born_during), step)][:5]
    else:
        born_selected = []

    selected = list(dict.fromkeys(
        initial + ([largest_eid] if largest_eid else []) + born_selected
    ))
    return selected[:12]


def _entity_series(recs: List[dict]) -> dict:
    al = [r.get("actif_liquide", 0) or 0 for r in recs]
    ap = [r.get("actif_prete", 0) or 0 for r in recs]
    ae = [r.get("actif_endoinvesti", 0) or 0 for r in recs]
    ax_ = [r.get("actif_exoinvesti", 0) or 0 for r in recs]
    pi_ = [r.get("passif_inne", 0) or 0 for r in recs]
    pe = [r.get("passif_endoinvesti", 0) or 0 for r in recs]
    px = [r.get("passif_exoinvesti", 0) or 0 for r in recs]
    pcd = [r.get("passif_credit_detenu", 0) or 0 for r in recs]
    extraction = [r.get("extraction", 0) or 0 for r in recs]
    interest_received = [r.get("interest_received", 0) or 0 for r in recs]
    interest_paid = [r.get("interest_paid", 0) or 0 for r in recs]
    depreciation = [r.get("depreciation", 0) or 0 for r in recs]
    actif_total = [r.get("actif_total", 0) or 0 for r in recs]
    passif_bilan = [
        (r.get("passif_total", 0) or 0) + (r.get("passif_credit_detenu", 0) or 0)
        for r in recs
    ]
    net_flux = [
        e + ir - ip - dep
        for e, ir, ip, dep in zip(extraction, interest_received, interest_paid, depreciation)
    ]
    return {
        "steps": [r["step"] for r in recs],
        "actifs": [al, ap, ae, ax_],
        "passifs": [pi_, pe, px, pcd],
        "extraction": extraction,
        "interest_received": interest_received,
        "interest_paid": interest_paid,
        "depreciation": depreciation,
        "actif_total": actif_total,
        "passif_bilan": passif_bilan,
        "net_flux": net_flux,
        "alpha": [r.get("alpha") for r in recs],
    }


def _add_system_background(ax, sys_steps, sys_actif, outward: float = 0.0):
    if not sys_steps or not sys_actif:
        return None
    ax_s = ax.twinx()
    if outward:
        ax_s.spines["right"].set_position(("axes", 1.0 + outward))
    ax_s.fill_between(sys_steps, 0, sys_actif, alpha=0.035, color="gray")
    ax_s.plot(sys_steps, sys_actif, color="lightgray", linewidth=0.55, alpha=0.38, linestyle="--")
    ax_s.set_ylabel("Actif système (J)", color="gray", fontsize=7)
    ax_s.tick_params(axis="y", labelcolor="gray", labelsize=6, pad=1)
    ax_s.grid(False)
    return ax_s


def _add_alpha_axis(ax, steps, alpha, *, color: str = "#ef9a9a", outward: float = 0.12, label_size: int = 8):
    values = [a for a in alpha if isinstance(a, (int, float)) and math.isfinite(a)]
    if not values:
        return None, None

    ymin, ymax = ax.get_ylim()
    if ymax <= ymin:
        return None, None
    zero_fraction = (0.0 - ymin) / (ymax - ymin)
    zero_fraction = min(0.92, max(0.08, zero_fraction))

    upper = max(max(values) * 1.08, 1e-9)
    lower = -upper * zero_fraction / (1.0 - zero_fraction)
    if min(values) < lower:
        lower = min(values) * 1.08

    ax_alpha = ax.twinx()
    ax_alpha.spines["right"].set_position(("axes", 1.0 + outward))
    ax_alpha.patch.set_visible(False)
    line, = ax_alpha.plot(
        steps,
        alpha,
        color=color,
        linewidth=1.8,
        linestyle="-",
        alpha=0.9,
        label="alpha",
    )
    ax_alpha.set_ylim(lower, upper)
    ax_alpha.axhline(0, color=color, linewidth=0.5, alpha=0.25)
    ax_alpha.set_ylabel("alpha", color=color, fontsize=label_size, labelpad=6)
    ax_alpha.tick_params(axis="y", labelcolor=color, labelsize=max(6, label_size - 1), pad=2)
    ax_alpha.grid(False)
    return ax_alpha, line


def _plot_entity_block(ax1, ax2, ax3, s: dict, sys_steps, sys_actif, *, show_legend: bool = False):
    steps = s["steps"]
    ax1.stackplot(
        steps, *s["actifs"],
        labels=["Liquide", "Prêté", "Endo-investi", "Exo-investi"],
        colors=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
        alpha=0.75,
    )
    ax1.set_ylabel("Actifs", fontsize=8)
    ax1.grid(True, alpha=0.18)
    _add_system_background(ax1, sys_steps, sys_actif)

    ax2.stackplot(
        steps, *s["passifs"],
        labels=["Inné", "Endo-investi", "Exo-investi", "Crédit détenu"],
        colors=["#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
        alpha=0.75,
    )
    ax2.set_ylabel("Passifs", fontsize=8)
    ax2.grid(True, alpha=0.18)
    _add_system_background(ax2, sys_steps, sys_actif)

    extr = s["extraction"]
    ir = s["interest_received"]
    ip = s["interest_paid"]
    dep = s["depreciation"]
    extr_plus_ir = [e + r for e, r in zip(extr, ir)]
    neg_ip = [-v for v in ip]
    neg_ip_dep = [-(a + b) for a, b in zip(ip, dep)]
    ax3.fill_between(steps, 0, extr, alpha=0.7, color="#2ca02c", label="Extraction")
    ax3.fill_between(steps, extr, extr_plus_ir, alpha=0.7, color="#1f77b4", label="Intérêts reçus")
    ax3.fill_between(steps, 0, neg_ip, alpha=0.7, color="#d62728", label="Intérêts payés")
    ax3.fill_between(steps, neg_ip, neg_ip_dep, alpha=0.7, color="#ff7f0e", label="Dépréciation")
    ax3.axhline(0, color="black", linewidth=0.8)
    ax3.set_ylabel("Flux", fontsize=8)
    ax3.set_xlabel("Pas", fontsize=8)
    ax3.grid(True, alpha=0.18)
    _add_system_background(ax3, sys_steps, sys_actif, outward=0.0)
    _, alpha_line = _add_alpha_axis(ax3, steps, s["alpha"], outward=0.14, label_size=7)

    if show_legend:
        ax1.legend(fontsize=6, loc="upper left")
        ax2.legend(fontsize=6, loc="upper left")
        handles, labels = ax3.get_legend_handles_labels()
        if alpha_line is not None:
            handles.append(alpha_line)
            labels.append("alpha")
        ax3.legend(handles, labels, fontsize=6, loc="upper left", ncol=2)


def plot_entity_lives_overview(folder: str, title_extra: str = ""):
    """
    Figure récapitulative: 10 entités, 5 colonnes × 2 lignes de blocs.
    Chaque bloc reprend la structure des figures individuelles : actifs, passifs, flux + alpha.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    histories = _load_entity_histories(csv_dir)
    if not histories:
        print("  Pas d'entity_histories.csv pour la figure récapitulative")
        return
    entity_ids = _select_entities_to_plot(histories)[:10]
    if not entity_ids:
        return
    series_by_id = {eid: _entity_series(histories[eid]) for eid in entity_ids}
    sys_rows = read_csv(os.path.join(csv_dir, "indicateurs_systemiques.csv"))
    sys_steps = [r["step"] for r in sys_rows]
    sys_actif = [r.get("actif_total", 0) or 0 for r in sys_rows]

    max_actifs = max(max(sum(values) for values in zip(*s["actifs"])) for s in series_by_id.values())
    max_passifs = max(max(sum(values) for values in zip(*s["passifs"])) for s in series_by_id.values())
    max_flux_pos = max(
        max([e + ir for e, ir in zip(s["extraction"], s["interest_received"])] or [0])
        for s in series_by_id.values()
    )
    max_flux_neg = min(
        min([-(ip + dep) for ip, dep in zip(s["interest_paid"], s["depreciation"])] or [0])
        for s in series_by_id.values()
    )
    max_step = max(max(s["steps"]) for s in series_by_id.values() if s["steps"])

    fig = plt.figure(figsize=(25, 14), constrained_layout=True)
    outer = fig.add_gridspec(2, 5, wspace=0.42, hspace=0.34)
    for idx, eid in enumerate(entity_ids):
        outer_cell = outer[idx // 5, idx % 5]
        inner = outer_cell.subgridspec(3, 1, hspace=0.12)
        ax1 = fig.add_subplot(inner[0, 0])
        ax2 = fig.add_subplot(inner[1, 0], sharex=ax1)
        ax3 = fig.add_subplot(inner[2, 0], sharex=ax1)
        s = series_by_id[eid]
        _plot_entity_block(ax1, ax2, ax3, s, sys_steps, sys_actif, show_legend=(idx == 0))
        ax1.set_title(f"Entité {eid}", fontsize=9, pad=4)
        ax1.set_ylim(0, max_actifs * 1.05 if max_actifs > 0 else 1)
        ax2.set_ylim(0, max_passifs * 1.05 if max_passifs > 0 else 1)
        ax3.set_ylim(max_flux_neg * 1.15 if max_flux_neg < 0 else -1, max_flux_pos * 1.15 if max_flux_pos > 0 else 1)
        ax3.set_xlim(0, max_step)
        ax1.tick_params(labelbottom=False, labelsize=6)
        ax2.tick_params(labelbottom=False, labelsize=6)
        ax3.tick_params(labelsize=6)

    title = "Vie comparée de 10 entités suivies"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=13)
    _save(fig, os.path.join(fig_dir, "entity_lives_overview.png"))


def plot_entity_lives(folder: str, title_extra: str = ""):
    """
    Pour chaque entité sélectionnée, crée une figure avec 3 sous-graphiques :
      1. Actifs (stacked area)
      2. Passifs (stacked area)
      3. Flux (extraction, intérêts reçus/payés, dépréciation)
    Axe secondaire (gris transparent) : actif total du système.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    detail_dir = os.path.join(fig_dir, "detail_vie_entites")
    os.makedirs(detail_dir, exist_ok=True)
    histories = _load_entity_histories(csv_dir)
    if not histories:
        print("  Pas d'entity_histories.csv")
        return

    # Load system total for secondary axis
    sys_rows = read_csv(os.path.join(csv_dir, "indicateurs_systemiques.csv"))
    sys_steps = [r["step"] for r in sys_rows]
    sys_actif = [r.get("actif_total", 0) or 0 for r in sys_rows]

    entity_ids = _select_entities_to_plot(histories)
    print(f"  Génération de {len(entity_ids)} figures d'entités individuelles...")

    for eid in entity_ids:
        recs = histories[eid]
        if len(recs) < 2:
            continue

        steps = [r["step"] for r in recs]
        creation = recs[0].get("creation_step", steps[0])

        # Actifs
        al    = [r.get("actif_liquide", 0) or 0      for r in recs]
        ap    = [r.get("actif_prete", 0) or 0         for r in recs]
        ae    = [r.get("actif_endoinvesti", 0) or 0   for r in recs]
        ax_   = [r.get("actif_exoinvesti", 0) or 0    for r in recs]

        # Passifs
        pi_   = [r.get("passif_inne", 0) or 0              for r in recs]
        pe    = [r.get("passif_endoinvesti", 0) or 0       for r in recs]
        px    = [r.get("passif_exoinvesti", 0) or 0        for r in recs]
        pcd   = [r.get("passif_credit_detenu", 0) or 0     for r in recs]

        # Flux
        extr  = [r.get("extraction", 0) or 0           for r in recs]
        ir    = [r.get("interest_received", 0) or 0    for r in recs]
        ip    = [r.get("interest_paid", 0) or 0        for r in recs]
        dep   = [r.get("depreciation", 0) or 0         for r in recs]
        alpha = [r.get("alpha") for r in recs]

        alive_flag = [bool(r.get("alive", 1)) for r in recs]
        death_step = None
        for i, a in enumerate(alive_flag):
            if not a:
                death_step = steps[i]
                break

        fig, axes = plt.subplots(3, 1, figsize=(13, 13), sharex=True)
        ax1, ax2, ax3 = axes

        # 1 — Actifs (stacked area)
        ax1.stackplot(steps, al, ap, ae, ax_,
                      labels=["Liquide", "Prêté", "Endo-investi", "Exo-investi"],
                      colors=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
                      alpha=0.75)
        ax1.set_ylabel("Actifs (J)", fontsize=10)
        ax1.legend(fontsize=8, loc="upper left")
        ax1.grid(True, alpha=0.2)
        _add_system_background(ax1, sys_steps, sys_actif)

        # 2 — Passifs (stacked area)
        ax2.stackplot(steps, pi_, pe, px, pcd,
                      labels=["Inné", "Endo-investi", "Exo-investi", "Crédit détenu"],
                      colors=["#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
                      alpha=0.75)
        ax2.set_ylabel("Passifs (J)", fontsize=10)
        ax2.legend(fontsize=8, loc="upper left")
        ax2.grid(True, alpha=0.2)
        _add_system_background(ax2, sys_steps, sys_actif)

        # 3 — Flux
        # Positifs : extraction + intérêts reçus
        extr_plus_ir = [e + r for e, r in zip(extr, ir)]
        ax3.fill_between(steps, 0, extr, alpha=0.7, color="#2ca02c", label="Extraction")
        ax3.fill_between(steps, extr, extr_plus_ir, alpha=0.7, color="#1f77b4",
                         label="Intérêts reçus")
        # Négatifs : intérêts payés + dépréciation
        neg_ip = [-v for v in ip]
        neg_ip_dep = [-(a + b) for a, b in zip(ip, dep)]
        ax3.fill_between(steps, 0, neg_ip, alpha=0.7, color="#d62728", label="Intérêts payés")
        ax3.fill_between(steps, neg_ip, neg_ip_dep, alpha=0.7, color="#ff7f0e",
                         label="Dépréciation (érosion)")
        ax3.axhline(0, color="black", linewidth=0.8)
        ax3.set_ylabel("Flux (J/snapshot)", fontsize=10)
        ax3.set_xlabel("Pas de simulation", fontsize=10)
        ax3.grid(True, alpha=0.2)
        _add_system_background(ax3, sys_steps, sys_actif, outward=0.0)
        _, alpha_line = _add_alpha_axis(ax3, steps, alpha, outward=0.14, label_size=8)
        handles, labels = ax3.get_legend_handles_labels()
        if alpha_line is not None:
            handles.append(alpha_line)
            labels.append("alpha")
        ax3.legend(handles, labels, fontsize=8, loc="upper left", ncol=2)

        # Ligne de mort
        if death_step is not None:
            for ax in axes:
                ax.axvline(death_step, color="black", linewidth=1.5, linestyle=":", alpha=0.7)

        label_type = ""
        if creation == 0:
            label_type = " [initiale]"
        title = f"Entité {eid} (née au pas {creation}){label_type}"
        if title_extra:
            title += f" — {title_extra}"
        fig.suptitle(title, fontsize=12)
        fig.tight_layout(rect=[0, 0, 0.92, 0.97])
        _save(fig, os.path.join(detail_dir, f"entity_{eid}.png"))


# ============================================================
# 9. ESPÉRANCE DE VIE VS TAILLE / ENDETTEMENT
# ============================================================

def plot_lifespan_analysis(folder: str, title_extra: str = ""):
    """
    Espérance de vie des entités surveillées en fonction de leur taille moyenne
    et de leur levier moyen. Le passif brut seul est volontairement omis.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    histories = _load_entity_histories(csv_dir)
    meta_rows = read_csv(os.path.join(csv_dir, "entity_meta.csv"))
    if not histories or not meta_rows:
        print("  Pas de données suffisantes pour l'analyse des durées de vie")
        return

    # Build per-entity summary
    meta_by_id = {r["entity_id"]: r for r in meta_rows}
    records = []
    for eid, recs in histories.items():
        if len(recs) < 3:
            continue
        meta = meta_by_id.get(eid, {})
        creation = meta.get("creation_step") or recs[0].get("creation_step", 0) or 0
        death = meta.get("death_step")
        still_alive = bool(meta.get("still_alive", 1))
        if death is None:
            if still_alive:
                last_step = recs[-1]["step"]
                lifespan = last_step - creation
                censored = True
            else:
                lifespan = recs[-1]["step"] - creation
                censored = False
        else:
            lifespan = death - creation
            censored = False

        if lifespan <= 0:
            continue

        actif_vals   = [r.get("actif_total", 0) or 0 for r in recs if r.get("alive", 1)]
        passif_vals  = [r.get("passif_total", 0) or 0 for r in recs if r.get("alive", 1)]
        if not actif_vals:
            continue

        mean_actif  = sum(actif_vals) / len(actif_vals)
        mean_passif = sum(passif_vals) / len(passif_vals) if passif_vals else 0
        mean_levier = mean_passif / mean_actif if mean_actif > 0 else 0

        records.append({
            "eid": eid,
            "lifespan": lifespan,
            "mean_actif": mean_actif,
            "mean_passif": mean_passif,
            "mean_levier": mean_levier,
            "censored": censored,
        })

    if len(records) < 5:
        print("  Trop peu d'entités pour l'analyse des durées de vie")
        return

    lifespans    = [r["lifespan"]    for r in records]
    mean_actifs  = [r["mean_actif"]  for r in records]
    mean_leviers = [r["mean_levier"] for r in records]
    censored     = [r["censored"]    for r in records]

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    def scatter_plot(ax, x_vals, xlabel, log_x=True):
        dead_x   = [x for x, c in zip(x_vals, censored) if not c and x > 0]
        dead_y   = [y for y, x, c in zip(lifespans, x_vals, censored) if not c and x > 0]
        alive_x  = [x for x, c in zip(x_vals, censored) if c and x > 0]
        alive_y  = [y for y, x, c in zip(lifespans, x_vals, censored) if c and x > 0]
        ax.scatter(dead_x, dead_y, s=18, alpha=0.6, color="#d62728", label="Décédée")
        ax.scatter(alive_x, alive_y, s=18, alpha=0.6, color="#2ca02c", marker="^",
                   label="Survivante")
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel("Durée de vie (pas)", fontsize=10)
        if log_x and all(v > 0 for v in x_vals):
            ax.set_xscale("log")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.25)

    scatter_plot(axes[0], mean_actifs, "Actif total moyen (J)")
    scatter_plot(axes[1], mean_leviers, "Levier moyen P/A", log_x=False)

    title = "Espérance de vie des entités"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    _save(fig, os.path.join(fig_dir, "lifespan_analysis.png"))


# ============================================================
# 11. RÉSEAU FINAL DES PRÊTS
# ============================================================

def plot_loan_network_final(folder: str, title_extra: str = "", max_nodes: int = 180, max_edges: int = 500):
    """
    Représente le réseau final des prêts actifs.

    Optimisation volontaire:
      - seules les arêtes les plus importantes par flux d'intérêt sont affichées;
      - les nœuds isolés hors de ces arêtes ne sont pas dessinés;
      - la figure est un snapshot final, pas une animation temporelle.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    entity_rows = read_csv(os.path.join(csv_dir, "entity_final_state.csv"))
    loan_rows = read_csv(os.path.join(csv_dir, "loan_network_final.csv"))
    if not entity_rows or not loan_rows:
        print("  Pas de données suffisantes pour loan_network_final")
        return

    entities = {int(r["entity_id"]): r for r in entity_rows if int(r.get("alive", 0) or 0) == 1}
    loans = sorted(
        [r for r in loan_rows if (r.get("interest_flow", 0) or 0) > 0],
        key=lambda r: r.get("interest_flow", 0) or 0,
        reverse=True,
    )
    if not loans:
        print("  Aucun prêt actif avec intérêt positif")
        return

    selected_edges = []
    selected_nodes = set()
    for loan in loans:
        lender = int(loan["lender_id"])
        borrower = int(loan["borrower_id"])
        if lender not in entities or borrower not in entities:
            continue
        if len(selected_edges) >= max_edges:
            break
        if len(selected_nodes | {lender, borrower}) > max_nodes:
            continue
        selected_edges.append((lender, borrower, loan))
        selected_nodes.update([lender, borrower])
    if len(selected_edges) < 2:
        print("  Trop peu d'arêtes pour loan_network_final")
        return

    node_list = sorted(selected_nodes)
    try:
        import networkx as nx
        graph = nx.DiGraph()
        graph.add_nodes_from(node_list)
        for lender, borrower, loan in selected_edges:
            graph.add_edge(borrower, lender, weight=loan.get("interest_flow", 0) or 0)
        positions = nx.spring_layout(graph, seed=42, weight="weight", iterations=80)
    except Exception:
        positions = {}
        for i, node in enumerate(node_list):
            angle = 2 * math.pi * i / len(node_list)
            positions[node] = (math.cos(angle), math.sin(angle))

    actif_values = [entities[n].get("actif_total", 0) or 0 for n in node_list]
    net_interest = [
        (entities[n].get("revenus_interets", 0) or 0) - (entities[n].get("charges_interets", 0) or 0)
        for n in node_list
    ]
    max_actif = max(actif_values) if actif_values else 1.0
    max_abs_net = max(abs(v) for v in net_interest) if net_interest else 1.0
    max_abs_net = max(max_abs_net, 1e-9)
    flows = [edge[2].get("interest_flow", 0) or 0 for edge in selected_edges]
    max_flow = max(flows) if flows else 1.0

    fig, ax = plt.subplots(figsize=(14, 11))
    ax.set_facecolor("#fbf7ef")

    for lender, borrower, loan in selected_edges:
        # Flux économique d'intérêts : l'emprunteur paie le prêteur.
        x1, y1 = positions[borrower]
        x2, y2 = positions[lender]
        xm, ym = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        flow = loan.get("interest_flow", 0) or 0
        width = 0.25 + 3.5 * math.sqrt(flow / max_flow)
        alpha = 0.08 + 0.32 * math.sqrt(flow / max_flow)
        ax.annotate(
            "",
            xy=(xm, ym),
            xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle="->",
                color="#2b6cb0",
                lw=width,
                alpha=alpha,
                shrinkA=6,
                shrinkB=1,
                mutation_scale=7,
            ),
        )
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(xm, ym),
            arrowprops=dict(
                arrowstyle="->",
                color="#c53030",
                lw=width,
                alpha=alpha,
                shrinkA=1,
                shrinkB=6,
                mutation_scale=8,
            ),
        )

    xs = [positions[n][0] for n in node_list]
    ys = [positions[n][1] for n in node_list]
    sizes = [35 + 520 * math.sqrt((entities[n].get("actif_total", 0) or 0) / max_actif) for n in node_list]
    colors = [
        ((entities[n].get("revenus_interets", 0) or 0) - (entities[n].get("charges_interets", 0) or 0)) / max_abs_net
        for n in node_list
    ]
    nodes = ax.scatter(
        xs,
        ys,
        s=sizes,
        c=colors,
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
        edgecolors="white",
        linewidths=0.7,
        alpha=0.9,
        zorder=3,
    )
    cbar = fig.colorbar(nodes, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Solde intérêts reçu - payé (normalisé)", fontsize=9)
    ax.legend(
        handles=[
            plt.Line2D([0], [0], color="#2b6cb0", lw=2, label="Flux sortant"),
            plt.Line2D([0], [0], color="#c53030", lw=2, label="Flux entrant"),
        ],
        loc="upper right",
        fontsize=9,
        frameon=True,
    )

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"Réseau final des prêts actifs: {len(node_list)} entités, {len(selected_edges)} arêtes principales",
        fontsize=12,
    )
    if title_extra:
        fig.suptitle(title_extra, fontsize=10, y=0.98)
    ax.text(
        0.01,
        0.01,
        "Taille des cercles: actif total. Épaisseur: intérêts versés par pas. Sens: emprunteur → prêteur. Bleu: flux sortant, rouge: flux entrant.",
        transform=ax.transAxes,
        fontsize=9,
        color="#66757f",
    )
    _save(fig, os.path.join(fig_dir, "loan_network_final.png"))


# ============================================================
# ANALYSE PAR CLASSE (Pop.1 / Pop.2)
# ============================================================

def _plot_class_revenue_series(class_dir: str, step_data: dict,
                               var_label: str, fname: str, title_extra: str = ""):
    """Distributions d'une variable par classe, layout 4×2 (full + zoom).

    step_data : {step: {'pop1': [valeurs+], 'pop2': [valeurs+]}}
    Miroir de plot_revenue_distributions mais avec Pop.1/Pop.2 comme séries.
    """
    all_steps = sorted(step_data)
    # Garder au plus 4 pas représentatifs
    selected = _select_plot_steps(all_steps, all_steps[-1])
    selected = selected[-4:] if len(selected) > 4 else selected
    selected = [s for s in selected
                if len(step_data[s].get("pop1", [])) + len(step_data[s].get("pop2", [])) >= 3]
    if not selected:
        return

    n_rows = len(selected)
    fig, axes = plt.subplots(n_rows, 2, figsize=(30, 3.4 * n_rows), squeeze=False)

    CLASS_STYLES = [
        ("pop1", "Pop.1 (petites)", "steelblue"),
        ("pop2", "Pop.2 (grandes)", "tomato"),
    ]

    for row_idx, step in enumerate(selected):
        ax_full = axes[row_idx][0]
        ax_zoom = axes[row_idx][1]

        all_values_step: list = []
        series_pts: list = []

        for cls_key, cls_label, color in CLASS_STYLES:
            values = [v for v in step_data[step].get(cls_key, []) if v is not None and v > 0]
            if len(values) < 5:
                continue
            result = _adaptive_log_histogram(values)
            centres, densities = result[0], result[1]
            if not centres:
                continue
            bin_counts = result[3]
            median_count = int(sorted(bin_counts)[len(bin_counts) // 2])
            legend_label = f"{cls_label}  n={len(values)}  (méd. {median_count}/bin)"
            all_values_step.extend(values)
            series_pts.append((centres, densities))
            for ax in (ax_full, ax_zoom):
                ax.plot(centres, densities,
                        marker="o", markersize=3, linewidth=0.9,
                        alpha=0.85, color=color, label=legend_label)

            # Fit LN vs Pareto sur la distribution de cette classe
            fit_s = _fit_single_best(values)
            if fit_s is not None:
                try:
                    from scipy.stats import lognorm as _lnorm, pareto as _spar
                    log_min = math.log10(min(values))
                    log_max = math.log10(max(values))
                    x_d = np.logspace(log_min, log_max, 300)
                    if fit_s["model"] == "ln":
                        mu, sigma = fit_s["params"]
                        y_fit = _lnorm.pdf(x_d, s=sigma, scale=math.exp(mu))
                        tag = f"LN μ={mu/math.log(10):.2f}"
                    else:
                        alpha, x_min = fit_s["params"]
                        y_fit = _spar.pdf(x_d, b=alpha, scale=x_min)
                        tag = f"Par α={alpha:.2f}"
                    for ax in (ax_full, ax_zoom):
                        ax.plot(x_d, y_fit, color=color, linewidth=1.2,
                                linestyle="--", alpha=0.7, label=f"  fit {tag}")
                except Exception:
                    pass

        zoom_lo = zoom_hi = zoom_y_lo = zoom_y_hi = None
        if all_values_step:
            log_all = np.log10(all_values_step)
            zoom_lo = 10 ** float(np.percentile(log_all, 10))
            zoom_hi = float(np.max(10 ** log_all))
            dens_in_zoom = [d for (cs, ds) in series_pts
                            for c, d in zip(cs, ds) if zoom_lo <= c <= zoom_hi and d > 0]
            if dens_in_zoom:
                zoom_y_lo = min(dens_in_zoom) / 3.0
                zoom_y_hi = max(dens_in_zoom) * 3.0

        for ax, is_zoom in ((ax_full, False), (ax_zoom, True)):
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel("Flux (J/pas)", fontsize=9)
            ax.set_ylabel("Densité", fontsize=9)
            ax.grid(True, which="both", alpha=0.2)
            ax.legend(fontsize=7)
            if is_zoom:
                if zoom_lo is not None and zoom_hi is not None and zoom_hi > zoom_lo:
                    ax.set_xlim(zoom_lo, zoom_hi)
                    if zoom_y_lo is not None:
                        ax.set_ylim(zoom_y_lo, zoom_y_hi)
                    ax.set_title(f"Pas {step} — zoom P10–P100", fontsize=10)
                else:
                    ax.set_visible(False)
            else:
                ax.set_title(f"Pas {step} — vue complète", fontsize=10)
                if (zoom_lo is not None and zoom_hi is not None
                        and zoom_y_lo is not None and zoom_y_hi is not None
                        and zoom_hi > zoom_lo and zoom_y_hi > zoom_y_lo):
                    ax.fill_between([zoom_lo, zoom_hi],
                                    [zoom_y_lo, zoom_y_lo], [zoom_y_hi, zoom_y_hi],
                                    alpha=0.10, color="#888888", zorder=0)
                    ax.plot([zoom_lo, zoom_hi, zoom_hi, zoom_lo, zoom_lo],
                            [zoom_y_lo, zoom_y_lo, zoom_y_hi, zoom_y_hi, zoom_y_lo],
                            color="#555555", linewidth=0.9, linestyle="--", alpha=0.6, zorder=1)

    ttl = f"{var_label} par classe"
    if title_extra:
        ttl += f" — {title_extra}"
    fig.suptitle(ttl, fontsize=12, y=1.01)
    fig.tight_layout()
    _save(fig, os.path.join(class_dir, fname))

def plot_entity_class_analysis(folder: str, title_extra: str = ""):
    """Graphiques stratifiés par classe d'entité (Pop.1 / Pop.2).

    Nécessite entity_final_state.csv + loan_network_final.csv + entity_histories.csv.
    Sauvegarde dans figures/analyse_par_classe/.
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    class_dir = os.path.join(fig_dir, "analyse_par_classe")
    os.makedirs(class_dir, exist_ok=True)

    # ── 1. Charger final state et classifier ──────────────────────────────────
    final_rows = read_csv(os.path.join(csv_dir, "entity_final_state.csv"))
    if not final_rows:
        print("  [classe] entity_final_state.csv absent, abandon.")
        return

    # Entités vivantes uniquement — fit et classification
    alive_rows = [e for e in final_rows
                  if e.get("alive") == 1 or e.get("alive") is True]
    if len(alive_rows) < 20:
        alive_rows = final_rows  # fallback si simulation très courte

    actif_vals = [e["actif_total"] for e in alive_rows
                  if e.get("actif_total") is not None and (e["actif_total"] or 0) > 0]
    if len(actif_vals) < 20:
        print("  [classe] pas assez d'entités pour le fit, abandon.")
        return

    fit_result = _fit_best_mixture(actif_vals)
    if fit_result is None:
        print("  [classe] fit de mélange échoué, abandon.")
        return

    model_type = fit_result["model"]
    params = fit_result["params"]
    all_aic = fit_result.get("all", {})
    delta_aic = ""
    if len(all_aic) == 2:
        aics = sorted(all_aic.items(), key=lambda kv: kv[1]["aic"])
        delta_aic = f"  ΔAIC={aics[1][1]['aic'] - aics[0][1]['aic']:.1f} en faveur de {aics[0][0]}"

    # Seuil monotone : x* où λ·f1(x*) = (1-λ)·f2(x*), entre les deux centres.
    # Pop.1 si actif ≤ x*, Pop.2 si actif > x*.
    threshold = _mixture_threshold(model_type, params)

    actif_arr = np.array([e.get("actif_total", 0) or 0 for e in alive_rows], dtype=float)
    post2 = _posterior_pop2(actif_arr, model_type, params)

    # Dictionnaire entity_id → attributs classifiés (vivantes uniquement)
    entity_info: dict = {}
    for i, e in enumerate(alive_rows):
        eid = e.get("entity_id")
        if eid is None:
            continue
        rev = e.get("revenus_interets") or 0
        chg = e.get("charges_interets") or 0
        passif_cd = e.get("passif_credit_detenu") or 0
        actif = e.get("actif_total") or 0
        entity_info[eid] = {
            "post2": float(post2[i]),
            "is_pop2": bool(actif > threshold),   # monotone : Pop.2 si actif > seuil
            "actif": actif,
            "rev_int": rev,
            "chg_int": chg,
            "net_int": rev - chg,
            "passif_cd": passif_cd,
            "levier": passif_cd / actif if actif > 0 else 0.0,
        }

    pop1 = {eid: d for eid, d in entity_info.items() if not d["is_pop2"]}
    pop2 = {eid: d for eid, d in entity_info.items() if d["is_pop2"]}
    n1, n2 = len(pop1), len(pop2)
    print(f"  [classe] {model_type}{delta_aic}  |  seuil={threshold:.2e} J  |  Pop.1={n1}  Pop.2={n2}")

    # ── 2b. Distributions de revenus par classe — distrib_brute (toutes entités) ──
    # Les fichiers distrib_brute_*.csv ont le même ordre positionnel à chaque pas :
    # position i dans actif_total = position i dans revenu_extraction, etc.
    # On classifie par seuil sur actif_total puis on splitte chaque autre variable.
    # Résultat : 600+ entités par pas au lieu des ~65 entités suivies survivantes.
    actif_dist = read_raw_distribution(csv_dir, "actif_total")
    if actif_dist:
        all_steps_dist = sorted(actif_dist)
        sel_dist = _select_plot_steps(all_steps_dist, all_steps_dist[-1])
        sel_dist = sel_dist[-4:] if len(sel_dist) > 4 else sel_dist

        brute_vars = [
            ("revenu_extraction",  "Extraction naturelle"),
            ("revenu_interets",    "Intérêts reçus"),
            ("charges_interets",   "Intérêts payés"),
            ("revenu_net",         "Revenu net (extraction + intérêts reçus)"),
        ]
        # Pour chaque variable : construire {step: {pop1: [...], pop2: [...]}}
        for brute_name, label in brute_vars:
            rev_dist = read_raw_distribution(csv_dir, brute_name)
            if not rev_dist:
                continue
            step_data_brute: dict = {}
            for s in sel_dist:
                actif_step = actif_dist.get(s, [])
                rev_step   = rev_dist.get(s, [])
                if len(actif_step) != len(rev_step) or not actif_step:
                    continue
                pop1_vals = [rv for av, rv in zip(actif_step, rev_step)
                             if rv is not None and rv > 0 and av <= threshold]
                pop2_vals = [rv for av, rv in zip(actif_step, rev_step)
                             if rv is not None and rv > 0 and av > threshold]
                if len(pop1_vals) + len(pop2_vals) >= 5:
                    step_data_brute[s] = {"pop1": pop1_vals, "pop2": pop2_vals}
            if step_data_brute:
                _plot_class_revenue_series(
                    class_dir, step_data_brute, label,
                    f"class_rev_{brute_name}.png", title_extra,
                )

    # ── 2. Intérêts nets par classe ───────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, pdict, label, color in [
        (axes[0], pop1, "Pop.1 (petites)", "steelblue"),
        (axes[1], pop2, "Pop.2 (grandes)", "tomato"),
    ]:
        nets = [d["net_int"] for d in pdict.values()]
        if not nets:
            ax.set_visible(False)
            continue
        n_ben = sum(1 for v in nets if v > 0)
        n_def = sum(1 for v in nets if v < 0)
        n_neu = len(nets) - n_ben - n_def
        nets_arr = np.array(nets)

        # Symlog histogram
        absmax = np.percentile(np.abs(nets_arr[nets_arr != 0]), 99) if np.any(nets_arr != 0) else 1
        bins_neg = -np.logspace(np.log10(max(absmax * 1e-3, 1e-6)), np.log10(absmax), 25)[::-1]
        bins_pos = np.logspace(np.log10(max(absmax * 1e-3, 1e-6)), np.log10(absmax), 25)
        bins = np.concatenate([bins_neg, [0], bins_pos])
        ax.hist(nets_arr, bins=bins, color=color, alpha=0.75, edgecolor="white", linewidth=0.4)
        ax.set_xscale("symlog", linthresh=absmax * 1e-3)
        ax.axvline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
        ax.set_xlabel("Intérêts nets reçus (J)", fontsize=9)
        ax.set_ylabel("Effectif", fontsize=9)
        ax.set_title(
            f"{label}  (n={len(nets)})\n"
            f"Bénéficiaires: {n_ben} ({100*n_ben/max(len(nets),1):.0f}%)  "
            f"Déficitaires: {n_def} ({100*n_def/max(len(nets),1):.0f}%)",
            fontsize=9,
        )
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.2)
        med = float(np.median(nets_arr))
        ax.axvline(med, color=color, linewidth=1.2, linestyle=":", alpha=0.8,
                   label=f"Médiane {med:.2e}")
        ax.legend(fontsize=7)

    ttl = "Intérêts nets par classe"
    if title_extra:
        ttl += f" — {title_extra}"
    fig.suptitle(ttl, fontsize=11)
    fig.tight_layout()
    _save(fig, os.path.join(class_dir, "class_interest.png"))

    # ── 3. Levier par classe ──────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    lev1 = [d["levier"] for d in pop1.values() if d["actif"] > 0]
    lev2 = [d["levier"] for d in pop2.values() if d["actif"] > 0]
    if lev1 and lev2:
        bdata = ax.boxplot([lev1, lev2], labels=["Pop.1\n(petites)", "Pop.2\n(grandes)"],
                           patch_artist=True, notch=False, widths=0.5)
        for patch, color in zip(bdata["boxes"], ["steelblue", "tomato"]):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        ax.set_ylabel("Levier  (passif_crédit / actif_total)", fontsize=10)
        ax.set_title("Levier financier par classe", fontsize=11)
        ax.tick_params(labelsize=9)
        ax.grid(True, axis="y", alpha=0.3)
        for i, (vals, color) in enumerate([(lev1, "steelblue"), (lev2, "tomato")], 1):
            ax.text(i, ax.get_ylim()[1] * 0.97,
                    f"med={np.median(vals):.3f}\nmoy={np.mean(vals):.3f}",
                    ha="center", va="top", fontsize=8, color=color)
    ttl = "Levier par classe"
    if title_extra:
        ttl += f" — {title_extra}"
    fig.suptitle(ttl, fontsize=11)
    fig.tight_layout()
    _save(fig, os.path.join(class_dir, "class_leverage.png"))

    # ── 4. Réseau de prêts ────────────────────────────────────────────────────
    loan_rows = read_csv(os.path.join(csv_dir, "loan_network_final.csv"))
    if loan_rows:
        # Compter prêts par entité (prêteur / emprunteur)
        loans_as_lender: dict = defaultdict(int)
        loans_as_borrower: dict = defaultdict(int)
        rates_by_borrower_class: dict = {"pop1": [], "pop2": []}
        loan_matrix_count = [[0, 0], [0, 0]]   # [lender_pop][borrower_pop]
        loan_matrix_principal = [[[], []], [[], []]]

        for loan in loan_rows:
            lid = loan.get("lender_id")
            bid = loan.get("borrower_id")
            rate = loan.get("rate")
            principal = loan.get("principal") or 0
            if lid is not None:
                loans_as_lender[lid] += 1
            if bid is not None:
                loans_as_borrower[bid] += 1
            # Classe emprunteur pour taux
            if bid in entity_info and rate is not None:
                cls = "pop2" if entity_info[bid]["is_pop2"] else "pop1"
                rates_by_borrower_class[cls].append(float(rate))
            # Matrice prêteur × emprunteur
            if lid in entity_info and bid in entity_info:
                lp = 1 if entity_info[lid]["is_pop2"] else 0
                bp = 1 if entity_info[bid]["is_pop2"] else 0
                loan_matrix_count[lp][bp] += 1
                loan_matrix_principal[lp][bp].append(principal)

        # Nombre de prêts émis / reçus par classe
        lend_pop1 = [loans_as_lender.get(eid, 0) for eid in pop1]
        lend_pop2 = [loans_as_lender.get(eid, 0) for eid in pop2]
        borr_pop1 = [loans_as_borrower.get(eid, 0) for eid in pop1]
        borr_pop2 = [loans_as_borrower.get(eid, 0) for eid in pop2]

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))

        # Panel (0,0): prêts émis par entité
        ax = axes[0][0]
        max_lend = max(max(lend_pop1 or [0]), max(lend_pop2 or [0]), 1)
        bins_l = range(0, max_lend + 2)
        ax.hist(lend_pop1, bins=bins_l, alpha=0.6, color="steelblue", label=f"Pop.1 (n={n1})",
                edgecolor="white", linewidth=0.4)
        ax.hist(lend_pop2, bins=bins_l, alpha=0.6, color="tomato", label=f"Pop.2 (n={n2})",
                edgecolor="white", linewidth=0.4)
        ax.set_xlabel("Nombre de prêts émis", fontsize=9)
        ax.set_ylabel("Effectif", fontsize=9)
        ax.set_title(f"Prêts émis par entité\nPop.1 méd={np.median(lend_pop1):.0f}  Pop.2 méd={np.median(lend_pop2):.0f}",
                     fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

        # Panel (0,1): prêts reçus par entité
        ax = axes[0][1]
        max_borr = max(max(borr_pop1 or [0]), max(borr_pop2 or [0]), 1)
        bins_b = range(0, max_borr + 2)
        ax.hist(borr_pop1, bins=bins_b, alpha=0.6, color="steelblue",
                label=f"Pop.1 méd={np.median(borr_pop1):.0f}", edgecolor="white", linewidth=0.4)
        ax.hist(borr_pop2, bins=bins_b, alpha=0.6, color="tomato",
                label=f"Pop.2 méd={np.median(borr_pop2):.0f}", edgecolor="white", linewidth=0.4)
        ax.set_xlabel("Nombre de prêts reçus", fontsize=9)
        ax.set_ylabel("Effectif", fontsize=9)
        ax.set_title("Prêts reçus par entité", fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

        # Panel (0,2): taux d'intérêt par classe emprunteur
        ax = axes[0][2]
        r1 = rates_by_borrower_class["pop1"]
        r2 = rates_by_borrower_class["pop2"]
        if r1 or r2:
            bdata = ax.boxplot(
                [r for r in [r1, r2] if r],
                labels=[f"Pop.1 emprunteur\n(n={len(r1)})" if r1 else "",
                        f"Pop.2 emprunteur\n(n={len(r2)})" if r2 else ""][:sum(1 for r in [r1, r2] if r)],
                patch_artist=True, widths=0.5,
            )
            colors_bp = ["steelblue" if r1 else "tomato", "tomato"][:len(bdata["boxes"])]
            for patch, color in zip(bdata["boxes"], colors_bp):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
        ax.set_ylabel("Taux d'intérêt", fontsize=9)
        ax.set_title("Taux d'intérêt par classe d'emprunteur", fontsize=9)
        ax.grid(True, axis="y", alpha=0.3)

        # Panel (1,0): heatmap nombre de prêts
        ax = axes[1][0]
        mat = np.array(loan_matrix_count, dtype=float)
        im = ax.imshow(mat, cmap="Blues", aspect="auto")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["Pop.1\nemprunteur", "Pop.2\nemprunteur"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["Pop.1\nprêteur", "Pop.2\nprêteur"])
        for r in range(2):
            for c in range(2):
                ax.text(c, r, f"{int(mat[r,c])}", ha="center", va="center", fontsize=11, fontweight="bold")
        ax.set_title("Nombre de prêts\n(prêteur × emprunteur)", fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.046)

        # Panel (1,1): heatmap principal médian
        ax = axes[1][1]
        med_mat = np.array([[np.median(loan_matrix_principal[r][c]) if loan_matrix_principal[r][c] else 0
                              for c in range(2)] for r in range(2)])
        im2 = ax.imshow(med_mat, cmap="Oranges", aspect="auto")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["Pop.1\nemprunteur", "Pop.2\nemprunteur"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["Pop.1\nprêteur", "Pop.2\nprêteur"])
        for r in range(2):
            for c in range(2):
                ax.text(c, r, f"{med_mat[r,c]:.2e}", ha="center", va="center", fontsize=9, fontweight="bold")
        ax.set_title("Principal médian (J)\n(prêteur × emprunteur)", fontsize=9)
        fig.colorbar(im2, ax=ax, fraction=0.046)

        # Panel (1,2): fractions bénéficiaire / déficitaire
        ax = axes[1][2]
        cats = ["Bénéficiaires\n(net>0)", "Neutres", "Déficitaires\n(net<0)"]
        for pdict, color, label, xoff in [
            (pop1, "steelblue", "Pop.1", -0.2),
            (pop2, "tomato", "Pop.2", 0.2),
        ]:
            nets = [d["net_int"] for d in pdict.values()]
            if not nets:
                continue
            vals = [
                sum(1 for v in nets if v > 0) / len(nets) * 100,
                sum(1 for v in nets if v == 0) / len(nets) * 100,
                sum(1 for v in nets if v < 0) / len(nets) * 100,
            ]
            xs = [0 + xoff, 1 + xoff, 2 + xoff]
            ax.bar(xs, vals, width=0.35, color=color, alpha=0.7, label=label)
        ax.set_xticks([0, 1, 2]); ax.set_xticklabels(cats, fontsize=8)
        ax.set_ylabel("%", fontsize=9)
        ax.set_title("Répartition bénéficiaire / déficitaire", fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, axis="y", alpha=0.3)

        ttl = "Analyse du réseau de prêts par classe"
        if title_extra:
            ttl += f" — {title_extra}"
        fig.suptitle(ttl, fontsize=11)
        fig.tight_layout()
        _save(fig, os.path.join(class_dir, "class_loans.png"))

    # ── 5. Trajectoires et extraction par classe ──────────────────────────────
    hist_rows = read_csv(os.path.join(csv_dir, "entity_histories.csv"))
    if hist_rows:
        # Regrouper par entité
        by_entity: dict = defaultdict(list)
        for row in hist_rows:
            eid = row.get("entity_id")
            if eid is not None:
                by_entity[eid].append(row)
        for eid in by_entity:
            by_entity[eid].sort(key=lambda r: r.get("step", 0))

        # Classer les entités historiques par leur actif_total max
        hist_classes: dict = {}
        for eid, recs in by_entity.items():
            if eid in entity_info:
                hist_classes[eid] = entity_info[eid]["is_pop2"]
            else:
                max_actif = max((r.get("actif_total") or 0) for r in recs)
                if max_actif > 0 and fit_result is not None:
                    p2 = float(_posterior_pop2([max_actif], model_type, params)[0])
                    hist_classes[eid] = p2 >= 0.5
                else:
                    hist_classes[eid] = False

        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Panel gauche: trajectoires actif_total colorées par classe
        ax = axes[0]
        for eid, recs in list(by_entity.items())[:120]:
            steps = [r.get("step", 0) for r in recs]
            actifs = [r.get("actif_total") or 0 for r in recs]
            is_p2 = hist_classes.get(eid, False)
            color = "tomato" if is_p2 else "steelblue"
            ax.plot(steps, actifs, color=color, alpha=0.25, linewidth=0.7)
        ax.set_yscale("log")
        ax.set_xlabel("Pas de simulation", fontsize=9)
        ax.set_ylabel("Actif total (J)", fontsize=9)
        ax.set_title("Trajectoires d'actif par classe\n(bleu=Pop.1, rouge=Pop.2)", fontsize=9)
        ax.grid(True, which="both", alpha=0.15)
        ax.plot([], [], color="steelblue", linewidth=1.5, label="Pop.1")
        ax.plot([], [], color="tomato", linewidth=1.5, label="Pop.2")
        ax.legend(fontsize=8)

        # Panel droit: extraction médiane par classe au fil du temps
        ax = axes[1]
        all_steps_hist = sorted({r.get("step", 0) for recs in by_entity.values() for r in recs})
        ext_pop1_by_step: dict = defaultdict(list)
        ext_pop2_by_step: dict = defaultdict(list)
        for eid, recs in by_entity.items():
            is_p2 = hist_classes.get(eid, False)
            for r in recs:
                s = r.get("step", 0)
                ext = r.get("extraction") or 0
                if is_p2:
                    ext_pop2_by_step[s].append(ext)
                else:
                    ext_pop1_by_step[s].append(ext)

        steps_p1 = sorted(ext_pop1_by_step)
        steps_p2 = sorted(ext_pop2_by_step)
        if steps_p1:
            med1 = [np.median(ext_pop1_by_step[s]) for s in steps_p1]
            ax.plot(steps_p1, med1, color="steelblue", linewidth=1.5, label="Pop.1 médiane")
            ax.fill_between(steps_p1,
                            [np.percentile(ext_pop1_by_step[s], 25) for s in steps_p1],
                            [np.percentile(ext_pop1_by_step[s], 75) for s in steps_p1],
                            color="steelblue", alpha=0.2)
        if steps_p2:
            med2 = [np.median(ext_pop2_by_step[s]) for s in steps_p2]
            ax.plot(steps_p2, med2, color="tomato", linewidth=1.5, label="Pop.2 médiane")
            ax.fill_between(steps_p2,
                            [np.percentile(ext_pop2_by_step[s], 25) for s in steps_p2],
                            [np.percentile(ext_pop2_by_step[s], 75) for s in steps_p2],
                            color="tomato", alpha=0.2)
        ax.set_xlabel("Pas de simulation", fontsize=9)
        ax.set_ylabel("Extraction (J/pas)", fontsize=9)
        ax.set_title("Extraction médiane par classe\n(bande = IQR P25–P75)", fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

        ttl = "Trajectoires et extraction par classe"
        if title_extra:
            ttl += f" — {title_extra}"
        fig.suptitle(ttl, fontsize=11)
        fig.tight_layout()
        _save(fig, os.path.join(class_dir, "class_trajectories.png"))



# ============================================================
# RÉSUMÉ TEXTE
# ============================================================

def save_text_summary(folder: str):
    csv_dir, fig_dir = _paths(folder)
    rows     = read_csv(os.path.join(csv_dir, "indicateurs_systemiques.csv"))
    cascades = read_csv(os.path.join(csv_dir, "tailles_cascades_brutes.csv"))
    meta     = read_meta(folder)

    out = os.path.join(folder, "resume_analyse.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("Résumé d'analyse\n================\n\n")
        if meta:
            f.write("Métadonnées\n-----------\n")
            if meta.get("label"):
                f.write(f"Label : {meta['label']}\n")
            if "date" in meta:
                f.write(f"Date : {meta['date']}\n")
            if "config" in meta:
                cfg = meta["config"]
                f.write(f"alpha = {cfg.get('alpha', '?')}\n")
                f.write(f"lambda_creation = {cfg.get('lambda_creation', '?')}\n")
                f.write(f"seed = {cfg.get('seed', '?')}\n")
            f.write("\n")
        if rows:
            last = rows[-1]
            f.write("Indicateurs finaux\n------------------\n")
            f.write(f"Pas final : {last['step']}\n")
            f.write(f"Nombre d'entités : {last.get('nb_entites', '?')}\n")
            f.write(f"Actif total : {last.get('actif_total', '?')}\n")
            f.write(f"Volume de prêts : {last.get('volume_prets', '?')}\n")
            f.write(f"Levier système : {last.get('levier_systeme', '?')}\n")
            total_destroyed = sum(r.get("volume_faillites", 0.0) or 0 for r in rows)
            total_failures  = sum(r.get("nb_faillites", 0) or 0     for r in rows)
            f.write(f"\nFaillites : {total_failures} entités, {total_destroyed:.2f} J détruits\n")
        if cascades:
            vols = sorted([c["volume_joules"] for c in cascades if (c["volume_joules"] or 0) > 0],
                          reverse=True)
            f.write(f"\nCascades : {len(vols)} événements")
            if vols:
                f.write(f", max={max(vols):.2f} J, médiane={vols[len(vols)//2]:.2f} J\n")
    print(f"  → {out}")


# ============================================================
# ANALYSE D'UN DOSSIER
# ============================================================

def analyze_folder(folder: str, label: str = ""):
    print(f"\nAnalyse de : {folder}")
    if not os.path.isdir(folder):
        print("  Dossier introuvable.")
        return

    save_text_summary(folder)

    if MATPLOTLIB_OK:
        print("Génération des graphiques :")
        plot_macro_overview(folder, title_extra=label)
        plot_cascades_rank_size(folder, title_extra=label)
        plot_entity_size_histograms(folder, title_extra=label)
        plot_extraction_power(folder, title_extra=label)
        plot_destruction_moving_average(folder, window=100, title_extra=label)
        plot_internal_rate_evolution(folder, title_extra=label)
        plot_gini_evolution(folder, title_extra=label)
        plot_gini_lorenz_snapshots(folder, title_extra=label)
        plot_revenue_distributions(folder, title_extra=label)
        plot_entity_lives_overview(folder, title_extra=label)
        plot_entity_lives(folder, title_extra=label)
        plot_loan_network_final(folder, title_extra=label)
        plot_lifespan_analysis(folder, title_extra=label)
        plot_entity_class_analysis(folder, title_extra=label)
        print("Graphiques générés.")


# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage : python analysis.py <dossier_simulation> [<dossier2> ...]")
        sys.exit(1)
    for folder in sys.argv[1:]:
        analyze_folder(folder)


if __name__ == "__main__":
    main()
