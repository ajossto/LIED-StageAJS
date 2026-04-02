"""
analysis.py — Analyse statistique et visualisation des résultats de simulation.

Graphiques produits dans <simu>/figures/ :
  1. macro_overview.png
  2. cascades_rank_size.png          — taille (X) vs fréquence (Y), log-log
  3. entity_size_histos.png          — histogrammes bâtons aux pas fixes
  4. extraction_power.png            — Π médiane, moyenne, max, Q10, Q90
  5. destruction_moving_avg.png      — destruction + puissance extraction totale
  6. actif_total_distribution.png    — distributions log-log, axes inversés
  7. internal_rate_evolution.png     — r* : max, min, moy, med, D1, D9
  8. entity_{id}.png (multiple)      — vie individuelle des entités surveillées
  9. lifespan_analysis.png           — espérance de vie vs taille / endettement

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
    Graphique taille-fréquence des cascades, biné en log-log.
    X : taille de la cascade (joules)
    Y : fréquence d'excédance
    """
    if not MATPLOTLIB_OK:
        return
    csv_dir, fig_dir = _paths(folder)
    rows = read_csv(os.path.join(csv_dir, "tailles_cascades_brutes.csv"))
    if not rows:
        print("  Pas de données de cascade")
        return
    volumes = sorted(
        [float(r["volume_joules"]) for r in rows if float(r["volume_joules"]) > 0],
        reverse=True,
    )
    n = len(volumes)
    if n < 5:
        print("  Trop peu de cascades pour un graphique rang-taille")
        return

    freqs = [(i + 1) / n for i in range(n)]

    # bins logarithmiques sur la taille (X)
    vmin, vmax = min(volumes), max(volumes)
    log_min = math.log10(vmin)
    log_max = math.log10(vmax)
    if log_max <= log_min:
        return
    bin_edges = [10 ** (log_min + i * (log_max - log_min) / n_bins) for i in range(n_bins + 1)]

    binned_x, binned_y = [], []
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        pts = [(v, f) for v, f in zip(volumes, freqs)
               if lo <= v < hi or (i == n_bins - 1 and lo <= v <= hi)]
        if not pts:
            continue
        vs = [p[0] for p in pts if p[0] > 0]
        fs = [p[1] for p in pts if p[1] > 0]
        if not vs or not fs:
            continue
        x_rep = 10 ** (sum(math.log10(v) for v in vs) / len(vs))
        y_rep = 10 ** (sum(math.log10(f) for f in fs) / len(fs))
        binned_x.append(x_rep)
        binned_y.append(y_rep)

    if len(binned_x) < 3:
        print("  Trop peu de bins non vides pour cascades_rank_size")
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(binned_x, binned_y, marker="o", linewidth=1.3, markersize=4, color="#d62728")

    # ajustement linéaire log-log
    tail_n = max(3, len(binned_x) // 2)
    log_fx = [math.log10(x) for x in binned_x[:tail_n]]
    log_vy = [math.log10(y) for y in binned_y[:tail_n]]
    slope, intercept = _linear_regression(log_fx, log_vy)
    fit_x = [binned_x[0], binned_x[tail_n - 1]]
    fit_y = [10 ** (intercept + slope * math.log10(x)) for x in fit_x]
    ax.plot(fit_x, fit_y, "k--", linewidth=1.2, alpha=0.8, label=f"Pente ≈ {slope:.2f}")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Taille de la cascade (joules)", fontsize=11)
    ax.set_ylabel("Fréquence d'excédance", fontsize=11)
    title = "Cascades de faillite : taille vs fréquence"
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

        # Vertical bars with log X axis: use Rectangle patches
        for i in range(n_bins):
            if counts[i] > 0:
                rect = mpatches.Rectangle(
                    (edges[i], 0), edges[i + 1] - edges[i], counts[i],
                    facecolor=color, alpha=0.75, edgecolor="white", linewidth=0.5
                )
                ax.add_patch(rect)

        ax.set_xlim(edges[0] * 0.9, edges[-1] * 1.1)
        ax.set_ylim(0, max(counts) * 1.15)
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
        # density = count / (total * bin_width_log)
        centres = [math.sqrt(edges[i] * edges[i + 1]) for i in range(n_bins)]
        densities = []
        for i in range(n_bins):
            width = edges[i + 1] - edges[i]
            densities.append(counts[i] / (total * width) if total * width > 0 else 0.0)

        # Horizontal bars: Y = taille (log), X = densité (log)
        # Use fill_betweenx for proper log-log rendering
        valid = [(centres[i], edges[i], edges[i + 1], densities[i])
                 for i in range(n_bins) if densities[i] > 0]
        for (centre, e_lo, e_hi, dens) in valid:
            ax.fill_betweenx([e_lo, e_hi], 0, dens, alpha=0.7, color=color)

        # Connect centres for outline
        dens_vals = [d for d in densities if d > 0]
        ctr_vals = [centres[i] for i in range(n_bins) if densities[i] > 0]
        if len(ctr_vals) > 1:
            ax.plot([densities[i] for i in range(n_bins) if densities[i] > 0],
                    [centres[i] for i in range(n_bins) if densities[i] > 0],
                    color=color, linewidth=1.0, alpha=0.9)

        ax.set_yscale("log")
        ax.set_xscale("log")
        ax.set_ylabel("Actif total (J)", fontsize=8)
        ax.set_xlabel("Densité", fontsize=8)
        ax.set_title(f"Pas {step} (n={total})", fontsize=9)
        ax.tick_params(labelsize=7)
        ax.grid(True, which="both", alpha=0.2)

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
# 8. VIE DES ENTITÉS INDIVIDUELLES
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
        pi_   = [r.get("passif_inne", 0) or 0          for r in recs]
        pe    = [r.get("passif_endoinvesti", 0) or 0   for r in recs]
        px    = [r.get("passif_exoinvesti", 0) or 0    for r in recs]

        # Flux
        extr  = [r.get("extraction", 0) or 0           for r in recs]
        ir    = [r.get("interest_received", 0) or 0    for r in recs]
        ip    = [r.get("interest_paid", 0) or 0        for r in recs]
        dep   = [r.get("depreciation", 0) or 0         for r in recs]

        alive_flag = [bool(r.get("alive", 1)) for r in recs]
        death_step = None
        for i, a in enumerate(alive_flag):
            if not a:
                death_step = steps[i]
                break

        fig, axes = plt.subplots(3, 1, figsize=(13, 13), sharex=True)
        ax1, ax2, ax3 = axes

        def add_sys_background(ax):
            ax_s = ax.twinx()
            ax_s.fill_between(sys_steps, 0, sys_actif, alpha=0.04, color="gray")
            ax_s.plot(sys_steps, sys_actif, color="lightgray", linewidth=0.6, alpha=0.4,
                      linestyle="--")
            ax_s.set_ylabel("Actif système (J)", color="gray", fontsize=7)
            ax_s.tick_params(axis="y", labelcolor="gray", labelsize=6)
            return ax_s

        # 1 — Actifs (stacked area)
        ax1.stackplot(steps, al, ap, ae, ax_,
                      labels=["Liquide", "Prêté", "Endo-investi", "Exo-investi"],
                      colors=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
                      alpha=0.75)
        ax1.set_ylabel("Actifs (J)", fontsize=10)
        ax1.legend(fontsize=8, loc="upper left")
        ax1.grid(True, alpha=0.2)
        add_sys_background(ax1)

        # 2 — Passifs (stacked area)
        ax2.stackplot(steps, pi_, pe, px,
                      labels=["Inné", "Endo-investi", "Exo-investi"],
                      colors=["#e377c2", "#7f7f7f", "#bcbd22"],
                      alpha=0.75)
        ax2.set_ylabel("Passifs (J)", fontsize=10)
        ax2.legend(fontsize=8, loc="upper left")
        ax2.grid(True, alpha=0.2)
        add_sys_background(ax2)

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
        ax3.legend(fontsize=8, loc="upper left")
        ax3.grid(True, alpha=0.2)
        add_sys_background(ax3)

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
        fig.tight_layout()
        _save(fig, os.path.join(fig_dir, f"entity_{eid}.png"))


# ============================================================
# 9. ESPÉRANCE DE VIE VS TAILLE / ENDETTEMENT
# ============================================================

def plot_lifespan_analysis(folder: str, title_extra: str = ""):
    """
    Espérance de vie des entités surveillées en fonction de :
    - leur actif total moyen
    - leur passif total moyen (endettement)
    - leur levier moyen
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
    mean_passifs = [r["mean_passif"] for r in records]
    mean_leviers = [r["mean_levier"] for r in records]
    censored     = [r["censored"]    for r in records]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

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

    scatter_plot(axes[0], mean_actifs,  "Actif total moyen (J)")
    scatter_plot(axes[1], mean_passifs, "Passif total moyen (J)")
    scatter_plot(axes[2], mean_leviers, "Levier moyen P/A", log_x=False)

    title = "Espérance de vie des entités"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    _save(fig, os.path.join(fig_dir, "lifespan_analysis.png"))


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
        plot_actif_total_distribution(folder, title_extra=label)
        plot_internal_rate_evolution(folder, title_extra=label)
        plot_entity_lives(folder, title_extra=label)
        plot_lifespan_analysis(folder, title_extra=label)
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
