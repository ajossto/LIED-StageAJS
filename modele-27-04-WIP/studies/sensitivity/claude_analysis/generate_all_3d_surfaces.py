"""
Surfaces 3D pour toutes les campagnes de sensibilité (coarse + adaptatives).

Chaque figure montre :
  - Une surface lissée (plot_surface sur grille régulière) de la fraction bornée
  - Les points de données superposés : taille ∝ demi-IC Wilson 95% (incertitude ↑ quand n↓)
  - Pour les campagnes adaptatives : 4 panneaux en 2×2 (fraction bornée, taux stationnarité,
    n_alive moyen, Gini moyen)

Figures produites (écrasent les anciennes) :
  report/figures/claude_surface_3d_{lambda_k,k_mu,sigma_k,theta_delta}.png  (coarse)
  report/figures/map_{lambda_k,k_mu,sigma_k,theta_delta}_3d.png              (adaptatives)

Usage :
  python generate_all_3d_surfaces.py [--coarse-only] [--adaptive-only]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from scipy.interpolate import griddata

HERE = Path(__file__).resolve().parent.parent
RESULTS = HERE / "results"
FIGURES = HERE / "report" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

FLOW_THRESHOLD = 0.15
Z95 = 1.96


# ── Utilitaires ──────────────────────────────────────────────────────────────

def wilson_half(k: float, n: int) -> float:
    """Demi-largeur de l'IC Wilson 95% pour une proportion k/n."""
    if n == 0:
        return 0.5
    p = k / n
    denom = 1.0 + Z95 ** 2 / n
    return Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n * n)) / denom


def _bounded(r: dict) -> bool:
    return bool((r.get("regime_diagnostics") or {}).get("bounded_tail", False))


def _flow_ok(r: dict) -> bool:
    flr = r.get("measure_failure_lambda_ratio", 0.0) or 0.0
    return abs(flr - 1.0) < FLOW_THRESHOLD


def _fill_nans(X, Y, Z):
    """Remplit les NaN par interpolation nearest-neighbor scipy."""
    flat_x = X.ravel()
    flat_y = Y.ravel()
    flat_z = Z.ravel()
    mask_known = ~np.isnan(flat_z)
    mask_nan = np.isnan(flat_z)
    if not mask_nan.any() or not mask_known.any():
        return Z
    pts_k = np.column_stack([flat_x[mask_known], flat_y[mask_known]])
    vals_k = flat_z[mask_known]
    pts_q = np.column_stack([flat_x[mask_nan], flat_y[mask_nan]])
    filled = griddata(pts_k, vals_k, pts_q, method="nearest")
    Z_out = Z.copy()
    Z_out.ravel()[mask_nan] = filled
    return Z_out


def _interp_fine(xs, ys, Z, factor=4):
    """Interpole la grille sur factor× plus de points (surface lisse)."""
    xs_fine = np.linspace(xs[0], xs[-1], len(xs) * factor)
    ys_fine = np.linspace(ys[0], ys[-1], len(ys) * factor)
    Xf, Yf = np.meshgrid(xs_fine, ys_fine)
    X, Y = np.meshgrid(xs, ys)
    Zf = griddata(
        np.column_stack([X.ravel(), Y.ravel()]),
        Z.ravel(),
        np.column_stack([Xf.ravel(), Yf.ravel()]),
        method="linear",
    ).reshape(Xf.shape)
    # Remplir les bords (extrapolation nearest)
    Zf_nn = griddata(
        np.column_stack([X.ravel(), Y.ravel()]),
        Z.ravel(),
        np.column_stack([Xf.ravel(), Yf.ravel()]),
        method="nearest",
    ).reshape(Xf.shape)
    Zf = np.where(np.isnan(Zf), Zf_nn, Zf)
    return Xf, Yf, Zf


# ── Agrégation ───────────────────────────────────────────────────────────────

def aggregate_adaptive(data: list, x_param: str, y_param: str) -> tuple:
    """Agrège les runs adaptatifs en points (x, y) → métriques."""
    groups: dict[tuple, list] = defaultdict(list)
    for r in data:
        x = r.get("params", {}).get(x_param)
        y = r.get("params", {}).get(y_param)
        if x is not None and y is not None:
            groups[(round(float(x), 6), round(float(y), 6))].append(r)

    xs = sorted(set(k[0] for k in groups))
    ys = sorted(set(k[1] for k in groups))
    points = {}
    for (x, y), runs in groups.items():
        n = len(runs)
        n_bt = sum(1 for r in runs if _bounded(r))
        n_stat = sum(1 for r in runs if _bounded(r) and _flow_ok(r))
        alive_v = [r.get("measure_n_alive_mean") for r in runs
                   if _bounded(r) and _flow_ok(r) and r.get("measure_n_alive_mean") is not None]
        gini_v = [r.get("measure_gini_actif_mean") for r in runs
                  if _bounded(r) and _flow_ok(r) and r.get("measure_gini_actif_mean") is not None]
        points[(x, y)] = {
            "n": n,
            "bounded_rate": n_bt / n,
            "stationary_rate": n_stat / n,
            "n_alive": float(np.mean(alive_v)) if alive_v else float("nan"),
            "gini": float(np.mean(gini_v)) if gini_v else float("nan"),
            "w_half": wilson_half(n_bt, n),
        }
    return xs, ys, points


def aggregate_coarse(data: list, x_key: str, y_key: str) -> tuple:
    """Agrège les données coarse (format agrégé JSON) en points."""
    groups: dict[tuple, dict] = {}
    for d in data:
        x = d[x_key]
        y = d[y_key]
        groups[(round(float(x), 6), round(float(y), 6))] = {
            "n": d.get("n", 3),
            "bounded_rate": d.get("bounded_share", float("nan")),
            "stationary_rate": float("nan"),
            "n_alive": d.get("alive_mean", float("nan")),
            "gini": d.get("gini_mean", float("nan")),
            "w_half": wilson_half(round(d.get("bounded_share", 0) * d.get("n", 3)),
                                  d.get("n", 3)),
        }
    xs = sorted(set(k[0] for k in groups))
    ys = sorted(set(k[1] for k in groups))
    return xs, ys, groups


def _build_grid(xs, ys, points: dict, field: str):
    """Construit X, Y, Z (meshgrid) + vecteurs scatter xs_sc, ys_sc, zs_sc, ws_sc, ns_sc."""
    X, Y = np.meshgrid(xs, ys)
    Z = np.full_like(X, np.nan, dtype=float)
    Ws = np.full_like(X, 0.5, dtype=float)
    Ns = np.zeros_like(X, dtype=int)
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            pt = points.get((round(x, 6), round(y, 6)))
            if pt is not None:
                v = pt.get(field, float("nan"))
                Z[i, j] = v if not (isinstance(v, float) and math.isnan(v)) else np.nan
                Ws[i, j] = pt.get("w_half", 0.5)
                Ns[i, j] = pt.get("n", 0)
    Z = _fill_nans(X, Y, Z)
    return X, Y, Z, Ws, Ns


# ── Dessin d'un panneau ───────────────────────────────────────────────────────

def _draw_panel(ax, xs, ys, points: dict, field: str,
                xlabel: str, ylabel: str, title: str,
                vmin: float = None, vmax: float = None,
                cmap: str = "viridis",
                invert_x: bool = False, invert_y: bool = False,
                elev: float = 28, azim: float = -55,
                show_uncertainty: bool = True):
    """Dessine surface + scatter incertitude sur ax."""
    X, Y, Z, Ws, Ns = _build_grid(xs, ys, points, field)
    _vmin = vmin if vmin is not None else float(np.nanmin(Z))
    _vmax = vmax if vmax is not None else float(np.nanmax(Z))
    if _vmin == _vmax:
        _vmax = _vmin + 1e-6

    # Surface fine interpolée
    Xf, Yf, Zf = _interp_fine(xs, ys, Z, factor=5)
    Zf = np.clip(Zf, _vmin, _vmax)
    surf = ax.plot_surface(Xf, Yf, Zf, cmap=cmap, vmin=_vmin, vmax=_vmax,
                           alpha=0.72, linewidth=0, antialiased=True)

    if show_uncertainty:
        # Scatter des points réels : taille ∝ demi-IC Wilson (incertitude)
        xs_sc = X.ravel()
        ys_sc = Y.ravel()
        zs_sc = Z.ravel()
        ws_sc = Ws.ravel()
        ns_sc = Ns.ravel()

        # Taille : plus grand = plus incertain (IC large = peu de seeds)
        w_max = max(ws_sc) if ws_sc.max() > 0 else 1.0
        sizes = np.clip(30 + 350 * (ws_sc / w_max), 30, 380)

        cmap_obj = cm.get_cmap(cmap)
        norm = plt.Normalize(_vmin, _vmax)
        colors = cmap_obj(norm(zs_sc))

        ax.scatter(xs_sc, ys_sc, zs_sc + 0.005,  # légèrement au-dessus
                   c=colors, s=sizes,
                   edgecolors="k", linewidths=0.6,
                   alpha=0.92, zorder=5)

    ax.set_xlabel(xlabel, fontsize=8, labelpad=4)
    ax.set_ylabel(ylabel, fontsize=8, labelpad=4)
    ax.set_zlabel("", fontsize=7)
    ax.set_title(title, fontsize=9, pad=4)
    ax.tick_params(labelsize=7)

    if invert_x:
        ax.invert_xaxis()
    if invert_y:
        ax.invert_yaxis()
    ax.view_init(elev=elev, azim=azim)

    return surf


# ── Campagnes coarse ─────────────────────────────────────────────────────────

COARSE_SPECS = [
    {
        "json": "claude_coupling_lambda_k_aggregate.json",
        "x_key": "lambda", "y_key": "k",
        "xlabel": r"$\lambda$ (taux création)", "ylabel": r"$k$ (candidats)",
        "title": r"Carte coarse $\lambda\times k$ — fraction bornée (n=3 seeds/pt)",
        "out": "claude_surface_3d_lambda_k.png",
        "invert_x": False, "invert_y": False,
        "elev": 28, "azim": -55,
    },
    {
        "json": "claude_coupling_k_mu_aggregate.json",
        "x_key": "k", "y_key": "mu",
        "xlabel": r"$k$ (candidats)", "ylabel": r"$\mu$ (friction)",
        "title": r"Carte coarse $k\times\mu$ — fraction bornée (n=3 seeds/pt)",
        "out": "claude_surface_3d_k_mu.png",
        "invert_x": True, "invert_y": True,
        "elev": 28, "azim": 125,
    },
    {
        "json": "claude_coupling_sigma_k_aggregate.json",
        "x_key": "sigma", "y_key": "k",
        "xlabel": r"$\sigma_\alpha$ (bruit Brownien)", "ylabel": r"$k$ (candidats)",
        "title": r"Carte coarse $\sigma_\alpha\times k$ — fraction bornée (n=3 seeds/pt)",
        "out": "claude_surface_3d_sigma_k.png",
        "invert_x": False, "invert_y": False,
        "elev": 28, "azim": -55,
    },
    {
        "json": "claude_coupling_theta_depr_aggregate.json",
        "x_key": "theta", "y_key": "depr_endo",
        "xlabel": r"$\theta$ (propension dépense)", "ylabel": r"$\delta_\mathrm{endo}$",
        "title": r"Carte coarse $\theta\times\delta_\mathrm{endo}$ — fraction bornée (n=3 seeds/pt)",
        "out": "claude_surface_3d_theta_delta.png",
        "invert_x": False, "invert_y": False,
        "elev": 28, "azim": -55,
    },
]


def run_coarse():
    for spec in COARSE_SPECS:
        path = RESULTS / spec["json"]
        if not path.exists():
            print(f"[SKIP] {spec['json']} absent")
            continue
        data = json.loads(path.read_text())
        xs, ys, points = aggregate_coarse(data, spec["x_key"], spec["y_key"])

        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
        surf = _draw_panel(
            ax, xs, ys, points, "bounded_rate",
            spec["xlabel"], spec["ylabel"], spec["title"],
            vmin=0.0, vmax=1.0,
            invert_x=spec["invert_x"], invert_y=spec["invert_y"],
            elev=spec["elev"], azim=spec["azim"],
        )
        cbar = fig.colorbar(surf, ax=ax, shrink=0.5, pad=0.12, label="fraction bornée")
        cbar.ax.tick_params(labelsize=8)

        # Légende taille des points
        _add_size_legend(fig, ax)

        fig.tight_layout()
        out = FIGURES / spec["out"]
        fig.savefig(out, dpi=150)
        plt.close(fig)
        print(f"  → {out}")


# ── Campagnes adaptatives ────────────────────────────────────────────────────

ADAPTIVE_SPECS = [
    {
        "json": "adaptive_lambda_k_extended.json",
        "x_param": "lambda_creation", "y_param": "n_candidats_pool",
        "xlabel": r"$\lambda$ (taux création)", "ylabel": r"$k$ (candidats)",
        "label": r"$\lambda\times k$ étendu",
        "out": "map_lambda_k_3d.png",
        "invert_x": False, "invert_y": False,
        "elev": 28, "azim": -55,
    },
    {
        "json": "adaptive_k_mu_extended.json",
        "x_param": "n_candidats_pool", "y_param": "mu",
        "xlabel": r"$k$ (candidats)", "ylabel": r"$\mu$ (friction)",
        "label": r"$k\times\mu$ étendu",
        "out": "map_k_mu_3d.png",
        "invert_x": True, "invert_y": True,
        "elev": 28, "azim": 125,
    },
    {
        "json": "adaptive_sigma_k_extended.json",
        "x_param": "alpha_sigma_brownien", "y_param": "n_candidats_pool",
        "xlabel": r"$\sigma_\alpha$ (bruit Brownien)", "ylabel": r"$k$ (candidats)",
        "label": r"$\sigma_\alpha\times k$ étendu",
        "out": "map_sigma_k_3d.png",
        "invert_x": False, "invert_y": False,
        "elev": 28, "azim": -55,
    },
    {
        "json": "adaptive_theta_delta_unified.json",
        "x_param": "theta", "y_param": "taux_depreciation_endo",
        "xlabel": r"$\theta$ (propension dépense)", "ylabel": r"$\delta_\mathrm{endo}$",
        "label": r"$\theta\times\delta$ unifié",
        "out": "map_theta_delta_3d.png",
        "invert_x": False, "invert_y": False,
        "elev": 28, "azim": -55,
    },
]

PANELS = [
    ("bounded_rate",    r"Fraction bornée $\mathcal{B}$",                  "viridis",  0.0, 1.0),
    ("stationary_rate", r"Taux stationnarité ($\mathcal{B}$∧$r_f$)",       "plasma",   0.0, 1.0),
    ("n_alive",         r"$\bar{n}_\mathrm{alive}$ (rég. stat.)",           "Blues",    None, None),
    ("gini",            r"Gini actif (rég. stat.)",                         "Oranges",  0.0, 1.0),
]


def run_adaptive():
    for spec in ADAPTIVE_SPECS:
        path = RESULTS / spec["json"]
        if not path.exists():
            print(f"[SKIP] {spec['json']} absent")
            continue
        data = json.loads(path.read_text())
        xs, ys, points = aggregate_adaptive(data, spec["x_param"], spec["y_param"])

        fig = plt.figure(figsize=(14, 11))
        fig.suptitle(
            f"Campagne adaptative — {spec['label']}\n"
            r"Points : taille $\propto$ demi-IC Wilson 95% (grand = peu de seeds = incertain)",
            fontsize=10, y=0.98,
        )

        for idx, (field, subtitle, cmap, vmin, vmax) in enumerate(PANELS):
            ax = fig.add_subplot(2, 2, idx + 1, projection="3d")

            # Pour n_alive et gini, limiter aux points non-NaN
            if field in ("n_alive", "gini"):
                # Construire vmin/vmax depuis les données
                vals = [pt[field] for pt in points.values()
                        if not math.isnan(pt.get(field, float("nan")))]
                vmin_eff = min(vals) if vals else 0.0
                vmax_eff = max(vals) if vals else 1.0
            else:
                vmin_eff = vmin
                vmax_eff = vmax

            surf = _draw_panel(
                ax, xs, ys, points, field,
                spec["xlabel"], spec["ylabel"], subtitle,
                vmin=vmin_eff, vmax=vmax_eff, cmap=cmap,
                invert_x=spec["invert_x"], invert_y=spec["invert_y"],
                elev=spec["elev"], azim=spec["azim"],
            )
            cbar = fig.colorbar(surf, ax=ax, shrink=0.45, pad=0.12)
            cbar.ax.tick_params(labelsize=7)

        _add_size_legend(fig, None, loc="lower center", ncol=3)
        fig.tight_layout(rect=[0, 0.04, 1, 0.96])
        out = FIGURES / spec["out"]
        fig.savefig(out, dpi=140)
        plt.close(fig)
        print(f"  → {out}")


# ── Légende taille des points ─────────────────────────────────────────────────

def _add_size_legend(fig, ax, loc="lower right", ncol=2):
    """Ajoute une mini-légende expliquant la taille des points."""
    handles = []
    for n_seeds, label in [(3, "n=3 (IC large)"), (15, "n=15 (IC étroit)")]:
        w = wilson_half(round(0.5 * n_seeds), n_seeds)
        # Reconstruction de la taille relative (max_w ≈ 0.5 pour n=3, p=0.5)
        w_max = wilson_half(round(0.5 * 3), 3)
        size = max(30, 30 + 350 * (w / w_max))
        handles.append(plt.scatter([], [], s=size, c="gray",
                                   edgecolors="k", linewidths=0.6,
                                   alpha=0.85, label=label))
    fig.legend(handles=handles, title="Incertitude (IC Wilson 95%)",
               loc=loc, ncol=ncol, fontsize=8, title_fontsize=8,
               framealpha=0.85)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coarse-only", action="store_true")
    parser.add_argument("--adaptive-only", action="store_true")
    args = parser.parse_args()

    if not args.adaptive_only:
        print("=== Campagnes coarse ===")
        run_coarse()

    if not args.coarse_only:
        print("=== Campagnes adaptatives ===")
        run_adaptive()

    print(f"\nFigures dans {FIGURES}")


if __name__ == "__main__":
    main()
