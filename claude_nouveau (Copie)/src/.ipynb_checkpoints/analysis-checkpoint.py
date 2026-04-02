"""
analysis.py — Analyse statistique et visualisation des résultats de simulation.

Graphiques produits :
  1. macro_overview.png          — Actifs agrégés, volume de prêts (axe gauche)
                                   + nombre d'entités vivantes (axe droit)
  2. cascades_rank_size.png      — Taille des cascades (ordonnée) en fonction
                                   de la fréquence d'excédance (abscisse), log-log
  3. entity_size_histos.png      — 5 histogrammes horizontaux de la distribution
                                   des tailles d'entités (actif total) :
                                   X = densité de probabilité, Y = taille
  4. hist_transition_<x>.png     — Distributions pendant la transition uniquement
  5. extraction_power.png        — Puissance extractrice Π = α√P :
                                   médiane, moyenne, max, Q10, Q90
  6. destruction_moving_avg.png  — Moyenne glissante de la destruction de capital

Usage :
    python analysis.py <dossier_resultats>
    python analysis.py <dossier1> <dossier2>
"""

import csv
import json
import math
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False
    print("matplotlib non disponible — seuls les résumés texte seront produits.")


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
            if v is None or v == "":
                converted[k] = v
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


def read_raw_distribution(folder: str, name: str) -> Dict[int, List[float]]:
    path = os.path.join(folder, f"distrib_brute_{name}.csv")
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


def _linear_histogram(values: List[float], n_bins: int = 20) -> Tuple:
    vals = [v for v in values if math.isfinite(v)]
    if len(vals) < 2:
        return None, None, None

    vmin, vmax = min(vals), max(vals)
    if vmax <= vmin:
        return None, None, None

    bw = (vmax - vmin) / n_bins
    edges = [vmin + i * bw for i in range(n_bins + 1)]
    counts = [0] * n_bins

    for v in vals:
        idx = min(int((v - vmin) / bw), n_bins - 1)
        counts[idx] += 1

    total = len(vals)
    centres = [(edges[i] + edges[i + 1]) / 2 for i in range(n_bins)]
    densities = [c / (total * bw) if bw > 0 else 0.0 for c in counts]
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


def _detect_transition_end(folder: str) -> int:
    """
    Proxy simple :
    fin de transition = premier pas où des faillites apparaissent.
    """
    rows = read_csv(os.path.join(folder, "indicateurs_systemiques.csv"))
    for r in rows:
        if r.get("nb_faillites", 0) > 0:
            return int(r["step"])
    return -1


def _subsample(steps: List[int], max_curves: int = 25) -> List[int]:
    if len(steps) <= max_curves:
        return steps
    step_size = max(1, len(steps) // max_curves)
    return steps[::step_size][:max_curves]


# ============================================================
# 1. VUE MACRO
# ============================================================

def plot_macro_overview(folder: str, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return

    rows = read_csv(os.path.join(folder, "indicateurs_systemiques.csv"))
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
    
    ymin = min(entites)
    ymax = max(entites)
    margin = max(5, 0.05 * (ymax - ymin))
    
    ax2.set_ylim(ymin - margin, ymax + margin)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="upper left")

    title = "Actifs agrégés, prêts et population vivante"
    if title_extra:
        title += f" — {title_extra}"
    ax1.set_title(title, fontsize=12)
    ax1.grid(True, alpha=0.25)

    _save(fig, os.path.join(folder, "macro_overview.png"))


# ============================================================
# 2. CASCADES : TAILLE EN FONCTION DE LA FRÉQUENCE
# ============================================================

def plot_cascades_rank_size(folder: str, title_extra: str = "", n_bins: int = 25):
    """
    Graphique taille-fréquence des cascades, biné en log-log.

    Axe X : fréquence d'excédance
    Axe Y : taille de la cascade (joules)

    On ne trace pas tous les points bruts :
    on les regroupe en bins logarithmiques sur la fréquence,
    avec un point représentatif par bin.
    """
    if not MATPLOTLIB_OK:
        return

    rows = read_csv(os.path.join(folder, "tailles_cascades_brutes.csv"))
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

    # bins logarithmiques sur la fréquence
    fmin = min(freqs)
    fmax = max(freqs)
    log_min = math.log10(fmin)
    log_max = math.log10(fmax)

    if log_max <= log_min:
        print("  Fréquences dégénérées")
        return

    bin_edges = [10 ** (log_min + i * (log_max - log_min) / n_bins) for i in range(n_bins + 1)]

    binned_x = []
    binned_y = []

    for i in range(n_bins):
        lo = bin_edges[i]
        hi = bin_edges[i + 1]

        pts = [(f, v) for f, v in zip(freqs, volumes) if lo <= f < hi or (i == n_bins - 1 and lo <= f <= hi)]
        if not pts:
            continue

        fs = [p[0] for p in pts]
        vs = [p[1] for p in pts if p[1] > 0]
        if not vs:
            continue

        # moyenne géométrique, plus cohérente en log-log
        x_rep = 10 ** (sum(math.log10(f) for f in fs) / len(fs))
        y_rep = 10 ** (sum(math.log10(v) for v in vs) / len(vs))

        binned_x.append(x_rep)
        binned_y.append(y_rep)

    if len(binned_x) < 3:
        print("  Trop peu de bins non vides pour cascades_rank_size")
        return

    fig, ax = plt.subplots(figsize=(7, 5))

    ax.plot(binned_x, binned_y, marker="o", linewidth=1.3, markersize=4, color="#d62728")

    # ajustement sur la queue
    tail_n = max(3, len(binned_x) // 2)
    log_fx = [math.log10(f) for f in binned_x[:tail_n]]
    log_vy = [math.log10(v) for v in binned_y[:tail_n]]
    slope, intercept = _linear_regression(log_fx, log_vy)

    fit_x = [binned_x[0], binned_x[tail_n - 1]]
    fit_y = [10 ** (intercept + slope * math.log10(x)) for x in fit_x]
    ax.plot(fit_x, fit_y, "k--", linewidth=1.2, alpha=0.8, label=f"Pente ≈ {slope:.2f}")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Fréquence d'excédance", fontsize=11)
    ax.set_ylabel("Taille de la cascade (joules)", fontsize=11)

    title = "Cascades de faillite : taille en fonction de la fréquence"
    if title_extra:
        title += f"\n{title_extra}"
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.3)

    _save(fig, os.path.join(folder, "cascades_rank_size.png"))
# ============================================================
# 3. 5 HISTOGRAMMES DE TAILLE DES ENTITÉS
# ============================================================

def plot_entity_size_histograms(folder: str, n_snapshots: int = 5, title_extra: str = ""):
    """
    5 histogrammes horizontaux de la distribution des tailles d'entités
    mesurées par l'actif total.

    Axe X : effectif dans la classe
    Axe Y : taille de l'entité (actif total)

    Histogramme ordinaire, pas densité de probabilité.
    """
    if not MATPLOTLIB_OK:
        return

    data = read_raw_distribution(folder, "actif_total")
    if not data:
        print("  Pas de distribution brute pour actif_total")
        return

    all_steps = sorted(data.keys())
    if len(all_steps) < 2:
        return

    if n_snapshots <= 1:
        selected = [all_steps[-1]]
    else:
        indices = [int(i * (len(all_steps) - 1) / (n_snapshots - 1)) for i in range(n_snapshots)]
        selected = [all_steps[i] for i in indices]

    cmap = plt.cm.viridis
    colors = [cmap(i / max(n_snapshots - 1, 1)) for i in range(len(selected))]

    fig, ax = plt.subplots(figsize=(8, 7))

    for step, color in zip(selected, colors):
        values = [v for v in data[step] if v > 0]
        if len(values) < 2:
            continue

        vmin = min(values)
        vmax = max(values)
        if vmax <= vmin:
            continue

        # bins logarithmiques sur les tailles
        n_bins = 20
        log_min = math.log10(vmin)
        log_max = math.log10(vmax)
        edges = [10 ** (log_min + i * (log_max - log_min) / n_bins) for i in range(n_bins + 1)]
        counts = [0] * n_bins

        for v in values:
            idx = int((math.log10(v) - log_min) / (log_max - log_min) * n_bins)
            idx = min(max(idx, 0), n_bins - 1)
            counts[idx] += 1

        centres = [math.sqrt(edges[i] * edges[i + 1]) for i in range(n_bins)]

        # histogramme horizontal "profilé"
        ax.plot(counts, centres, color=color, linewidth=1.8, alpha=0.85, label=f"Pas {step}")
        ax.scatter(counts, centres, color=color, s=18, zorder=3, alpha=0.75)

    ax.set_yscale("log")
    ax.set_xlabel("Effectif dans la classe", fontsize=11)
    ax.set_ylabel("Actif total (joules)", fontsize=11)

    title = "Histogrammes des tailles d'entités — 5 instantanés"
    if title_extra:
        title += f"\n{title_extra}"
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, which="both", alpha=0.3)

    _save(fig, os.path.join(folder, "entity_size_histos.png"))
# ============================================================
# 4. HISTOGRAMMES ÉVOLUTIFS — TRANSITION SEULEMENT
# ============================================================

def plot_evolving_histograms(
    folder: str,
    name: str,
    title_extra: str = "",
    log_x: bool = True,
    log_y: bool = True,
    n_snapshots: int = 5,
):
    """
    Histogrammes/distributions à plusieurs dates sur toute la durée
    de la simulation.

    On choisit n_snapshots pas de temps répartis uniformément
    sur l'ensemble de la simulation.
    """
    if not MATPLOTLIB_OK:
        return

    data = read_raw_distribution(folder, name)
    if not data:
        print(f"  Pas de distribution brute pour {name}")
        return

    all_steps = sorted(data.keys())
    if len(all_steps) < 2:
        print(f"  Trop peu de snapshots pour {name}")
        return

    if n_snapshots <= 1:
        plot_steps = [all_steps[-1]]
    else:
        indices = [
            int(i * (len(all_steps) - 1) / (n_snapshots - 1))
            for i in range(n_snapshots)
        ]
        plot_steps = [all_steps[i] for i in indices]

    cmap = plt.cm.cool
    colors = [cmap(i / max(len(plot_steps) - 1, 1)) for i in range(len(plot_steps))]

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, step in enumerate(plot_steps):
        values = [v for v in data[step] if math.isfinite(v)]
        if len(values) < 2:
            continue

        if log_x:
            centres, densities, _ = _log_binned_histogram(values, n_bins=20)
        else:
            centres, densities, _ = _linear_histogram(values, n_bins=20)

        if centres is None:
            continue

        ax.plot(
            centres,
            densities,
            color=colors[i],
            alpha=0.85,
            linewidth=1.4,
            label=f"Pas {step}",
        )

    readable_names = {
        "actif_liquide": "Actif liquide L (joules)",
        "actif_total":   "Actif total A (joules)",
        "taux_interne":  "Taux interne marginal r*",
        "levier_entite": "Levier individuel P/A",
    }

    xlabel = readable_names.get(name, name)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel("Densité", fontsize=11)

    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")

    title = f"Évolution de la distribution — {xlabel}"
    if title_extra:
        title += f"\n{title_extra}"
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, which="both" if (log_x or log_y) else "major", alpha=0.3)

    _save(fig, os.path.join(folder, f"hist_{name}.png"))


# ============================================================
# 5. PUISSANCE EXTRACTRICE
# ============================================================

def plot_extraction_power(folder: str, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return

    meta = read_meta(folder)
    alpha = meta.get("config", {}).get("alpha", 1.0)

    passif_data = read_raw_distribution(folder, "passif_total")
    if not passif_data:
        print("  Pas de distribution brute pour passif_total")
        return

    steps_sorted = sorted(passif_data.keys())
    steps_out = []
    means, medians, maxs, q10s, q90s = [], [], [], [], []

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

    _save(fig, os.path.join(folder, "extraction_power.png"))


# ============================================================
# 6. MOYENNE GLISSANTE DE DESTRUCTION
# ============================================================

def plot_destruction_moving_average(folder: str, window: int = 100, title_extra: str = ""):
    if not MATPLOTLIB_OK:
        return

    rows = read_csv(os.path.join(folder, "indicateurs_systemiques.csv"))
    if not rows:
        return

    steps = [r["step"] for r in rows]
    destroyed = [r.get("volume_faillites", 0.0) for r in rows]
    moving = _rolling_mean(destroyed, window)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(steps, destroyed, linewidth=0.8, alpha=0.35, color="#d62728", label="Destruction brute")
    ax.plot(steps, moving, linewidth=2.0, color="black", label=f"Moyenne glissante ({window})")

    ax.set_xlabel("Pas de simulation", fontsize=11)
    ax.set_ylabel("Capital détruit (joules)", fontsize=11)

    title = "Destruction de capital et moyenne glissante"
    if title_extra:
        title += f" — {title_extra}"
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.25)

    _save(fig, os.path.join(folder, "destruction_moving_avg.png"))


# ============================================================
# RÉSUMÉ TEXTE
# ============================================================

def save_text_summary(folder: str):
    rows = read_csv(os.path.join(folder, "indicateurs_systemiques.csv"))
    cascades = read_csv(os.path.join(folder, "tailles_cascades_brutes.csv"))
    meta = read_meta(folder)

    out = os.path.join(folder, "resume_analyse.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("Résumé d'analyse\n")
        f.write("================\n\n")

        if meta:
            f.write("Métadonnées\n")
            f.write("-----------\n")
            label = meta.get("label", "")
            if label:
                f.write(f"Label : {label}\n")
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
            f.write("Indicateurs finaux\n")
            f.write("------------------\n")
            f.write(f"Pas final : {last['step']}\n")
            f.write(f"Nombre d'entités : {last.get('nb_entites', '?')}\n")
            f.write(f"Actif total : {last.get('actif_total', '?')}\n")
            f.write(f"Volume de prêts : {last.get('volume_prets', '?')}\n")
            f.write(f"Levier système : {last.get('levier_systeme', '?')}\n")
            f.write(f"Ratio de liquidité : {last.get('ratio_liquidite', '?')}\n")
            f.write(f"Concentration des prêts : {last.get('concentration_prets', '?')}\n")
            f.write("\n")

            total_destroyed = sum(r.get("volume_faillites", 0.0) for r in rows)
            total_failures = sum(r.get("nb_faillites", 0) for r in rows)
            f.write("Faillites agrégées\n")
            f.write("------------------\n")
            f.write(f"Nombre total d'entités faillies : {total_failures}\n")
            f.write(f"Capital total détruit : {total_destroyed}\n")
            f.write("\n")

        if cascades:
            vols = sorted([c["volume_joules"] for c in cascades if c["volume_joules"] > 0], reverse=True)
            f.write("Cascades\n")
            f.write("--------\n")
            f.write(f"Nombre de cascades enregistrées : {len(vols)}\n")
            if vols:
                f.write(f"Cascade maximale (joules) : {max(vols)}\n")
                f.write(f"Cascade médiane (joules) : {vols[len(vols)//2]}\n")
            f.write("\n")

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
        plot_entity_size_histograms(folder, n_snapshots=5, title_extra=label)

        plot_evolving_histograms(folder, "actif_liquide", label, log_x=True,  log_y=True,  n_snapshots=5)
        plot_evolving_histograms(folder, "actif_total",   label, log_x=True,  log_y=True,  n_snapshots=5)
        plot_evolving_histograms(folder, "taux_interne",  label, log_x=True,  log_y=True,  n_snapshots=5)
        plot_evolving_histograms(folder, "levier_entite", label, log_x=False, log_y=False, n_snapshots=5)

        plot_extraction_power(folder, title_extra=label)
        plot_destruction_moving_average(folder, window=100, title_extra=label)

        print("Graphiques générés.")


# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage : python analysis.py <dossier_resultats> [<dossier2> ...]")
        sys.exit(1)

    folders = sys.argv[1:]
    for folder in folders:
        analyze_folder(folder)


if __name__ == "__main__":
    main()