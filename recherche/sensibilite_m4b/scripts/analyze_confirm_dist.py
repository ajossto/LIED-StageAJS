"""Analyses distributionnelles et temporelles des runs confirmatoires.

Depuis les instantanés périodiques (tous les 100 pas, t >= T/4) des lots
Simulation Lab :

1. trajectoires du Gini du capital et renouvellement du top 1 % (recouvrement
   de Jaccard des ensembles d'identifiants entre instantanés consécutifs) ;
2. CCDF de K et du revenu au dernier instantané, par graine (jamais de
   pooling inter-graines pour les ajustements) ;
3. scaling de taille : susceptibilité, taille maximale et coupure par
   graine en fonction de lambda (cellules ref_lam10 / centre_lam30 /
   lam100), avec pente log-log de la susceptibilité ;
4. table des lois d'avalanches par cellule : alpha (moyenne ± écart-type
   inter-graines), b, Vuong, LRT coupure — depuis les métriques déjà
   extraites par analyze_confirm.py.

Sorties : figures/confirm_gini_renewal.png, confirm_ccdf.png,
confirm_scaling.png ; results/summary/confirm_laws.csv.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs as L

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LAB_RUNS = Path("/home/anatole/jupyter/simulation_lab_data/runs")
MANIFEST = L.CAMPAIGN_ROOT / "manifests" / "confirm_lab.json"
METRICS_DIR = L.CAMPAIGN_ROOT / "results" / "metrics_confirm"
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary"
FIG_DIR = L.CAMPAIGN_ROOT / "figures"

GINI_CELLS = ["centre_lam30", "sigma0", "sigma010", "sigma050", "k2", "k10"]
CCDF_CELLS = ["centre_lam30", "sigma0", "k2", "k10"]


def gini(values: np.ndarray) -> float:
    values = np.sort(values[np.isfinite(values) & (values >= 0)])
    n = len(values)
    if n == 0 or values.sum() <= 0:
        return 0.0
    return float((2 * np.dot(np.arange(1, n + 1), values) / values.sum() - n - 1) / n)


def snapshots_after_burn(run_dir: Path, burn: int):
    for path in sorted((run_dir / "snapshots").glob("entities_t*.npz")):
        t = int(path.stem.split("_t")[1])
        if t >= burn:
            with np.load(path) as data:
                yield t, {key: data[key].copy() for key in data.files}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    cells = {entry["cell"]: entry for entry in manifest["cells"]}

    # ---------- 1. Gini(t) et renouvellement du top 1 % ----------
    fig, (axis_g, axis_r) = plt.subplots(1, 2, figsize=(14, 5))
    renewal_summary = {}
    for index, name in enumerate(GINI_CELLS):
        if name not in cells:
            continue
        color = f"C{index}"
        T = cells[name]["parameters"]["T"]
        burn = T // 4
        renewal_cell = []
        for pos, run_id in enumerate(cells[name]["run_ids"]):
            times, ginis, overlaps = [], [], []
            previous_top: set | None = None
            for t, snap in snapshots_after_burn(LAB_RUNS / run_id, burn):
                K = snap["K"]
                if len(K) < 20:
                    continue
                times.append(t)
                ginis.append(gini(K))
                n_top = max(1, len(K) // 100)
                top = set(np.asarray(snap["id"])[np.argsort(K)[-n_top:]].tolist())
                if previous_top:
                    union = len(top | previous_top)
                    overlaps.append(len(top & previous_top) / union if union else np.nan)
                previous_top = top
            if times:
                axis_g.plot(times, ginis, color=color, alpha=0.5, lw=0.8,
                            label=name if pos == 0 else None)
            if overlaps:
                renewal_cell.append(float(np.nanmean(overlaps)))
        if renewal_cell:
            renewal_summary[name] = (float(np.mean(renewal_cell)),
                                     float(np.std(renewal_cell)))
    axis_g.set_xlabel("t"); axis_g.set_ylabel("Gini du capital")
    axis_g.set_title("Gini(t) après burn-in — 5 graines par cellule")
    axis_g.grid(alpha=0.25); axis_g.legend(fontsize=8)
    names = list(renewal_summary)
    means = [renewal_summary[n][0] for n in names]
    sds = [renewal_summary[n][1] for n in names]
    axis_r.bar(range(len(names)), means, yerr=sds, capsize=4, color="C0", alpha=0.8)
    axis_r.set_xticks(range(len(names)), names, rotation=30, fontsize=8)
    axis_r.set_ylabel("recouvrement de Jaccard moyen (top 1 % de K)\nentre instantanés à 100 pas")
    axis_r.set_title("Persistance du haut de la distribution")
    axis_r.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "confirm_gini_renewal.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # ---------- 2. CCDF de K et du revenu (dernier instantané) ----------
    fig, axes = plt.subplots(2, len(CCDF_CELLS), figsize=(4.2 * len(CCDF_CELLS), 8),
                             sharey="row")
    for column, name in enumerate(CCDF_CELLS):
        if name not in cells:
            continue
        for row_index, field in enumerate(("K", "income")):
            axis = axes[row_index][column]
            for run_id in cells[name]["run_ids"]:
                snaps = sorted((LAB_RUNS / run_id / "snapshots").glob("entities_t*.npz"))
                if not snaps:
                    continue
                with np.load(snaps[-1]) as data:
                    values = data[field]
                values = np.sort(values[values > 0])[::-1]
                if len(values) < 10:
                    continue
                ccdf = np.arange(1, len(values) + 1) / len(values)
                axis.loglog(values, ccdf, lw=0.8, alpha=0.6)
            axis.set_title(f"{name} — {field}", fontsize=9)
            axis.grid(alpha=0.25, which="both")
            if column == 0:
                axis.set_ylabel("CCDF")
            if row_index == 1:
                axis.set_xlabel("valeur (J)")
    fig.suptitle("CCDF de K et du revenu brut, dernier instantané — une courbe par graine "
                 "(pas de pooling)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "confirm_ccdf.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # ---------- 3. scaling de taille ----------
    size_cells = [("ref_lam10", 10.0), ("centre_lam30", 30.0), ("lam100", 100.0)]
    quantities = {"susceptibility": [], "av_size_max": [], "cutoff_sc": []}
    for name, lam in size_cells:
        for run_id in cells[name]["run_ids"]:
            path = METRICS_DIR / f"{run_id}.json"
            if not path.exists():
                continue
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from extract_metrics import flat_row
            row = flat_row(json.loads(path.read_text()))
            for quantity in quantities:
                value = row.get(quantity)
                if value is not None and np.isfinite(value):
                    quantities[quantity].append((lam, float(value), row.get("av_size_max")))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    labels = {"susceptibility": "susceptibilité ⟨s²⟩/⟨s⟩",
              "av_size_max": "taille maximale d'avalanche",
              "cutoff_sc": "coupure ŝ_c (non tracée si > 4·s_max)"}
    for axis, (quantity, points) in zip(axes, quantities.items()):
        xs = np.array([p[0] for p in points]); ys = np.array([p[1] for p in points])
        if quantity == "cutoff_sc":
            smax = np.array([p[2] or np.inf for p in points])
            keep = ys < 4 * smax
            xs, ys = xs[keep], ys[keep]
        axis.loglog(xs, ys, "o", ms=5, alpha=0.7)
        if len(np.unique(xs)) > 1 and len(xs) > 3:
            slope, intercept = np.polyfit(np.log(xs), np.log(ys), 1)
            grid = np.linspace(np.log(xs.min()), np.log(xs.max()), 10)
            axis.plot(np.exp(grid), np.exp(intercept + slope * grid), "r--",
                      label=f"pente log-log = {slope:.2f}")
            axis.legend(fontsize=8)
        axis.set_xlabel("λ"); axis.set_title(labels[quantity], fontsize=10)
        axis.grid(alpha=0.25, which="both")
    fig.suptitle("Scaling de taille — cellules confirmatoires λ=10/30/100, points par graine")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "confirm_scaling.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # ---------- 4. table des lois par cellule ----------
    rows = []
    for name, entry in cells.items():
        if name == "lam2_ext":
            continue
        alphas, branchings, vuongs, lrts, cutoffs, smaxs = [], [], [], [], [], []
        for run_id in entry["run_ids"]:
            path = METRICS_DIR / f"{run_id}.json"
            if not path.exists():
                continue
            metrics = json.loads(path.read_text())
            avalanche = metrics["windows"].get("burn0.25", {}).get("avalanches", {})
            if not avalanche.get("identifiable"):
                continue
            if avalanche.get("powerlaw"):
                alphas.append(avalanche["powerlaw"]["alpha"])
            if avalanche.get("branching_ratio") is not None:
                branchings.append(avalanche["branching_ratio"])
            if avalanche.get("vuong_pl_vs_ln"):
                vuongs.append(avalanche["vuong_pl_vs_ln"]["z"])
            if avalanche.get("lrt_cutoff_vs_pure"):
                lrts.append(avalanche["lrt_cutoff_vs_pure"]["p_value"])
            if avalanche.get("powerlaw_cutoff"):
                cutoffs.append(avalanche["powerlaw_cutoff"]["cutoff"])
            if avalanche.get("size_max"):
                smaxs.append(avalanche["size_max"])
        def fmt(values):
            return (round(float(np.mean(values)), 4),
                    round(float(np.std(values, ddof=1)), 4)) if len(values) > 1 else (None, None)
        rows.append({
            "cell": name, "n_seeds": len(alphas),
            "alpha_mean": fmt(alphas)[0], "alpha_sd": fmt(alphas)[1],
            "b_mean": fmt(branchings)[0], "b_sd": fmt(branchings)[1],
            "vuong_mean": fmt(vuongs)[0], "vuong_sd": fmt(vuongs)[1],
            "vuong_all_neg": int(all(v < 0 for v in vuongs)) if vuongs else None,
            "vuong_all_pos": int(all(v > 0 for v in vuongs)) if vuongs else None,
            "lrt_p_max": round(float(np.max(lrts)), 6) if lrts else None,
            "cutoff_mean": fmt(cutoffs)[0],
            "smax_mean": fmt(smaxs)[0],
        })
    with (SUMMARY / "confirm_laws.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)

    print("figures :", FIG_DIR / "confirm_gini_renewal.png",
          FIG_DIR / "confirm_ccdf.png", FIG_DIR / "confirm_scaling.png")
    print("table   :", SUMMARY / "confirm_laws.csv")
    print("renouvellement top1% :", {k: (round(v[0], 3), round(v[1], 3))
                                     for k, v in renewal_summary.items()})


if __name__ == "__main__":
    main()
