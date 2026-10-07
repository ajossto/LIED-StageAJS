"""Screening global sur le plan LHS : PRCC, SRC, surface quadratique, variance.

Lit results/summary/lhs.csv et produit :
- results/summary/lhs_screening.csv : pour chaque métrique de réponse,
  PRCC et SRC par paramètre avec IC bootstrap à 95 % (rééchantillonnage
  des points du plan), R² linéaire, R² CV de la surface quadratique,
  importance par permutation, décomposition de variance paramètres/graines ;
- figures/lhs_prcc.png et figures/lhs_src.png : profils par métrique ;
- figures/lhs_scatter_<métrique>.png : nuages métrique vs chaque paramètre.

Analyse exploratoire (graines 1-3, T=2000) au sens du protocole : elle
sert à choisir les coupes 2D et les cellules confirmatoires.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs as L
import lib_screening as S

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG_DIR = L.CAMPAIGN_ROOT / "figures"
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary"

PARAMS = ["delta", "sigma", "log10K0", "k"]
METRICS = [
    "N_over_lambda", "deaths_rate", "age_death_mean", "K_per_capita",
    "loans_per_capita", "debt_to_K", "gini_K", "gini_income",
    "branching_ratio", "alpha_pl", "susceptibility", "av_max_over_pop",
    "cutoff_sc", "depth_max", "nw_negative_frac", "principal_gini",
]


def load(plan: str = "lhs"):
    with (SUMMARY / f"{plan}.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    X, groups, ys, statuses = [], [], {m: [] for m in METRICS}, []
    group_index = {}
    for row in rows:
        key = (row["delta"], row["sigma"], row["K0"], row["k"])
        group_index.setdefault(key, len(group_index))
        X.append([float(row["delta"]), float(row["sigma"]),
                  np.log10(float(row["K0"])), float(row["k"])])
        groups.append(group_index[key])
        statuses.append(row["status"])
        for metric in METRICS:
            raw = row.get(metric, "")
            ys[metric].append(float(raw) if raw not in ("", None) else np.nan)
    return (np.asarray(X), np.asarray(groups),
            {m: np.asarray(v) for m, v in ys.items()}, statuses)


def main() -> None:
    X, groups, ys, statuses = load()
    from collections import Counter
    print("statuts :", dict(Counter(statuses)))

    out_rows = []
    prcc_matrix, src_matrix, kept_metrics = [], [], []
    for metric in METRICS:
        y = ys[metric]
        keep = np.isfinite(y)
        if keep.sum() < 60:
            print(f"{metric}: {keep.sum()} valeurs finies — ignoré")
            continue
        Xk, yk, gk = X[keep], y[keep], groups[keep]
        prcc_pt, prcc_lo, prcc_hi = S.bootstrap_ci(S.prcc, Xk, yk, gk, n_boot=1000)
        src_pt, src_lo, src_hi = S.bootstrap_ci(S.src, Xk, yk, gk, n_boot=1000)
        design = np.hstack([np.ones((len(yk), 1)),
                            (Xk - Xk.mean(0)) / Xk.std(0)])
        beta, *_ = np.linalg.lstsq(design, yk, rcond=None)
        r2_lin = 1 - np.sum((yk - design @ beta) ** 2) / np.sum((yk - yk.mean()) ** 2)
        r2_cv = S.cv_r2_by_group(S.QuadraticSurface, Xk, yk, gk)
        surface = S.QuadraticSurface().fit(Xk, yk)
        importance = S.permutation_importance(surface, Xk, yk)
        decomposition = S.variance_decomposition(yk, gk)
        row = {"metric": metric, "n": int(keep.sum()),
               "r2_linear": round(float(r2_lin), 4),
               "r2_cv_quadratic": round(float(r2_cv), 4),
               **{f"var_{k}": round(float(v), 4) if np.isfinite(v) else ""
                  for k, v in decomposition.items()}}
        for i, name in enumerate(PARAMS):
            row[f"prcc_{name}"] = round(float(prcc_pt[i]), 4)
            row[f"prcc_{name}_lo"] = round(float(prcc_lo[i]), 4)
            row[f"prcc_{name}_hi"] = round(float(prcc_hi[i]), 4)
            row[f"src_{name}"] = round(float(src_pt[i]), 4)
            row[f"src_{name}_lo"] = round(float(src_lo[i]), 4)
            row[f"src_{name}_hi"] = round(float(src_hi[i]), 4)
            row[f"perm_{name}"] = round(float(importance[i]), 4)
        out_rows.append(row)
        prcc_matrix.append(prcc_pt); src_matrix.append(src_pt)
        kept_metrics.append(metric)
        print(f"{metric:18s} R2lin={r2_lin:.2f} R2cv={r2_cv:.2f} "
              f"PRCC={np.round(prcc_pt, 2)} perm={np.round(importance, 3)}")

    path = SUMMARY / "lhs_screening.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(out_rows[0].keys()))
        writer.writeheader(); writer.writerows(out_rows)
    print(f"-> {path}")

    for name, matrix in (("prcc", prcc_matrix), ("src", src_matrix)):
        matrix = np.asarray(matrix)
        fig, axis = plt.subplots(figsize=(7.5, 0.5 * len(kept_metrics) + 2))
        image = axis.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        axis.set_xticks(range(len(PARAMS)), ["δ", "σ", "log₁₀K₀", "k"])
        axis.set_yticks(range(len(kept_metrics)), kept_metrics, fontsize=8)
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                axis.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center",
                          fontsize=7,
                          color="white" if abs(matrix[i, j]) > 0.6 else "black")
        axis.set_title(f"{name.upper()} — plan LHS (λ=30, T=2000, graines 1-3)")
        fig.colorbar(image, shrink=0.8)
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"lhs_{name}.png", dpi=140, bbox_inches="tight")
        plt.close(fig)

    # nuages pour les métriques clés
    for metric in ("N_over_lambda", "gini_K", "branching_ratio", "alpha_pl"):
        y = ys[metric]
        keep = np.isfinite(y)
        fig, panels = plt.subplots(1, 4, figsize=(16, 3.6), sharey=True)
        for j, (panel, name) in enumerate(zip(panels, PARAMS)):
            panel.plot(X[keep, j], y[keep], "o", ms=3, alpha=0.5)
            panel.set_xlabel(name); panel.grid(alpha=0.25)
        panels[0].set_ylabel(metric)
        fig.suptitle(f"{metric} — nuages LHS (exploratoire)")
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"lhs_scatter_{metric}.png", dpi=140,
                    bbox_inches="tight")
        plt.close(fig)
    print(f"figures : {FIG_DIR}/lhs_*.png")


if __name__ == "__main__":
    main()
