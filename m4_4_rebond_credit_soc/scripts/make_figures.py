"""Engendre TOUTES les figures des rapports M4.4 depuis `results/analysis/`.

Même règle que `make_numbers.py` pour les nombres : aucune figure n'est
dessinée à la main, aucune donnée n'est recopiée. Chaque figure porte le nom
du fichier d'analyse dont elle vient, et les valeurs qu'elle ANNOTE sont
déposées dans `report/figures/manifest.json` pour être confrontées aux macros
LaTeX par `tests/test_figures.py`.

    python3 scripts/make_figures.py [--only prefixe]

Les figures vont dans `report/figures/` (versionné). Celles qui lisent des
sources non versionnées — panneaux, arêtes — déposent en plus la série
tracée dans `report/figures/data/`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from figures_base import (  # noqa: E402
    CAMPAIGN, ccdf, colour, dump, french_axis, label, loglog_fit, number,
    fr, percent, read_csv, read_json, save, setup, student, write_manifest,
)

REGISTRY: list = []


def figure(name: str):
    def wrap(function):
        REGISTRY.append((name, function))
        return function
    return wrap


# ---------------------------------------------------------------------------
# §3 — le protocole et la reproduction de la lignée
# ---------------------------------------------------------------------------

@figure("f01_ancrages")
def f01() -> None:
    """Les élasticités mesurées ici contre celles publiées par la lignée v2."""
    gate = read_json("lotB_gate.json")
    if not gate:
        return
    published = {"epsilon_prod_tot": 0.7473, "dln_pop_dlnA": -0.7043,
                 "dln_n_prod_dlnA": -0.6834}
    names = {"epsilon_prod_tot": "production totale $\\varepsilon$",
             "dln_pop_dlnA": "effectif de fin de pas",
             "dln_n_prod_dlnA": "effectif producteur"}
    keys = [k for k in published if k in gate["measured"]]
    figure_, axes = plt.subplots(figsize=(5.6, 2.1))
    y = np.arange(len(keys))
    means = [gate["measured"][k]["mean"] for k in keys]
    errs = [gate["measured"][k]["ci95"] for k in keys]
    axes.errorbar(means, y, xerr=errs, fmt="o", color=colour("control"),
                  capsize=3, markersize=5, linewidth=1.2, label="M4.4 (12 graines appariées)")
    axes.scatter([published[k] for k in keys], y, marker="|", s=260,
                 color=colour("all_A150"), linewidth=1.6, label="lignée M4.3Live-v2")
    axes.set_yticks(y)
    axes.set_yticklabels([names[k] for k in keys])
    axes.axvline(0.0, color="#999999", linewidth=0.6)
    axes.set_xlabel("élasticité par rapport à la productivité $A$")
    axes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2)
    axes.invert_yaxis()
    french_axis(axes.xaxis, 2)
    save(figure_, "f01_ancrages",
         "Reproduction de la lignée avant prolongement.",
         {k: gate["measured"][k]["mean"] for k in keys})


@figure("f02_identite")
def f02() -> None:
    """La décomposition de l'élasticité, graine par graine : une identité."""
    rows = read_csv("decomposition_epsilon.csv")
    if not rows:
        return
    seeds = [int(r["seed"]) for r in rows]
    eps = [number(r, "epsilon") for r in rows]
    terms = {"terme_n_prod": "effectif producteur",
             "terme_gamma_Keq": "échelle par entité"}
    figure_, axes = plt.subplots(figsize=(5.6, 2.6))
    width = 0.34
    x = np.arange(len(seeds))
    bottom_pos = np.zeros(len(seeds))
    bottom_neg = np.zeros(len(seeds))
    for index, (key, name) in enumerate(terms.items()):
        values = np.array([number(r, key) for r in rows])
        base = np.where(values >= 0, bottom_pos, bottom_neg)
        axes.bar(x - width / 2, values, width, bottom=base, label=name,
                 color=colour("", index), edgecolor="white", linewidth=0.4)
        bottom_pos = np.where(values >= 0, bottom_pos + values, bottom_pos)
        bottom_neg = np.where(values < 0, bottom_neg + values, bottom_neg)
    axes.bar(x + width / 2, eps, width, color="#444444", label="$\\varepsilon$ mesuré",
             edgecolor="white", linewidth=0.4)
    residual = max(abs(number(r, "somme_identite") - number(r, "epsilon")) for r in rows)
    axes.axhline(0.0, color="#666666", linewidth=0.6)
    axes.set_xticks(x)
    axes.set_xticklabels(seeds)
    axes.set_xlabel("graine")
    axes.set_ylabel("contribution à $\\varepsilon$")
    axes.set_title(f"somme des termes $-$ $\\varepsilon$ : {residual:.1e} (identité)".replace(".", ","))
    axes.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.28))
    french_axis(axes.yaxis, 1)
    save(figure_, "f02_identite", "L'identité de décomposition se referme.",
         {"residu": residual})


# ---------------------------------------------------------------------------
# §4 — où va le surcroît de production
# ---------------------------------------------------------------------------

QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999]


def _quantile_ratios(arm: str) -> dict:
    """Rapport bras/contrôle par quantile, apparié graine par graine."""
    rows = [r for r in read_csv("lotB_distribution.csv") if r["statistic"] == "mean"]
    treated = {int(r["seed"]): r for r in rows if r["arm"] == arm}
    control = {int(r["seed"]): r for r in rows if r["arm"] == "control"}
    seeds = sorted(set(treated) & set(control))
    out: dict[str, dict] = {}
    for quantity in ("prod", "income", "income_net", "int_in", "nw", "K"):
        means, errs = [], []
        for q in QUANTILES:
            key = f"q{q}_{quantity}"
            ratios = []
            for seed in seeds:
                a, b = number(treated[seed], key), number(control[seed], key)
                if b != 0 and np.isfinite(a) and np.isfinite(b):
                    ratios.append(a / b)
            mean, ci, _ = student(ratios)
            means.append(mean)
            errs.append(ci)
        out[quantity] = {"mean": means, "ci95": errs}
    return out


@figure("f03_quantiles")
def f03() -> None:
    """FIGURE MAÎTRESSE du §4 : le surcroît va au corps, pas à la queue."""
    ratios = _quantile_ratios("all_A150")
    if not ratios:
        return
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 2.9), sharex=True)
    x = np.arange(len(QUANTILES))
    for index, quantity in enumerate(("prod", "income", "nw", "K")):
        entry = ratios[quantity]
        left.errorbar(x, entry["mean"], yerr=entry["ci95"], marker="o", markersize=3.5,
                      capsize=2, linewidth=1.2, color=colour("", index),
                      label=label(quantity))
    left.axhline(1.0, color="#888888", linewidth=0.6, linestyle="--")
    left.set_ylabel("rapport $A\\times1{,}5$ / contrôle")
    left.set_title("le corps monte d'un bloc, le sommet moins")
    left.legend(ncol=2)

    entry = ratios["int_in"]
    right.errorbar(x, entry["mean"], yerr=entry["ci95"], marker="o", markersize=3.5,
                   capsize=2, linewidth=1.4, color=colour("all_A150"),
                   label=label("int_in"))
    right.axhline(1.0, color="#888888", linewidth=0.6, linestyle="--")
    right.set_yscale("log")
    right.set_title("le bas du canal d'intérêt s'effondre")
    right.legend()

    for axes in (left, right):
        axes.set_xticks(x)
        axes.set_xticklabels([f"{100 * q:g}".replace(".", ",") for q in QUANTILES])
        axes.set_xlabel("centile")
    french_axis(left.yaxis, 2)
    save(figure_, "f03_quantiles",
         "Rapport par quantile entre le bras de rebond et son contrôle.",
         {"prod_q0.1": ratios["prod"]["mean"][0],
          "prod_q0.99": ratios["prod"]["mean"][6],
          "income_q0.999": ratios["income"]["mean"][7],
          "nw_q0.999": ratios["nw"]["mean"][7],
          "int_in_q0.1": ratios["int_in"]["mean"][0]})


@figure("f04_deciles")
def f04() -> None:
    """Parts de production et de revenu d'intérêt par décile de capital."""
    rows = [r for r in read_csv("lotB_distribution.csv") if r["statistic"] == "mean"]
    if not rows:
        return
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 2.6), sharex=True)
    x = np.arange(10)
    for axes, suffix, title in ((left, "prodshare", "part de la production"),
                                (right, "int_inshare", "part du revenu d'intérêt")):
        for index, arm in enumerate(("control", "all_A150")):
            subset = [r for r in rows if r["arm"] == arm]
            means, errs = [], []
            for decile in range(10):
                values = [number(r, f"Kdec{decile}_{suffix}") for r in subset]
                mean, ci, _ = student(values)
                means.append(mean)
                errs.append(ci)
            axes.errorbar(x, means, yerr=errs, marker="o", markersize=3.5, capsize=2,
                          linewidth=1.2, color=colour(arm), label=label(arm))
        axes.set_title(title)
        axes.set_xlabel("décile de capital")
        axes.set_xticks(x)
        axes.set_xticklabels([str(d + 1) for d in x])
        percent(axes.yaxis, 0)
    left.set_ylabel("part du total")
    left.legend()
    save(figure_, "f04_deciles",
         "Concentration par décile de capital, contrôle contre bras de rebond.")


@figure("f05_position_nette")
def f05() -> None:
    """Producteurs ou rentiers : effectif, production, revenu net par position."""
    rows = [r for r in read_csv("lotB_distribution.csv") if r["statistic"] == "mean"]
    if not rows:
        return
    groups = ("crediteur", "debiteur", "neutre")
    families = (("popshare", "effectif"), ("prodshare", "production"),
                ("income_netshare", "revenu net"))
    figure_, axes = plt.subplots(figsize=(6.0, 2.6))
    width = 0.13
    positions = np.arange(len(families))
    for index, arm in enumerate(("control", "all_A150")):
        subset = [r for r in rows if r["arm"] == arm]
        for gindex, group in enumerate(groups):
            means, errs = [], []
            for prefix, _ in families:
                mean, ci, _ = student([number(r, f"{prefix}_{group}") for r in subset])
                means.append(mean)
                errs.append(ci)
            offset = (index * len(groups) + gindex - 2.5) * width
            axes.bar(positions + offset, means, width, yerr=errs, capsize=1.5,
                     color=colour("", gindex),
                     alpha=1.0 if arm == "control" else 0.55,
                     edgecolor="white", linewidth=0.4,
                     label=f"{group} — {label(arm)}")
    axes.set_xticks(positions)
    axes.set_xticklabels([name for _, name in families])
    axes.set_ylabel("part du total")
    percent(axes.yaxis, 0)
    axes.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=7)
    save(figure_, "f05_position_nette",
         "Répartition par position nette, contrôle contre bras de rebond.")


# ---------------------------------------------------------------------------
# §5 — ce qui gouverne la contraction de population
# ---------------------------------------------------------------------------

@figure("f06_mortalite_rotation")
def f06() -> None:
    """FIGURE MAÎTRESSE du §5 : l'exposant n'est pas universel.

    Deux familles de leviers, deux pentes, intervalles disjoints — et les
    deux valeurs publiées antérieurement tombent chacune sur un bras.
    """
    rows = read_csv("lotB_paired.csv")
    gate = read_json("lotB_gate.json")
    if not rows or not gate:
        return
    window = "residuel"
    arms = ["all_A150", "new_A150", "new_A075", "new_g060"]

    def series(arm: str, quantity: str) -> dict[int, float]:
        return {int(r["seed"]): number(r, "ratio") for r in rows
                if r["arm"] == arm and r["window"] == window and r["quantity"] == quantity}

    figure_, (left, right) = plt.subplots(
        1, 2, figsize=(6.9, 3.2), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # À gauche : chaque graine est un point, et l'exposant du bras est la
    # pente de la droite qui joint le contrôle (1, 1) au nuage — c'est la
    # définition même de `a` employée par le lot B, pas un ajustement libre.
    for index, arm in enumerate(arms):
        rotation, mortality = series(arm, "rotation"), series(arm, "mortality")
        seeds = sorted(set(rotation) & set(mortality))
        xs = np.array([rotation[s] for s in seeds])
        ys = np.array([mortality[s] for s in seeds])
        left.scatter(xs, ys, s=17, color=colour(arm), label=label(arm),
                     edgecolor="white", linewidth=0.3, zorder=3)
        exponent = gate["a_by_arm"].get(arm, {}).get("mean")
        if exponent and xs.size:
            grid = np.linspace(min(xs.min(), 1.0), max(xs.max(), 1.0), 40)
            left.plot(grid, grid ** exponent, color=colour(arm), linewidth=1.0,
                      linestyle="--", alpha=0.8, zorder=2)
    left.scatter([1.0], [1.0], marker="+", s=80, color="#333333", zorder=4,
                 linewidth=1.2)
    left.annotate("contrôle", (1.0, 1.0), textcoords="offset points",
                  xytext=(6, -12), fontsize=7.5, color="#444444")
    left.set_xscale("log")
    left.set_yscale("log")
    # Les graduations mineures d'une échelle logarithmique se chevauchent sur
    # moins d'une décade : on les fixe à la main.
    for axis, ticks in ((left.xaxis, [0.9, 1.0, 1.2, 1.4, 1.6]),
                        (left.yaxis, [0.8, 1.0, 1.5, 2.0])):
        axis.set_major_locator(FixedLocator(ticks))
        axis.set_minor_locator(NullLocator())
    left.set_xlabel("rotation du crédit, rapport au contrôle")
    left.set_ylabel("mortalité, rapport au contrôle")
    left.set_title("mortalité $\\propto$ rotation$^{a}$", fontsize=9)
    left.legend(loc="upper left", fontsize=7)
    french_axis(left.xaxis, 1)
    french_axis(left.yaxis, 1)

    # À droite : les quatre exposants et leurs intervalles, avec les deux
    # valeurs publiées par la lignée. C'est là que se lit le résultat —
    # `all_A150` et `new_g060` ont des intervalles DISJOINTS, et chacune des
    # deux valeurs héritées tombe sur un bras différent.
    ordered = sorted(arms, key=lambda a: -gate["a_by_arm"].get(a, {}).get("mean", 0))
    y = np.arange(len(ordered))
    means = [gate["a_by_arm"][a]["mean"] for a in ordered]
    errs = [gate["a_by_arm"][a]["ci95"] for a in ordered]
    right.errorbar(means, y, xerr=errs, fmt="o", markersize=5.5, capsize=3,
                   linewidth=1.3, color=colour("control"))
    for reference, name, shade in ((1.337, "publié par v1 : $1{,}337$", "#8a2f2f"),
                                   (1.260, "publié par v2 : $1{,}260$", "#2e8b74")):
        right.axvline(reference, color=shade, linestyle="--", linewidth=1.1,
                      label=name)
    right.legend(loc="lower center", fontsize=7, bbox_to_anchor=(0.5, -0.02))
    right.set_yticks(y)
    right.set_yticklabels([label(a) for a in ordered], fontsize=7.5)
    right.set_xlabel("exposant $a$")
    right.set_title("il n'est pas universel", fontsize=9)
    right.invert_yaxis()
    right.set_ylim(len(ordered) + 0.35, -0.6)
    french_axis(right.xaxis, 2)
    save(figure_, "f06_mortalite_rotation",
         "L'exposant liant mortalité et rotation dépend du levier employé.",
         {f"a_{a}": gate["a_by_arm"][a]["mean"] for a in arms})


@figure("f07_chaine")
def f07() -> None:
    """La chaîne du rebond, maillon par maillon, avec son intervalle."""
    gate = read_json("lotB_gate.json")
    if not gate:
        return
    order = [("dln_rotation_dlnA", "rotation du crédit"),
             ("dln_mortality_dlnA", "mortalité"),
             ("dln_pop_dlnA", "effectif"),
             ("dln_K_eq_dlnA", "capital équivalent"),
             ("epsilon_prod_tot", "production totale")]
    keys = [(k, n) for k, n in order if k in gate["measured"]]
    figure_, axes = plt.subplots(figsize=(5.6, 2.4))
    x = np.arange(len(keys))
    means = [gate["measured"][k]["mean"] for k, _ in keys]
    errs = [gate["measured"][k]["ci95"] for k, _ in keys]
    colours = [colour("all_A150") if m < 0 else colour("control") for m in means]
    axes.bar(x, means, 0.55, yerr=errs, capsize=3, color=colours,
             edgecolor="white", linewidth=0.5)
    axes.axhline(0.0, color="#666666", linewidth=0.7)
    axes.set_xticks(x)
    axes.set_xticklabels([n for _, n in keys], rotation=18, ha="right")
    axes.set_ylabel("élasticité en $A$")
    for index, (mean, err) in enumerate(zip(means, errs)):
        axes.annotate(f"{mean:+.3f}".replace(".", ","),
                      (index, mean + (0.06 if mean >= 0 else -0.10)),
                      ha="center", fontsize=7.5, color="#333333")
    axes.set_ylim(min(means) - 0.25, max(means) + 0.25)
    save(figure_, "f07_chaine", "Chaîne causale du rebond, élasticité par maillon.",
         {k: gate["measured"][k]["mean"] for k, _ in keys})


# ---------------------------------------------------------------------------
# §6 — avalanches et branchement
# ---------------------------------------------------------------------------

@figure("f08_avalanches_ccdf")
def f08() -> None:
    """Survie des tailles d'avalanche, log-log, avec la pente ajustée."""
    figure_, axes = plt.subplots(figsize=(5.4, 3.2))
    exported: list[list] = []
    annotated = {}
    for index, arm in enumerate(("control", "all_A150", "new_g060")):
        sizes: list[float] = []
        directory = CAMPAIGN / "arms" / "free" / arm
        if not directory.is_dir():
            continue
        for run in sorted(directory.iterdir())[:4]:
            for row in read_csv(str(run / "avalanches.csv")):
                time = number(row, "t")
                if 3000 < time <= 4000:
                    sizes.append(number(row, "size"))
        if not sizes:
            continue
        x, y = ccdf(sizes)
        axes.plot(x, y, drawstyle="steps-post", linewidth=1.3,
                  color=colour(arm), label=f"{label(arm)} ($n = {len(sizes)}$)")
        exported.extend([[arm, float(a), float(b)] for a, b in zip(x, y)])
        body = (x >= 2) & (y > 1e-4)
        fit = loglog_fit(x[body], y[body])
        if fit:
            annotated[f"pente_{arm}"] = fit["pente"]
    axes.set_xscale("log")
    axes.set_yscale("log")
    axes.set_xlabel("taille d'avalanche $s$ (nombre de faillites)")
    axes.set_ylabel("$P(S \\geq s)$")
    axes.set_title("distribution des tailles d'avalanche")
    axes.legend()
    dump("f08_avalanches_ccdf", ["bras", "taille", "survie"], exported)
    save(figure_, "f08_avalanches_ccdf",
         "Survie des tailles d'avalanche par bras (source : avalanches.csv, non versionné).",
         annotated)


@figure("f09_b1_b2")
def f09() -> None:
    """Les deux estimateurs du rapport de branchement, cellule par cellule."""
    rows = read_csv("lotD_avalanches.csv")
    if not rows:
        return
    figure_, axes = plt.subplots(figsize=(4.6, 3.4))
    families = {"leviers du rebond": "free/", "institution de taux": "bargain/",
                "ablation vers M4B": "ablation/"}
    for index, (name, prefix) in enumerate(families.items()):
        subset = [r for r in rows if r["arm"].startswith(prefix)]
        if not subset:
            continue
        axes.scatter([number(r, "b1") for r in subset], [number(r, "b2") for r in subset],
                     s=13, color=colour("", index), label=name, alpha=0.75,
                     edgecolor="white", linewidth=0.25)
    lo = min(number(r, "b1") for r in rows) * 0.95
    hi = max(number(r, "b2") for r in rows) * 1.02
    axes.plot([lo, hi], [lo, hi], color="#888888", linewidth=0.8, linestyle="--",
              label="$b_2 = b_1$")
    axes.set_xlabel("$b_1 = 1 - \\mathrm{racines}/\\mathrm{morts}$")
    axes.set_ylabel("$b_2 = \\mathrm{couples\\ causaux}/\\mathrm{morts}$")
    axes.set_title("deux estimateurs, un écart systématique")
    axes.legend(loc="upper left", fontsize=7.5)
    french_axis(axes.xaxis, 1)
    french_axis(axes.yaxis, 1)
    save(figure_, "f09_b1_b2", "Les deux estimateurs du rapport de branchement.")


@figure("f10_k0")
def f10() -> None:
    """La fragilité du rebond est un effet d'échelle de la dotation."""
    rows = read_csv("lotD_avalanches.csv")
    if not rows:
        return
    arms = ["free/control", "free/all_A150", "free/all_A150_K0comp"]
    figure_, axes = plt.subplots(figsize=(4.6, 2.6))
    means, errs, names = [], [], []
    for arm in arms:
        subset = [r for r in rows if r["arm"] == arm]
        mean, ci, _ = student([number(r, "b1") for r in subset])
        means.append(mean)
        errs.append(ci)
        names.append(label(arm.split("/", 1)[1]))
    x = np.arange(len(arms))
    axes.bar(x, means, 0.5, yerr=errs, capsize=3,
             color=[colour(a.split("/", 1)[1]) for a in arms],
             edgecolor="white", linewidth=0.5)
    axes.set_xticks(x)
    axes.set_xticklabels(names, rotation=12, ha="right")
    axes.set_ylabel("rapport de branchement $b_1$")
    axes.set_ylim(min(means) - 4 * max(errs) - 0.01, max(means) + 0.01)
    effect = means[1] - means[0]
    residual = means[2] - means[0]
    cancelled = 100 * (1 - abs(residual) / abs(effect)) if effect else float("nan")
    axes.set_title(f"effet de $A$ : {effect:+.4f} ; résiduel après compensation : "
                   f"{residual:+.4f}".replace(".", ","), fontsize=8.5)
    axes.annotate(f"{cancelled:.1f}  % de l'effet annulé".replace(".", ","),
                  (2, means[2]), textcoords="offset points", xytext=(0, 12),
                  ha="center", fontsize=8, color="#333333")
    french_axis(axes.yaxis, 3)
    save(figure_, "f10_k0",
         "Compenser l'échelle de dotation annule l'effet de la productivité sur le branchement.",
         {"effet": effect, "residuel": residual, "part_annulee": cancelled})


# ---------------------------------------------------------------------------
# §7 — couverture de queue et classes de lois
# ---------------------------------------------------------------------------

@figure("f11_couverture")
def f11() -> None:
    """La couverture de queue n'est plus l'obstacle — et l'exposant ne bouge pas.

    M4.2B avait conclu que l'existence de la queue de Pareto n'est pas
    décidable, et imputait le blocage à la COUVERTURE : 113 points au-delà du
    seuil. Ici la couverture double, et une campagne dédiée où le taux de
    naissance passe de 30 à 50 la porte encore de moitié — sans déplacer
    l'exposant. C'est ce que montrent les deux panneaux : l'obstacle a
    disparu, et l'indécidabilité est restée.
    """
    base = read_json("lotC0_coverage.json")
    dense_path = ROOT / "results" / "analysis_lam50" / "lotC0_coverage.json"
    dense = None
    if dense_path.exists():
        import json as _json
        dense = _json.loads(dense_path.read_text(encoding="utf-8"))
    if not base:
        return
    quantities = ["int_in", "nw", "K", "prod"]
    keys = [f"tous/{q}" for q in quantities]
    if not all(k in base["groups"] for k in keys):
        return

    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 2.9))
    x = np.arange(len(quantities))
    width = 0.36
    campaigns = [("$\\lambda = 30$", base, colour("control"), -0.5)]
    if dense:
        campaigns.append(("$\\lambda = 50$", dense, colour("all_A150"), 0.5))
    annotated = {}
    for name, data, shade, offset in campaigns:
        tails = [data["groups"][k]["n_tail_median"] for k in keys]
        left.bar(x + offset * width, tails, width, color=shade, label=name,
                 edgecolor="white", linewidth=0.5)
        for index, value in enumerate(tails):
            left.annotate(f"{value:.0f}", (index + offset * width, value),
                          textcoords="offset points", xytext=(0, 2), ha="center",
                          fontsize=6.5, color="#333333")
    target = base.get("target_n_tail", 400)
    left.axhline(target, color="#333333", linestyle="--", linewidth=1.0,
                 label=f"cible dérivée : {target:.0f}")
    left.axhline(113, color="#8a2f2f", linestyle=":", linewidth=1.0,
                 label="M4.2B : 113")
    left.set_xticks(x)
    left.set_xticklabels([label(q) for q in quantities], rotation=16, ha="right",
                         fontsize=7.5)
    left.set_ylabel("points au-delà du seuil (médiane)")
    left.set_title("la couverture", fontsize=9)
    left.set_ylim(0, max(dense["groups"][k]["n_tail_median"] for k in keys) * 1.28
                  if dense else None)
    left.legend(fontsize=6.5, ncol=2, loc="upper left")
    annotated["n_tail_int_in"] = base["groups"]["tous/int_in"]["n_tail_median"]

    for name, data, shade, offset in campaigns:
        alphas = [data["groups"][k]["alpha_median"] for k in keys]
        errors = [data["groups"][k]["se_hill_at_median"] for k in keys]
        right.errorbar(x + offset * width * 0.5, alphas, yerr=errors, fmt="o",
                       markersize=5, capsize=3, linewidth=1.2, color=shade, label=name)
    right.axhspan(1.0, 5.0, color="#c1442e", alpha=0.07)
    right.annotate("queue lourde", (0.02, 0.20), xycoords="axes fraction",
                   fontsize=7.5, color="#8a2f2f")
    right.set_yscale("log")
    right.set_xticks(x)
    right.set_xticklabels([label(q) for q in quantities], rotation=16, ha="right",
                          fontsize=7.5)
    right.set_ylabel("exposant $\\alpha$")
    right.set_title("l'exposant, invariant au taux de naissance", fontsize=9)
    right.legend(fontsize=7, loc="upper left")
    for index, quantity in enumerate(quantities):
        annotated[f"alpha_{quantity}"] = base["groups"][f"tous/{quantity}"]["alpha_median"]
    save(figure_, "f11_couverture",
         "Couverture de queue et exposant, sous deux taux de naissance.", annotated)


@figure("f12_alpha_bras")
def f12() -> None:
    """Les exposants ne bougent pas sous les leviers du rebond."""
    rows = read_csv("lotC_alpha.csv")
    if not rows:
        return
    quantities = ["int_in", "nw"]
    arms = ["free/control", "free/new_A075", "free/all_A150", "free/new_A150",
            "free/new_g060", "free/all_A150_K0comp"]
    figure_, axes = plt.subplots(figsize=(6.0, 2.8))
    width = 0.36
    annotated = {}
    for index, quantity in enumerate(quantities):
        means, errs = [], []
        for arm in arms:
            subset = [r for r in rows if r["arm"] == arm and r["quantity"] == quantity
                      and r["group"] == "tous"]
            mean, ci, _ = student([number(r, "alpha_mean") for r in subset])
            means.append(mean)
            errs.append(ci)
        x = np.arange(len(arms)) + (index - 0.5) * width
        axes.errorbar(x, means, yerr=errs, fmt="o", markersize=4.5, capsize=2.5,
                      linewidth=1.2, color=colour("", index), label=label(quantity))
        finite = [m for m in means if m == m]
        if finite:
            annotated[f"etendue_{quantity}"] = 100 * (max(finite) - min(finite)) / np.mean(finite)
    axes.set_xticks(np.arange(len(arms)))
    axes.set_xticklabels([label(a.split("/", 1)[1]) for a in arms], rotation=16, ha="right")
    axes.set_ylabel("exposant de queue $\\alpha$")
    spans = ", ".join(f"{label(q)} : {annotated.get(f'etendue_{q}', float('nan')):.1f}  %"
                      for q in quantities).replace(".", ",")
    axes.set_title(f"étendue sur tous les bras — {spans}", fontsize=8.5)
    axes.legend()
    french_axis(axes.yaxis, 2)
    save(figure_, "f12_alpha_bras",
         "Les exposants de queue sous les leviers du rebond.", annotated)


@figure("f13_vuong")
def f13() -> None:
    """Pourquoi le test de Vuong n'a pas de pouvoir sur ce couple de lois.

    Restreinte aux deux grandeurs dont le rapport discute la queue — le
    revenu d'intérêt et la valeur nette —, de sorte que les effectifs
    affichés soient exactement ceux des macros `\\DegenereesInteret` et
    `\\DegenereesNW`.
    """
    rows = read_csv("lotC_families.csv")
    if not rows:
        return
    quantities = ("int_in", "nw")
    figure_, grid = plt.subplots(1, 2, figsize=(6.9, 3.0), sharey=True)
    annotated = {}
    for axes, quantity in zip(grid, quantities):
        subset = [r for r in rows if r["quantity"] == quantity]
        if not subset:
            axes.set_visible(False)
            continue
        degenerate = [r for r in subset
                      if r.get("lognormal_degenerate") in ("True", "1", "true")]
        regular = [r for r in subset if r not in degenerate]
        for group, name, marker, shade in (
                (regular, "ajustement régulier", "o", colour("control")),
                (degenerate, "log-normale dégénérée", "x", colour("all_A150"))):
            if not group:
                continue
            axes.scatter([number(r, "lognormal_sigma") for r in group],
                         [number(r, "vuong_pl_vs_ln") for r in group],
                         s=20, marker=marker, color=shade, alpha=0.8,
                         linewidth=1.0, label=f"{name} ($n$ = {len(group)})")
        axes.axvline(10.0, color="#666666", linestyle="--", linewidth=0.9)
        for level in (-1.96, 1.96):
            axes.axhline(level, color="#aaaaaa", linewidth=0.6, linestyle=":")
        axes.set_xscale("log")
        axes.set_xlabel("$\\sigma$ de la log-normale ajustée")
        share = 100 * len(degenerate) / len(subset)
        axes.set_title(f"{label(quantity)} — {len(degenerate)}/{len(subset)} "
                       f"dégénèrent ({share:.0f} %)".replace(".", ","), fontsize=9)
        axes.legend(loc="lower left", fontsize=7)
        annotated[f"degenerees_{quantity}"] = len(degenerate)
        annotated[f"ajustements_{quantity}"] = len(subset)
    grid[0].set_ylabel("statistique de Vuong (puissance / log-normale)")
    grid[0].annotate("seuil $\\sigma = 10$", (10.0, 0.02), xycoords=("data", "axes fraction"),
                     textcoords="offset points", xytext=(4, 0), fontsize=7.5,
                     color="#444444")
    figure_.suptitle("la log-normale tronquée CONTIENT la loi de puissance : "
                     "au-delà du seuil, le test ne discrimine plus", fontsize=9.5)
    save(figure_, "f13_vuong",
         "Dégénérescence de la log-normale et absence de pouvoir du test de Vuong.",
         annotated)


# ---------------------------------------------------------------------------
# §8 — le taux comme variable de partage
# ---------------------------------------------------------------------------

BARGAIN_LEVELS = {"p=0": 0.0, "p=0.25": 0.25, "p=0.5": 0.5, "p=0.75": 0.75, "p=1": 1.0}


def _bargain(quantity: str) -> tuple[list[float], list[float], list[float], tuple]:
    rows = read_csv("bargain_runs.csv")
    xs, means, errs = [], [], []
    for arm, level in sorted(BARGAIN_LEVELS.items(), key=lambda kv: kv[1]):
        subset = [r for r in rows if r["arm"] == arm]
        if not subset:
            continue
        mean, ci, _ = student([number(r, quantity) for r in subset])
        xs.append(level)
        means.append(mean)
        errs.append(ci)
    historical = [r for r in rows if r["arm"] == "marginal"]
    h_mean, h_ci, _ = student([number(r, quantity) for r in historical])
    h_p, _, _ = student([number(r, "mkt_p_implied") for r in historical])
    return xs, means, errs, (h_p, h_mean, h_ci)


@figure("f14_bargain_population")
def f14() -> None:
    """FIGURE MAÎTRESSE du §8 : équitable en moyenne, asservissant en effet.

    L'écart vertical entre la courbe lue en $p = 0{,}53$ et le point de la
    règle historique EST le résultat.
    """
    xs, means, errs, (h_p, h_mean, h_ci) = _bargain("pop")
    if not xs:
        return
    figure_, axes = plt.subplots(figsize=(5.6, 3.4))
    axes.errorbar(xs, means, yerr=errs, marker="o", markersize=5, capsize=3,
                  linewidth=1.6, color=colour("control"), label="partage fixe $p$")
    expected = float(np.interp(h_p, xs, means))
    axes.errorbar([h_p], [h_mean], yerr=[h_ci], marker="D", markersize=7, capsize=3,
                  color=colour("all_A150"), linewidth=1.4, zorder=5,
                  label="règle historique")
    axes.annotate("", xy=(h_p, h_mean), xytext=(h_p, expected),
                  arrowprops=dict(arrowstyle="<->", color="#333333", linewidth=1.1))
    axes.annotate(f"$-{100 * (1 - h_mean / expected):.0f}$  %".replace(".", ","),
                  ((h_p), (h_mean + expected) / 2), textcoords="offset points",
                  xytext=(10, 0), fontsize=9, color="#333333")
    axes.scatter([h_p], [expected], marker="_", s=200, color="#333333", zorder=4)
    axes.annotate(f"partage moyen mesuré : $p = {h_p:.2f}$".replace(".", ","),
                  (h_p, expected), textcoords="offset points", xytext=(-6, 16),
                  ha="right", fontsize=8, color="#444444")
    axes.axhline(means[-1], color=colour("p=1"), linestyle=":", linewidth=1.1,
                 label="niveau de $p = 1$")
    # Orientation IDENTIQUE à celle du corps du rapport (`p = 1` rapporté à
    # la règle historique) : afficher l'inverse serait vrai et illisible.
    #
    # Et la valeur vient du contraste APPARIÉ par graine, pas du rapport des
    # deux moyennes de bras. Les deux diffèrent au cinquième chiffre, ce qui
    # suffirait à faire dire deux choses à une même grandeur — c'est le test
    # de cohérence qui l'a relevé.
    contrasts = (read_json("bargain_summary.json") or {}).get("contrasts_vs_marginal", {})
    paired = contrasts.get("p=1", {}).get("pop")
    ratio_p1 = paired["mean"] if paired else means[-1] / h_mean
    axes.annotate(f"$p = 1$ rapporté à la règle : {fr(ratio_p1, 4)}",
                  (1.0, means[-1]), textcoords="offset points", xytext=(-6, 10),
                  ha="right", fontsize=8, color=colour("p=1"))
    axes.set_xlabel("partage $p$ — 0 : altruisme, 1 : asservissement")
    axes.set_ylabel("effectif stationnaire")
    axes.set_title("une institution équitable en moyenne produit l'état de $p = 1$")
    axes.legend(loc="upper right")
    french_axis(axes.xaxis, 2)
    save(figure_, "f14_bargain_population",
         "Effectif contre partage, et la position de la règle historique.",
         {"p_moyen": h_p, "pop_historique": h_mean, "pop_attendue": expected,
          "rapport": h_mean / expected, "rapport_p1": ratio_p1})


@figure("f15_bargain_gini")
def f15() -> None:
    """La seconde invariance : le Gini de la valeur nette ne bouge pas."""
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 2.8))
    annotated = {}
    for index, quantity in enumerate(("gini_nw_signed", "gini_K", "gini_int_in")):
        xs, means, errs, (h_p, h_mean, _) = _bargain(quantity)
        if not xs:
            continue
        finite = [m for m in means if m == m]
        span = 100 * (max(finite) - min(finite)) / np.mean(finite) if finite else float("nan")
        annotated[f"etendue_{quantity}"] = span
        name = {"gini_nw_signed": "valeur nette", "gini_K": "capital",
                "gini_int_in": "revenu d'intérêt"}[quantity]
        left.errorbar(xs, np.array(means) / means[0], yerr=np.array(errs) / means[0],
                      marker="o", markersize=4, capsize=2, linewidth=1.3,
                      color=colour("", index),
                      label=f"{name} — étendue {span:.1f}  %".replace(".", ","))
    left.axhline(1.0, color="#888888", linewidth=0.6, linestyle="--")
    left.set_xlabel("partage $p$")
    left.set_ylabel("Gini, rapporté à $p = 0$")
    left.set_title("ce que le partage ne déplace pas")
    left.legend(fontsize=7.5)

    for index, quantity in enumerate(("pop", "K_tot", "prod_tot")):
        xs, means, errs, _ = _bargain(quantity)
        if not xs or not means[0]:
            continue
        right.errorbar(xs, np.array(means) / means[0], yerr=np.array(errs) / means[0],
                       marker="o", markersize=4, capsize=2, linewidth=1.3,
                       color=colour("", index),
                       label={"pop": "effectif", "K_tot": "capital total",
                              "prod_tot": "production totale"}[quantity])
    right.axhline(1.0, color="#888888", linewidth=0.6, linestyle="--")
    right.set_xlabel("partage $p$")
    right.set_ylabel("rapporté à $p = 0$")
    right.set_title("ce qu'il déplace, pendant ce temps")
    right.legend(fontsize=7.5)
    for axes in (left, right):
        french_axis(axes.xaxis, 2)
    save(figure_, "f15_bargain_gini",
         "Invariance du Gini de la valeur nette sur toute l'échelle du partage.",
         annotated)


@figure("f16_bargain_systeme")
def f16() -> None:
    """Branchement, tension, rotation et taux du carnet contre le partage."""
    panels = (("b1", "rapport de branchement $b_1$"),
              ("tension", "tension $K_{\\mathrm{aut}}/K_{\\mathrm{eq}}$"),
              ("rotation", "rotation du crédit"),
              ("book_rate", "taux moyen du carnet"))
    figure_, grid = plt.subplots(2, 2, figsize=(6.6, 4.6))
    figure_.subplots_adjust(hspace=0.62, wspace=0.30)
    annotated = {}
    for axes, (quantity, title) in zip(grid.ravel(), panels):
        xs, means, errs, (h_p, h_mean, h_ci) = _bargain(quantity)
        if not xs:
            axes.set_visible(False)
            continue
        axes.errorbar(xs, means, yerr=errs, marker="o", markersize=4, capsize=2,
                      linewidth=1.3, color=colour("control"))
        if h_mean == h_mean:
            axes.errorbar([h_p], [h_mean], yerr=[h_ci], marker="D", markersize=6,
                          color=colour("all_A150"), capsize=2, zorder=5)
            annotated[f"historique_{quantity}"] = h_mean
        axes.set_title(title, fontsize=8.5)
        axes.set_xlabel("partage $p$")
        french_axis(axes.xaxis, 2)
    save(figure_, "f16_bargain_systeme",
         "Effet du partage sur les grandeurs systémiques ; le losange est la règle historique.",
         annotated)


# ---------------------------------------------------------------------------
# §9 — ce qui contrôle les exposants
# ---------------------------------------------------------------------------

@figure("f17_rho_controle")
def f17() -> None:
    """L'intensité de marché contrôle ce qu'aucun autre levier ne déplace."""
    rows = read_csv("lotE_rho_runs.csv")
    if not rows:
        return
    quantities = (("alpha_int_in", "exposant du revenu d'intérêt"),
                  ("alpha_nw", "exposant de la valeur nette"),
                  ("b1", "rapport de branchement $b_1$"),
                  ("gini", "coefficient de Gini"))
    figure_, grid = plt.subplots(2, 2, figsize=(6.6, 4.8))
    figure_.subplots_adjust(hspace=0.70, wspace=0.30)
    annotated = {}
    for axes, (quantity, title) in zip(grid.ravel(), quantities):
        levels = sorted({number(r, "rho") for r in rows})
        xs, means, errs = [], [], []
        for level in levels:
            subset = [r for r in rows if number(r, "rho") == level]
            mean, ci, _ = student([number(r, quantity) for r in subset])
            xs.append(level)
            means.append(mean)
            errs.append(ci)
        axes.errorbar(xs, means, yerr=errs, marker="o", markersize=4, capsize=2,
                      linewidth=1.3, color=colour("control"))
        fit = loglog_fit(xs, means)
        if fit:
            grid_x = np.linspace(min(xs), max(xs), 60)
            axes.plot(grid_x, np.exp(fit["ordonnee"]) * grid_x ** fit["pente"],
                      color="#8a2f2f", linewidth=1.0, linestyle="--")
            axes.set_title(f"{title}\npente en $\\ln\\rho$ : "
                           f"{fr(fit['pente'], 3)}", fontsize=8.5)
            annotated[f"pente_{quantity}"] = fit["pente"]
        else:
            axes.set_title(title, fontsize=8.5)
        axes.set_xscale("log")
        axes.set_xlabel("intensité de marché $\\rho$")
    save(figure_, "f17_rho_controle",
         "L'intensité de marché déplace les exposants de queue et le branchement.",
         annotated)


@figure("f18_rotation_rho")
def f18() -> None:
    """La relation héritée `rotation = rho x Gini` ne survit pas au levier."""
    rows = read_csv("lotE_rho_runs.csv")
    if not rows:
        return
    levels = sorted({number(r, "rho") for r in rows})
    measured, predicted, errs = [], [], []
    for level in levels:
        subset = [r for r in rows if number(r, "rho") == level]
        mean, ci, _ = student([number(r, "rotation") for r in subset])
        gini, _, _ = student([number(r, "gini") for r in subset])
        measured.append(mean)
        errs.append(ci)
        predicted.append(level * gini)
    figure_, axes = plt.subplots(figsize=(5.0, 3.0))
    axes.errorbar(levels, measured, yerr=errs, marker="o", markersize=5, capsize=3,
                  linewidth=1.4, color=colour("control"), label="rotation mesurée")
    axes.plot(levels, predicted, marker="s", markersize=4, linewidth=1.3,
              linestyle="--", color=colour("all_A150"),
              label="prédiction $\\rho \\times \\bar{G}$")
    axes.set_xlabel("intensité de marché $\\rho$")
    axes.set_ylabel("rotation du crédit")
    axes.set_title("une relation héritée qui ne survit pas au changement de levier")
    axes.legend()
    reference = min(range(len(levels)), key=lambda i: abs(levels[i] - 3.0))
    annotated = {"mesure_rho3": measured[reference], "predit_rho3": predicted[reference]}
    axes.annotate(f"{measured[reference]:.3f} contre {predicted[reference]:.3f} attendus".replace(".", ","),
                  (levels[reference], measured[reference]), textcoords="offset points",
                  xytext=(-10, -22), ha="right", fontsize=8, color="#333333")
    french_axis(axes.yaxis, 2)
    save(figure_, "f18_rotation_rho",
         "Rotation mesurée contre la relation héritée, sous un balayage de l'intensité.",
         annotated)


@figure("f19_ablation")
def f19() -> None:
    """L'écart de branchement avec M4B : ce qui le ferme, et ce qui reste.

    Des BARRES et non une ligne brisée : chaque bras est une ablation d'un
    facteur à la fois par rapport au contrôle, pas une étape d'une séquence.
    Une ligne les relierait comme si l'on descendait un escalier, ce qui
    n'est pas ce que la campagne a fait.
    """
    data = read_json("lotD_avalanches.json")
    if not data:
        return
    summary = data["summary"]
    order = [("free/control", "cette lignée"),
             ("ablation/delta005", "dépréciation de M4B"),
             ("ablation/sigma025", "volatilité de M4B"),
             ("ablation/m4b_like", "les deux ensemble")]
    keys = [(k, n) for k, n in order if k in summary]
    if len(keys) < 2:
        return
    target = 0.297
    figure_, (left, right) = plt.subplots(
        1, 2, figsize=(6.9, 3.0), gridspec_kw={"width_ratios": [1.25, 1.0]})
    figure_.subplots_adjust(wspace=0.32)

    means = [summary[k]["b1"]["mean"] for k, _ in keys]
    errs = [summary[k]["b1"].get("ci95", 0.0) for k, _ in keys]
    x = np.arange(len(keys))
    start_value = means[0]
    shades = [colour("control")] + [colour("all_A150")] * (len(keys) - 1)
    left.bar(x, means, 0.55, yerr=errs, capsize=3, color=shades,
             edgecolor="white", linewidth=0.5)
    left.axhline(target, color="#333333", linestyle="--", linewidth=1.1,
                 label="M4B publié : 0,297")
    for index, value in enumerate(means[1:], start=1):
        closed = 100 * (start_value - value) / (start_value - target)
        left.annotate(f"{closed:.0f} % fermés".replace(".", ","), (index, value),
                      textcoords="offset points", xytext=(0, 4), ha="center",
                      fontsize=7, color="#333333")
    left.set_xticks(x)
    left.set_xticklabels([n for _, n in keys], rotation=18, ha="right", fontsize=7.5)
    left.set_ylabel("rapport de branchement $b_1$")
    left.set_ylim(0, max(means) * 1.22)
    left.set_title("un facteur à la fois", fontsize=9)
    left.legend(fontsize=7.5)

    # Le balayage de la volatilité : c'est le facteur dominant, et il est
    # monotone. Le contrôle en est le point de départ (sigma = 0,01).
    sweep = [(0.01, "free/control"), (0.05, "ablation/sigma005"),
             (0.10, "ablation/sigma010"), (0.25, "ablation/sigma025")]
    sweep = [(value, key) for value, key in sweep if key in summary]
    if len(sweep) >= 3:
        xs = [value for value, _ in sweep]
        ys = [summary[key]["b1"]["mean"] for _, key in sweep]
        es = [summary[key]["b1"].get("ci95", 0.0) for _, key in sweep]
        right.errorbar(xs, ys, yerr=es, marker="o", markersize=5, capsize=3,
                       linewidth=1.4, color=colour("all_A150"))
        right.axhline(target, color="#333333", linestyle="--", linewidth=1.0)
        right.set_xscale("log")
        right.set_xlabel("volatilité $\\sigma$")
        right.set_ylabel("rapport de branchement $b_1$")
        right.set_title("la volatilité, facteur dominant", fontsize=9)
        french_axis(right.yaxis, 2)
    explained = 100 * (start_value - means[-1]) / (start_value - target)
    save(figure_, "f19_ablation",
         "Ablation vers le régime M4B : ce qui explique l'écart de branchement.",
         {"part_expliquee": explained, "b1_m4b_like": means[-1],
          "b1_controle": start_value})


@figure("f20_rampes")
def f20() -> None:
    """Le partage qui évolue : montée et descente se superposent."""
    rows = read_csv("lotT_ramp.csv")
    if not rows:
        return
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 2.8), sharex=True)
    for axes, quantity, title in ((left, "pop", "effectif"),
                                  (right, "n_loans", "contrats vivants")):
        for index, direction in enumerate(sorted({r["direction"] for r in rows})):
            subset = [r for r in rows if r["direction"] == direction]
            levels = sorted({number(r, "p") for r in subset})
            means, errs = [], []
            for level in levels:
                cell = [r for r in subset if number(r, "p") == level]
                mean, ci, _ = student([number(r, quantity) for r in cell])
                means.append(mean)
                errs.append(ci)
            axes.errorbar(levels, means, yerr=errs, marker="o" if index == 0 else "s",
                          markersize=4, capsize=2, linewidth=1.3,
                          linestyle="-" if index == 0 else "--",
                          color=colour("", index),
                          label="montée" if "up" in direction else "descente")
        axes.set_title(title, fontsize=9)
        axes.set_xlabel("partage $p$ du palier")
        french_axis(axes.xaxis, 2)
    left.legend()
    save(figure_, "f20_rampes",
         "Montée et descente du partage : pas de dépendance au chemin à cette échelle.")


# ---------------------------------------------------------------------------
# Lots I et J — les hypothèses calculées
# ---------------------------------------------------------------------------

@figure("f21_hasard")
def f21() -> None:
    """La convexité posée en hypothèse : ce que la mesure en dit."""
    data = read_json("lotI_convexity.json")
    if not data or "marginal" not in data.get("courbes", {}):
        return
    curve = data["courbes"]["marginal"]
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 2.9))
    centre = np.array(curve["centre"])
    rate = np.array(curve["rate"])
    error = np.array(curve["se"])
    left.errorbar(centre, rate, yerr=error, marker="o", markersize=3.5, capsize=2,
                  linewidth=1.2, color=colour("marginal"))
    # Les traits et le rapport annoté viennent du RÉSUMÉ par run — la
    # convention appariée de la lignée, et la source de `\RapportJensen` —
    # et non de la courbe mise en commun, qui ne sert qu'à donner la forme.
    summary = data.get("resume", {}).get("marginal", {})
    jensen = {key: summary[key]["mean"] for key in
              ("mortalite_observee", "mortalite_au_service_moyen", "service_moyen")
              } if summary else curve["jensen"]
    left.axvline(jensen["service_moyen"], color="#666666", linestyle="--", linewidth=0.8)
    left.axhline(jensen["mortalite_observee"], color=colour("control"),
                 linestyle=":", linewidth=1.0, label="mortalité observée $E[h(s)]$")
    left.axhline(jensen["mortalite_au_service_moyen"], color=colour("new_A075"),
                 linestyle=":", linewidth=1.0, label="au fardeau moyen $h(E[s])$")
    left.annotate("", xy=(centre[-3], jensen["mortalite_observee"]),
                  xytext=(centre[-3], jensen["mortalite_au_service_moyen"]),
                  arrowprops=dict(arrowstyle="<->", color="#333333", linewidth=1.0))
    ratio = jensen["mortalite_observee"] / jensen["mortalite_au_service_moyen"]
    left.annotate(f"$\\times {ratio:.1f}$".replace(".", ","),
                  (centre[-3], np.sqrt(jensen["mortalite_observee"]
                                       * jensen["mortalite_au_service_moyen"])),
                  textcoords="offset points", xytext=(-30, 0), fontsize=9)
    left.set_xlabel("fardeau $s = $ dettes / production")
    left.set_ylabel("risque d'insolvabilité à 10 pas")
    left.set_title("non monotone, et non convexe", fontsize=9)
    left.legend(fontsize=7, loc="upper right")

    for index, entry in enumerate(data.get("conditionnel", {}).get("marginal", [])):
        right.errorbar([index], [entry["c2"]], yerr=[2 * entry["c2_se"]], marker="o",
                       markersize=5, capsize=3, linewidth=1.2,
                       color=colour("control") if entry["c2"] > 2 * entry["c2_se"]
                       else colour("all_A150"))
    right.axhline(0.0, color="#666666", linewidth=0.8)
    verdict = data.get("verdict", {})
    right.set_xlabel("classe de capital (croissante)")
    right.set_ylabel("courbure ajustée $c_2$")
    right.set_title(f"à capital donné : "
                    f"{verdict.get('n_classes_convexes', 0)}/"
                    f"{verdict.get('n_classes_capital', 0)} classes convexes", fontsize=9)
    right.set_xticks(range(len(data.get("conditionnel", {}).get("marginal", []))))
    dump("f21_hasard", ["fardeau", "risque", "erreur"],
         [[float(a), float(b), float(c)] for a, b, c in zip(centre, rate, error)])
    save(figure_, "f21_hasard",
         "Risque d'insolvabilité contre fardeau (source : panels.npz, non versionné).",
         {"rapport_jensen": ratio,
          "n_classes_convexes": verdict.get("n_classes_convexes", 0)})


@figure("f22_ponderation")
def f22() -> None:
    """FIGURE MAÎTRESSE du lot I : le partage compté en contrats et en joules.

    Les bras à partage fixe tombent sur la diagonale — c'est le témoin. La
    règle historique en est à quarante et un points.
    """
    data = read_json("lotI_convexity.json")
    if not data or not data.get("ponderation"):
        return
    figure_, (left, right) = plt.subplots(1, 2, figsize=(7.1, 3.1))
    figure_.subplots_adjust(wspace=0.34)
    annotated = {}
    for arm, entry in data["ponderation"].items():
        if not entry:
            continue
        x = entry["p_moyen"]["mean"]
        y = entry["p_pondere"]["mean"]
        historical = arm == "marginal"
        left.errorbar([x], [y], yerr=[entry["p_pondere"]["ci95"]],
                      marker="D" if historical else "o",
                      markersize=8 if historical else 5.5, capsize=3, linewidth=1.2,
                      color=colour(arm), zorder=5 if historical else 3,
                      label=label(arm) if historical else None)
        if historical:
            annotated["p_moyen"] = x
            annotated["p_pondere"] = y
            annotated["covariance"] = entry["covariance_normalisee"]["mean"]
            left.annotate("", xy=(x, y), xytext=(x, x),
                          arrowprops=dict(arrowstyle="->", color="#333333", linewidth=1.2))
            left.annotate(f"$\\mathrm{{Cov}}(p,\\Delta)\\,/\\,E[\\Delta]$ = +{fr(y - x, 3)}",
                          (0.04, 0.70), xycoords="axes fraction",
                          fontsize=8.5, color="#333333")
    left.plot([0, 1], [0, 1], color="#888888", linestyle="--", linewidth=0.8,
              label="partage fixe : les deux lectures coïncident")
    left.set_xlabel("partage moyen PAR CONTRAT")
    left.set_ylabel("partage PONDÉRÉ par le surplus en jeu")
    left.set_title("compter des contrats ou compter des joules", fontsize=9)
    left.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.21),
                ncol=1)
    french_axis(left.xaxis, 2)
    french_axis(left.yaxis, 2)

    arms = sorted(data.get("resume", {}), key=lambda a: (a != "marginal", a))
    names, gaps, errs = [], [], []
    for arm in arms:
        entry = data["resume"][arm]
        names.append(label(arm))
        gaps.append(entry["ecart_jensen"]["mean"])
        errs.append(entry["ecart_jensen"]["ci95"])
    x = np.arange(len(names))
    right.bar(x, gaps, 0.55, yerr=errs, capsize=2.5,
              color=[colour(a) for a in arms], edgecolor="white", linewidth=0.5)
    right.set_xticks(x)
    right.set_xticklabels(names, rotation=18, ha="right")
    right.set_ylabel("écart de Jensen $E[h(s)] - h(E[s])$")
    right.set_title("l'écart croît avec le partage", fontsize=9)
    french_axis(right.yaxis, 3)
    save(figure_, "f22_ponderation",
         "Le partage lu par contrat et pondéré par la valeur : l'écart est une covariance.",
         annotated)


@figure("f23_suffisance")
def f23() -> None:
    """La sur-détermination des cascades n'est pas une suffisance."""
    data = read_json("lotJ_sufficiency.json")
    if not data:
        return
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 2.9))
    arms = sorted(data["resume"])
    reference = data["verdict"]["bras_reference"]
    entry = data["resume"][reference]
    edges = np.array(entry["histogramme_bornes"])
    counts = np.array(entry["histogramme_concentration"])
    centres = 0.5 * (edges[:-1] + edges[1:])
    left.bar(centres, counts, width=edges[1] - edges[0], color=colour("control"),
             edgecolor="white", linewidth=0.3)
    mean = entry["concentration_moyenne"]["mean"]
    left.axvline(mean, color=colour("all_A150"), linewidth=1.2, linestyle="--",
                 label=f"moyenne : {mean:.2f}".replace(".", ","))
    left.set_xlabel("part du choc portée par le plus gros créancier")
    left.set_ylabel("densité (victimes sur-déterminées)")
    left.set_title("un choc rarement concentré", fontsize=9)
    left.legend(fontsize=7.5)

    x = np.arange(len(arms))
    floors = [data["resume"][a]["plancher_suffisance"]["mean"] for a in arms]
    ferrs = [data["resume"][a]["plancher_suffisance"]["ci95"] for a in arms]
    over = [data["resume"][a]["part_sur_determinees"]["mean"] for a in arms]
    right.bar(x - 0.2, over, 0.4, color=colour("control"), edgecolor="white",
              linewidth=0.4, label="victimes sur-déterminées")
    right.bar(x + 0.2, floors, 0.4, yerr=ferrs, capsize=2, color=colour("all_A150"),
              edgecolor="white", linewidth=0.4,
              label="dont une cause certainement suffisante")
    right.set_xticks(x)
    right.set_xticklabels([label(a) for a in arms], rotation=32, ha="right", fontsize=6.5)
    right.set_title("plusieurs causes, rarement chacune suffisante", fontsize=9)
    percent(right.yaxis, 0)
    right.legend(fontsize=7, loc="upper right")
    save(figure_, "f23_suffisance",
         "Sur-détermination et suffisance des chocs de cascade (plancher).",
         {"plancher": data["verdict"]["plancher"],
          "toutes_suffisantes": data["verdict"]["toutes_suffisantes"],
          "incidence_effacement": data["verdict"]["incidence_effacement"]})


# ---------------------------------------------------------------------------
# Rapport de conception
# ---------------------------------------------------------------------------

@figure("g01_cout")
def g01() -> None:
    """Le prix de l'instrumentation, mesuré avant que `k` ne soit fixé."""
    data = read_json("lotA_cost.json")
    if not data:
        return
    budget = data["derived"].get("budget", {})
    if not budget:
        return
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.6, 2.5))
    keys = sorted(budget, key=lambda k: float(k.split("=")[1]))
    steps = [float(k.split("=")[1]) for k in keys]
    left.plot(steps, [budget[k]["gio_campagne"] for k in keys], marker="o",
              markersize=5, linewidth=1.4, color=colour("control"))
    chosen = 10.0
    if chosen in steps:
        index = steps.index(chosen)
        left.scatter([chosen], [budget[keys[index]]["gio_campagne"]], s=90,
                     facecolor="none", edgecolor=colour("all_A150"), linewidth=1.6,
                     zorder=5, label="valeur retenue")
        left.legend(fontsize=7.5)
    left.set_xlabel("pas d'échantillonnage $k$")
    left.set_ylabel("empreinte de la campagne (Gio)")
    left.set_title("stockage contre finesse", fontsize=9)
    left.set_xscale("log")

    overheads = {"événements": data["derived"].get("events_overhead_share"),
                 "sonde de Gini": data["derived"].get("market_stats_overhead_share")}
    names = [n for n, v in overheads.items() if v is not None]
    values = [100 * overheads[n] for n in names]
    right.barh(np.arange(len(names)), values, 0.45, color=colour("control"),
               edgecolor="white", linewidth=0.5)
    right.set_yticks(np.arange(len(names)))
    right.set_yticklabels(names)
    right.set_xlabel("surcoût en temps ( %)")
    right.set_title("prix des enregistrements", fontsize=9)
    for index, value in enumerate(values):
        right.annotate(f"{value:.1f}  %".replace(".", ","), (value, index),
                       textcoords="offset points", xytext=(4, -3), fontsize=8)
    right.set_xlim(0, max(values) * 1.35)
    save(figure_, "g01_cout", "Coût mesuré de l'instrumentation ajoutée par M4.4.",
         {"gio_k10": budget.get("k=10", {}).get("gio_campagne")})


@figure("g02_parite")
def g02() -> None:
    """La parité bit à bit : huit mille pas, et pas un bit d'écart.

    Deux panneaux, parce qu'un seul mentirait. À droite l'écart, nul ; à
    gauche la trajectoire sur laquelle il est nul — sans quoi « écart nul »
    pourrait aussi bien décrire un run qui ne fait rien.
    """
    rows = read_csv("parity_deviations_8000.csv")
    if not rows:
        return
    times = np.array([number(r, "t") for r in rows])
    deviation = np.array([number(r, "ecart_max_toutes_colonnes") for r in rows])
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 2.6))
    figure_.subplots_adjust(wspace=0.34)
    for index, (key, name) in enumerate((("prod_tot", "production totale"),
                                         ("K_tot", "capital total"))):
        values = np.array([number(r, key) for r in rows])
        if not np.isfinite(values).any():
            continue
        left.plot(times, values, linewidth=0.9, color=colour("", index), label=name)
    left.set_yscale("log")
    left.set_xlabel("pas")
    left.set_ylabel("valeur")
    left.set_title("la trajectoire comparée", fontsize=9)
    left.legend(fontsize=7.5)

    right.plot(times, deviation, linewidth=1.0, color=colour("all_A150"))
    peak = float(np.nanmax(deviation))
    right.set_ylim(-1e-15, 1e-15)
    right.set_xlabel("pas")
    right.set_ylabel("écart maximal, toutes colonnes")
    right.set_title(f"écart maximal sur {len(rows)} pas : {peak:g}", fontsize=9)
    right.annotate("identiquement nul", (0.5, 0.55), xycoords="axes fraction",
                   ha="center", fontsize=10, color="#333333")
    save(figure_, "g02_parite", "Parité bit à bit contre le moteur gelé.",
         {"ecart_max": peak, "n_pas": len(rows)})


@figure("g03_partage_analytique")
def g03() -> None:
    """Le partage implicite de la règle historique, tiré des FONCTIONS du moteur.

    Cette figure ne lit aucun run. Elle évalue directement `pair_rate`,
    `extraction_loss` et `joint_production_gain` sur une grille de paires, en
    régime homogène où la règle de principal coïncide avec l'arithmétique,
    et calcule `p = (r q - L)/Δ` comme le moteur le fait.

    Elle montre que la covariance entre la part prise et le surplus en jeu,
    mesurée sur la campagne au lot I, n'est pas un accident de cette
    campagne-là : c'est une propriété de la règle de taux elle-même. Sur les
    petites paires elle partage à la moitié ; sur les grandes elle dépasse
    l'asservissement total.
    """
    from m4_4.model import (  # noqa: PLC0415 — dépendance de cette seule figure
        extraction_loss, joint_production_gain, pair_rate)

    coefficient, exponent = 1.0, 0.5
    receivers = [50.0, 200.0, 400.0, 700.0]
    figure_, (left, right) = plt.subplots(1, 2, figsize=(6.9, 3.0))
    figure_.subplots_adjust(wspace=0.30)
    exported: list[list] = []
    for index, receiver in enumerate(receivers):
        donors = np.linspace(receiver * 1.02, 2400.0, 160)
        shares, surpluses, principals = [], [], []
        for donor in donors:
            principal = (donor - receiver) / 2.0
            surplus = joint_production_gain(coefficient, exponent, coefficient,
                                            exponent, receiver, donor, principal)
            if surplus <= 0:
                continue
            loss = extraction_loss(coefficient, exponent, donor, principal)
            rate = pair_rate(donor, receiver, exponent, coefficient,
                             exponent, coefficient)
            shares.append((rate * principal - loss) / surplus)
            surpluses.append(surplus)
            principals.append(principal)
            exported.append([receiver, float(donor), float(principal),
                             float(surplus), shares[-1]])
        shade = colour("", index)
        left.plot(principals, shares, linewidth=1.4, color=shade,
                  label=f"receveuse à $K$ = {receiver:.0f}")
        right.plot(surpluses, shares, linewidth=1.4, color=shade)
    for axes, name in ((left, "principal du contrat $q$"),
                       (right, "surplus coopératif $\\Delta$")):
        axes.axhline(1.0, color=colour("p=1"), linestyle=":", linewidth=1.1)
        axes.axhline(0.5, color="#888888", linestyle="--", linewidth=0.9)
        axes.set_xlabel(name)
        french_axis(axes.yaxis, 2)
    left.set_ylabel("partage implicite $p = (rq - L)/\\Delta$")
    left.set_title("la règle partage d'autant plus\nque le contrat est gros", fontsize=9)
    left.legend(fontsize=7)
    right.set_xscale("log")
    right.set_title("et le surplus croît avec le contrat :\nd'où la covariance", fontsize=9)
    right.annotate("asservissement total", (0.03, 0.90), xycoords="axes fraction",
                   fontsize=7.5, color=colour("p=1"))
    right.annotate("partage équitable", (0.03, 0.06), xycoords="axes fraction",
                   fontsize=7.5, color="#666666")
    dump("g03_partage_analytique",
         ["K_receveuse", "K_donneuse", "principal", "surplus", "partage"], exported)
    save(figure_, "g03_partage_analytique",
         "Le partage implicite de la règle historique, évalué sur les fonctions du moteur.",
         {"p_min": min(row[4] for row in exported),
          "p_max": max(row[4] for row in exported)})


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", type=str, default="")
    args = parser.parse_args(argv[1:])

    setup()
    made, skipped = 0, []
    for name, function in REGISTRY:
        if args.only and not name.startswith(args.only):
            continue
        try:
            before = len(str(function))
            function()
            made += 1
            del before
        except Exception as error:  # noqa: BLE001
            skipped.append(f"{name} : {type(error).__name__} — {error}")
    write_manifest()
    print(f"\n{made} figures tentées, {len(skipped)} en échec")
    for item in skipped:
        print(f"  ÉCHEC {item}", file=sys.stderr)
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
