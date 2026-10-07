"""Figures de caracterisation de l'exposant alpha (existence de la loi de
Pareto en queue des interets recus acquise par hypothese -- JOURNAL.md
§20-21). Remplace les figures fig3/fig4/fig5 (construites sur l'ancien
critere pass/fail) par des courbes alpha(parametre) avec barres d'erreur
a plusieurs niveaux, tirees de results/alpha_characterization_cells.csv.

Convention visuelle : cellules "mild" (fenetre post-3.tau valide,
plusieurs instantanes) en points pleins avec barre d'erreur =
between_seed_sd (reproductibilite graine a graine, la plus pertinente
pour juger un effet de parametre). Cellules "severes" (K0_2000,
K0_500, gamma_0.3333, gamma_0.4000, control_geometric, K0_100 -- un
seul instantane par graine, stationnarite NON confirmee) en marqueur
creux, meme barre d'erreur mais annotees explicitement : ce sont des
points, pas des mesures de regime etabli.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CELLS_CSV = ROOT / "results" / "alpha_characterization_cells.csv"
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10,
    "axes.grid": True, "grid.alpha": 0.25,
})


def load_cells():
    rows = list(csv.DictReader(open(CELLS_CSV)))
    out = {}
    for r in rows:
        key = (r["campaign"], r["label"])
        # params depuis analysis.json d'un seed de ce label
        base = ROOT / "results" / ("campaign" if r["campaign"] == "exploration" else "confirmation")
        seed_dirs = sorted((base / r["label"]).glob("seed*"))
        params = {}
        if seed_dirs:
            aj = seed_dirs[0] / "analysis.json"
            if aj.exists():
                params = json.load(open(aj)).get("params", {})
        out[key] = {
            "alpha": float(r["alpha_cell_mean"]),
            "err": float(r["between_seed_sd"]) if r["between_seed_sd"] not in (None, "", "None") else 0.0,
            "severe": r["classification"] == "severe",
            "params": params,
        }
    return out


def _plot_branch(ax, cells, labels, x_key, color, marker_label, log_x=False):
    xs, ys, errs, severes = [], [], [], []
    for camp, label in labels:
        if (camp, label) not in cells:
            continue
        c = cells[(camp, label)]
        xs.append(c["params"].get(x_key))
        ys.append(c["alpha"])
        errs.append(c["err"])
        severes.append(c["severe"])
    xs, ys, errs = np.array(xs, dtype=float), np.array(ys), np.array(errs)
    order = np.argsort(xs)
    xs, ys, errs = xs[order], ys[order], errs[order]
    severes = [severes[i] for i in order]
    ax.plot(xs, ys, "-", color=color, lw=1.3, alpha=0.6, zorder=1)
    for x, y, e, sev in zip(xs, ys, errs, severes):
        if sev:
            ax.errorbar([x], [y], yerr=[e], fmt="o", mfc="white", mec=color, mew=1.8,
                        ecolor=color, capsize=3, ms=7, zorder=3)
        else:
            ax.errorbar([x], [y], yerr=[e], fmt="o", color=color, ecolor=color,
                        capsize=3, ms=6, zorder=3)
    if log_x:
        ax.set_xscale("log")
    ax.plot([], [], "o", color=color, label=marker_label)


def fig_k0():
    cells = load_cells()
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    raw_labels = [("exploration", l) for l in ("K0_1", "K0_5", "baseline", "K0_100", "K0_500", "K0_2000")]
    comp_labels = [("exploration", l) for l in
                   ("gamma_comp_0.3333", "gamma_comp_0.4000", "baseline", "gamma_comp_0.6000", "gamma_comp_0.6667")]
    conf_raw = [("confirmation", l) for l in ("K0_1", "K0_2000")]
    conf_comp = [("confirmation", l) for l in ("gamma_comp_0.3333", "gamma_comp_0.6667")]
    _plot_branch(ax, cells, raw_labels, "K0", "#1f77b4", "γ=0,5 fixe (exploration)", log_x=True)
    _plot_branch(ax, cells, comp_labels, "K0", "#2ca02c", "γ compensé (exploration)", log_x=True)
    _plot_branch(ax, cells, conf_raw, "K0", "#1f77b4", None, log_x=True)
    _plot_branch(ax, cells, conf_comp, "K0", "#2ca02c", None, log_x=True)
    for camp, label in conf_raw + conf_comp:
        if (camp, label) in cells:
            c = cells[(camp, label)]
            ax.plot(c["params"]["K0"], c["alpha"], "D", mfc="none",
                     mec="crimson" if c["severe"] else "black", ms=9, mew=1.5, zorder=4)
    ax.plot([], [], "D", mfc="none", mec="black", label="confirmation (losange)")
    ax.plot([], [], "o", mfc="white", mec="gray", mew=1.8, label="cellule sévère (1 instantané, non stationnaire)")
    ax.set_xlabel("K0 (log)")
    ax.set_ylabel("α̂ (seuil KS, moyenne de cellule)")
    ax.set_title("α̂ vs K0 — barres d'erreur = reproductibilité graine à graine (between-seed SD)")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    p = OUT / "fig12_alpha_vs_K0.png"
    fig.savefig(p, bbox_inches="tight")
    print(f"écrit : {p}")


def fig_gamma():
    cells = load_cells()
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    raw_labels = [("exploration", l) for l in ("gamma_0.3333", "gamma_0.4000", "baseline", "gamma_0.6000", "gamma_0.6667")]
    comp_labels = [("exploration", l) for l in
                   ("gamma_comp_0.3333", "gamma_comp_0.4000", "baseline", "gamma_comp_0.6000", "gamma_comp_0.6667")]
    conf_raw = [("confirmation", "gamma_0.6667")]
    conf_comp = [("confirmation", l) for l in ("gamma_comp_0.3333", "gamma_comp_0.6667")]
    _plot_branch(ax, cells, raw_labels, "gamma", "#1f77b4", "K0=25 fixe (exploration)")
    _plot_branch(ax, cells, comp_labels, "gamma", "#2ca02c", "K0 compensé (exploration)")
    _plot_branch(ax, cells, conf_raw, "gamma", "#1f77b4", None)
    _plot_branch(ax, cells, conf_comp, "gamma", "#2ca02c", None)
    for camp, label in conf_raw + conf_comp:
        if (camp, label) in cells:
            c = cells[(camp, label)]
            ax.plot(c["params"]["gamma"], c["alpha"], "D", mfc="none",
                     mec="crimson" if c["severe"] else "black", ms=9, mew=1.5, zorder=4)
    ax.plot([], [], "D", mfc="none", mec="black", label="confirmation (losange)")
    ax.set_xlabel("γ")
    ax.set_ylabel("α̂ (seuil KS, moyenne de cellule)")
    ax.set_title("α̂ vs γ, brut vs compensé — barres d'erreur = between-seed SD")
    ax.legend(fontsize=8)
    fig.tight_layout()
    p = OUT / "fig13_alpha_vs_gamma.png"
    fig.savefig(p, bbox_inches="tight")
    print(f"écrit : {p}")


def fig_eta():
    cells = load_cells()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    rho_labels = [("exploration", l) for l in ("rho_0.125", "rho_0.25", "rho_0.5", "baseline", "rho_2", "rho_4")]
    conf_rho = [("confirmation", l) for l in ("rho_0.125", "rho_4")]
    _plot_branch(ax, cells, rho_labels, "rho", "#1f77b4", "exploration", log_x=True)
    for camp, label in conf_rho:
        if (camp, label) in cells:
            c = cells[(camp, label)]
            ax.errorbar([c["params"]["rho"]], [c["alpha"]], yerr=[c["err"]], fmt="D",
                        mfc="none", mec="crimson", ecolor="crimson", capsize=3, ms=8, mew=1.5,
                        zorder=4, label="confirmation" if label == "rho_0.125" else None)
    ax.set_xscale("log")
    ax.set_xlabel("ρ (η linéaire, log)")
    ax.set_ylabel("α̂")
    ax.set_title("α̂ vs ρ")
    ax.legend(fontsize=8)

    ax = axes[1]
    beta_labels = [("exploration", l) for l in ("beta_0.50", "beta_0.75", "baseline", "beta_1.25", "beta_1.50")]
    _plot_branch(ax, cells, beta_labels, "eta_beta", "#1f77b4", "exploration")
    ax.set_xlabel("β (η non linéaire)")
    ax.set_ylabel("α̂")
    ax.set_title("α̂ vs β")

    fig.suptitle("α̂ vs paramètres de η — barres d'erreur = between-seed SD", y=1.02)
    fig.tight_layout()
    p = OUT / "fig14_alpha_vs_eta.png"
    fig.savefig(p, bbox_inches="tight")
    print(f"écrit : {p}")


def fig_deltasigma():
    cells = load_cells()
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    # UNIQUEMENT les cellules ou delta=sigma exactement (sweep conjoint) --
    # deltasigma_0.05_0.25 a delta=0.05 =/= sigma=0.25, ne PAS la mettre sur
    # cette meme ligne (elle testerait sigma seul a delta fixe, pas le
    # sweep conjoint) : tracee a part, annotee.
    labels = [("exploration", l) for l in
              ("baseline", "deltasigma_0.02_0.02", "deltasigma_0.05_0.05", "deltasigma_0.1_0.1")]
    conf_labels = [("confirmation", "deltasigma_0.1_0.1")]
    xs, ys, errs = [], [], []
    for camp, label in labels:
        if (camp, label) not in cells:
            continue
        c = cells[(camp, label)]
        assert c["params"]["delta"] == c["params"]["sigma"], (label, c["params"])
        xs.append(c["params"]["sigma"])
        ys.append(c["alpha"])
        errs.append(c["err"])
    order = np.argsort(xs)
    xs = np.array(xs)[order]; ys = np.array(ys)[order]; errs = np.array(errs)[order]
    ax.errorbar(xs, ys, yerr=errs, fmt="o-", color="#1f77b4", ecolor="#1f77b4", capsize=3, label="exploration (δ=σ conjoints)")
    for camp, label in conf_labels:
        c = cells[(camp, label)]
        ax.errorbar([c["params"]["sigma"]], [c["alpha"]], yerr=[c["err"]], fmt="D", mfc="none",
                    mec="crimson", ecolor="crimson", capsize=3, ms=8, mew=1.5, label="confirmation")
    # point hors-branche : delta=0.05 fixe, sigma=0.25 seul varie
    key = ("exploration", "deltasigma_0.05_0.25")
    if key in cells:
        c = cells[key]
        ax.errorbar([c["params"]["sigma"]], [c["alpha"]], yerr=[c["err"]], fmt="^", color="#ff7f0e",
                    ecolor="#ff7f0e", capsize=3, ms=8,
                    label=f"δ=0,05 fixe, σ=0,25 seul (hors sweep conjoint)")
    ax.set_xlabel("σ (= δ sur la branche conjointe, sauf triangle orange)")
    ax.set_ylabel("α̂")
    ax.set_title("α̂ vs δ=σ conjoints — barres d'erreur = between-seed SD")
    ax.legend(fontsize=7.5)
    fig.tight_layout()
    p = OUT / "fig15_alpha_vs_deltasigma.png"
    fig.savefig(p, bbox_inches="tight")
    print(f"écrit : {p}")


if __name__ == "__main__":
    fig_k0()
    fig_gamma()
    fig_eta()
    fig_deltasigma()
