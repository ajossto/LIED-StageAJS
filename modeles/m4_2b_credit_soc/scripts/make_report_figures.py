"""Génère les figures de synthèse du rapport final M4.2B (report/
rapport_final.md/.tex) à partir des tables déjà produites par
aggregate_exploration.py et aggregate_confirmation.py. Ne relit AUCUN
run brut, seulement les CSV agrégés. Écrit dans report/figures/.

Complète (ne remplace pas) les figures de simulation individuelles
copiées depuis simulation_lab (voir report/figures/README_figures.md)
avec des figures QUI N'EXISTENT NULLE PART AILLEURS : verdict par
critère, effet par branche de paramètre, compromis objectif A/objectif B.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EXPLORATION_CSV = ROOT / "results" / "campaign" / "exploration_summary.csv"
CONFIRM_RUNS_CSV = ROOT / "results" / "confirmation" / "confirmation_runs.csv"
CONFIRM_VERDICTS_CSV = ROOT / "results" / "confirmation" / "confirmation_verdicts.csv"
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10.5,
    "axes.grid": True, "grid.alpha": 0.25,
})


def _f(row, key):
    v = row.get(key)
    if v in (None, "", "None"):
        return None
    return float(v)


def load_csv(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def mean_std(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None
    a = np.array(xs, dtype=float)
    return float(a.mean()), float(a.std())


# ---------------------------------------------------------------------------
# Figure 1 : stabilite de seuil sur les 29 cellules d'exploration
# ---------------------------------------------------------------------------
def fig_threshold_stability_all_cells():
    rows = load_csv(EXPLORATION_CSV)
    by_label = {}
    for r in rows:
        by_label.setdefault(r["label"], []).append(r)
    labels = sorted(l for l in by_label if l not in ("t10000_baseline",))
    means, stds = [], []
    for l in labels:
        vals = [_f(r, "threshold_reldiff_frac_under_20pct") for r in by_label[l]]
        m, s = mean_std(vals)
        means.append(m or 0.0)
        stds.append(s or 0.0)

    order = np.argsort(means)[::-1]
    labels = [labels[i] for i in order]
    means = [means[i] for i in order]
    stds = [stds[i] for i in order]
    colors = ["#d62728" if l == "deltasigma_0.1_0.1" else "#4c72b0" for l in labels]

    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(labels))
    ax.barh(y, means, xerr=stds, color=colors, height=0.7, ecolor="#333333", capsize=2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Fraction des instantanés stables au seuil (critère 1)\n"
                   "(|α̂(seuil) − α̂(seuil/2)| / α̂(seuil) < 20 %)")
    ax.set_title("Stabilité de seuil sur les 29 cellules d'exploration\n"
                  "(moyenne ± écart-type sur 3 graines ; rouge = seule cellule hors du bruit)")
    ax.axvline(0.5, color="black", ls="--", lw=1, alpha=0.6)
    ax.text(0.5, len(labels) - 0.5, " seuil de\n passage\n par graine\n (0,5)",
            fontsize=7, va="top", ha="left")
    ax.set_xlim(0, 1)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_stabilite_seuil_toutes_cellules.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2 : matrice de verdict (9 cellules de confirmation x 5 criteres)
# ---------------------------------------------------------------------------
def fig_verdict_matrix():
    rows = load_csv(CONFIRM_VERDICTS_CSV)
    rows.sort(key=lambda r: r["label"])
    labels = [r["label"] for r in rows]
    crit_cols = ["n_seeds_crit1", "n_seeds_crit2", "n_seeds_crit3", "n_seeds_crit4"]
    crit_names = ["1. Stabilité\nde seuil", "2. n_tail\n≥ 100", "3. Signe\ncohérent",
                  "4. Vuong\nfavorise PL"]
    mat = np.array([[_f(r, c) / 5.0 for c in crit_cols] for r in rows])
    crit5 = np.array([1.0 if r["crit5_pass"] == "True" else 0.0 for r in rows])
    mat_full = np.hstack([mat, crit5.reshape(-1, 1)])
    crit_names_full = crit_names + ["5. Pas réductible\nà Gini/deg_out"]

    fig, ax = plt.subplots(figsize=(8.5, 6))
    cmap = plt.cm.RdYlGn
    im = ax.imshow(mat_full, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(mat_full.shape[0]):
        for j in range(mat_full.shape[0] if False else mat_full.shape[1]):
            if j < 4:
                txt = f"{int(round(mat_full[i, j] * 5))}/5"
            else:
                txt = "OK" if mat_full[i, j] == 1 else "non"
            color = "white" if mat_full[i, j] < 0.35 or mat_full[i, j] > 0.85 else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=9, color=color)
    ax.set_xticks(range(len(crit_names_full)))
    ax.set_xticklabels(crit_names_full, fontsize=8.5)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title("Verdict par critère — 9 cellules × 5 graines de confirmation disjointes\n"
                 "(vert = critère satisfait, rouge = échec ; robuste seulement si les 5 critères tiennent)")
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03, label="fraction de graines satisfaisant le critère")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_matrice_verdict.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3 : alpha vs K0
# ---------------------------------------------------------------------------
def fig_alpha_vs_k0():
    rows = load_csv(EXPLORATION_CSV)
    branch = {"K0_1": 1, "K0_5": 5, "baseline": 25, "K0_100": 100, "K0_500": 500, "K0_2000": 2000}
    by_label = {}
    for r in rows:
        by_label.setdefault(r["label"], []).append(r)

    k0s, means, stds = [], [], []
    for label, k0 in sorted(branch.items(), key=lambda kv: kv[1]):
        vals = [_f(r, "alpha_density_mean") for r in by_label.get(label, [])]
        m, s = mean_std(vals)
        k0s.append(k0); means.append(m); stds.append(s)

    conf = load_csv(CONFIRM_RUNS_CSV)
    conf_by_label = {}
    for r in conf:
        conf_by_label.setdefault(r["label"], []).append(r)
    conf_k0 = {"K0_1": 1, "K0_2000": 2000}
    ck0s, cmeans, cstds = [], [], []
    for label, k0 in conf_k0.items():
        vals = [_f(r, "alpha_density_mean") for r in conf_by_label.get(label, [])]
        m, s = mean_std(vals)
        ck0s.append(k0); cmeans.append(m); cstds.append(s)

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.errorbar(k0s, means, yerr=stds, marker="o", color="#4c72b0",
                label="exploration (3 graines)", capsize=3)
    ax.errorbar(ck0s, cmeans, yerr=cstds, marker="D", color="#d62728", ls="none",
                label="confirmation (5 graines disjointes)", capsize=3, markersize=8)
    ax.set_xscale("log")
    ax.set_xlabel("K0 (capital de départ, échelle log)")
    ax.set_ylabel("α̂ (exposant apparent de la queue des intérêts)")
    ax.set_title("Effet de K0 sur α̂ — non monotone mais très reproductible\n"
                  "(α̂ plus bas = queue plus lourde)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "fig3_alpha_vs_K0.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4 : alpha vs gamma, brut vs compense
# ---------------------------------------------------------------------------
def fig_alpha_vs_gamma():
    rows = load_csv(EXPLORATION_CSV)
    by_label = {}
    for r in rows:
        by_label.setdefault(r["label"], []).append(r)

    raw = {"gamma_0.3333": 1/3, "gamma_0.4000": 0.4, "baseline": 0.5,
           "gamma_0.6000": 0.6, "gamma_0.6667": 2/3}
    comp = {"gamma_comp_0.3333": 1/3, "gamma_comp_0.4000": 0.4, "baseline": 0.5,
            "gamma_comp_0.6000": 0.6, "gamma_comp_0.6667": 2/3}

    def series(mapping):
        gs, means, stds = [], [], []
        for label, g in sorted(mapping.items(), key=lambda kv: kv[1]):
            vals = [_f(r, "alpha_density_mean") for r in by_label.get(label, [])]
            m, s = mean_std(vals)
            gs.append(g); means.append(m); stds.append(s)
        return gs, means, stds

    gs_raw, m_raw, s_raw = series(raw)
    gs_comp, m_comp, s_comp = series(comp)

    conf = load_csv(CONFIRM_RUNS_CSV)
    conf_by_label = {}
    for r in conf:
        conf_by_label.setdefault(r["label"], []).append(r)

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.errorbar(gs_raw, m_raw, yerr=s_raw, marker="o", color="#4c72b0",
                label="K0=25 fixe (brut, exploration)", capsize=3)
    ax.errorbar(gs_comp, m_comp, yerr=s_comp, marker="s", color="#55a868",
                label="K0/K*aut constant (compensé, exploration)", capsize=3)

    for label, g, color in (("gamma_0.6667", 2/3, "#4c72b0"),
                             ("gamma_comp_0.3333", 1/3, "#55a868"),
                             ("gamma_comp_0.6667", 2/3, "#55a868")):
        vals = [_f(r, "alpha_density_mean") for r in conf_by_label.get(label, [])]
        m, s = mean_std(vals)
        if m is not None:
            ax.errorbar([g], [m], yerr=[s], marker="D", color="#d62728", ls="none",
                        capsize=3, markersize=8,
                        label="confirmation (5 graines)" if label == "gamma_0.6667" else None)

    ax.set_xlabel("γ (concavité de la production)")
    ax.set_ylabel("α̂ (exposant apparent de la queue des intérêts)")
    ax.set_title("Effet de γ sur α̂ : plat en brut, net une fois l'échelle compensée")
    ax.legend(fontsize=8.5)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_alpha_vs_gamma.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5 : alpha / tau / branchement vs rho (eta lineaire)
# ---------------------------------------------------------------------------
def fig_eta_panel():
    rows = load_csv(EXPLORATION_CSV)
    by_label = {}
    for r in rows:
        by_label.setdefault(r["label"], []).append(r)
    branch = {"rho_0.125": 0.125, "rho_0.25": 0.25, "rho_0.5": 0.5,
              "baseline": 1.0, "rho_2": 2.0, "rho_4": 4.0}

    def series(key):
        rs, means, stds = [], [], []
        for label, rho in sorted(branch.items(), key=lambda kv: kv[1]):
            vals = [_f(r, key) for r in by_label.get(label, [])]
            m, s = mean_std(vals)
            rs.append(rho); means.append(m); stds.append(s)
        return rs, means, stds

    conf = load_csv(CONFIRM_RUNS_CSV)
    conf_by_label = {}
    for r in conf:
        conf_by_label.setdefault(r["label"], []).append(r)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
    specs = [("alpha_density_mean", "α̂", axes[0]),
             ("tau_hat", "τ̂ (avalanches)", axes[1]),
             ("branching_ratio", "rapport de branchement", axes[2])]
    for key, ylab, ax in specs:
        rs, means, stds = series(key)
        ax.errorbar(rs, means, yerr=stds, marker="o", color="#4c72b0", capsize=3,
                    label="exploration")
        for label, rho in (("rho_0.125", 0.125), ("rho_4", 4.0)):
            vals = [_f(r, key) for r in conf_by_label.get(label, [])]
            m, s = mean_std(vals)
            if m is not None:
                ax.errorbar([rho], [m], yerr=[s], marker="D", color="#d62728", ls="none",
                            capsize=3, markersize=8,
                            label="confirmation" if rho == 0.125 else None)
        ax.set_xscale("log")
        ax.set_xlabel("ρ (η = ρ·N, échelle log)")
        ax.set_ylabel(ylab)
        ax.legend(fontsize=8)
    fig.suptitle("η (levier linéaire) : effet systématique sur les trois diagnostics")
    fig.tight_layout()
    fig.savefig(OUT / "fig5_eta_panel.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 6 : compromis objectif A / objectif B (branche delta-sigma + tout le grid)
# ---------------------------------------------------------------------------
def fig_tradeoff_scatter():
    rows = load_csv(EXPLORATION_CSV)
    by_label = {}
    for r in rows:
        by_label.setdefault(r["label"], []).append(r)

    deltasigma_order = ["baseline", "deltasigma_0.02_0.02", "deltasigma_0.05_0.05",
                         "deltasigma_0.1_0.1", "deltasigma_0.05_0.25"]

    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    all_x, all_y = [], []
    for label, rs in by_label.items():
        for r in rs:
            x = _f(r, "threshold_reldiff_frac_under_20pct")
            y = _f(r, "branching_ratio")
            if x is not None and y is not None:
                all_x.append(x); all_y.append(y)
    ax.scatter(all_x, all_y, s=18, color="#b0b0b0", alpha=0.7, label="autres cellules (exploration, toutes graines)")

    xs, ys = [], []
    for label in deltasigma_order:
        for r in by_label.get(label, []):
            x = _f(r, "threshold_reldiff_frac_under_20pct")
            y = _f(r, "branching_ratio")
            if x is not None and y is not None:
                xs.append(x); ys.append(y)
    xs_m = [np.mean([_f(r, "threshold_reldiff_frac_under_20pct") for r in by_label.get(l, [])]) for l in deltasigma_order]
    ys_m = [np.mean([_f(r, "branching_ratio") for r in by_label.get(l, [])]) for l in deltasigma_order]
    ax.plot(xs_m, ys_m, "-o", color="#d62728", label="branche δ=σ (baseline → 0,10 → M4.2)", zorder=5)
    for l, x, y in zip(deltasigma_order, xs_m, ys_m):
        ax.annotate(l.replace("deltasigma_", "").replace("_", "="), (x, y),
                    textcoords="offset points", xytext=(6, 4), fontsize=7.5)

    ax.set_xlabel("stabilité de seuil (critère 1 ; plus haut = plus stable, objectif A)")
    ax.set_ylabel("rapport de branchement des avalanches (objectif B)")
    ax.set_title("Compromis objectif A / objectif B\n"
                  "seul mouvement notable sur la stabilité de seuil, au prix de la criticalité")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig6_compromis_A_B.png")
    plt.close(fig)


if __name__ == "__main__":
    fig_threshold_stability_all_cells()
    fig_verdict_matrix()
    fig_alpha_vs_k0()
    fig_alpha_vs_gamma()
    fig_eta_panel()
    fig_tradeoff_scatter()
    print(f"6 figures ecrites dans {OUT}")
