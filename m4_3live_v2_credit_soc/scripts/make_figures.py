"""Engendre TOUTES les figures des rapports M4.3Live-v2 depuis `results/`.

Même règle que `make_numbers.py` pour les nombres : aucune figure n'est
dessinée à la main, aucune donnée n'est recopiée. Les valeurs qu'une figure
ANNOTE sont déposées dans `report/figures/manifest.json` et confrontées aux
macros de `report/numbers.tex` par `tests/test_figures.py` — une figure qui
affiche autre chose que le texte qu'elle illustre est un défaut silencieux, et
c'est celui-là que le manifeste rend impossible.

    python3 scripts/make_figures.py [--only prefixe]

Les figures vont dans `report/figures/` (VERSIONNÉ). Celles qui lisent
`results/campaign/**`, `results/rotation_*` ou tout autre chemin ignoré par
git déposent en plus la série RÉELLEMENT TRACÉE — l'agrégat, pas la source de
8000 lignes — dans `report/figures/data/`, également versionné : sans cela,
une figure du rapport ne serait pas reproductible depuis le dépôt seul.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from figures_base import (  # noqa: E402
    ANALYSIS, CAMPAIGN, HETERO, T0, T_CRITICAL, blocks, colour, column, dump,
    french_axis, fr, gini, label, loglog_fit, lorenz, number, percent,
    read_csv, read_json, save, series, setup, student, windows, write_manifest,
)

REGISTRY: list = []
SEEDS = range(12)
ARMS_MIXED = ("new_A150", "new_A075", "new_g060")


def figure(name: str):
    def wrap(function):
        REGISTRY.append((name, function))
        return function
    return wrap


def _both_rules(arm: str, seed: int, key: str, name: str = "series.csv"):
    """La même colonne sous les deux règles de sens, pour un bras apparié."""
    out = {}
    for direction in ("free", "richest_lends"):
        rows = series(direction, arm, seed, name)
        if rows:
            out[direction] = (column(rows, "t"), column(rows, key))
    return out


# ---------------------------------------------------------------------------
# §2 — l'institution, avant toute mesure
# ---------------------------------------------------------------------------

@figure("f01_institution")
def f01() -> None:
    """Ce que la règle « la plus riche prête » s'interdisait, en algèbre.

    Aucune donnée : deux tracés de la condition d'optimalité. C'est le cœur
    conceptuel du chantier, et il n'existait jusqu'ici que sous forme de trois
    lignes de calcul au milieu d'un paragraphe.
    """
    gamma = 0.5
    exponent = 1.0 / (1.0 - gamma)
    ratios = np.linspace(0.4, 3.0, 400)          # A_2 / A_1
    lambda_star = 1.0 / (1.0 + ratios ** exponent)

    figure_, axes = plt.subplots(1, 2, figsize=(9.4, 3.5))

    axes[0].plot(ratios, lambda_star, color=colour("free"), lw=1.6)
    axes[0].axhline(0.5, color="#999999", lw=0.7, ls=":")
    axes[0].axvline(1.0, color="#999999", lw=0.7, ls=":")
    star = 1.0 / (1.0 + 1.5 ** exponent)
    axes[0].plot([1.5], [star], "o", color=colour("richest_lends"), ms=6, zorder=5)
    axes[0].annotate(f"$A_2/A_1 = 1{{,}}5$\n$\\lambda^* = {fr(star, 3, math_mode=True)}$",
                     xy=(1.5, star), xytext=(1.85, star + 0.13), fontsize=8,
                     color=colour("richest_lends"),
                     arrowprops=dict(arrowstyle="-", lw=0.7,
                                     color=colour("richest_lends")))
    axes[0].set_xlabel(r"$A_2/A_1$ — avance technologique de l'entité 2")
    axes[0].set_ylabel(r"$\lambda^*$ — part du capital commun revenant à 1")
    axes[0].set_title(r"(a) l'optimum ne partage pas également", fontsize=9.5)
    axes[0].set_ylim(0, 1)
    french_axis(axes[0].yaxis, 1)
    french_axis(axes[0].xaxis, 1)

    # (b) Le plan (K_1, K_2). L'optimum demande à 1 de céder dès que
    #     K_1 > [λ*/(1-λ*)] K_2 ; v1 ne l'autorisait que si K_1 > K_2.
    threshold = star / (1.0 - star)
    k2 = np.linspace(0, 1, 200)
    axes[1].fill_between(k2, threshold * k2, k2, color=colour("richest_lends"),
                         alpha=0.28, lw=0)
    axes[1].fill_between(k2, 0, threshold * k2, color=colour("free"),
                         alpha=0.13, lw=0)
    axes[1].plot(k2, k2, color="#444444", lw=1.1, ls="--")
    axes[1].plot(k2, threshold * k2, color=colour("richest_lends"), lw=1.5)
    # Les régions sont étiquetées SUR le tracé : une légende, ici, se pose
    # forcément sur l'une des deux et la rend illisible.
    axes[1].text(0.62, 0.50, "l'optimum veut un prêt,\nv1 le refusait",
                 fontsize=7.6, ha="center", va="center",
                 color="#7a2418", rotation=32)
    axes[1].text(0.70, 0.16, "1 reçoit\n(les deux règles)", fontsize=7.6,
                 ha="center", va="center", color="#254a6e")
    axes[1].text(0.985, 0.96, r"$K_1 = K_2$" + "\nfrontière de v1", fontsize=7.2,
                 ha="right", va="top", color="#444444")
    axes[1].text(0.985, threshold * 0.985 - 0.035,
                 r"$K_1 = " + fr(threshold, 3, math_mode=True) + r"\,K_2$"
                 + "\nfrontière de l'optimum", fontsize=7.2, ha="right",
                 va="top", color=colour("richest_lends"))
    axes[1].set_xlim(0, 1)
    axes[1].set_ylim(0, 1)
    axes[1].set_xlabel(r"capital $K_2$ de l'entité efficace (unités arbitraires)")
    axes[1].set_ylabel(r"capital $K_1$ de l'entité de faible rendement")
    axes[1].set_title(r"(b) la bande interdite, à $A_2/A_1 = 1{,}5$", fontsize=9.5)
    french_axis(axes[1].xaxis, 1)
    french_axis(axes[1].yaxis, 1)

    dump("f01_institution", ["A2_sur_A1", "lambda_star"],
         [[f"{r:.6g}", f"{v:.10g}"] for r, v in zip(ratios[::8], lambda_star[::8])])
    save(figure_, "f01_institution",
         "La bande d'échanges que la règle de richesse s'interdisait.",
         {"lambda_star": star, "seuil_bande": threshold})


# ---------------------------------------------------------------------------
# §3 — le protocole
# ---------------------------------------------------------------------------

@figure("f02_stationnarite")
def f02() -> None:
    """Le contrôle de stationnarité, et le seuil hérité qui ne transfère pas."""
    rows = [r for r in read_csv("stationarity_runs.csv") if r["fenetre"] == "residuel"]
    if not rows:
        return
    arms = ["control", "all_A150", "new_A150", "new_A075", "new_g060"]
    figure_, axes = plt.subplots(1, 2, figsize=(10.4, 3.6),
                                 gridspec_kw={"width_ratios": [1.35, 1],
                                              "wspace": 0.22})

    # (a) chaque graine, chaque bras, sous le sens libre.
    plotted = []
    for index, arm in enumerate(arms):
        values = [float(r["K_tot"]) for r in rows
                  if r["bras"] == arm and r["direction"] == "free"]
        if not values:
            continue
        jitter = np.linspace(-0.17, 0.17, len(values))
        axes[0].scatter(index + jitter, values, s=17, color=colour(arm),
                        zorder=3, alpha=0.85)
        mean, half, n = student(values)
        axes[0].errorbar([index], [mean], yerr=[half], fmt="_", ms=22,
                         color="#1a1a1a", lw=1.3, capsize=4, zorder=4)
        plotted += [[arm, r["graine"], f"{float(r['K_tot']):.10g}"]
                    for r in rows if r["bras"] == arm and r["direction"] == "free"]
    axes[0].axhspan(0.99, 1.01, color=colour("richest_lends"), alpha=0.16, lw=0)
    axes[0].axhline(1.0, color="#666666", lw=0.8)
    outside = sum(1 for r in rows if r["bras"] == "control"
                  and r["direction"] == "free"
                  and not (0.99 <= float(r["K_tot"]) <= 1.01))
    total = sum(1 for r in rows if r["bras"] == "control" and r["direction"] == "free")
    axes[0].annotate(f"la bande fixe $[0{{,}}99\\,;\\,1{{,}}01]$ rejette\n"
                     f"{outside} des {total} graines du CONTRÔLE",
                     xy=(0.20, 1.007), xytext=(1.30, 1.032), fontsize=7.4,
                     color=colour("richest_lends"), ha="left",
                     arrowprops=dict(arrowstyle="->", lw=0.8,
                                     color=colour("richest_lends")))
    axes[0].set_xticks(range(len(arms)))
    axes[0].set_xticklabels([label(a) for a in arms], fontsize=7.4, rotation=12)
    axes[0].set_ylabel(r"$K_{\rm tot}$ : dernier quart / quart précédent")
    axes[0].set_title("(a) le rapport de quarts, graine par graine", fontsize=9.5)
    french_axis(axes[0].yaxis, 2)

    # (b) ce que le critère de Student retient, lui.
    payload = read_json("lot_d_residuel.json") or {}
    entries = [e for e in payload.get("stationarity", []) if "K_tot" in e]
    names, ts, colours_ = [], [], []
    for entry in entries:
        names.append(f"{label(entry['arm'])}\n{label(entry['direction'])}")
        ts.append((entry["K_tot"]["mean"] - 1.0) / entry["K_tot"]["se"])
        colours_.append(colour("free") if entry["direction"] == "free"
                        else colour("richest_lends"))
    order = np.argsort(np.abs(ts))
    axes[1].barh(range(len(ts)), [ts[i] for i in order],
                 color=[colours_[i] for i in order], height=0.68)
    axes[1].axvline(T_CRITICAL, color="#1a1a1a", lw=0.9, ls="--")
    axes[1].axvline(-T_CRITICAL, color="#1a1a1a", lw=0.9, ls="--")
    axes[1].axvspan(-T_CRITICAL, T_CRITICAL, color="#2e8b74", alpha=0.10, lw=0)
    axes[1].set_yticks(range(len(ts)))
    axes[1].set_yticklabels([names[i] for i in order], fontsize=6.4)
    axes[1].yaxis.tick_right()          # sinon les étiquettes mordent sur (a)
    axes[1].set_xlabel(r"statistique de Student sur la moyenne")
    axes[1].set_title(r"(b) le critère employé : $|t| \leq 2{,}201$", fontsize=9.5)
    french_axis(axes[1].xaxis, 1)

    dump("f02_stationnarite", ["bras", "graine", "rapport_K_tot"], plotted)
    save(figure_, "f02_stationnarite",
         "Un seuil hérité d'une autre fenêtre rejetterait le contrôle lui-même.",
         {"controle_hors_bande": outside, "controle_graines": total})


# ---------------------------------------------------------------------------
# §4 — le régime que le sens libre rend possible
# ---------------------------------------------------------------------------

@figure("f03_horizon")
def f03() -> None:
    """La part à contre-sens décroît, puis PLAFONNE ; et la cohorte survit."""
    block = 50
    figure_, axes = plt.subplots(1, 2, figsize=(10.4, 3.6))
    plotted: list[list] = []

    for arm in ARMS_MIXED:
        stacked = []
        for seed in SEEDS:
            rows = series("free", arm, seed)
            if not rows:
                continue
            after = [r for r in rows if int(r["t"]) > T0]
            reversed_ = column(after, "mkt_reversed")
            rounds = column(after, "mkt_rounds")
            with np.errstate(invalid="ignore", divide="ignore"):
                stacked.append(blocks(np.where(rounds > 0, reversed_ / rounds, np.nan),
                                      block))
        if not stacked:
            continue
        width = min(len(s) for s in stacked)
        mean = np.nanmean(np.array([s[:width] for s in stacked]), axis=0)
        steps = T0 + block * (np.arange(width) + 0.5)
        axes[0].plot(steps, 100 * mean, color=colour(arm), lw=1.3, label=label(arm))
        plotted += [[arm, int(t), f"{100 * v:.6g}"] for t, v in zip(steps, mean)]

    windows(axes[0])
    axes[0].set_yscale("log")
    axes[0].set_xlabel("$t$ (pas)")
    axes[0].set_ylabel("part des rondes à contre-sens (%)")
    axes[0].set_title(f"(a) moyenne sur douze graines, blocs de {block} pas",
                      fontsize=9.5)
    axes[0].legend(loc="upper right")

    # (b) la cohorte d'origine, sous les deux règles.
    for direction in ("free", "richest_lends"):
        stacked = []
        for seed in SEEDS:
            rows = series(direction, "new_A150", seed, "tech_series.csv")
            if not rows:
                continue
            steps = sorted({int(r["t"]) for r in rows if int(r["t"]) > T0})
            alive = {int(r["t"]): number(r, "n_alive") for r in rows if r["tech"] == "0"}
            stacked.append(np.array([alive.get(t, 0.0) for t in steps]))
        if not stacked:
            continue
        width = min(len(s) for s in stacked)
        mean = np.mean(np.array([s[:width] for s in stacked]), axis=0)
        axis_steps = np.array(steps[:width])
        axes[1].plot(axis_steps, mean, color=colour(direction), lw=1.3,
                     label=label(direction))
        keep = slice(None, None, 20)
        plotted += [[f"tech0_{direction}", int(t), f"{v:.6g}"]
                    for t, v in zip(axis_steps[keep], mean[keep])]

    windows(axes[1])
    axes[1].set_yscale("log")
    axes[1].set_xlabel("$t$ (pas)")
    axes[1].set_ylabel("effectif de la cohorte d'origine")
    axes[1].set_title(r"(b) bras $A\times1{,}5$ (nouvelles) : qui survit",
                      fontsize=9.5)
    axes[1].legend(loc="upper right")

    dump("f03_horizon", ["serie", "t", "valeur"], plotted)
    save(figure_, "f03_horizon",
         "Le régime nouveau ne s'éteint pas : il plafonne.")


@figure("f04_contrefactuel")
def f04() -> None:
    """Le nombre d'échanges à contre-sens, et le volume qu'ils portent.

    Deux observables distinctes, et le rapport insiste sur le fait qu'elles
    diffèrent : les prêts à contre-sens n'ont pas la taille moyenne des
    autres. La figure montre que le signe de cet écart CHANGE entre les deux
    fenêtres, ce qu'aucun des deux niveaux publiés ne laisse voir seul.
    """
    figure_, axes = plt.subplots(1, 2, figsize=(10.4, 3.5),
                                 gridspec_kw={"width_ratios": [1.2, 1],
                                              "wspace": 0.26})
    block = 50
    plotted: list[list] = []

    stacked: dict[str, list] = {"nombre": [], "volume": []}
    for seed in SEEDS:
        rows = series("free", "new_A150", seed)
        if not rows:
            continue
        after = [r for r in rows if int(r["t"]) > T0]
        rounds = column(after, "mkt_rounds")
        volume = column(after, "loan_volume")
        with np.errstate(invalid="ignore", divide="ignore"):
            stacked["nombre"].append(blocks(
                np.where(rounds > 0, column(after, "mkt_reversed") / rounds, np.nan),
                block))
            stacked["volume"].append(blocks(
                np.where(volume > 0, column(after, "mkt_volume_rev") / volume, np.nan),
                block))
    styles = {"nombre": (colour("free"), "-", "part du NOMBRE de rondes"),
              "volume": (colour("all_A150"), "-", "part du VOLUME prêté")}
    for key, runs in stacked.items():
        if not runs:
            continue
        width = min(len(s) for s in runs)
        mean = np.nanmean(np.array([s[:width] for s in runs]), axis=0)
        steps = T0 + block * (np.arange(width) + 0.5)
        tint, style, name = styles[key]
        axes[0].plot(steps, 100 * mean, lw=1.4, ls=style, color=tint, label=name)
        plotted += [[key, int(s), f"{100 * v:.6g}"] for s, v in zip(steps, mean)]
    windows(axes[0])
    axes[0].set_yscale("log")
    axes[0].set_xlabel("$t$ (pas)")
    axes[0].set_ylabel("part à contre-sens (%)")
    axes[0].set_title(r"(a) bras $A\times1{,}5$ (nouvelles), douze graines",
                      fontsize=9.5)
    axes[0].legend(loc="upper right")

    payload = read_json("lot_d_transition.json") or {}
    names, bars = [], {"blocked_share": [], "reversed_share": [], "volume_rev_share": []}
    for arm in ARMS_MIXED:
        levels = payload.get("arms", {}).get(arm, {}).get("levels_free", {})
        if not levels:
            continue
        names.append(label(arm))
        for key in bars:
            bars[key].append(100 * levels[key]["mean"])
    x = np.arange(len(names))
    legends = {
        "blocked_share": (colour("richest_lends"),
                          "refusées par la règle ancienne\n(contrefactuel, instantané)"),
        "reversed_share": (colour("free"), "conclues à contre-sens"),
        "volume_rev_share": (colour("all_A150"), "volume qu'elles portent"),
    }
    for index, (key, (tint, name)) in enumerate(legends.items()):
        axes[1].bar(x + (index - 1) * 0.27, bars[key], width=0.25,
                    color=tint, label=name)
        for xi, value in zip(x + (index - 1) * 0.27, bars[key]):
            axes[1].text(xi, value + 0.35, fr(value, 2), ha="center", fontsize=6.4,
                         color=tint)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(names, fontsize=7, rotation=8)
    axes[1].set_ylabel("part, fenêtre de transition (%)")
    axes[1].set_ylim(0, 33)
    axes[1].set_title("(b) les trois bras mixtes", fontsize=9.5)
    # Légende SOUS le panneau : les barres montent à 26 % et la note occupe
    # le haut ; il n'y a pas de coin libre à l'intérieur.
    axes[1].legend(fontsize=6.6, loc="upper center", bbox_to_anchor=(0.5, -0.20),
                   ncol=1, handlelength=1.2)

    worst = max(abs(b - r) for b, r in zip(bars["blocked_share"],
                                           bars["reversed_share"]))
    axes[1].text(0.5, 0.985,
                 "contrefactuel et prêts conclus : "
                 f"jamais plus de {fr(worst, 3)} point d'écart",
                 transform=axes[1].transAxes, fontsize=6.6, va="top", ha="center")
    dump("f04_contrefactuel", ["serie", "t", "part_pct"], plotted)
    save(figure_, "f04_contrefactuel",
         "Le compteur contrefactuel n'est pas une trajectoire, et le volume "
         "ne suit pas le nombre.",
         {"reversed_new_A150": bars["reversed_share"][0] / 100,
          "blocked_new_A150": bars["blocked_share"][0] / 100,
          "volume_new_A150": bars["volume_rev_share"][0] / 100,
          "ecart_contrefactuel_max": worst})


@figure("f05_survivants")
def f05() -> None:
    """Qui survit, et de quoi elle vit."""
    rows = read_csv("survivors_entities.csv")
    summary = read_csv("survivors.csv")
    if not rows or not summary:
        return
    seeds = sorted({int(r["seed"]) for r in summary})
    figure_, axes = plt.subplots(1, 3, figsize=(11.6, 3.4),
                                 gridspec_kw={"wspace": 0.30})

    # (a) l'effectif survivant de la cohorte d'origine, graine par graine.
    width = 0.36
    for index, direction in enumerate(("free", "richest_lends")):
        counts = []
        for seed in seeds:
            match = [s for s in summary if int(s["seed"]) == seed
                     and s["direction"] == direction and int(s["tech"]) == 0]
            counts.append(float(match[0]["n"]) if match else 0.0)
        positions = [s + (index - 0.5) * width for s in seeds]
        axes[0].bar(positions, counts, width=width, color=colour(direction),
                    label=label(direction))
        # Un effectif nul ne dessine aucune barre : on l'écrit, sinon un
        # lecteur croit à une donnée manquante.
        for x, value in zip(positions, counts):
            if value == 0:
                axes[0].text(x, 0.12, "0", ha="center", va="bottom", fontsize=7.5,
                             color=colour(direction), fontweight="bold")
    axes[0].set_xticks(seeds)
    axes[0].set_xlabel("graine")
    axes[0].set_ylabel("ancienne technologie :\neffectif encore vivant")
    axes[0].set_title(r"(a) à $t_0 + 2000$", fontsize=9.5)
    axes[0].legend(fontsize=7.2)

    # (b) position nette contre capital, état final, sens libre.
    subset = [r for r in rows if r["direction"] == "free"
              and int(r["seed"]) == seeds[0]]
    for tech, name, size, alpha in ((1, "nouvelle technologie", 6, 0.30),
                                    (0, "ancienne technologie", 26, 0.95)):
        group = [r for r in subset if int(r["tech"]) == tech]
        if not group:
            continue
        axes[1].scatter([float(r["K"]) for r in group],
                        [float(r["net_position"]) for r in group],
                        s=size, alpha=alpha, color=colour(f"tech{tech}"),
                        label=name, zorder=3 if tech == 0 else 1,
                        rasterized=True, linewidths=0)
    axes[1].axhline(0.0, color="#666666", lw=0.8)
    axes[1].set_yscale("symlog", linthresh=100)
    axes[1].set_xlabel("capital $K$")
    axes[1].set_ylabel("position nette (créances $-$ dettes)")
    axes[1].set_title("(b) qui détient les créances, sens libre", fontsize=9.5)
    axes[1].legend(fontsize=7.2, loc="lower right")

    # (c) la part du revenu qui vient de l'intérêt.
    labels_, values, tints = [], [], []
    for direction in ("free", "richest_lends"):
        for tech in (0, 1):
            match = [s for s in summary if s["direction"] == direction
                     and int(s["tech"]) == tech]
            if not match:
                continue
            labels_.append(("libre" if direction == "free" else "ancienne")
                           + ("\nanc. tech." if tech == 0 else "\nnouv. tech."))
            values.append(100 * sum(float(m["part_du_revenu_en_interets"])
                                    for m in match) / len(match))
            tints.append(colour(direction) if tech == 1 else colour("tech0"))
    axes[2].bar(range(len(labels_)), values, color=tints, width=0.62)
    for index, value in enumerate(values):
        axes[2].text(index, value + 1.4, fr(value, 1), ha="center", fontsize=7.4)
    axes[2].set_xticks(range(len(labels_)))
    axes[2].set_xticklabels(labels_, fontsize=6.8)
    axes[2].set_ylim(0, 108)
    axes[2].set_ylabel("part du revenu venant des intérêts (%)")
    axes[2].set_title("(c) vivre de sa production, ou de l'intérêt", fontsize=9.5)

    dump("f05_survivants_entites", ["direction", "graine", "tech", "K",
                                    "position_nette"],
         [[r["direction"], r["seed"], r["tech"], f"{number(r, 'K'):.10g}",
           f"{number(r, 'net_position'):.10g}"]
          for r in rows if r["direction"] == "free" and int(r["seed"]) == seeds[0]])
    dump("f05_survivants", ["direction", "graine", "tech", "effectif",
                            "part_du_revenu_en_interets"],
         [[r["direction"], r["seed"], r["tech"], r["n"],
           f"{number(r, 'part_du_revenu_en_interets'):.10g}"] for r in summary])

    old_free = [s for s in summary if s["direction"] == "free" and int(s["tech"]) == 0]
    new_free = [s for s in summary if s["direction"] == "free" and int(s["tech"]) == 1]
    annotated = {
        "interet_ancienne_libre": (sum(float(s["part_du_revenu_en_interets"])
                                       for s in old_free) / len(old_free)),
        "interet_nouvelle_libre": (sum(float(s["part_du_revenu_en_interets"])
                                       for s in new_free) / len(new_free)),
    }
    save(figure_, "f05_survivants",
         "Les survivantes de l'ancienne technologie vivent de l'intérêt.",
         annotated)


@figure("f06_apparie")
def f06() -> None:
    """Les effets agrégés appariés, les deux fenêtres côte à côte."""
    columns = (("prod_tot", "production"), ("K_tot", "capital"),
               ("pop", "population"), ("deaths_per_pop", "mortalité"),
               ("n_loans", "contrats"), ("rotation", "rotation"),
               ("interest_paid", "intérêts"))
    figure_, axes = plt.subplots(1, 2, figsize=(10.6, 3.7), sharey=False,
                                 gridspec_kw={"wspace": 0.24})
    plotted: list[list] = []
    counted: dict[str, tuple] = {}
    for panel, (window, title) in enumerate((
            ("transition", r"(a) fenêtre de transition $]t_0,\ t_0+200]$"),
            ("residuel", r"(b) régime résiduel $]t_0+1000,\ t_0+2000]$"))):
        payload = read_json(f"lot_d_{window}.json") or {}
        arms = [a for a in ARMS_MIXED
                if payload.get("arms", {}).get(a, {}).get("paired_free_vs_v1")]
        width = 0.8 / max(len(arms), 1)
        for index, arm in enumerate(arms):
            entry = payload["arms"][arm]["paired_free_vs_v1"]
            xs = np.arange(len(columns)) + index * width
            values = [100 * entry[c]["mean"] for c, _ in columns]
            errors = [100 * entry[c]["se"] * (entry[c]["t_crit_5pct"] or T_CRITICAL)
                      for c, _ in columns]
            axes[panel].bar(xs, values, width=width * 0.9, yerr=errors, capsize=2,
                            color=colour(arm), label=label(arm),
                            error_kw={"lw": 0.8, "ecolor": "#333333"})
            plotted += [[window, arm, c, f"{100 * entry[c]['mean']:.6g}",
                         f"{100 * entry[c]['se']:.6g}", f"{entry[c]['t']:.6g}"]
                        for c, _ in columns]
        # Combien de ces barres sont indistinguables de zéro : c'est
        # l'argument des deux fenêtres, rendu comptable.
        total = crossing = 0
        largest = 0.0
        for arm in arms:
            entry = payload["arms"][arm]["paired_free_vs_v1"]
            for name, _ in columns:
                node = entry[name]
                total += 1
                crossing += abs(node["t"]) < (node["t_crit_5pct"] or T_CRITICAL)
                largest = max(largest, abs(node["mean"]))
        counted[window] = (crossing, total, largest)
        axes[panel].text(0.02, 0.97,
                         f"{crossing} des {total} écarts sont\n"
                         "indistinguables de zéro",
                         transform=axes[panel].transAxes, fontsize=7.2,
                         va="top", ha="left")
        axes[panel].axhline(0.0, color="#1a1a1a", lw=0.9)
        axes[panel].set_xticks(np.arange(len(columns)) + 0.4 - width / 2)
        axes[panel].set_xticklabels([name for _, name in columns], rotation=22,
                                    fontsize=7.4, ha="right")
        axes[panel].set_title(title, fontsize=9.5)
        french_axis(axes[panel].yaxis, 1)
    axes[0].set_ylabel("écart sens libre / règle ancienne (%)")
    # Légende commune SOUS les deux panneaux : dans chacun d'eux, les quatre
    # coins portent soit des barres, soit le compte annoté.
    handles, names = axes[0].get_legend_handles_labels()
    figure_.legend(handles, names, fontsize=7.4, loc="lower center", ncol=3,
                   bbox_to_anchor=(0.5, -0.10))

    transition = read_json("lot_d_transition.json") or {}
    annotated = {
        key: transition["arms"]["new_A150"]["paired_free_vs_v1"][key]["mean"]
        for key in ("prod_tot", "K_tot", "deaths_per_pop", "n_loans")
    }
    for window, (crossing, total, largest) in counted.items():
        tag = "Transition" if window == "transition" else "Residuel"
        annotated[f"nuls{tag}"] = float(crossing)
        annotated[f"total{tag}"] = float(total)
    dump("f06_apparie", ["fenetre", "bras", "colonne", "moyenne_pct", "se_pct", "t"],
         plotted)
    save(figure_, "f06_apparie",
         "Le levier agit fort pendant la transition, presque plus après.",
         annotated)


@figure("f07_creanciers")
def f07() -> None:
    """La signature structurelle du changement de règle."""
    figure_, axes = plt.subplots(1, 3, figsize=(11.6, 3.3),
                                 gridspec_kw={"wspace": 0.28})
    plotted: list[list] = []
    panels = (("K_share_creditors", r"part du capital aux créancières nettes",
               "(a) qui détient le capital"),
              ("corr_K_net", "$r$ de Pearson",
               "(b) corr(capital, position nette)"),
              ("corr_marg_net", "$r$ de Pearson",
               "(c) corr(rendement marginal, position nette)"))
    for index, (key, ylabel, title) in enumerate(panels):
        for direction in ("richest_lends", "free"):
            rows = series(direction, "new_A150", 0)
            if not rows:
                continue
            steps = column(rows, "t")
            values = column(rows, key)
            keep = steps > T0 - 600
            axes[index].plot(steps[keep], values[keep], lw=0.4,
                             color=colour(direction), alpha=0.22)
            smooth = np.convolve(values[keep], np.ones(25) / 25, mode="valid")
            axes[index].plot(steps[keep][24:], smooth, lw=1.3,
                             color=colour(direction), label=label(direction))
            sparse = slice(None, None, 10)
            plotted += [[key, direction, int(s), f"{v:.8g}"]
                        for s, v in zip(steps[keep][sparse], values[keep][sparse])]
        # Le NIVEAU du régime résiduel, sous chaque règle. C'est lui que le
        # rapport cite : un écart relatif sur une corrélation signée traverse
        # zéro et ne veut rien dire.
        residual = read_json("lot_d_residuel.json") or {}
        entry = residual.get("arms", {}).get("new_A150", {})
        for side, direction in (("levels_free", "free"), ("levels_v1", "richest_lends")):
            mean = entry.get(side, {}).get(key, {}).get("mean")
            if mean is None or mean != mean:
                continue
            axes[index].plot([T0 + 1000, T0 + 2000], [mean, mean], lw=1.6,
                             color=colour(direction), ls=(0, (1, 1)))
            # Les deux niveaux peuvent coïncider (c'est le cas du rendement
            # marginal) : sans décalage, les deux étiquettes se superposent et
            # le lecteur croit à une seule mesure.
            offset = 0.028 if direction == "free" else -0.028
            axes[index].annotate(fr(mean, 3), xy=(T0 + 2000, mean),
                                 xytext=(T0 + 2060, mean + offset * abs(mean or 1)
                                         * 2 + offset * 0.4 * (
                                             axes[index].get_ylim()[1]
                                             - axes[index].get_ylim()[0])),
                                 fontsize=6.8, va="center", ha="left",
                                 color=colour(direction))
        axes[index].axvline(T0, color="#1a1a1a", lw=0.9, ls=":")
        axes[index].set_xlim(T0 - 620, T0 + 2380)
        axes[index].set_xlabel("$t$ (pas)")
        axes[index].set_ylabel(ylabel)
        axes[index].set_title(title, fontsize=9.5)
        french_axis(axes[index].yaxis, 2)
    axes[0].legend(fontsize=7.2, loc="lower left")

    residual = read_json("lot_d_residuel.json") or {}
    entry = residual.get("arms", {}).get("new_A150", {})
    annotated = {
        f"{key}_{tag}": entry.get(side, {}).get(key, {}).get("mean")
        for key in ("corr_K_net", "corr_marg_net")
        for side, tag in (("levels_free", "free"), ("levels_v1", "v1"))
    }
    dump("f07_creanciers", ["colonne", "regle", "t", "valeur"], plotted)
    save(figure_, "f07_creanciers",
         "Sous le sens libre, ce ne sont plus les riches qui détiennent les créances.",
         annotated)


@figure("f08_chaine")
def f08() -> None:
    """La chaîne causale : plus d'échanges, donc moins de production."""
    payload = read_json("lot_d_transition.json") or {}
    paired = payload.get("arms", {}).get("new_A150", {}).get("paired_free_vs_v1", {})
    if not paired:
        return
    chain = (("n_loans", "1. contrats vivants"),
             ("interest_paid", "2. intérêts versés"),
             ("deaths_per_pop", "3. mortalité"),
             ("destroyed_per_K", "4. capital détruit,\nrapporté au stock"),
             ("pop", "5. population"),
             ("K_tot", "6. capital total"),
             ("prod_tot", "7. production"))
    figure_, axes = plt.subplots(figsize=(7.0, 3.6))
    y = np.arange(len(chain))
    means = [100 * paired[c]["mean"] for c, _ in chain]
    errors = [100 * paired[c]["se"] * (paired[c]["t_crit_5pct"] or T_CRITICAL)
              for c, _ in chain]
    tints = [colour("free") if m > 0 else colour("richest_lends") for m in means]
    axes.barh(y, means, xerr=errors, color=tints, height=0.62, capsize=3,
              error_kw={"lw": 0.9, "ecolor": "#333333"})
    for yi, mean, err in zip(y, means, errors):
        offset = 0.6 if mean > 0 else -0.6
        axes.text(mean + np.sign(mean) * (err + 0.6), yi,
                  fr(mean, 2) + " %", va="center", fontsize=7.4,
                  ha="left" if mean > 0 else "right",
                  color=tints[yi])
    axes.axvline(0.0, color="#1a1a1a", lw=0.9)
    axes.set_yticks(y)
    axes.set_yticklabels([name for _, name in chain], fontsize=7.6)
    axes.invert_yaxis()
    axes.set_xlabel("écart apparié sens libre / règle ancienne (%),"
                    "\nfenêtre de transition, barres de Student à 5 %")
    axes.set_xlim(-17, 30)
    french_axis(axes.xaxis, 0)
    dump("f08_chaine", ["maillon", "colonne", "moyenne_pct", "demi_intervalle_pct",
                        "t"],
         [[name, key, f"{100 * paired[key]['mean']:.6g}",
           f"{100 * paired[key]['se'] * (paired[key]['t_crit_5pct'] or T_CRITICAL):.6g}",
           f"{paired[key]['t']:.6g}"] for key, name in chain])
    save(figure_, "f08_chaine",
         "Le surplus est un flux, le service qu'il crée est une charge perpétuelle.",
         {key: paired[key]["mean"] for key, _ in chain})


@figure("f09_loi_en_defaut")
def f09() -> None:
    """La loi de la lignée précédente, et ce que le levier nouveau lui fait."""
    payload = read_json("lot_d_transition.json") or {}
    arms = [a for a in ARMS_MIXED
            if payload.get("arms", {}).get(a, {}).get("paired_free_vs_v1")]
    if not arms:
        return
    EXPONENT = 1.337        # exposant publié par la lignée M4.3Live
    figure_, axes = plt.subplots(1, 2, figsize=(10.0, 3.5),
                                 gridspec_kw={"width_ratios": [1, 1.1],
                                              "wspace": 0.26})

    rotations, predicted, measured = [], [], []
    for arm in arms:
        entry = payload["arms"][arm]["paired_free_vs_v1"]
        rotations.append(entry["rotation"]["mean"])
        predicted.append((1 + entry["rotation"]["mean"]) ** EXPONENT - 1)
        measured.append(entry["deaths_per_pop"]["mean"])
    x = np.arange(len(arms))
    axes[0].bar(x - 0.19, [100 * v for v in predicted], width=0.36,
                color=colour("richest_lends"),
                label=r"prédite par $(\text{rotation})^{1{,}337}$")
    axes[0].bar(x + 0.19, [100 * v for v in measured], width=0.36,
                color=colour("free"), label="mesurée")
    for xi, value in zip(x - 0.19, predicted):
        axes[0].text(xi, 100 * value + 0.4, fr(100 * value, 1), ha="center",
                     fontsize=7, color=colour("richest_lends"))
    for xi, value in zip(x + 0.19, measured):
        axes[0].text(xi, 100 * value + 0.4, fr(100 * value, 1), ha="center",
                     fontsize=7, color=colour("free"))
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([label(a) for a in arms], fontsize=7, rotation=8)
    axes[0].set_ylabel("écart apparié de mortalité (%)")
    axes[0].set_title("(a) la loi sur-prédit d'un facteur 3 à 10", fontsize=9.5)
    axes[0].legend(fontsize=7)

    # (b) la même chose dans le plan de la loi, avec la courbe elle-même.
    grid = np.linspace(0.0, max(rotations) * 1.25, 100)
    axes[1].plot(100 * grid, 100 * ((1 + grid) ** EXPONENT - 1),
                 color=colour("richest_lends"), lw=1.4,
                 label=r"$\Delta$mortalité $=(1+\Delta\text{rotation})^{1{,}337}-1$")
    for arm, rot, mes in zip(arms, rotations, measured):
        axes[1].scatter([100 * rot], [100 * mes], s=42, color=colour(arm),
                        zorder=4, label=label(arm))
        axes[1].plot([100 * rot, 100 * rot],
                     [100 * mes, 100 * ((1 + rot) ** EXPONENT - 1)],
                     color="#999999", lw=0.8, ls=":")
    axes[1].axhline(0.0, color="#666666", lw=0.7)
    axes[1].set_xlabel("écart apparié de rotation du crédit (%)")
    axes[1].set_ylabel("écart apparié de mortalité (%)")
    axes[1].set_title("(b) l'écart à la loi, levier par levier", fontsize=9.5)
    axes[1].legend(fontsize=6.6, loc="upper left")

    dump("f09_loi_en_defaut", ["bras", "ecart_rotation", "mortalite_predite",
                               "mortalite_mesuree"],
         [[arm, f"{rot:.10g}", f"{pred:.10g}", f"{mes:.10g}"]
          for arm, rot, pred, mes in zip(arms, rotations, predicted, measured)])
    annotated = {}
    for arm, rot, pred, mes in zip(arms, rotations, predicted, measured):
        annotated[f"rotation_{arm}"] = rot
        annotated[f"predite_{arm}"] = pred
        annotated[f"mesuree_{arm}"] = mes
    save(figure_, "f09_loi_en_defaut",
         "Un cinquième levier, et la régularité ne s'y range pas.", annotated)


# ---------------------------------------------------------------------------
# §5 — l'ordre des phases
# ---------------------------------------------------------------------------

@figure("f10_service_ratio")
def f10() -> None:
    """La fenêtre de bascule est vide, et on voit de combien."""
    values = np.sort(np.array([number(row, "rapport_capital_sur_du")
                               for row in read_csv("service_ratio.csv")]))
    if values.size == 0:
        return
    delta = 0.01
    threshold = 1.0 / (1.0 - delta)
    figure_, axis = plt.subplots(figsize=(8.4, 3.2))
    bins = np.logspace(0, 2.6, 110)
    axis.hist(values, bins=bins, color=colour("free"), alpha=0.9, lw=0)
    axis.axvspan(1.0, threshold, color=colour("richest_lends"), alpha=0.85, zorder=3)
    axis.axvline(values[0], color=colour("richest_lends"), lw=1.2, ls="--")
    top = axis.get_ylim()[1]
    axis.annotate(f"fenêtre de bascule $[1\\,;\\,{fr(threshold, 4, math_mode=True)}]$\n"
                  "— un cheveu, à cette échelle",
                  xy=(1.02, top * 0.42), xytext=(1.30, top * 0.72), fontsize=7.4,
                  color=colour("richest_lends"),
                  arrowprops=dict(arrowstyle="->", color=colour("richest_lends"),
                                  lw=0.9))
    axis.annotate(f"minimum observé : {fr(values[0], 2)}\n"
                  f"soit {fr(values[0] / threshold, 2)} fois le seuil",
                  xy=(values[0], top * 0.22), xytext=(values[0] * 1.7, top * 0.45),
                  fontsize=7.4, arrowprops=dict(arrowstyle="->", lw=0.9))
    axis.set_xscale("log")
    axis.set_xlim(0.92, 300)
    axis.set_xlabel(r"rapport capital / dû à l'instant du service (échelle log)")
    axis.set_ylabel("nombre de débitrices")
    axis.set_title(f"{len(values)} observations de débitrices sur les douze "
                   "amorçages — aucune dans la fenêtre", fontsize=9.5)
    counts, edges = np.histogram(values, bins=bins)
    dump("f10_service_ratio", ["borne_basse", "borne_haute", "effectif"],
         [[f"{lo:.6g}", f"{hi:.6g}", int(n)]
          for lo, hi, n in zip(edges[:-1], edges[1:], counts) if n > 0])
    save(figure_, "f10_service_ratio",
         "Le levier ne peut pas mordre à cette dépréciation.",
         {"n_debitrices": float(values.size), "minimum": float(values[0]),
          "seuil": threshold})


@figure("f11_redistribution")
def f11() -> None:
    """L'échange des phases ne crée aucun défaut : il redistribue."""
    payload = read_json("lot_e_residuel.json") or {}
    paired = payload.get("paired", {})
    if not paired:
        return
    figure_, axes = plt.subplots(1, 2, figsize=(10.2, 3.5),
                                 gridspec_kw={"width_ratios": [1, 1.2],
                                              "wspace": 0.26})

    # Les défauts NE sont PAS dans ce panneau : ils valent zéro dans les deux
    # bras, donc l'écart relatif est 0/0 et n'existe pas. Une barre absente
    # se lit comme une donnée manquante ; le fait est donc écrit.
    columns = (("deaths_per_pop", "mortalité"), ("prod_tot", "production"),
               ("K_tot", "capital"), ("pop", "population"))
    x = np.arange(len(columns))
    means = [100 * paired[c]["mean"] for c, _ in columns]
    errors = [100 * paired[c]["se"] * (paired[c].get("t_crit_5pct") or T_CRITICAL)
              for c, _ in columns]
    tints = [colour("free") if m > 0 else colour("richest_lends") for m in means]
    axes[0].bar(x, means, yerr=errors, capsize=3, width=0.6, color=tints,
                error_kw={"lw": 0.9, "ecolor": "#333333"})
    axes[0].axhline(0.0, color="#1a1a1a", lw=0.9)
    prediction = payload.get("prediction", {})
    measured = prediction.get("defauts_mesures", float("nan"))
    axes[0].text(0.97, 0.97,
                 "défauts de liquidité :\n"
                 f"{fr(measured, 3)} par pas dans les DEUX bras.\n"
                 "La prédiction annonçait zéro de plus ;\n"
                 "l'écart relatif, lui, n'est pas défini.",
                 transform=axes[0].transAxes, fontsize=6.8, va="top",
                 ha="right", color=colour("richest_lends"))
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([name for _, name in columns], fontsize=7.2, rotation=12)
    axes[0].set_ylabel("écart apparié, ordre inversé / ordre v1 (%)")
    axes[0].set_title("(a) régime résiduel, douze graines appariées", fontsize=9.5)
    french_axis(axes[0].yaxis, 1)

    # (b) la dérive s'accumule : peu sur un pas, beaucoup sur mille.
    plotted: list[list] = []
    stacked = []
    for seed in SEEDS:
        treated = read_csv(CAMPAIGN / "phase" / "deprec_first" / f"seed{seed}"
                           / "series.csv")
        reference = series("free", "control", seed)
        if not treated or not reference:
            continue
        width = min(len(treated), len(reference))
        steps = column(treated[:width], "t")
        ratio = column(treated[:width], "prod_tot") / column(reference[:width], "prod_tot")
        keep = steps > T0 - 250     # montrer que les deux bras sont IDENTIQUES avant
        stacked.append((steps[keep], ratio[keep]))
    if stacked:
        size = min(len(s) for s, _ in stacked)
        steps = stacked[0][0][:size]
        matrix = np.array([r[:size] for _, r in stacked])
        mean = matrix.mean(axis=0)
        half = T_CRITICAL * matrix.std(axis=0, ddof=1) / math.sqrt(matrix.shape[0])
        axes[1].plot(steps, 100 * (mean - 1), lw=1.3, color=colour("free"),
                     label="moyenne sur douze graines")
        axes[1].fill_between(steps, 100 * (mean - half - 1), 100 * (mean + half - 1),
                             color=colour("free"), alpha=0.20, lw=0,
                             label="intervalle de Student à 5 %")
        sparse = slice(None, None, 20)
        plotted += [[int(s), f"{100 * (v - 1):.6g}"]
                    for s, v in zip(steps[sparse], mean[sparse])]
    windows(axes[1])
    axes[1].axhline(0.0, color="#1a1a1a", lw=0.9)
    axes[1].set_xlabel("$t$ (pas)")
    axes[1].set_ylabel("production : écart au bras de référence (%)")
    axes[1].set_title(r"(b) identiques jusqu'à $t_0$, puis durablement écartés",
                      fontsize=9.5)
    axes[1].legend(fontsize=7.2, loc="lower left")
    french_axis(axes[1].yaxis, 1)

    dump("f11_redistribution", ["t", "ecart_production_pct"], plotted)
    save(figure_, "f11_redistribution",
         "Zéro défaut de plus, et pourtant des agrégats déplacés.",
         {"defauts_mesures": measured,
          "prod_tot": paired["prod_tot"]["mean"],
          "part_redistribuee": prediction.get("part_du_capital_redistribuee")})


# ---------------------------------------------------------------------------
# §6 — l'instrumentation
# ---------------------------------------------------------------------------

@figure("f12_tension")
def f12() -> None:
    """La tension, native et exacte, sur toute la durée d'un run."""
    rows = read_csv(CAMPAIGN / "arms" / "free" / "control" / "seed0" / "tension_agg.csv")
    if not rows:
        return
    steps = column(rows, "t")
    figure_, axes = plt.subplots(1, 2, figsize=(10.4, 3.4),
                                 gridspec_kw={"wspace": 0.30})

    # (a) les deux échelles. K_mean n'est PAS tracé : il colle à K_eq à moins
    #     de 3 % (c'est le rapport de Jensen, panneau b), et deux courbes
    #     superposées ne se lisent pas.
    axes[0].plot(steps, column(rows, "K_aut"), lw=1.5, color=colour("richest_lends"),
                 label=r"$K^*_{\rm aut} = [A(1-\delta)/\delta]^{1/(1-\gamma)}$")
    axes[0].plot(steps, column(rows, "K_eq"), lw=1.5, color=colour("free"),
                 label=r"$K_{\rm eq} = (\Pi/nA)^{1/\gamma}$")
    residual = read_json("lot_d_residuel.json") or {}
    levels = residual.get("arms", {}).get("control", {}).get("levels_free", {})
    tension_level = levels.get("tension", {}).get("mean")
    jensen_level = levels.get("jensen", {}).get("mean")
    if tension_level:
        mid = T0 + 1500
        top = number(rows[min(mid, len(rows)) - 1], "K_aut")
        bottom = number(rows[min(mid, len(rows)) - 1], "K_eq")
        axes[0].annotate("", xy=(mid, top), xytext=(mid, bottom),
                         arrowprops=dict(arrowstyle="<->", lw=1.1, color="#1a1a1a"))
        axes[0].text(mid - 120, math.sqrt(top * bottom),
                     f"tension\n$T = {fr(tension_level, 1, math_mode=True)}$",
                     fontsize=7.6, ha="right", va="center")
    axes[0].set_yscale("log")
    axes[0].set_ylim(20, 4e4)
    axes[0].set_xlabel("$t$ (pas)")
    axes[0].set_ylabel("capital (joules, échelle log)")
    axes[0].set_title("(a) les deux échelles que la tension compare", fontsize=9.5)
    axes[0].legend(fontsize=7.2, loc="lower right")

    # (b) la relaxation, et le rapport de Jensen que le calcul natif rend exact.
    axes[1].plot(steps, column(rows, "tension"), lw=1.3, color=colour("all_A150"),
                 label=r"tension $T$")
    if tension_level:
        axes[1].plot([T0 + 1000, T0 + 2000], [tension_level] * 2, lw=2.2,
                     color="#1a1a1a")
        axes[1].text(T0 + 1500, tension_level * 1.18,
                     f"$T = {fr(tension_level, 1, math_mode=True)}$",
                     fontsize=7.6, ha="center")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("$t$ (pas)")
    axes[1].set_ylabel("tension (échelle log)")
    twin = axes[1].twinx()
    jensen = column(rows, "jensen")
    twin.plot(steps, jensen, lw=0.4, color=colour("new_A075"), alpha=0.25)
    smooth = np.convolve(jensen, np.ones(51) / 51, mode="valid")
    twin.plot(steps[50:], smooth, lw=1.2, color=colour("new_A075"),
              label=r"Jensen $K_{\rm eq}/\bar K$ (moyenne glissante)")
    twin.set_ylabel("rapport de Jensen", color=colour("new_A075"))
    twin.tick_params(axis="y", colors=colour("new_A075"))
    twin.set_ylim(0.955, 1.002)
    twin.grid(False)
    if jensen_level:
        twin.annotate(f"Jensen $= {fr(jensen_level, 4, math_mode=True)}$",
                      xy=(2600, jensen_level), xytext=(700, 0.9640),
                      fontsize=7.4, color=colour("new_A075"),
                      arrowprops=dict(arrowstyle="->", lw=0.8,
                                      color=colour("new_A075")))
    axes[1].set_title("(b) contrôle, graine 0 : la relaxation", fontsize=9.5)
    handles, labels_ = axes[1].get_legend_handles_labels()
    extra = twin.get_legend_handles_labels()
    axes[1].legend(handles + extra[0], labels_ + extra[1], fontsize=6.8,
                   loc="upper right")

    dump("f12_tension", ["t", "K_aut", "K_eq", "K_mean", "tension", "jensen"],
         [[int(rows[i]["t"])] + [f"{number(rows[i], k):.8g}" for k in
                                 ("K_aut", "K_eq", "K_mean", "tension", "jensen")]
          for i in range(0, len(rows), 25)])
    save(figure_, "f12_tension",
         "La tension et le rapport de Jensen, calculés dans le moteur.",
         {"tension_controle": tension_level, "jensen_controle": jensen_level})


@figure("f13_amplitude")
def f13() -> None:
    """Un levier sur gamma n'est pas un cadran de puissance."""
    rows = read_csv("amplitude.csv")
    if not rows:
        return
    figure_, axes = plt.subplots(1, 2, figsize=(10.4, 3.4),
                                 gridspec_kw={"width_ratios": [1.35, 1],
                                              "wspace": 0.30})
    names = [row["levier"] for row in rows]
    x = np.arange(len(rows))
    triples = (("m_exact", colour("free"), "amplitude MESURÉE $m$"),
               ("m_naif_capital_unite", colour("richest_lends"),
                r"prédiction naïve « $K = 1$ »"),
               ("m_naif_K_eq", colour("all_A150"),
                r"prédiction au capital équivalent $K_{\rm eq}$"))
    for index, (key, tint, name) in enumerate(triples):
        values = [number(row, key) for row in rows]
        axes[0].bar(x + (index - 1) * 0.27, values, width=0.25, color=tint, label=name)
    gamma_row = next((r for r in rows if r["param"] == "gamma"), None)
    if gamma_row is not None:
        position = names.index(gamma_row["levier"])
        axes[0].annotate("le levier ferait « rien »\nsi l'on croyait la naïve",
                         xy=(position, 1.03), xytext=(position - 1.30, 1.55),
                         fontsize=7.2, color=colour("richest_lends"),
                         arrowprops=dict(arrowstyle="->", lw=0.9,
                                         color=colour("richest_lends")))
        axes[0].text(position, number(gamma_row, "m_exact") + 0.05,
                     fr(number(gamma_row, "m_exact"), 6), ha="center",
                     fontsize=7.2, color=colour("free"))
    axes[0].axhline(1.0, color="#1a1a1a", lw=0.8, ls=":")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(names, fontsize=6.6, rotation=10)
    axes[0].set_ylabel("amplitude $m$ (facteur sur la production traitée)")
    axes[0].set_ylim(0, 2.35)
    axes[0].set_title("(a) mesurer, ou croire la formule", fontsize=9.5)
    axes[0].legend(fontsize=6.8, loc="upper left")
    french_axis(axes[0].yaxis, 1)

    shares = [number(row, "p_ex_ante") for row in rows]
    axes[1].bar(x, shares, width=0.55, color=colour("control"))
    for xi, value in zip(x, shares):
        axes[1].text(xi, value * 1.25, fr(value, 6), ha="center", fontsize=6.8)
    axes[1].set_yscale("log")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(names, fontsize=6.6, rotation=10)
    axes[1].set_ylabel(r"part traitée $p$ \emph{ex ante} (échelle log)"
                       .replace("\\emph{", "").replace("}", ""))
    axes[1].set_ylim(2e-3, 6.0)
    axes[1].set_title("(b) et la part de production que cela touche", fontsize=9.5)

    dump("f13_amplitude", ["levier", "m_exact", "m_naif_capital_unite",
                           "m_naif_K_eq", "p_ex_ante"],
         [[row["levier"], row["m_exact"], row["m_naif_capital_unite"],
           row["m_naif_K_eq"], row["p_ex_ante"]] for row in rows])
    annotated = {}
    for row in rows:
        tag = {("A", "all"): "AllA", ("A", "fraction"): "FractionA",
               ("gamma", "all"): "Gamma", ("A", "new"): "NewA"}[
                   (row["param"], row["portee"])]
        annotated[f"m_{tag}"] = number(row, "m_exact")
        annotated[f"naive_{tag}"] = number(row, "m_naif_capital_unite")
        annotated[f"keq_{tag}"] = number(row, "m_naif_K_eq")
        annotated[f"p_{tag}"] = number(row, "p_ex_ante")
    save(figure_, "f13_amplitude",
         "L'amplitude d'un levier sur l'exposant dépend du capital.", annotated)


# ---------------------------------------------------------------------------
# §7 — ce qui détermine la rotation du crédit
# ---------------------------------------------------------------------------

def _sweep_rows() -> list[dict]:
    return read_csv("rotation_runs.csv")


def _lever_of(row: dict) -> str:
    return row["run"].split("/")[0].split("_")[0]


def _predicted_cv(row: dict) -> float:
    renewal = number(row, "births_per_pop")
    ratio = number(row, "K0") / number(row, "K_mean")
    return math.sqrt((renewal * (1.0 - ratio) ** 2 + number(row, "sigma") ** 2)
                     / number(row, "rho"))


@figure("f14_decomposition")
def f14() -> None:
    """Deux facteurs sur trois sont pinés ; le troisième porte tout."""
    rows = _sweep_rows()
    if not rows:
        return
    summary = read_json("rotation_summary.json") or {}
    figure_, axes = plt.subplots(1, 3, figsize=(11.6, 3.3),
                                 gridspec_kw={"wspace": 0.30})
    families = sorted({row["family"] for row in rows})
    tints = {"v1": colour("richest_lends"), "v2": colour("free"),
             "balayage v2": colour("new_A075")}
    for family in families:
        subset = [row for row in rows if row["family"] == family]
        tint = tints.get(family, colour("control"))
        axes[0].scatter([number(r, "rho") for r in subset],
                        [number(r, "f1_rounds_per_entity") for r in subset],
                        s=13, alpha=0.55, color=tint, label=family,
                        rasterized=True, linewidths=0)
        axes[1].scatter([number(r, "rotation") for r in subset],
                        [number(r, "f2_trade_probability") for r in subset],
                        s=13, alpha=0.55, color=tint, label=family,
                        rasterized=True, linewidths=0)
        axes[2].scatter([number(r, "f3_transfer_over_Kmean") for r in subset],
                        [number(r, "rotation") / number(r, "rho") for r in subset],
                        s=13, alpha=0.55, color=tint, label=family,
                        rasterized=True, linewidths=0)
    grid = [min(number(r, "f3_transfer_over_Kmean") for r in rows),
            max(number(r, "f3_transfer_over_Kmean") for r in rows)]
    axes[2].plot(grid, grid, color="#1a1a1a", lw=0.9, ls="--", label="identité")

    gap = summary.get("f1_vs_rho_max_gap")
    if gap is not None:
        axes[0].plot([0.4, 2.1], [0.4, 2.1], color="#1a1a1a", lw=0.8, ls="--")
        axes[0].set_title(r"(a) $f_1 = \lfloor \rho N\rfloor/N$ : combinatoire pure"
                          + f"\nécart maximal à $\\rho$ : {fr(gap, 3)}",
                          fontsize=9)
    axes[0].set_xlabel(r"$\rho$ (paramètre)")
    axes[0].set_ylabel(r"$f_1$ — rondes par entité")

    lo, hi = summary.get("f2_min"), summary.get("f2_max")
    if lo is not None:
        axes[1].axhspan(lo, hi, color=colour("new_A075"), alpha=0.20, lw=0)
        axes[1].set_title(r"(b) $f_2$ — probabilité de traiter"
                          + f"\ntoute la plage : [{fr(lo, 4)} ; {fr(hi, 4)}]",
                          fontsize=9)
    axes[1].set_xlabel("rotation du crédit")
    axes[1].set_ylabel(r"$f_2$ — prêts conclus / rondes")
    axes[1].set_ylim(0.990, 1.0005)

    axes[2].set_xlabel(r"$f_3 = \mathbb{E}|\delta| / \bar K$")
    axes[2].set_ylabel(r"rotation $/\ \rho$")
    axes[2].set_title(r"(c) toute la variation est dans $f_3$", fontsize=9)
    for axis in axes:
        axis.legend(fontsize=6.6)
    dump("f14_decomposition", ["famille", "run", "rho", "f1", "f2", "f3",
                               "rotation"],
         [[r["family"], r["run"], r["rho"], r["f1_rounds_per_entity"],
           r["f2_trade_probability"], r["f3_transfer_over_Kmean"], r["rotation"]]
          for r in rows])
    save(figure_, "f14_decomposition",
         "Une identité en trois facteurs, dont deux sont pinés.",
         {"f1_gap": gap, "f2_min": lo, "f2_max": hi})


@figure("f15_gini")
def f15() -> None:
    """f_3 EST le Gini — et la phase de marché resserre ce qu'elle consomme."""
    rows = [r for r in _sweep_rows() if r.get("gini_logmean")]
    entities = read_csv("survivors_entities.csv")
    figure_, axes = plt.subplots(1, 2, figsize=(10.2, 3.6),
                                 gridspec_kw={"wspace": 0.28})

    # (a) ce qu'un coefficient de Gini de 0,07 veut dire, vu comme une courbe.
    annotated: dict = {}
    for direction in ("richest_lends", "free"):
        capitals = [number(r, "K") for r in entities
                    if r["direction"] == direction and r["seed"] == "0"]
        if not capitals:
            continue
        x, y = lorenz(capitals)
        coefficient = gini(capitals)
        annotated[f"gini_{direction}"] = coefficient
        axes[0].plot(x, y, lw=1.5, color=colour(direction),
                     label=f"{label(direction)} — $G = {fr(coefficient, 4, math_mode=True)}$")
    axes[0].plot([0, 1], [0, 1], color="#1a1a1a", lw=0.9, ls="--",
                 label="égalité parfaite")
    axes[0].set_xlabel("part des entités, du plus pauvre au plus riche")
    axes[0].set_ylabel("part du capital détenue")
    axes[0].set_title(r"(a) la distribution des capitaux à $t_0+2000$", fontsize=9.5)
    axes[0].legend(fontsize=7, loc="upper left")
    french_axis(axes[0].xaxis, 1)
    french_axis(axes[0].yaxis, 1)

    # (b) le Gini d'AVANT la phase de marché surestime f3 ; la moyenne
    #     logarithmique le corrige.
    if rows:
        f3 = np.array([number(r, "f3_transfer_over_Kmean") for r in rows])
        before = np.array([number(r, "gini_before") for r in rows])
        logmean = np.array([number(r, "gini_logmean") for r in rows])
        axes[1].scatter(before, f3, s=26, marker="^", color=colour("richest_lends"),
                        alpha=0.85, label=r"$G$ AVANT la phase de marché")
        axes[1].scatter(logmean, f3, s=26, color=colour("free"),
                        label=r"$\bar G$ — moyenne logarithmique sur la phase")
        span = [min(logmean.min(), f3.min()) * 0.92, max(before.max(), f3.max()) * 1.08]
        axes[1].plot(span, span, color="#1a1a1a", lw=0.9, ls="--", label="identité")
        summary = read_json("rotation_summary.json") or {}
        med_before = summary.get("f3_over_gini_before", {}).get("median")
        med_log = summary.get("f3_over_gini_logmean", {}).get("median")
        if med_before is not None:
            axes[1].text(0.03, 0.95,
                         f"biais médian :\n  $G$ avant  {fr(100 * med_before, 1)} %\n"
                         f"  $\\bar G$        {fr(100 * med_log, 1)} %",
                         transform=axes[1].transAxes, fontsize=7.4, va="top")
            annotated["biais_avant"] = med_before
            annotated["biais_logmean"] = med_log
        axes[1].set_xscale("log")
        axes[1].set_yscale("log")
    axes[1].set_xlabel("coefficient de Gini des capitaux")
    axes[1].set_ylabel(r"$f_3 = \mathbb{E}|\delta|/\bar K$ mesuré")
    axes[1].set_title("(b) la correction que la phase s'inflige à elle-même",
                      fontsize=9.5)
    axes[1].legend(fontsize=6.8, loc="lower right")
    lorenz_rows: list[list] = []
    for direction in ("richest_lends", "free"):
        capitals = [number(r, "K") for r in entities
                    if r["direction"] == direction and r["seed"] == "0"]
        if not capitals:
            continue
        x, y = lorenz(capitals)
        step = max(1, len(x) // 200)
        lorenz_rows += [[direction, f"{a:.6g}", f"{b:.8g}"]
                        for a, b in zip(x[::step], y[::step])]
    dump("f15_gini_lorenz", ["direction", "part_des_entites", "part_du_capital"],
         lorenz_rows)
    dump("f15_gini", ["run", "gini_avant", "gini_moyenne_log", "f3"],
         [[r["run"], r["gini_before"], r["gini_logmean"],
           r["f3_transfer_over_Kmean"]] for r in rows])
    save(figure_, "f15_gini",
         "La rotation du crédit n'est pas une grandeur de crédit : c'est une "
         "inégalité.", annotated)


@figure("f16_fermeture")
def f16() -> None:
    """Le bilan de variance donne le bon ordre de grandeur, pas une loi."""
    rows = [r for r in _sweep_rows() if r.get("gini_logmean")]
    if not rows:
        return
    summary = read_json("rotation_summary.json") or {}
    fit = summary.get("fits", {}).get(r"rotation $\sim CV$ prédit $\times\ \rho$", {})
    figure_, axes = plt.subplots(1, 2, figsize=(10.2, 3.6),
                                 gridspec_kw={"wspace": 0.28})

    levers: dict[str, list[dict]] = {}
    for row in rows:
        levers.setdefault(_lever_of(row), []).append(row)
    for lever, group in sorted(levers.items()):
        axes[0].scatter([_predicted_cv(r) for r in group],
                        [number(r, "f3_transfer_over_Kmean") for r in group],
                        s=30, color=colour(lever), label=f"levier {label(lever)}",
                        zorder=3)
    xs = np.array([_predicted_cv(r) for r in rows])
    axes[0].plot(sorted(xs), sorted(xs / math.sqrt(math.pi)), color="#1a1a1a",
                 lw=1.0, ls="--", label=r"prédiction $CV/\sqrt{\pi}$")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel(r"$CV$ prédit par le bilan de variance")
    axes[0].set_ylabel(r"$f_3$ mesuré")
    axes[0].set_title("(a) l'ordre de grandeur est bon", fontsize=9.5)
    axes[0].legend(fontsize=6.6, loc="upper left")

    gaps = np.array([number(r, "rotation")
                     / (number(r, "rho") * _predicted_cv(r) / math.sqrt(math.pi)) - 1.0
                     for r in rows])
    axes[1].hist(100 * gaps, bins=18, color=colour("free"), alpha=0.85, lw=0)
    axes[1].axvline(0.0, color="#1a1a1a", lw=1.0)
    node = summary.get("rotation_over_closed_form", {})
    if node:
        axes[1].axvline(100 * node["median"], color=colour("richest_lends"), lw=1.4,
                        ls="--",
                        label=f"médiane {fr(100 * node['median'], 1)} %")
        axes[1].legend(fontsize=7.2)
    axes[1].set_xlabel(r"écart de la rotation à $\rho\,CV/\sqrt{\pi}$ (%)")
    axes[1].set_ylabel("nombre de runs instrumentés")
    axes[1].set_title("(b) mais la forme fermée se trompe de 20 %", fontsize=9.5)
    dump("f16_fermeture", ["levier", "run", "cv_predit", "f3", "ecart_forme_fermee"],
         [[_lever_of(r), r["run"], f"{_predicted_cv(r):.10g}",
           r["f3_transfer_over_Kmean"], f"{g:.10g}"]
          for r, g in zip(rows, gaps)])
    save(figure_, "f16_fermeture",
         "Un ordre de grandeur correct n'est pas une loi.",
         {"ecart_median": node.get("median"), "pente_groupee": fit.get("slope"),
          "r2_groupe": fit.get("r2")})


@figure("f17_leviers")
def f17() -> None:
    """Le contrôle par famille, qui invalide la fermeture."""
    summary = read_json("rotation_summary.json") or {}
    levers = summary.get("fits_par_levier", {})
    grouped = summary.get("fits", {}).get(
        r"rotation $\sim CV$ prédit $\times\ \rho$", {})
    if not levers:
        return
    order = ["rho", "K0", "sigma", "lam", "delta"]
    order = [name for name in order if name in levers]
    figure_, axes = plt.subplots(1, 2, figsize=(10.2, 3.4),
                                 gridspec_kw={"width_ratios": [1, 1.1],
                                              "wspace": 0.30})

    spans = [levers[name]["span"] for name in order]
    axes[0].barh(range(len(order)), [100 * (s - 1) for s in spans],
                 color=[colour(name) for name in order], height=0.6)
    axes[0].axvline(10.0, color="#1a1a1a", lw=1.0, ls="--")
    axes[0].text(0.97, 0.20, "10 % — en deçà,\nl'exposant ne mesure rien",
                 transform=axes[0].transAxes, fontsize=7.2, va="center", ha="right")
    for index, span in enumerate(spans):
        axes[0].text(100 * (span - 1) + 2, index, f"×{fr(span, 2)}",
                     va="center", fontsize=7)
    axes[0].set_yticks(range(len(order)))
    axes[0].set_yticklabels([label(name) for name in order])
    axes[0].set_xscale("symlog", linthresh=1.0)
    axes[0].set_xlabel(r"étendue de $x$ balayée (%), échelle log")
    axes[0].set_title("(a) ce que chaque famille couvre", fontsize=9.5)

    slopes = [levers[name]["slope"] for name in order]
    errors = [T_CRITICAL * levers[name]["se_slope"] for name in order]
    usable = [levers[name]["span"] >= 1.10 for name in order]
    axes[1].errorbar([s for s, u in zip(slopes, usable) if u],
                     [i for i, u in enumerate(usable) if u],
                     xerr=[e for e, u in zip(errors, usable) if u],
                     fmt="o", ms=6, lw=1.2, capsize=3, color=colour("free"),
                     label="famille exploitable")
    axes[1].errorbar([s for s, u in zip(slopes, usable) if not u],
                     [i for i, u in enumerate(usable) if not u],
                     xerr=[e for e, u in zip(errors, usable) if not u],
                     fmt="o", ms=6, lw=1.2, capsize=3, color=colour("richest_lends"),
                     alpha=0.55, label="étendue trop faible")
    if grouped:
        axes[1].axvline(grouped["slope"], color="#1a1a1a", lw=1.3, ls="--",
                        label=f"ajustement groupé : {fr(grouped['slope'], 3)}")
    axes[1].set_yticks(range(len(order)))
    axes[1].set_yticklabels([label(name) for name in order])
    axes[1].set_xlim(-3.0, 12.0)
    axes[1].set_xlabel("exposant ajusté à l'intérieur de la famille")
    axes[1].set_title("(b) et les exposants ne coïncident pas", fontsize=9.5)
    axes[1].legend(fontsize=6.6, loc="upper right")
    french_axis(axes[1].xaxis, 0)
    for axis in axes:
        axis.invert_yaxis()

    dump("f17_leviers", ["levier", "etendue", "exposant", "se_exposant", "r2", "n"],
         [[name, f"{levers[name]['span']:.10g}", f"{levers[name]['slope']:.10g}",
           f"{levers[name]['se_slope']:.10g}", f"{levers[name]['r2']:.10g}",
           levers[name]["n"]] for name in order]
         + [["groupé", f"{grouped.get('span', float('nan')):.10g}",
             f"{grouped.get('slope', float('nan')):.10g}",
             f"{grouped.get('se_slope', float('nan')):.10g}",
             f"{grouped.get('r2', float('nan')):.10g}", grouped.get("n", "")]])
    annotated = {f"pente_{name}": levers[name]["slope"] for name in order}
    annotated["pente_groupee"] = grouped.get("slope")
    save(figure_, "f17_leviers",
         "Le R² groupé reflète la géométrie du balayage, pas une réponse.",
         annotated)


@figure("f18_hetero")
def f18() -> None:
    """La relation hors du régime homogène : bonne en médiane, à queue lourde."""
    rows = read_csv("hetero_gap.csv")
    if not rows:
        return
    summary = (read_json("rotation_summary.json") or {}).get("hetero", {})
    figure_, axes = plt.subplots(1, 2, figsize=(10.2, 3.4),
                                 gridspec_kw={"width_ratios": [1.25, 1],
                                              "wspace": 0.26})
    plotted: list[list] = []
    for direction in ("free", "richest_lends"):
        subset = [r for r in rows if r["direction"] == direction]
        if not subset:
            continue
        for seed in sorted({r["graine"] for r in subset}):
            run = [r for r in subset if r["graine"] == seed]
            steps = np.array([int(r["t"]) for r in run])
            gaps = np.array([number(r, "ecart") for r in run])
            axes[0].plot(steps, 100 * gaps, lw=0.35, alpha=0.45,
                         color=colour(direction), rasterized=True)
            smooth = np.convolve(gaps, np.ones(51) / 51, mode="valid")
            axes[0].plot(steps[50:], 100 * smooth, lw=1.2, color=colour(direction))
            plotted += [[direction, seed, int(s), f"{100 * v:.6g}"]
                        for s, v in zip(steps[50::25], smooth[::25])]
        gaps = np.array([number(r, "ecart") for r in subset])
        node = summary.get(direction, {})
        axes[1].hist(100 * gaps, bins=70, alpha=0.55, color=colour(direction),
                     lw=0, label=(f"{label(direction)} — médiane "
                                  f"{fr(100 * node['median'], 2)} %"
                                  if node else label(direction)))
    windows(axes[0])
    axes[0].axhline(0.0, color="#1a1a1a", lw=0.9)
    axes[0].set_xlabel("$t$ (pas)")
    axes[0].set_ylabel(r"$f_3/\bar G - 1$ (%)")
    axes[0].set_title(r"(a) bras $A\times1{,}5$ (nouvelles) : deux technologies",
                      fontsize=9.5)
    axes[1].axvline(0.0, color="#1a1a1a", lw=0.9)
    axes[1].set_xlabel(r"$f_3/\bar G - 1$ (%)")
    axes[1].set_ylabel("nombre de pas")
    axes[1].set_title("(b) la queue est lourde des deux côtés", fontsize=9.5)
    axes[1].legend(fontsize=6.8)
    dump("f18_hetero", ["direction", "graine", "t", "ecart_lisse_pct"], plotted)
    save(figure_, "f18_hetero",
         "Une loi du régime homogène, robuste en médiane hors de lui.",
         {f"median_{d}": summary.get(d, {}).get("median")
          for d in ("free", "richest_lends") if summary.get(d)})


@figure("f19_mortalite_rotation")
def f19() -> None:
    """La relation que la lignée précédente avait établie, sur tout le corpus."""
    rows = [r for r in _sweep_rows()
            if number(r, "rotation") > 0 and number(r, "deaths_per_pop") > 0]
    if not rows:
        return
    summary = read_json("rotation_summary.json") or {}
    fit = summary.get("fits", {}).get("mortalité $\\sim$ rotation (tous runs)", {})
    figure_, axes = plt.subplots(1, 2, figsize=(10.2, 3.6),
                                 gridspec_kw={"width_ratios": [1.2, 1],
                                              "wspace": 0.28})

    for direction in ("richest_lends", "free"):
        subset = [r for r in rows if r["loan_direction"] == direction]
        axes[0].scatter([number(r, "rotation") for r in subset],
                        [number(r, "deaths_per_pop") for r in subset],
                        s=15, alpha=0.55, color=colour(direction),
                        label=f"{label(direction)} ({len(subset)} runs)",
                        rasterized=True, linewidths=0)
    x = np.array([number(r, "rotation") for r in rows])
    grid = np.array([x.min(), x.max()])
    if fit:
        axes[0].plot(grid, fit["factor"] * grid ** fit["slope"], color="#1a1a1a",
                     lw=1.2,
                     label=(f"exposant {fr(fit['slope'], 3)} $\\pm$ "
                            f"{fr(fit['se_slope'], 3)}, $R^2 = {fr(fit['r2'], 4, math_mode=True)}$"))
    published = 1.337
    if fit:
        anchor = fit["factor"] * (grid.mean() ** fit["slope"]) / grid.mean() ** published
        axes[0].plot(grid, anchor * grid ** published, color=colour("all_A150"),
                     lw=1.2, ls="--",
                     label=r"exposant $1{,}337$ publié par la lignée")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("rotation du crédit (échelle log)")
    axes[0].set_ylabel("morts par entité et par pas (échelle log)")
    axes[0].set_title(f"(a) {len(rows)} runs des deux lignées", fontsize=9.5)
    axes[0].legend(fontsize=6.6, loc="upper left")

    # (b) le biais résiduel par règle de sens : la loi décrit bien les NIVEAUX.
    bias = summary.get("biais_residuel", {}).get("loan_direction", {})
    if fit and bias:
        for direction in ("free", "richest_lends"):
            subset = [r for r in rows if r["loan_direction"] == direction]
            residual = [number(r, "deaths_per_pop")
                        / (fit["factor"] * number(r, "rotation") ** fit["slope"]) - 1.0
                        for r in subset]
            node = bias.get(direction, {})
            axes[1].hist([100 * v for v in residual], bins=30, alpha=0.55, lw=0,
                         color=colour(direction),
                         label=(f"{label(direction)} — médiane "
                                f"{fr(100 * node['biais_median'], 2)} %"
                                if node else label(direction)))
        axes[1].axvline(0.0, color="#1a1a1a", lw=0.9)
    axes[1].set_xlabel("biais résiduel à l'ajustement (%)")
    axes[1].set_ylabel("nombre de runs")
    axes[1].set_title("(b) le levier nouveau ne déplace pas le niveau",
                      fontsize=9.5)
    axes[1].legend(fontsize=6.8)
    dump("f19_mortalite_rotation", ["famille", "run", "regle", "rotation",
                                    "morts_par_entite"],
         [[r["family"], r["run"], r["loan_direction"], r["rotation"],
           r["deaths_per_pop"]] for r in rows])
    save(figure_, "f19_mortalite_rotation",
         "La rotation prédit la mortalité en niveau, sur tout le corpus.",
         {"pente": fit.get("slope"), "r2": fit.get("r2"), "n": fit.get("n"),
          "span": fit.get("span")})


# ---------------------------------------------------------------------------
# Rapport de conception
# ---------------------------------------------------------------------------

@figure("g01_cout")
def g01() -> None:
    """Le coût quadratique de v1, et ce que la purge en fait."""
    rows = read_csv("cost_profile.csv")
    summary = read_csv("cost_profile_summary.csv")
    if not rows:
        return
    names = {"v1": "v1 — clefs mortes conservées", "v2": "v2 — purge à la mort"}
    figure_, axes = plt.subplots(1, 2, figsize=(10.4, 3.5),
                                 gridspec_kw={"wspace": 0.28})
    plotted: list[list] = []
    for engine in ("v1", "v2"):
        subset = [row for row in rows if row["engine"] == engine]
        if not subset:
            continue
        steps = column(subset, "t")
        seconds = column(subset, "seconds")
        window = 101
        smooth = np.array([np.median(seconds[max(0, i - window // 2):
                                              i + window // 2 + 1])
                           for i in range(len(seconds))])
        axes[0].plot(steps, 1000 * smooth, color=colour(engine), lw=1.3,
                     label=names[engine])
        keys = column(subset, "book_keys")
        axes[1].plot(steps, keys, color=colour(engine), lw=1.3, label=names[engine])
        plotted += [[engine, int(s), f"{1000 * m:.6g}", f"{k:.0f}"]
                    for s, m, k in zip(steps[::25], smooth[::25], keys[::25])]
        if engine == "v2":
            axes[1].plot(steps, column(subset, "pop"), color=colour("control"),
                         lw=1.0, ls="--", label="population vivante")
    row = next((r for r in summary if r["engine"] == "v1"), None)
    other = next((r for r in summary if r["engine"] == "v2"), None)
    if row and other:
        share = 100 * (1 - float(other["book_keys_final"])
                       / float(row["book_keys_final"]))
        axes[1].annotate(f"{fr(share, 1)} % des clefs de v1\nsont VIDES à $t=4000$",
                         xy=(3900, float(row["book_keys_final"])),
                         xytext=(1200, float(row["book_keys_final"]) * 0.30),
                         fontsize=7.4, color=colour("v1"),
                         arrowprops=dict(arrowstyle="->", lw=0.9, color=colour("v1")))
        axes[0].annotate(f"×{fr(float(row['growth']), 3)} sur l'horizon",
                         xy=(3700, 1000 * float(row["median_s_last200"])),
                         xytext=(1400, 1000 * float(row["median_s_last200"]) * 1.22),
                         fontsize=7.4, color=colour("v1"),
                         arrowprops=dict(arrowstyle="->", lw=0.9, color=colour("v1")))
    axes[0].set_xlabel("$t$ (pas)")
    axes[0].set_ylabel("millisecondes par pas")
    axes[0].set_title("(a) coût d'un pas (médiane glissante, 101 pas)", fontsize=9.5)
    axes[0].legend(fontsize=7.2, loc="upper left")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("$t$ (pas)")
    axes[1].set_ylabel(r"clefs parcourues à la phase d'intérêts")
    axes[1].set_title(r"(b) la croissance en $\lambda t$ du carnet mort", fontsize=9.5)
    axes[1].legend(fontsize=7.2, loc="lower right")

    annotated = {}
    if row and other:
        annotated = {"clefs_v1": float(row["book_keys_final"]),
                     "clefs_v2": float(other["book_keys_final"]),
                     "croissance_v1": float(row["growth"]),
                     "croissance_v2": float(other["growth"]),
                     "part_vide": share / 100}
    dump("g01_cout", ["moteur", "t", "ms_par_pas", "clefs"], plotted)
    save(figure_, "g01_cout",
         "Un coût total en λT²/2, et une correction qui le rend linéaire.",
         annotated)


@figure("g02_parite")
def g02() -> None:
    """La parité est NULLE, pas petite."""
    figure_, axes = plt.subplots(1, 2, figsize=(10.2, 3.4),
                                 gridspec_kw={"width_ratios": [1.15, 1],
                                              "wspace": 0.28})
    sources = (("parity_deviations_8000.csv", "moteur livré", colour("free")),
               ("parity_deviations_8000_lotA.csv", "moteur du lot A",
                colour("all_A150")),
               ("parity_deviations_500.csv", "passe intermédiaire",
                colour("new_A075")))
    plotted: list[list] = []
    reference = None
    for index, (name, title, tint) in enumerate(sources):
        rows = read_csv(name)
        if not rows:
            continue
        steps = column(rows, "t")
        gaps = np.abs(column(rows, "ecart_max_toutes_colonnes"))
        # Trois séries rigoureusement nulles se recouvrent, et une seule reste
        # visible. On trace donc le CUMUL des pas en écart — qui reste plat à
        # zéro — contre le cumul des pas comparés, qui monte. La figure dit
        # alors ce qu'elle doit dire : rien n'a jamais divergé.
        axes[1].plot(steps, np.arange(1, len(steps) + 1), lw=1.4 - 0.3 * index,
                     color=tint, ls=["-", "--", ":"][index],
                     label=f"{title} — {len(rows)} pas comparés")
        axes[1].plot(steps, np.cumsum(gaps > 0), lw=1.6, color=tint, alpha=0.9)
        if reference is None:
            reference = rows
        plotted += [[name, int(s), f"{g:.3g}"] for s, g in zip(steps[::50], gaps[::50])]

    if reference:
        steps = column(reference, "t")
        for key, tint, name in (("K_tot", colour("free"), r"$K_{\rm tot}$"),
                                ("prod_tot", colour("richest_lends"),
                                 r"production agrégée")):
            axes[0].plot(steps, column(reference, key), lw=1.3, color=tint, label=name)
        # L'échelle du dernier bit : c'est à CE niveau que l'égalité est
        # constatée, et un « écart relatif petit » ne dirait pas la même chose.
        axes[0].plot(steps, np.spacing(column(reference, "K_tot")), lw=1.1,
                     ls="--", color="#1a1a1a",
                     label=r"un ULP de $K_{\rm tot}$ — le dernier bit")
        axes[0].set_yscale("log")
        axes[0].set_xlabel("$t$ (pas)")
        axes[0].set_ylabel("joules (échelle log)")
        axes[0].set_title("(a) les grandeurs comparées, et leur dernier bit",
                          fontsize=9.5)
        axes[0].legend(fontsize=7.2, loc="center right")

    axes[1].axhline(0.0, color="#1a1a1a", lw=1.0)
    axes[1].annotate("pas présentant un écart : ZÉRO,\npour les trois passes",
                     xy=(4300, 0), xytext=(2600, 1400), fontsize=7.6,
                     arrowprops=dict(arrowstyle="->", lw=0.9))
    axes[1].set_xlabel("$t$ (pas)")
    axes[1].set_ylabel("cumul de pas")
    axes[1].set_title("(b) pas comparés, et pas en écart", fontsize=9.5)
    axes[1].legend(fontsize=6.8, loc="upper left")

    steps_count = len(read_csv("parity_deviations_8000.csv"))
    dump("g02_parite", ["source", "t", "ecart_max"], plotted)
    save(figure_, "g02_parite",
         "L'écart n'est pas petit : il est nul, à chacun des 8000 pas.",
         {"pas": float(steps_count),
          "ecart_max": float(max((abs(number(r, "ecart_max_toutes_colonnes"))
                                  for r in read_csv("parity_deviations_8000.csv")),
                                 default=float("nan")))})


@figure("g03_taux")
def g03() -> None:
    """Pourquoi la règle de taux n'a pas eu à changer, et ce que coûterait
    l'alternative.

    Aucune donnée : deux formules tracées. La règle en vigueur est la moyenne
    GÉOMÉTRIQUE des rendements marginaux ; l'alternative naturelle — le
    rendement marginal commun d'après l'échange — est la moyenne
    ARITHMÉTIQUE des capitaux. Les deux coïncident à capitaux égaux et
    divergent partout ailleurs, ce qui détruirait la parité.
    """
    gamma, coefficient = 0.5, 1.0
    ratios = np.logspace(0, 2, 300)          # K_b / K_a
    k_a = 1.0
    k_b = ratios * k_a
    current = gamma * coefficient * (k_a * k_b) ** ((gamma - 1) / 2)
    alternative = gamma * coefficient * ((k_a + k_b) / 2) ** (gamma - 1)

    figure_, axes = plt.subplots(1, 2, figsize=(9.6, 3.3),
                                 gridspec_kw={"wspace": 0.30})
    axes[0].plot(ratios, current, lw=1.5, color=colour("free"),
                 label=r"règle en vigueur : $\gamma A\,(K_a K_b)^{(\gamma-1)/2}$")
    axes[0].plot(ratios, alternative, lw=1.5, ls="--", color=colour("richest_lends"),
                 label=r"alternative : $\gamma A\,(C/2)^{\gamma-1}$")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel(r"$K_b/K_a$ — dispersion de la paire (échelle log)")
    axes[0].set_ylabel(r"taux $r$")
    axes[0].set_title(r"(a) moyenne géométrique contre arithmétique", fontsize=9.5)
    axes[0].legend(fontsize=7, loc="lower left")

    axes[1].plot(ratios, 100 * (alternative / current - 1), lw=1.5,
                 color=colour("richest_lends"))
    axes[1].axhline(0.0, color="#1a1a1a", lw=0.9)
    axes[1].axvline(1.0, color="#666666", lw=0.8, ls=":")
    axes[1].annotate("elles coïncident\nà capitaux égaux", xy=(1.0, 0.0),
                     xytext=(2.0, -12.0), fontsize=7.4,
                     arrowprops=dict(arrowstyle="->", lw=0.8))
    axes[1].set_xscale("log")
    axes[1].set_xlabel(r"$K_b/K_a$ (échelle log)")
    axes[1].set_ylabel("écart de l'alternative à la règle (%)")
    axes[1].set_title("(b) ce que l'alternative changerait", fontsize=9.5)
    french_axis(axes[1].yaxis, 0)

    dump("g03_taux", ["Kb_sur_Ka", "regle_en_vigueur", "alternative"],
         [[f"{r:.6g}", f"{c:.10g}", f"{a:.10g}"]
          for r, c, a in zip(ratios[::10], current[::10], alternative[::10])])
    save(figure_, "g03_taux",
         "La règle de taux est symétrique, et l'alternative détruirait la parité.")


@figure("g04_ordre_phases")
def g04() -> None:
    """L'échange des deux phases : ce qu'il fait exactement, en algèbre.

    Aucune donnée. Sous l'ordre `v1`, une débitrice finit le pas à
    (1-δ)(K - dû) ; sous l'ordre inverse, à (1-δ)K - dû. L'écart est
    -δ·dû, et il est exactement compensé chez la créancière. La figure trace
    les deux, et la troisième courbe — la somme — est plate à zéro.
    """
    delta = 0.01
    capital = 1000.0
    due = np.linspace(0.0, 300.0, 300)
    debtor = -delta * due
    creditor = delta * due
    figure_, axes = plt.subplots(1, 2, figsize=(9.8, 3.3),
                                 gridspec_kw={"width_ratios": [1, 1.1],
                                              "wspace": 0.30})

    # (a) l'ordre des deux phases, en schéma.
    for row, (name, blocks_) in enumerate((
            (r"ordre \code{v1}", ["production", "marché", "intérêts", "dépréciation"]),
            (r"ordre \code{deprec\_first}",
             ["production", "marché", "dépréciation", "intérêts"]))):
        for index, block in enumerate(blocks_):
            swapped = block in ("intérêts", "dépréciation")
            axes[0].add_patch(plt.Rectangle((index, -row - 0.3), 0.92, 0.6,
                                            facecolor=(colour("all_A150") if swapped
                                                       else "#e8e8e8"),
                                            alpha=0.85 if swapped else 1.0, lw=0))
            axes[0].text(index + 0.46, -row, block, ha="center", va="center",
                         fontsize=7.4)
        axes[0].text(-0.15, -row, name.replace(r"\code{", "").replace("}", "")
                     .replace("\\_", "_"),
                     ha="right", va="center", fontsize=8)
    axes[0].set_xlim(-1.5, 4.05)
    axes[0].set_ylim(-1.75, 0.75)
    axes[0].axis("off")
    axes[0].set_title("(a) les deux ordonnancements du pas", fontsize=9.5)

    # (b) l'effet, exact, et sa compensation.
    axes[1].plot(due, debtor, lw=1.5, color=colour("richest_lends"),
                 label=r"débitrice : $-\delta \times$ dû")
    axes[1].plot(due, creditor, lw=1.5, color=colour("free"),
                 label=r"créancière : $+\delta \times$ versement")
    axes[1].plot(due, debtor + creditor, lw=2.0, color="#1a1a1a", ls="--",
                 label="somme : capital total inchangé")
    axes[1].axhline(0.0, color="#666666", lw=0.7)
    axes[1].set_xlabel(r"dû au pas (joules), à $K = " + f"{capital:.0f}" + r"$")
    axes[1].set_ylabel(r"écart de capital de fin de pas (joules)")
    axes[1].set_title(r"(b) une pure redistribution, à $\delta = 0{,}01$",
                      fontsize=9.5)
    axes[1].legend(fontsize=7.2, loc="upper left")
    french_axis(axes[1].yaxis, 1)

    save(figure_, "g04_ordre_phases",
         "Échanger les deux phases conserve le capital et le redistribue.")


# ---------------------------------------------------------------------------
# MARQUEUR_FIN_DES_FIGURES
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default=None,
                        help="ne régénérer que les figures dont le nom commence ainsi")
    args = parser.parse_args(argv)
    setup()
    selected = [(name, function) for name, function in REGISTRY
                if args.only is None or name.startswith(args.only)]
    if not selected:
        print(f"aucune figure ne commence par « {args.only} »")
        return 1
    print(f"{len(selected)} figure(s) :")
    for name, function in selected:
        try:
            function()
        except Exception as error:  # noqa: BLE001 — on veut le nom de la figure
            print(f"  {name} : ÉCHEC — {type(error).__name__}: {error}")
            raise
    path = write_manifest()
    print(f"manifeste : {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
