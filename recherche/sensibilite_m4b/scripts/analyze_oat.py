"""Analyse OAT : courbes par axe, incertitude inter-graines, contrastes appariés.

Lit results/summary/oat.csv (produit par extract_metrics.py) et produit :
- figures/oat_<axe>.png : panneaux métrique par métrique le long de l'axe,
  points par graine reliés au centre (appariement) ;
- results/summary/oat_contrasts.csv : contraste apparié (cellule - centre,
  même graine) pour chaque métrique, moyenne et écart-type inter-graines.

Analyse exploratoire (graines 1-3, T=2000) au sens du protocole.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs as L

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG_DIR = L.CAMPAIGN_ROOT / "figures"
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary"

CENTER = dict(lam=30.0, delta=0.05, sigma=0.25, K0=25.0, k=3)
AXES = ("delta", "sigma", "K0", "k", "lam")

METRICS = [
    ("N_over_lambda", "population / λ (N/λ)"),
    ("deaths_rate", "taux de mortalité (morts/pas/tête)"),
    ("age_death_mean", "âge moyen au décès (pas)"),
    ("K_per_capita", "capital par tête (J)"),
    ("loans_per_capita", "prêts par tête"),
    ("debt_to_K", "dette / capital (final)"),
    ("gini_K", "Gini du capital"),
    ("branching_ratio", "rapport de branchement b"),
    ("alpha_pl", "exposant α (s_min=2)"),
    ("susceptibility", "susceptibilité ⟨s²⟩/⟨s⟩"),
    ("av_max_over_pop", "avalanche max / population"),
    ("cutoff_sc", "coupure s_c (loi tronquée)"),
]


def load_rows(plan: str) -> list[dict]:
    with (SUMMARY / f"{plan}.csv").open() as stream:
        return list(csv.DictReader(stream))


def cell_key(row: dict) -> tuple:
    return (float(row["lam"]), float(row["delta"]), float(row["sigma"]),
            float(row["K0"]), int(row["k"]))


def is_center(key: tuple) -> bool:
    return key == (CENTER["lam"], CENTER["delta"], CENTER["sigma"],
                   CENTER["K0"], CENTER["k"])


def axis_of(key: tuple) -> str | None:
    """Axe OAT auquel appartient la cellule (None si plusieurs différences)."""
    names = ("lam", "delta", "sigma", "K0", "k")
    diffs = [n for n, v in zip(names, key) if float(v) != float(CENTER[n])]
    if len(diffs) == 0:
        return "centre"
    if len(diffs) == 1:
        return diffs[0]
    return None


def value(row: dict, metric: str) -> float:
    raw = row.get(metric, "")
    return float(raw) if raw not in ("", None) else np.nan


def main() -> None:
    rows = load_rows("oat")
    by_cell = defaultdict(dict)
    for row in rows:
        by_cell[cell_key(row)][int(row["seed"])] = row
    seeds = sorted({int(row["seed"]) for row in rows})
    center_rows = next(v for k, v in by_cell.items() if is_center(k))

    contrast_rows = []
    for axis in AXES:
        cells = {key: v for key, v in by_cell.items()
                 if axis_of(key) in (axis, "centre")}
        index = ("lam", "delta", "sigma", "K0", "k").index(axis)
        values = sorted({key[index] for key in cells})
        fig, axes_grid = plt.subplots(3, 4, figsize=(17, 10))
        for panel, (metric, title) in zip(np.ravel(axes_grid), METRICS):
            means, sds = [], []
            for v in values:
                key = tuple(CENTER[n] if n != axis else v
                            for n in ("lam", "delta", "sigma", "K0", "k"))
                cell = by_cell.get(key, {})
                ys = [value(cell[s], metric) for s in seeds if s in cell]
                means.append(np.nanmean(ys) if ys else np.nan)
                sds.append(np.nanstd(ys) if ys else np.nan)
                for s in seeds:
                    if s in cell:
                        panel.plot(v, value(cell[s], metric), "o", ms=3,
                                   color="C0", alpha=0.45)
            panel.errorbar(values, means, yerr=sds, color="C3", lw=1.4,
                           marker="s", ms=4, capsize=3)
            panel.set_title(title, fontsize=9)
            panel.grid(alpha=0.25)
            if axis in ("K0",):
                panel.set_xscale("log")
            panel.set_xlabel(axis, fontsize=8)
        for panel in np.ravel(axes_grid)[len(METRICS):]:
            panel.axis("off")
        fig.suptitle(f"OAT {axis} — moyenne ± écart-type inter-graines "
                     f"(graines {seeds}, T=2000, exploratoire)", fontsize=12)
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"oat_{axis}.png", dpi=140, bbox_inches="tight")
        plt.close(fig)

        # contrastes appariés vs centre
        for key in cells:
            if axis_of(key) == "centre":
                continue
            cell = by_cell[key]
            for metric, _ in METRICS:
                deltas = [value(cell[s], metric) - value(center_rows[s], metric)
                          for s in seeds if s in cell and s in center_rows]
                deltas = [d for d in deltas if np.isfinite(d)]
                if not deltas:
                    continue
                contrast_rows.append({
                    "axis": axis, "value": key[index], "metric": metric,
                    "delta_mean": float(np.mean(deltas)),
                    "delta_sd": float(np.std(deltas, ddof=1)) if len(deltas) > 1 else np.nan,
                    "n_seeds": len(deltas),
                })

    path = SUMMARY / "oat_contrasts.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(contrast_rows[0].keys()))
        writer.writeheader()
        writer.writerows(contrast_rows)
    print(f"contrastes : {path}")
    print(f"figures : {FIG_DIR}/oat_<axe>.png")


if __name__ == "__main__":
    main()
