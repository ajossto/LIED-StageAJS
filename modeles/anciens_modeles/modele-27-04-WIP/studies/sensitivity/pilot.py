"""
pilot.py — Étude pilote : validation du régime permanent et corrélations.

Lance N_PILOT = 5 × 3 seeds = 15 simulations (baseline, alpha homogène).
Produit :
  - Figures PDF dans report/figures/pilot_*.pdf
  - JSON agrégé dans results/pilot_results.json
  - Matrice de corrélation des métriques
"""

from __future__ import annotations

import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect, detect_regime, BASELINE, FIXED_PARAMS

ROOT_WIP = HERE.parents[1]
FIGURES_DIR = HERE / "report" / "figures"
RESULTS_DIR = HERE / "results"
RAW_DIR = ROOT_WIP / "simulations étude de sensibilité paramètres" / "pilot"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

N_STEPS = 1000
SEEDS = [42, 7, 123, 456, 789]
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]


# ─────────────────────────────────────────────
#  Exécution parallèle
# ─────────────────────────────────────────────

def _worker(seed):
    return run_and_collect({}, n_steps=N_STEPS, seed=seed)


def run_pilot():
    print(f"Lancement de {len(SEEDS)} simulations pilotes (N_STEPS={N_STEPS})…")
    results = []
    with ProcessPoolExecutor(max_workers=min(len(SEEDS), os.cpu_count() or 4)) as exe:
        futures = {exe.submit(_worker, seed): seed for seed in SEEDS}
        for fut in as_completed(futures):
            seed = futures[fut]
            res = fut.result()
            results.append(res)
            t_regime = res["t_regime"]
            conv = "✓ régime" if res["converged"] else "~ fallback"
            print(
                f"  seed={seed:4d} | t_regime={t_regime:4d} | {conv} | "
                f"n_alive={res['n_alive_mean']:.0f}±{res['n_alive_std']:.0f} | "
                f"actif={res['actif_mean']:.0f} | "
                f"loan_density={res['loan_density_mean']:.2f} | "
                f"gini={res['gini_actif_mean']:.3f}"
            )
    results.sort(key=lambda r: r["seed"])
    return results


# ─────────────────────────────────────────────
#  Figure 1 : trajectoires temporelles
# ─────────────────────────────────────────────

def plot_trajectories(results: list, save_path: Path):
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle("Trajectoires pilotes — alpha homogène (alpha=1, sigma=0)", fontsize=13)

    metrics = [
        ("ts_n_alive",    "Entités vivantes (n_alive)",       axes[0, 0]),
        ("ts_actif",      "Actif total du système",            axes[0, 1]),
        ("ts_n_loans",    "Prêts actifs",                      axes[1, 0]),
        ("ts_failures",   "Faillites par pas",                 axes[1, 1]),
        ("ts_densite_fin","Densité financière (vol_prêts/actif)", axes[2, 0]),
        ("ts_gini",       "Gini actif",                        axes[2, 1]),
    ]

    for key, label, ax in metrics:
        for res, col in zip(results, COLORS):
            seed = res["seed"]
            series = res[key]
            steps = list(range(1, len(series) + 1))
            ax.plot(steps, series, color=col, alpha=0.8, linewidth=1.2, label=f"seed {seed}")
            # Marquer t_regime
            t_r = res["t_regime"]
            if 0 < t_r < len(series):
                ax.axvline(t_r, color=col, linestyle="--", alpha=0.4, linewidth=0.8)
        ax.set_xlabel("Pas de temps")
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.3)

    axes[0, 0].legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(str(save_path), bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  → {save_path.name}")


# ─────────────────────────────────────────────
#  Figure 2 : distribution des tailles en régime
# ─────────────────────────────────────────────

def plot_size_distributions(results: list, save_path: Path):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Distribution des tailles d'entités (actif total) en régime permanent", fontsize=12)

    # Axe 1 : distributions empiriques normalisées par leur médiane.
    ax = axes[0]
    for res, col in zip(results, COLORS):
        values = [v for v in res.get("dist_values_regime", []) if v > 0]
        if not values:
            continue
        med = np.median(values)
        scaled = np.array(values) / med if med > 0 else np.array(values)
        ax.hist(scaled, bins=35, density=True, histtype="step", color=col,
                linewidth=1.3, label=f"seed {res['seed']}")
    ax.set_xscale("log")
    ax.set_xlabel("Actif total / médiane")
    ax.set_ylabel("Densité empirique")
    ax.set_title("Forme normalisée")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    seeds = [r["seed"] for r in results]
    x = np.arange(len(seeds))

    # Axe 2 : quantiles bruts.
    ax = axes[1]
    width = 0.22
    for offset, pname, label in [(-width, "median", "Médiane"), (0, "p90", "P90"), (width, "p99", "P99")]:
        vals = [r["dist_stats"].get(pname, 0) for r in results]
        ax.bar(x + offset, vals, width=width, label=label, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"s{s}" for s in seeds])
    ax.set_title("Quantiles actif")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=7)

    # Axe 3 : mesures de concentration / dispersion.
    ax = axes[2]
    width = 0.25
    for offset, pname, label in [(-width, "gini", "Gini"), (0, "cv", "CV"), (width, "lognormal_sigma", "sigma log")]:
        vals = [r["dist_stats"].get(pname, 0) for r in results]
        ax.bar(x + offset, vals, width=width, label=label, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"s{s}" for s in seeds])
    ax.set_title("Dispersion actif")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=7)

    plt.tight_layout()
    fig.savefig(str(save_path), bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  → {save_path.name}")


# ─────────────────────────────────────────────
#  Figure 3 : matrice de corrélation
# ─────────────────────────────────────────────

def plot_correlation_matrix(results: list, save_path: Path):
    metric_keys = [
        "n_alive_mean", "actif_mean", "n_loans_mean",
        "loan_density_mean", "densite_fin_mean", "gini_actif_mean",
        "failure_rate_mean", "levier_mean", "n_alive_cv", "actif_cv",
    ]
    labels = [
        "n_alive", "actif", "n_loans",
        "loan/alive", "vol/actif", "Gini",
        "fail/pas", "levier", "CV_alive", "CV_actif",
    ]

    data = [[r[k] for r in results] for k in metric_keys]
    n = len(metric_keys)

    # Matrice de corrélation
    corr = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            xi = data[i]; xj = data[j]
            mx = sum(xi) / len(xi); my = sum(xj) / len(xj)
            num = sum((a - mx) * (b - my) for a, b in zip(xi, xj))
            dx = math.sqrt(sum((a - mx) ** 2 for a in xi))
            dy = math.sqrt(sum((b - my) ** 2 for b in xj))
            corr[i][j] = num / (dx * dy) if dx > 0 and dy > 0 else 0.0

    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{corr[i][j]:.2f}", ha="center", va="center",
                    fontsize=7, color="black" if abs(corr[i][j]) < 0.7 else "white")
    plt.colorbar(im, ax=ax, label="Corrélation de Pearson")
    ax.set_title(f"Corrélation entre métriques en régime permanent (n={len(results)} runs pilotes)", fontsize=11)
    plt.tight_layout()
    fig.savefig(str(save_path), bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  → {save_path.name}")


# ─────────────────────────────────────────────
#  Sauvegarde JSON
# ─────────────────────────────────────────────

def save_results(results: list, path: Path):
    compact = []
    for r in results:
        c = {k: v for k, v in r.items() if not k.startswith("ts_") and k != "dist_values_regime"}
        compact.append(c)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(compact, f, indent=2)
    print(f"  → {path.name} ({len(compact)} runs)")


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import math

    results = run_pilot()

    print("\nGénération des figures…")
    plot_trajectories(results, FIGURES_DIR / "pilot_trajectoires.pdf")
    plot_size_distributions(results, FIGURES_DIR / "pilot_distributions.pdf")
    plot_correlation_matrix(results, FIGURES_DIR / "pilot_correlations.pdf")
    save_results(results, RESULTS_DIR / "pilot_results.json")

    print("\nRésumé régime permanent (baseline, alpha homogène) :")
    print(f"{'Seed':>6} {'t_reg':>5} {'conv':>5} {'n_alive':>8} {'actif':>10} {'loan/alive':>10} {'Gini':>6} {'CV_alive':>8}")
    for r in results:
        print(
            f"{r['seed']:6d} {r['t_regime']:5d} {'Y' if r['converged'] else 'N':>5} "
            f"{r['n_alive_mean']:8.1f} {r['actif_mean']:10.0f} "
            f"{r['loan_density_mean']:10.3f} {r['gini_actif_mean']:6.3f} "
            f"{r['n_alive_cv']:8.3f}"
        )
    print("\nPilote terminé.")
