"""Figures du rapport M4.2 — régénérables depuis results/tables/*.csv.

Chaque figure imprime sa source de données dans son pied de page. Style :
matplotlib sobre (grille discrète, marques fines), couleurs fixes par
entité — λ=10/30/100 gardent la même couleur sur toutes les figures
(palette Okabe-Ito, sûre pour les daltonismes) ; une seule échelle par axe.

Usage : make_figures.py [--only F1,F2,...]   → figures/*.png
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "figures"

# Couleur fixe par taille de système (jamais recyclée).
LAM_COLORS = {10.0: "#0072B2", 30.0: "#E69F00", 100.0: "#009E73"}
GAMMA_COLOR = "#0072B2"
ACCENT = "#D55E00"
NEUTRAL = "#555555"


def read_table(name: str) -> list[dict]:
    path = TABLES / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        rows = []
        for row in csv.DictReader(stream):
            converted = {}
            for key, value in row.items():
                if value in (None, ""):
                    converted[key] = None
                    continue
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = value
            rows.append(converted)
        return rows


def save(fig, name: str, source: str) -> None:
    FIGURES.mkdir(exist_ok=True)
    fig.text(0.01, 0.005, f"source : {source}", fontsize=6.5, color="#777777")
    fig.savefig(FIGURES / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"figure : {FIGURES / name}")


def _cells(rows: list[dict], **filters) -> list[dict]:
    out = []
    for row in rows:
        if all(row.get(key) == value for key, value in filters.items()):
            out.append(row)
    return out


def _series_by_lam(rows: list[dict], key: str):
    by_lam: dict[float, list[tuple[float, float, float | None]]] = defaultdict(list)
    for row in rows:
        if row.get(f"{key}_mean") is None or row["A"] != 1.0:
            continue
        by_lam[row["lam"]].append(
            (row["gamma"], row[f"{key}_mean"], row.get(f"{key}_sd")))
    for lam in by_lam:
        by_lam[lam].sort()
    return by_lam


def _plot_vs_gamma(axis, by_lam, ylabel: str, logy: bool = False) -> None:
    for lam in sorted(by_lam):
        points = by_lam[lam]
        x = [p[0] for p in points]
        y = [p[1] for p in points]
        err = [p[2] if p[2] is not None else 0.0 for p in points]
        color = LAM_COLORS.get(lam, NEUTRAL)
        axis.errorbar(x, y, yerr=err, fmt="o-", ms=4.5, lw=1.6, capsize=3,
                      color=color, label=f"λ={lam:g}")
        axis.annotate(f"λ={lam:g}", xy=(x[-1], y[-1]), xytext=(5, 0),
                      textcoords="offset points", fontsize=8, color=color,
                      va="center")
    axis.set_xlabel("Exposant de concavité γ")
    axis.set_ylabel(ylabel)
    if logy:
        axis.set_yscale("log")
    axis.grid(True, alpha=0.2)
    axis.legend(fontsize=8, frameon=False)


def fig_tau(cells: list[dict]) -> None:
    """F1 : métrique primaire τ̂(γ) par taille de système."""
    fig, axis = plt.subplots(figsize=(8.2, 5.2))
    _plot_vs_gamma(axis, _series_by_lam(cells, "tau_hat"),
                   "τ̂ (exposant tronqué, s_min=2, fenêtre T/4)")
    axis.set_title("Exposant d'avalanche τ̂ selon γ — moyenne ± écart-type "
                   "inter-graines (fits par graine)")
    save(fig, "tau_vs_gamma.png", "results/tables/avalanches_cells.csv")


def fig_cutoff(cells: list[dict]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5))
    _plot_vs_gamma(axes[0], _series_by_lam(cells, "s_c"),
                   "Coupure ajustée ŝ_c", logy=True)
    axes[0].set_title("Coupure de taille finie ŝ_c(γ, λ)")
    _plot_vs_gamma(axes[1], _series_by_lam(cells, "branching"),
                   "Rapport de branchement b")
    axes[1].set_title("b(γ, λ) — invariance institutionnelle attendue")
    save(fig, "cutoff_branching_vs_gamma.png",
         "results/tables/avalanches_cells.csv")


def fig_demography(observables: list[dict]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5))
    _plot_vs_gamma(axes[0], _series_by_lam(observables, "N_over_lambda"),
                   "Population stationnaire N/λ")
    axes[0].set_title("Démographie : N/λ selon γ")
    _plot_vs_gamma(axes[1], _series_by_lam(observables, "K_per_capita"),
                   "Capital par tête (J)", logy=True)
    axes[1].set_title("Échelle de capital selon γ")
    save(fig, "demography_vs_gamma.png", "results/tables/observables_cells.csv")


def fig_scaling(cells: list[dict]) -> None:
    """F4 : ŝ_c, s_max, χ contre λ (log-log), une couleur par grandeur,
    petits multiples par γ."""
    gammas = sorted({row["gamma"] for row in cells
                     if row["A"] == 1.0 and row["T"] in (4000.0, 8000.0)})
    gammas = [g for g in gammas if len({row["lam"] for row in cells
                                        if row["gamma"] == g}) >= 3]
    if not gammas:
        print("scaling : moins de trois λ — figure sautée")
        return
    fig, axes = plt.subplots(1, len(gammas), figsize=(3.1 * len(gammas), 4.6),
                             sharey=True)
    if len(gammas) == 1:
        axes = [axes]
    quantities = (("s_c", "ŝ_c", "#0072B2"), ("size_max", "s_max", "#E69F00"),
                  ("susceptibility", "χ", "#009E73"))
    for axis, gamma in zip(axes, gammas):
        rows = sorted(_cells(cells, gamma=gamma, A=1.0), key=lambda r: r["lam"])
        for key, label, color in quantities:
            points = [(row["lam"], row[f"{key}_mean"]) for row in rows
                      if row.get(f"{key}_mean")
                      # coupures dégénérées (hors portée) exclues du scaling
                      and not (key == "s_c" and row.get("s_c_out_n"))]
            minimum = 2 if key == "s_c" else 3
            if len(points) < minimum:
                continue
            x = np.log([p[0] for p in points])
            y = np.log([p[1] for p in points])
            slope = float(np.polyfit(x, y, 1)[0])
            suffix = " (2 pts)" if len(points) == 2 else ""
            axis.plot([p[0] for p in points], [p[1] for p in points], "o-",
                      ms=4, lw=1.4, color=color,
                      label=f"{label} ∝ λ^{slope:.2f}{suffix}")
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_title(f"γ = {gamma:.3g}", fontsize=10)
        axis.set_xlabel("λ")
        axis.grid(True, which="both", alpha=0.18)
        axis.legend(fontsize=7.5, frameon=False)
    axes[0].set_ylabel("Grandeur (échelle log)")
    fig.suptitle("Scalings de taille finie par γ (3 points — exploratoire)")
    save(fig, "scaling_lambda.png", "results/tables/avalanches_cells.csv")


def fig_mechanism(observables: list[dict], mecanisme: list[dict]) -> None:
    lam30 = [row for row in observables if row["lam"] == 30.0 and row["A"] == 1.0]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.6))

    axis = axes[0][0]
    by = _series_by_lam(lam30, "rate_median")
    if 30.0 in by:
        points = by[30.0]
        axis.errorbar([p[0] for p in points], [p[1] for p in points],
                      yerr=[p[2] or 0 for p in points], fmt="o-", ms=4.5,
                      lw=1.6, capsize=3, color=GAMMA_COLOR,
                      label="taux médian du carnet")
    grid = np.linspace(0.30, 0.78, 50)
    axis.plot(grid, grid * 0.05 / 0.95, "--", lw=1.3, color=ACCENT,
              label="prédiction γ·δ/(1−δ)")
    axis.set_xlabel("γ")
    axis.set_ylabel("Taux d'intérêt (par pas)")
    axis.set_title("Maillon 1 : γ → taux contractuels")
    axis.grid(True, alpha=0.2)
    axis.legend(fontsize=8, frameon=False)

    axis = axes[0][1]
    for key, label, color in (("interest_to_prod", "intérêts payés / production",
                               GAMMA_COLOR),
                              ("cause_liquidity", "part des morts par liquidité",
                               ACCENT)):
        by = _series_by_lam(lam30, key)
        if 30.0 in by:
            points = by[30.0]
            axis.errorbar([p[0] for p in points], [p[1] for p in points],
                          yerr=[p[2] or 0 for p in points], fmt="o-", ms=4.5,
                          lw=1.6, capsize=3, color=color, label=label)
    axis.set_xlabel("γ")
    axis.set_title("Maillon 2 : service des intérêts")
    axis.grid(True, alpha=0.2)
    axis.legend(fontsize=8, frameon=False)

    axis = axes[1][0]
    for key, label, color in (("age_mean", "âge moyen au décès (pas)",
                               GAMMA_COLOR),
                              ("loans_per_capita", "contrats par tête", ACCENT),
                              ("debt_to_K", "levier ΣD/ΣK", "#009E73")):
        by = _series_by_lam(lam30, key)
        if 30.0 in by:
            points = by[30.0]
            axis.errorbar([p[0] for p in points], [p[1] for p in points],
                          yerr=[p[2] or 0 for p in points], fmt="o-", ms=4.5,
                          lw=1.6, capsize=3, color=color, label=label)
    axis.set_xlabel("γ")
    axis.set_title("Maillon 3 : durée de vie, exposition, réseau")
    axis.grid(True, alpha=0.2)
    axis.legend(fontsize=8, frameon=False)

    axis = axes[1][1]
    if mecanisme:
        rows = sorted(mecanisme, key=lambda row: row["gamma"])
        x = [row["gamma"] for row in rows]
        for key, label, color in (("debt_at_death_mean",
                                   "dette moyenne au décès (J)", GAMMA_COLOR),
                                  ("loss_per_member",
                                   "perte par membre d'avalanche (J)", ACCENT)):
            values = [row.get(key) for row in rows]
            if any(v is not None for v in values):
                axis.plot(x, values, "o-", ms=4.5, lw=1.6, color=color,
                          label=label)
        axis.set_yscale("log")
        axis.set_xlabel("γ")
        axis.set_title("Maillon 4 : expositions unitaires (volet mécanisme)")
        axis.grid(True, which="both", alpha=0.2)
        axis.legend(fontsize=8, frameon=False)
    else:
        axis.axis("off")
        axis.text(0.5, 0.5, "volet mécanisme non exécuté", ha="center")
    fig.suptitle("Chaîne causale γ → taux → service → exposition → propagation "
                 "(λ=30)")
    fig.tight_layout()
    save(fig, "mechanism_chain.png",
         "results/tables/observables_cells.csv + mecanisme.csv")


def fig_ratio(cells: list[dict]) -> None:
    """Collapse : τ̂ contre le rapport adimensionnel K0/K*_aut.

    Trois familles de cellules à λ=30, T=4000 : axe γ (A=1, K0=25),
    ablation A_norm (K*_aut égalisé), test K0 (γ=1/2, K0 varié). Si le
    rapport pilote τ̂, les trois familles tombent sur une même courbe.
    """
    rows = [row for row in cells
            if row["lam"] == 30.0 and row["T"] == 4000.0
            and row.get("tau_hat_mean") is not None
            and row.get("K0") is not None]
    if not rows:
        print("ratio : données insuffisantes — figure sautée")
        return
    families = {
        "axe γ (A=1, K0=25)": ("o", "#0072B2",
                               lambda r: r["A"] == 1.0 and r["K0"] == 25.0),
        "ablation A_norm (K* égalisé)": ("s", "#009E73",
                                         lambda r: r["A"] != 1.0),
        "test K0 (γ=1/2)": ("^", ACCENT,
                            lambda r: r["A"] == 1.0 and r["K0"] != 25.0),
    }
    fig, axis = plt.subplots(figsize=(8.6, 5.4))
    for label, (marker, color, predicate) in families.items():
        family = [row for row in rows if predicate(row)]
        if not family:
            continue
        ratio = [row["K0"] / (((1 - row["delta"]) * row["A"] / row["delta"])
                              ** (1.0 / (1.0 - row["gamma"])))
                 for row in family]
        tau = [row["tau_hat_mean"] for row in family]
        err = [row.get("tau_hat_sd") or 0.0 for row in family]
        axis.errorbar(ratio, tau, yerr=err, fmt=marker, ms=6.5, capsize=3,
                      lw=0, elinewidth=1.2, color=color, label=label)
        for x, y, row in zip(ratio, tau, family):
            axis.annotate(f"γ={row['gamma']:.2g}" if row["K0"] == 25.0
                          else f"K₀={row['K0']:g}",
                          xy=(x, y), xytext=(4, 4),
                          textcoords="offset points", fontsize=7,
                          color=NEUTRAL)
    axis.set_xscale("log")
    axis.set_xlabel("Rapport adimensionnel K₀ / K*_aut(γ, A)")
    axis.set_ylabel("τ̂ (exposant tronqué, fenêtre T/4)")
    axis.set_title("τ̂ contre la taille relative des nouveau-nées — "
                   "λ=30, T=4000")
    axis.grid(True, which="both", alpha=0.2)
    axis.legend(fontsize=8, frameon=False, loc="lower left")
    save(fig, "tau_vs_ratio.png", "results/tables/avalanches_cells.csv")


def fig_confirm() -> None:
    """F : forêt des 4 contrastes confirmatoires (graines 11-15) — effet
    total vs résiduel à échelle égalisée pour g033 (confirmatoire, 5
    graines 11-15 des deux côtés)."""
    rows = read_table("confirm_contrasts.csv")
    rows = [row for row in rows if row["condition"] == "1_ic_apparie"]
    if not rows:
        print("confirm : table absente — figure sautée")
        return
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6),
                             gridspec_kw={"width_ratios": [1.3, 1]})

    axis = axes[0]
    rows.sort(key=lambda r: r["gamma"])
    y = np.arange(len(rows))
    for i, row in enumerate(rows):
        color = GAMMA_COLOR if "1_ic_apparie" in row["verdict"] or True else NEUTRAL
        axis.errorbar(row["delta_tau_mean"], i,
                      xerr=[[row["delta_tau_mean"] - row["ci_lo"]],
                            [row["ci_hi"] - row["delta_tau_mean"]]],
                      fmt="o", ms=7, capsize=4, color=GAMMA_COLOR)
    axis.axvline(0, color="black", lw=0.9)
    axis.set_yticks(y)
    axis.set_yticklabels([f"γ={row['gamma']:.3g}" for row in rows])
    axis.set_xlabel("Δτ̂ vs centre γ=1/2 (contraste apparié, graines 11-15)")
    axis.set_title("Contrastes confirmatoires (IC95 de Student)")
    axis.grid(True, axis="x", alpha=0.2)

    axis = axes[1]
    total = next((r for r in rows if abs(r["gamma"] - 1/3) < 1e-6), None)
    if total:
        axis.errorbar([0], [total["delta_tau_mean"]],
                      yerr=[[total["delta_tau_mean"] - total["ci_lo"]],
                            [total["ci_hi"] - total["delta_tau_mean"]]],
                      fmt="o", ms=9, capsize=5, color=GAMMA_COLOR,
                      label="effet total (A=1)")
        # Résiduel confirmatoire (calculé séparément, cf. JOURNAL 27/07).
        residual_mean, residual_lo, residual_hi = 0.0310, 0.0014, 0.0605
        axis.errorbar([1], [residual_mean],
                      yerr=[[residual_mean - residual_lo],
                            [residual_hi - residual_mean]],
                      fmt="o", ms=9, capsize=5, color=ACCENT,
                      label="effet résiduel (A_norm)")
    axis.axhline(0, color="black", lw=0.9)
    axis.set_xticks([0, 1])
    axis.set_xticklabels(["total\n(A=1)", "résiduel\n(A_norm)"])
    axis.set_ylabel("Δτ̂ vs centre γ=1/2 (graines 11-15)")
    axis.set_title("γ=1/3 : décomposition confirmatoire")
    axis.grid(True, axis="y", alpha=0.2)
    fig.suptitle("Volet 4 — confirmation (graines disjointes 11-15)")
    fig.tight_layout()
    save(fig, "confirm_forest.png",
         "results/tables/confirm_contrasts.csv + JOURNAL.md (ablation_A_confirm)")


def fig_ablation() -> None:
    rows = read_table("ablation_A.csv")
    rows = [row for row in rows if row["quantity"] == "tau_hat"]
    if not rows:
        print("ablation : table absente — figure sautée")
        return
    fig, axis = plt.subplots(figsize=(7.2, 4.8))
    positions = np.arange(len(rows))
    width = 0.34
    axis.bar(positions - width / 2, [row["total_mean"] for row in rows],
             width, color=GAMMA_COLOR, label="effet total (A=1)")
    axis.bar(positions + width / 2, [row["residual_mean"] for row in rows],
             width, color=ACCENT, label="effet résiduel (A_norm)")
    axis.axhline(0, color="black", lw=0.8)
    axis.set_xticks(positions)
    axis.set_xticklabels([f"γ={row['gamma']:.3g}" for row in rows])
    axis.set_ylabel("Δτ̂ vs centre γ=1/2 (contraste apparié)")
    axis.set_title("Contrôle d'échelle : effet total vs effet résiduel de la "
                   "concavité")
    axis.grid(True, axis="y", alpha=0.2)
    axis.legend(fontsize=8, frameon=False)
    save(fig, "ablation_scale.png", "results/tables/ablation_A.csv")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    selected = {s for s in args.only.split(",") if s}

    cells = read_table("avalanches_cells.csv")
    observables = read_table("observables_cells.csv")
    mecanisme = read_table("mecanisme.csv")

    figures = {
        "tau": lambda: fig_tau(cells),
        "cutoff": lambda: fig_cutoff(cells),
        "demography": lambda: fig_demography(observables),
        "scaling": lambda: fig_scaling(cells),
        "ratio": lambda: fig_ratio(cells),
        "mechanism": lambda: fig_mechanism(observables, mecanisme),
        "ablation": fig_ablation,
        "confirm": fig_confirm,
    }
    for name, recipe in figures.items():
        if selected and name not in selected:
            continue
        recipe()


if __name__ == "__main__":
    main()
