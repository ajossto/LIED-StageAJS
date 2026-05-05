"""
Génère les figures de surface 3D + heatmap 2D pour les 4 cartes de couplage.

Sources : rerun_ts_coupling_*.json dans results/.
Critère de stationnarité : bounded_tail AND flow_balanced (|ratio_faillites/λ - 1| < 0.15).

Sorties :
  figures/map_3d_lambda_k.png
  figures/map_3d_k_mu.png
  figures/map_3d_sigma_k.png
  figures/map_3d_theta_delta.png
  + version _heatmap.png pour chacune

Usage :
  python generate_3d_maps.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"
FIGURES.mkdir(exist_ok=True)

FLOW_THRESHOLD = 0.15


def load_campaign(fname: str) -> list[dict]:
    path = RESULTS / fname
    if not path.exists():
        print(f"[SKIP] {fname} absent.")
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def compute_point(runs: list[dict]) -> dict:
    """Agrège les métriques d'un groupe de seeds en un point de la carte."""
    bounded = []
    stationary = []
    n_alive_vals = []
    gini_vals = []
    flr_vals = []
    for r in runs:
        bt = r.get("regime_diagnostics", {}).get("bounded_tail", False) or False
        flr = r.get("measure_failure_lambda_ratio", 0.0) or 0.0
        fb = abs(flr - 1.0) < FLOW_THRESHOLD
        stat = bt and fb
        bounded.append(bt)
        stationary.append(stat)
        flr_vals.append(flr)
        if stat:
            n_alive_vals.append(r.get("measure_n_alive_mean", 0))
            gini_vals.append(r.get("measure_gini_actif_mean", 0))
    n = len(runs)
    return {
        "n": n,
        "bounded_rate": sum(bounded) / n,
        "stationary_rate": sum(stationary) / n,
        "stationary_std": (sum((x - sum(stationary)/n)**2 for x in stationary) / n) ** 0.5 if n > 1 else 0,
        "n_alive_mean": sum(n_alive_vals) / len(n_alive_vals) if n_alive_vals else float("nan"),
        "gini_mean": sum(gini_vals) / len(gini_vals) if gini_vals else float("nan"),
        "flr_mean": sum(flr_vals) / n,
        "flr_std": (sum((x - sum(flr_vals)/n)**2 for x in flr_vals) / n) ** 0.5 if n > 1 else 0,
    }


def make_grid(data: list[dict], x_key: str, y_key: str,
              x_param: str, y_param: str) -> tuple:
    """Construit les grilles X, Y, Z pour l'affichage."""
    groups: dict[tuple, list] = defaultdict(list)
    for r in data:
        px = r.get("params", {}).get(x_param)
        py = r.get("params", {}).get(y_param)
        if px is not None and py is not None:
            groups[(round(float(px), 6), round(float(py), 6))].append(r)
    points = {k: compute_point(v) for k, v in groups.items()}
    xs = sorted(set(k[0] for k in points))
    ys = sorted(set(k[1] for k in points))
    return xs, ys, points


def _make_heatmap_grid(xs, ys, points, field):
    grid = np.full((len(ys), len(xs)), np.nan)
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            pt = points.get((round(x, 6), round(y, 6)))
            if pt is not None:
                v = pt.get(field, float("nan"))
                grid[i, j] = v if not math.isnan(v) else np.nan
    return grid


def plot_campaign(data, x_param, y_param, x_label, y_label, title_prefix, out_prefix):
    """Génère figure 3D + heatmap pour une campagne."""
    if not data:
        print(f"[SKIP] {out_prefix} : données vides.")
        return

    xs, ys, points = make_grid(data, x_param, y_param, x_param, y_param)
    if not xs or not ys:
        print(f"[SKIP] {out_prefix} : pas de points valides.")
        return

    # ── Figure 3D ────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(18, 5))
    titles = ["Taux stationnarité", "n_alive en régime", "Gini en régime", "Variabilité inter-seeds"]
    fields = ["stationary_rate", "n_alive_mean", "gini_mean", "stationary_std"]

    for subplot_i, (field, subtitle) in enumerate(zip(fields, titles)):
        ax = fig.add_subplot(1, 4, subplot_i + 1, projection="3d")
        grid = _make_heatmap_grid(xs, ys, points, field)
        X, Y = np.meshgrid(xs, ys)
        valid = ~np.isnan(grid)
        if valid.any():
            surf = ax.plot_surface(X, Y, np.where(np.isnan(grid), 0, grid),
                                   cmap="viridis", alpha=0.85, linewidth=0)
            fig.colorbar(surf, ax=ax, shrink=0.5, pad=0.1)
        ax.set_xlabel(x_label, fontsize=8)
        ax.set_ylabel(y_label, fontsize=8)
        ax.set_title(subtitle, fontsize=9)
        ax.tick_params(labelsize=7)

    fig.suptitle(f"{title_prefix} — surfaces 3D (n={list(points.values())[0]['n']} seeds/pt)", fontsize=10)
    fig.tight_layout()
    out = FIGURES / f"{out_prefix}_3d.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"  → {out}")

    # ── Heatmap 2D ───────────────────────────────────────────────────────────
    fig2, axes = plt.subplots(1, 4, figsize=(18, 4))
    for ax, field, subtitle in zip(axes, fields, titles):
        grid = _make_heatmap_grid(xs, ys, points, field)
        if field == "stationary_rate":
            cmap, vmin, vmax = "RdYlGn", 0, 1
        elif field == "n_alive_mean":
            cmap, vmin, vmax = "Blues", 0, None
        elif field == "gini_mean":
            cmap, vmin, vmax = "Oranges", 0, 1
        else:
            cmap, vmin, vmax = "Purples", 0, None
        im = ax.imshow(grid, origin="lower", aspect="auto",
                       cmap=cmap, vmin=vmin, vmax=vmax,
                       extent=[xs[0], xs[-1], ys[0], ys[-1]])
        ax.set_xlabel(x_label, fontsize=9)
        ax.set_ylabel(y_label, fontsize=9)
        ax.set_title(subtitle, fontsize=9)
        fig2.colorbar(im, ax=ax, shrink=0.8)
        # Annotations
        grid2 = _make_heatmap_grid(xs, ys, points, field)
        for i, y in enumerate(ys):
            for j, x in enumerate(xs):
                v = grid2[i, j]
                if not math.isnan(v):
                    ax.text(x, y, f"{v:.2f}", ha="center", va="center",
                            fontsize=6.5, color="white" if v < 0.5 and field == "stationary_rate" else "black")
    fig2.suptitle(f"{title_prefix} — heatmaps 2D", fontsize=10)
    fig2.tight_layout()
    out2 = FIGURES / f"{out_prefix}_heatmap.png"
    fig2.savefig(out2, dpi=130)
    plt.close(fig2)
    print(f"  → {out2}")


def main():
    FIGURES.mkdir(exist_ok=True)

    # ── λ × k ────────────────────────────────────────────────────────────────
    print("λ × k…")
    data = load_campaign("rerun_ts_coupling_lambda_k.json")
    plot_campaign(data, "lambda_creation", "n_candidats_pool", "λ (lambda_creation)", "k",
                  "Couplage λ × k", "map_lambda_k")

    # ── k × μ ────────────────────────────────────────────────────────────────
    print("k × μ…")
    data = load_campaign("rerun_ts_coupling_k_mu.json")
    plot_campaign(data, "n_candidats_pool", "mu", "k", "μ (mu)",
                  "Couplage k × μ", "map_k_mu")

    # ── σ × k ────────────────────────────────────────────────────────────────
    print("σ × k…")
    data = load_campaign("rerun_ts_coupling_sigma_k.json")
    plot_campaign(data, "alpha_sigma_brownien", "n_candidats_pool", "σ_α", "k",
                  "Couplage σ_α × k", "map_sigma_k")

    # ── θ × δ_endo ────────────────────────────────────────────────────────────
    print("θ × δ…")
    data = load_campaign("rerun_ts_coupling_theta_depr.json")
    plot_campaign(data, "theta", "taux_depreciation_endo", "θ", "δ_endo",
                  "Couplage θ × δ_endo", "map_theta_delta")

    print(f"\nTous les fichiers dans {FIGURES}")


if __name__ == "__main__":
    main()
