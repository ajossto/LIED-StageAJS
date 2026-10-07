"""Dépouillement des pilotes : audit des plages, contrôle temporel, coûts.

Produit :
- un tableau texte par cellule pilote (statut, population, dérive,
  stationnarité, identifiabilité des avalanches, coût) ;
- le contrôle temporel du centre (T=2000 vs 4000, burn-ins) ;
- le contrôle du coin lent (T=8000) ;
- figures/pilotes_*.png : trajectoires de population des coins.

Analyse exploratoire — sert à réviser les bornes avant l'OAT/LHS.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs as L
import lib_metrics as M

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG_DIR = L.CAMPAIGN_ROOT / "figures"
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary" / "pilotes.csv"


def label_of(row: dict) -> str:
    parts = []
    for key, ref in (("lam", 30.0), ("delta", 0.05), ("sigma", 0.25),
                     ("K0", 25.0), ("k", 3), ("T", 2000)):
        value = float(row[key])
        if value != ref:
            parts.append(f"{key}={value:g}")
    return " ".join(parts) if parts else "centre"


def main() -> None:
    with SUMMARY.open() as stream:
        rows = list(csv.DictReader(stream))

    cells = defaultdict(list)
    for row in rows:
        cells[label_of(row)].append(row)

    print(f"{'cellule':38s} {'st':4s} {'pop':>7s} {'dérive':>7s} {'st.1/2':>7s} "
          f"{'N/λ':>6s} {'n_tail':>6s} {'b':>6s} {'α':>5s} {'Gini K':>6s}")
    for label in sorted(cells):
        for row in sorted(cells[label], key=lambda r: int(r["seed"])):
            fmt = lambda key, digits=2: (
                f"{float(row[key]):.{digits}f}" if row.get(key) not in ("", None) else "--")
            print(f"{label:38s} {row['status'][:4]:4s} {fmt('pop_mean',0):>7s} "
                  f"{fmt('pop_rel_drift'):>7s} {fmt('stat_rel_diff'):>7s} "
                  f"{fmt('N_over_lambda',1):>6s} {row.get('av_n_tail') or '--':>6s} "
                  f"{fmt('branching_ratio'):>6s} {fmt('alpha_pl'):>5s} {fmt('gini_K'):>6s}")

    # Coût par cellule (durée du manifeste)
    print("\nCoûts (s) :")
    for label in sorted(cells):
        durations = []
        for row in cells[label]:
            manifest = L.RESULTS_ROOT / row["run_id"] / "manifest.json"
            durations.append(json.loads(manifest.read_text())["duration_seconds"])
        print(f"  {label:38s} {np.mean(durations):7.1f}")

    # Figures : trajectoires de population des coins et contrôles
    FIG_DIR.mkdir(exist_ok=True)
    ordered = sorted(cells)
    n_col = 3
    n_row = (len(ordered) + n_col - 1) // n_col
    fig, axes = plt.subplots(n_row, n_col, figsize=(15, 3.1 * n_row),
                             sharex=False)
    for axis, label in zip(np.ravel(axes), ordered):
        for row in cells[label]:
            series = M.read_series(L.RESULTS_ROOT / row["run_id"])
            axis.plot(series["t"], series["pop"], lw=0.8,
                      label=f"graine {row['seed']}")
        axis.set_title(label, fontsize=9)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=7)
    for axis in np.ravel(axes)[len(ordered):]:
        axis.axis("off")
    fig.suptitle("Pilotes M4B : trajectoires de population", y=1.002)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "pilotes_population.png", dpi=140,
                bbox_inches="tight")
    plt.close(fig)
    print(f"\nfigure : {FIG_DIR / 'pilotes_population.png'}")


if __name__ == "__main__":
    main()
