"""Figures pour le facteur d'admissibilite (critere 1 revise, bootstrap
KS re-scanne a chaque tirage). Deux figures :

- fig10 : exemple travaille (baseline, seed0, t=2225) -- distribution
  bootstrap des seuils selectionnes (diagnostic direct du "coude" signale
  par l'utilisateur : un second mode/etalement au-dela du seuil primaire
  serait visible ici), courbe z-score/flatness, et CCDF avec l'enveloppe
  des refits bootstrap.
- fig11 : classement des 37 cellules par A moyen (toutes graines,
  instantanes selectionnes confondus), style barres horizontales comme
  fig9.

Lit results/admissibility_all_runs.csv (produit par
admissibility_rollout.py) pour fig11 ; refait un calcul UNIQUE et
instrumente pour fig10 (les diagnostics bruts bootstrap ne sont pas
persistes dans le CSV en masse, trop volumineux)."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import interest_income  # noqa: E402
import tail_test  # noqa: E402
from admissibility_factor import admissibility_factor, MIN_N, X_TARGET  # noqa: E402

OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10,
    "axes.grid": True, "grid.alpha": 0.25,
})


def fig_worked_example():
    RUN_DIR = ROOT / "results" / "campaign" / "baseline" / "seed0"
    snaps = interest_income.load_all_entity_snapshots(RUN_DIR, t_min=750, t_max=3000)
    snap = dict(snaps)[2225]
    p0, positive = interest_income.zero_mass_and_positive(snap["int_in"])
    best = tail_test.fit_powerlaw_xmin(positive, min_tail=MIN_N)
    seuil = best["x_min"]
    rng = np.random.default_rng(0)
    result = admissibility_factor(positive, seuil, rng)

    boot_seuil = np.array(result["boot_seuil"])
    boot_seuil = boot_seuil[np.isfinite(boot_seuil)]
    grid_x = np.array(result["grid_x"])
    z = np.array(result["z"])
    f = np.array(result["f"])

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))

    ax = axes[0]
    ax.hist(boot_seuil, bins=30, color="#555555", alpha=0.8)
    ax.axvline(seuil, color="crimson", lw=2, label=f"seuil sur données réelles = {seuil:.1f}")
    ax.set_xlabel("seuil KS-optimal par tirage bootstrap")
    ax.set_ylabel(f"nombre de tirages (sur {len(boot_seuil)}/{len(result['boot_seuil'])} valides)")
    ax.set_title("A. Où le KS re-sélectionne le seuil\nsur 300 tirages bootstrap")
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.plot(grid_x, z, "o-", color="#1f77b4", label="z = |Δα| / écart-type bootstrap")
    ax.axhline(1.0, color="gray", ls="--", lw=1, label="z=1 (1 écart-type)")
    ax2 = ax.twinx()
    ax2.plot(grid_x, f, "s--", color="crimson", alpha=0.6, label="f = exp(-z²/2)")
    ax2.set_ylabel("f (score de platitude)", color="crimson")
    ax.set_xlabel("facteur x (seuil testé = x·seuil)")
    ax.set_ylabel("z-score", color="#1f77b4")
    ax.set_title(f"B. Platitude sur la plage testable\nx_max={result['x_max']:.2f}, "
                 f"couverture={result['coverage']:.2f}, flatness={result['flatness']:.2f}")

    ax = axes[2]
    x_ccdf = np.sort(positive)
    n = len(x_ccdf)
    ccdf = 1.0 - np.arange(0, n) / n
    ax.plot(x_ccdf, ccdf, ".", color="#888888", ms=3, alpha=0.5, label=f"données (n={n})")
    xr = np.geomspace(seuil, positive.max(), 100)
    yr = (seuil / xr) ** (best["alpha"] - 1) * (best["n_tail"] / n)
    ax.plot(xr, yr, "-", color="crimson", lw=2, label=f"seuil réel : α̂={best['alpha']:.2f}")
    boot_alpha0 = np.array(result["boot_alpha"])[:, 0]
    sel = np.isfinite(boot_seuil) & np.isfinite(boot_alpha0)
    idx = np.random.default_rng(1).choice(np.where(sel)[0], size=min(40, sel.sum()), replace=False)
    for i in idx:
        sb = np.array(result["boot_seuil"])[i]
        ab = boot_alpha0[i]
        xr_b = np.geomspace(sb, positive.max(), 50)
        n_tail_b = (positive >= sb).sum()
        yr_b = (sb / xr_b) ** (ab - 1) * (n_tail_b / n)
        ax.plot(xr_b, yr_b, "-", color="#1f77b4", lw=0.5, alpha=0.15)
    ax.plot([], [], "-", color="#1f77b4", lw=1, alpha=0.5, label="40 refits bootstrap (KS re-scanné)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("intérêts reçus (J/pas, log)")
    ax.set_ylabel("CCDF (log)")
    ax.set_title("C. Enveloppe bootstrap des refits\n(seuil + pente re-sélectionnés à chaque tirage)")
    ax.legend(fontsize=7.5, loc="lower left")

    fig.suptitle(f"Facteur d'admissibilité — exemple travaillé (baseline, seed0, t=2225) — "
                 f"A={result['A']:.2f}", fontsize=11, y=1.03)
    fig.tight_layout()
    out_path = OUT / "fig10_admissibilite_exemple.png"
    fig.savefig(out_path, bbox_inches="tight")
    print(f"écrit : {out_path}  (A={result['A']:.3f}, x_max={result['x_max']:.2f})")


def fig_classification():
    rows = list(csv.DictReader(open(ROOT / "results" / "admissibility_all_runs.csv")))
    cells = defaultdict(list)
    for r in rows:
        if r.get("A") in (None, "", "None"):
            continue
        key = (r["campaign"], r["label"])
        cells[key].append(float(r["A"]))

    entries = []
    for (camp, label), a_vals in cells.items():
        entries.append((f"{label} ({camp[:4]})", np.mean(a_vals), np.std(a_vals), len(a_vals)))
    entries.sort(key=lambda x: x[1])

    labels = [e[0] for e in entries]
    means = [e[1] for e in entries]
    stds = [e[2] for e in entries]
    ns = [e[3] for e in entries]

    fig, ax = plt.subplots(figsize=(9, 10.5))
    y = range(len(entries))
    colors = ["crimson" if m < 0.5 else ("#e8a33d" if m < 0.75 else "#1f77b4") for m in means]
    ax.barh(y, means, xerr=stds, color=colors, height=0.7, capsize=2, ecolor="#999999")
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{l}  (n={n})" for l, n in zip(labels, ns)], fontsize=7)
    ax.axvline(0.5, color="black", ls="--", lw=1)
    ax.set_xlabel("A moyen (facteur d'admissibilité) sur les instantanés sélectionnés\n"
                  "bleu ≥0,75 | orange 0,5-0,75 | rouge <0,5")
    ax.set_title("Classement des 37 cellules par facteur d'admissibilité moyen\n"
                 "(couverture × platitude, bootstrap KS re-scanné, n_min=80)")
    fig.tight_layout()
    out_path = OUT / "fig11_classification_admissibilite.png"
    fig.savefig(out_path, bbox_inches="tight")
    print(f"écrit : {out_path}")


if __name__ == "__main__":
    fig_worked_example()
    fig_classification()
