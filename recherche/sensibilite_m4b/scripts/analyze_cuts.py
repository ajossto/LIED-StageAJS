"""Analyse des coupes 2D sigma×k et sigma×delta.

Pour chaque coupe et chaque métrique clé :
- carte de chaleur des moyennes inter-graines sur la grille ;
- courbes métrique(sigma) par niveau du second facteur (croisements =
  interaction qualitative) ;
- indice d'interaction : contraste extrême du second facteur calculé à
  chaque sigma ; variation relative de ce contraste le long de sigma
  (et changement de signe éventuel).

Sorties : figures/cut_<plan>_<metrique>.png, figures/cut_<plan>_heat.png,
results/summary/cut_interactions.csv. Analyse exploratoire.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs as L

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG_DIR = L.CAMPAIGN_ROOT / "figures"
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary"

METRICS = [
    ("N_over_lambda", "N/λ"),
    ("gini_K", "Gini du capital"),
    ("branching_ratio", "rapport de branchement b"),
    ("alpha_pl", "exposant α"),
    ("susceptibility", "susceptibilité"),
    ("debt_to_K", "dette/capital"),
]

CUTS = {"cut_sigma_k": "k", "cut_sigma_delta": "delta"}


def analyze(plan: str, other: str, interaction_rows: list) -> None:
    with (SUMMARY / f"{plan}.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    grid = defaultdict(list)
    for row in rows:
        grid[(float(row["sigma"]), float(row[other]))].append(row)
    sigmas = sorted({key[0] for key in grid})
    others = sorted({key[1] for key in grid})

    fig_h, axes_h = plt.subplots(2, 3, figsize=(16, 8.5))
    for (metric, title), axis in zip(METRICS, np.ravel(axes_h)):
        matrix = np.full((len(others), len(sigmas)), np.nan)
        for i, ov in enumerate(others):
            for j, sv in enumerate(sigmas):
                values = [float(r[metric]) for r in grid.get((sv, ov), ())
                          if r.get(metric)]
                if values:
                    matrix[i, j] = np.mean(values)
        image = axis.imshow(matrix, aspect="auto", origin="lower",
                            cmap="viridis",
                            extent=None)
        axis.set_xticks(range(len(sigmas)), [f"{s:g}" for s in sigmas],
                        fontsize=7)
        axis.set_yticks(range(len(others)), [f"{o:g}" for o in others],
                        fontsize=8)
        axis.set_xlabel("σ"); axis.set_ylabel(other)
        axis.set_title(title, fontsize=10)
        fig_h.colorbar(image, ax=axis, shrink=0.85)
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                if np.isfinite(matrix[i, j]):
                    axis.text(j, i, f"{matrix[i, j]:.2f}", ha="center",
                              va="center", fontsize=6, color="white")
    fig_h.suptitle(f"Coupe {plan} — moyennes inter-graines (T=2000, "
                   "graines 1-3, exploratoire)")
    fig_h.tight_layout()
    fig_h.savefig(FIG_DIR / f"{plan}_heat.png", dpi=140, bbox_inches="tight")
    plt.close(fig_h)

    fig_l, axes_l = plt.subplots(2, 3, figsize=(16, 8.5))
    for (metric, title), axis in zip(METRICS, np.ravel(axes_l)):
        for ov in others:
            means, sds = [], []
            for sv in sigmas:
                values = [float(r[metric]) for r in grid.get((sv, ov), ())
                          if r.get(metric)]
                means.append(np.mean(values) if values else np.nan)
                sds.append(np.std(values) if values else np.nan)
            axis.errorbar(sigmas, means, yerr=sds, marker="o", ms=3,
                          capsize=2, lw=1.1, label=f"{other}={ov:g}")
        axis.set_xlabel("σ"); axis.set_title(title, fontsize=10)
        axis.grid(alpha=0.25); axis.legend(fontsize=7)
        # indice d'interaction : contraste extrême du 2e facteur selon sigma
        lo_level, hi_level = others[0], others[-1]
        contrasts = []
        for sv in sigmas:
            v_lo = [float(r[metric]) for r in grid.get((sv, lo_level), ()) if r.get(metric)]
            v_hi = [float(r[metric]) for r in grid.get((sv, hi_level), ()) if r.get(metric)]
            if v_lo and v_hi:
                contrasts.append(np.mean(v_hi) - np.mean(v_lo))
        contrasts = np.asarray(contrasts)
        if len(contrasts) > 2 and np.mean(np.abs(contrasts)) > 0:
            interaction_rows.append({
                "plan": plan, "metric": metric,
                "contrast_mean": round(float(contrasts.mean()), 4),
                "contrast_sd_over_sigma": round(float(contrasts.std()), 4),
                "relative_variation": round(float(contrasts.std() / np.mean(np.abs(contrasts))), 3),
                "sign_change": int(np.nanmin(contrasts) < 0 < np.nanmax(contrasts)),
            })
    fig_l.suptitle(f"Coupe {plan} — courbes σ par niveau de {other}")
    fig_l.tight_layout()
    fig_l.savefig(FIG_DIR / f"{plan}_lines.png", dpi=140, bbox_inches="tight")
    plt.close(fig_l)


def main() -> None:
    interaction_rows: list = []
    for plan, other in CUTS.items():
        analyze(plan, other, interaction_rows)
    path = SUMMARY / "cut_interactions.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(interaction_rows[0].keys()))
        writer.writeheader(); writer.writerows(interaction_rows)
    print(path)
    for row in interaction_rows:
        print(row)


if __name__ == "__main__":
    main()
