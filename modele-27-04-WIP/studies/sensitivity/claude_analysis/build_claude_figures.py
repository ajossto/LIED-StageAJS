"""
Figures analytiques produites par Claude pour le rapport final.

Produit :
  report/figures/claude_lambda_fine_sweep.pdf
  report/figures/claude_oat_robustness.pdf
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

HERE = Path(__file__).resolve().parent.parent
RESULTS = HERE / "results"
FIGURES = HERE / "report" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)


# ── Palette cohérente ────────────────────────────────────────────────────────
C_K3 = "#e07b39"   # orange
C_K4 = "#3a7abf"   # bleu
C_BOUNDED = "#2ca02c"
C_UNBOUNDED = "#d62728"


def _mean(xs): return sum(xs)/len(xs) if xs else float("nan")
def _std(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs)/len(xs))


# ── Figure 1 : balayage fin de lambda ────────────────────────────────────────

def fig_lambda():
    agg_file = RESULTS / "claude_lambda_fine_sweep_aggregate.json"
    if not agg_file.exists():
        print("Agrégat lambda absent, skip.")
        return

    data = json.loads(agg_file.read_text())
    k4 = sorted([r for r in data if r["center"] == "k4"], key=lambda r: r["lambda_creation"])
    k3 = sorted([r for r in data if r["center"] == "k3"], key=lambda r: r["lambda_creation"])

    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    fig.suptitle(r"Balayage fin de $\lambda$ — $k=3$ et $k=4$, 3 seeds, 1500 pas, $\epsilon=10^{-3}$", fontsize=12)

    for row_idx, (rows, center_name, color) in enumerate([(k4, "k=4 (régime)", C_K4), (k3, "k=3 (sous-critique)", C_K3)]):
        lambdas = [r["lambda_creation"] for r in rows]
        df_mean = [r["densite_fin_mean"] for r in rows]
        df_std = [r["densite_fin_std"] for r in rows]
        alive_mean = [r["n_alive_mean"] for r in rows]
        alive_std = [r["n_alive_std"] for r in rows]
        bounded = [r["bounded_tail_share"] for r in rows]
        gini = [r["gini_mean"] for r in rows]

        ax0 = axes[row_idx][0]
        ax0.errorbar(lambdas, df_mean, yerr=df_std, fmt="o-", color=color, capsize=4, linewidth=1.5)
        ax0.set_xlabel(r"$\lambda$")
        ax0.set_ylabel("Densité financière")
        ax0.set_title(f"{center_name} — densité fin.")
        ax0.set_ylim(bottom=0)
        ax0.axhline(0.1, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)

        ax1 = axes[row_idx][1]
        ax1.errorbar(lambdas, alive_mean, yerr=alive_std, fmt="s-", color=color, capsize=4, linewidth=1.5)
        ax1.set_xlabel(r"$\lambda$")
        ax1.set_ylabel(r"$n_\mathrm{alive}$ moyen")
        ax1.set_title(f"{center_name} — taille")
        ax1.set_yscale("log")

        ax2 = axes[row_idx][2]
        n_seeds = [r["n"] for r in rows]
        bounded_abs = [b * n for b, n in zip(bounded, n_seeds)]
        for i, (lam, b, n) in enumerate(zip(lambdas, bounded_abs, n_seeds)):
            col = C_BOUNDED if b == n else (C_UNBOUNDED if b == 0 else "goldenrod")
            ax2.bar(i, b, color=col, alpha=0.85)
        ax2.set_xticks(range(len(lambdas)))
        ax2.set_xticklabels([f"{l:.1f}" for l in lambdas], rotation=45, fontsize=8)
        ax2.set_ylabel("Nombre de seeds bornées")
        ax2.set_title(f"{center_name} — bounded_tail")
        ax2.set_ylim(0, max(n_seeds) + 0.5)

    plt.tight_layout()
    out = FIGURES / "claude_lambda_fine_sweep.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure lambda: {out}")


# ── Figure 2 : robustesse OAT (3 seeds) ─────────────────────────────────────

def fig_oat_robustness():
    agg_file = RESULTS / "claude_oat_robustness_aggregate.json"
    if not agg_file.exists():
        print("Agrégat robustesse OAT absent, skip.")
        return

    data = json.loads(agg_file.read_text())

    # Regrouper par (centre, paramètre) et calculer delta vs centre
    # Charger le centre k4 et k3 depuis l'agrégat codex
    codex_agg_file = RESULTS / "codex_oat_screen_steps1500_seeds42_aggregate.json"
    codex_agg = json.loads(codex_agg_file.read_text()) if codex_agg_file.exists() else []
    center_vals = {}
    for e in codex_agg:
        if e.get("direction") == "center":
            center_vals[e["center"]] = {
                "df": e.get("measure_densite_fin_mean_mean", 0),
                "alive": e.get("measure_n_alive_mean_mean", 0),
                "bounded": e.get("bounded_tail_share", 0),
            }

    # Construire tableau d'effets robustes
    params_k4 = {}
    params_k3 = {}
    for row in data:
        center = row["center"]
        param = row["parameter"]
        val = row["value"]
        c_df = center_vals.get(center, {}).get("df", 0)
        delta = row["densite_fin_mean"] - c_df
        key = f"{param}={val}"
        if center == "regime_k4":
            params_k4[key] = {"delta": delta, "std": row["densite_fin_std"], "bounded": row["bounded_tail_share"], "n": row["n"]}
        else:
            params_k3[key] = {"delta": delta, "std": row["densite_fin_std"], "bounded": row["bounded_tail_share"], "n": row["n"]}

    def _plot_effects(ax, effects_dict, title, color):
        items = sorted(effects_dict.items(), key=lambda x: abs(x[1]["delta"]), reverse=True)[:14]
        labels = [k for k, _ in items]
        deltas = [v["delta"] for _, v in items]
        stds = [v["std"] for _, v in items]
        colors = [C_BOUNDED if v["bounded"] >= 0.67 else (C_UNBOUNDED if v["bounded"] < 0.34 else "goldenrod") for _, v in items]

        y = np.arange(len(labels))
        ax.barh(y, deltas, xerr=stds, color=colors, alpha=0.8, capsize=3, height=0.7)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel(r"$\Delta$ densité financière vs centre")
        ax.set_title(title)
        ax.invert_yaxis()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
    fig.suptitle("Effets OAT robustes (3 seeds : 42, 7, 123)\n"
                 "Vert = queue bornée, rouge = non bornée, jaune = partiel", fontsize=11)
    _plot_effects(ax1, params_k4, r"Centre $k=4$ (régime)", C_K4)
    _plot_effects(ax2, params_k3, r"Centre $k=3$ (sous-critique)", C_K3)

    plt.tight_layout()
    out = FIGURES / "claude_oat_robustness.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure OAT robustesse: {out}")


if __name__ == "__main__":
    fig_lambda()
    fig_oat_robustness()
    print("Figures terminées.")
