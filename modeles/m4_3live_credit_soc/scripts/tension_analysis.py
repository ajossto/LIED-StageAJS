"""Lecture croisée de la tension : est-elle le paramètre d'état du système ?

Trois questions, une par figure :

1. **La tension distingue-t-elle les bras ?** Tension en régime établi pour
   chaque bras de la campagne, de l'ablation K0 et de la loi d'échelle.
2. **La compensation de K0 ramène-t-elle la tension à celle du contrôle ?**
   C'est la prédiction de l'invariance d'échelle : si le système est
   covariant, multiplier A et K0 de façon cohérente laisse la tension
   inchangée. Réponse attendue : oui, exactement.
3. **La mortalité est-elle une fonction de la tension seule ?** (note [22])
   On superpose tous les runs dans le plan (tension, morts/population). S'ils
   se rassemblent sur une seule courbe, la tension résume à elle seule ce que
   les paramètres font à la mortalité.

Sorties : `results/analysis/tension_*.csv` et `report/figures/tension_*.png`.

    python3 scripts/tension_analysis.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FixedLocator, FormatStrFormatter, NullLocator  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from simulation_lab.plot_utils import apply_style  # noqa: E402

FIGURES = ROOT / "report" / "figures"
ANALYSIS = ROOT / "results" / "analysis"

#: Fenêtre de régime établi : les `WINDOW` derniers pas du run.
WINDOW = 1000

FAMILIES = (
    ("campagne", ROOT / "results" / "campaign" / "arms"),
    ("ablation K0", ROOT / "results" / "ablation_k0"),
    ("balayage", ROOT / "results" / "tension_sweep"),
)

#: Levier employé par chaque bras du balayage, lu sur son nom. C'est la
#: variable qui décide si la relation mortalité ↔ tension dépend du chemin.
def lever_of(family: str, arm: str) -> str:
    if family != "balayage":
        return {"campagne": "A (campagne)", "ablation K0": "A et K0 (ablation)"}.get(
            family, family
        )
    if arm == "sweep_control":
        return "contrôle"
    return {"K0": "$K_0$ seul", "delta": "$\\delta$ seul", "A": "$A$ seul"}.get(
        arm.split("_")[0], arm
    )


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run_summary(directory: Path) -> dict | None:
    """Tension et mortalité moyennes sur la fenêtre finale d'un run."""
    aggregate = read_csv(directory / "tension_agg.csv")
    series = read_csv(directory / "series.csv")
    if not aggregate or not series:
        return None
    last = int(float(aggregate[-1]["t"]))
    low = last - WINDOW
    tension = [float(row["tension"]) for row in aggregate if low < int(float(row["t"])) <= last]
    jensen = [float(row["jensen"]) for row in aggregate if low < int(float(row["t"])) <= last]
    window = [row for row in series if low < int(float(row["t"])) <= last]
    if not tension or not window:
        return None
    population = np.array([float(row["pop"]) for row in window])
    deaths = np.array([float(row["deaths"]) for row in window])
    insolvency = np.array([float(row["roots_insolvency"]) for row in window])
    liquidity = np.array([float(row["roots_liquidity"]) for row in window])
    capital = np.array([float(row["K_tot"]) for row in window])
    volume = np.array([float(row["loan_volume"]) for row in window])
    n_loans = np.array([float(row["n_loans"]) for row in window])
    parameters: dict = {}
    for name in ("summary.json", "burn.json", "run.json"):
        if (directory / name).exists():
            payload = json.loads((directory / name).read_text(encoding="utf-8"))
            parameters = payload.get("parameters", {})
            break
    K_eq = [float(row["K_eq"]) for row in aggregate if low < int(float(row["t"])) <= last]
    K_aut = [float(row["K_aut"]) for row in aggregate if low < int(float(row["t"])) <= last]
    return {
        "tension": float(np.mean(tension)),
        "tension_sd": float(np.std(tension, ddof=1)),
        "jensen": float(np.mean(jensen)),
        "death_rate": float(np.sum(deaths) / np.sum(population)),
        # durée de vie moyenne = effectif / flux de morts (jamais la moyenne
        # des rapports : elle diverge dès qu'un pas est sans mort)
        "lifetime": float(np.sum(population) / np.sum(deaths)) if np.sum(deaths) else float("nan"),
        "insolvency_rate": float(np.sum(insolvency) / np.sum(population)),
        "liquidity_rate": float(np.sum(liquidity) / np.sum(population)),
        "pop": float(np.mean(population)),
        "K_eq": float(np.mean(K_eq)),
        "K_aut": float(np.mean(K_aut)),
        # Intensité de rotation du crédit : principal transféré au pas,
        # rapporté au stock de capital. Prédicteur concurrent de la tension.
        "turnover": float(np.mean(volume / capital)),
        "loans_per_entity": float(np.mean(n_loans / population)),
        # Rapport de naissance : la petitesse d'une entrante rapportée à
        # l'échelle à laquelle le système tourne réellement. Candidat
        # concurrent de la tension comme paramètre d'état.
        "birth_ratio": float(parameters.get("K0", float("nan"))) / float(np.mean(K_eq)),
        "A": float(parameters.get("A", float("nan"))),
        "gamma": float(parameters.get("gamma", float("nan"))),
        "delta": float(parameters.get("delta", float("nan"))),
        "K0": float(parameters.get("K0", float("nan"))),
        "basis": aggregate[-1].get("basis", "?"),
        "t_final": last,
    }


def collect() -> list[dict]:
    rows: list[dict] = []
    for family, root in FAMILIES:
        if not root.exists():
            continue
        for cell in sorted(root.iterdir()):
            if not cell.is_dir():
                continue
            for seed_dir in sorted(cell.glob("seed*")):
                summary = run_summary(seed_dir)
                if summary:
                    rows.append({"famille": family, "bras": cell.name,
                                 "levier": lever_of(family, cell.name),
                                 "seed": seed_dir.name, **summary})
    scaling = ROOT / "results" / "scaling_gamma"
    if scaling.exists():
        for gamma_dir in sorted(scaling.iterdir()):
            if not gamma_dir.is_dir():
                continue
            for cell in sorted(gamma_dir.iterdir()):
                if not cell.is_dir():
                    continue
                for seed_dir in sorted(cell.glob("seed*")):
                    summary = run_summary(seed_dir)
                    if not summary:
                        continue
                    if summary["gamma"] != summary["gamma"]:
                        # les amorçages de la loi d'échelle ont été importés
                        # sans bloc `parameters` : γ est dans le nom du dossier
                        summary["gamma"] = float(gamma_dir.name.lstrip("g"))
                    rows.append({"famille": f"échelle {gamma_dir.name}",
                                 "bras": cell.name,
                                 "levier": f"γ = {gamma_dir.name.lstrip('g')}",
                                 "seed": seed_dir.name, **summary})
    return rows


def by_arm(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Moyenne et erreur-type sur les graines, par bras."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["famille"], row["bras"]), []).append(row)
    out = {}
    for key, group in groups.items():
        entry = {"n": len(group), "famille": key[0], "bras": key[1],
                 "basis": group[0]["basis"]}
        for field in ("tension", "jensen", "death_rate", "lifetime",
                      "insolvency_rate", "liquidity_rate", "pop"):
            values = np.array([row[field] for row in group])
            entry[field] = float(values.mean())
            entry[f"{field}_sem"] = (
                float(values.std(ddof=1) / math.sqrt(len(values))) if len(values) > 1 else 0.0
            )
        out[key] = entry
    return out


# --------------------------------------------------------------------------
def figure_arms(arms: dict, path: Path) -> None:
    """Tension par bras, campagne et ablation côte à côte."""
    campaign = [entry for entry in arms.values() if entry["famille"] == "campagne"]
    ablation = [entry for entry in arms.values() if entry["famille"] == "ablation K0"]
    campaign.sort(key=lambda entry: entry["tension"])
    ablation.sort(key=lambda entry: entry["tension"])

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.6),
                                gridspec_kw={"width_ratios": [1.5, 1]})
    for axis, group, title in (
        (axes[0], campaign, "campagne §7 — tension en régime établi"),
        (axes[1], ablation, "ablation K0 — tension en régime établi"),
    ):
        labels = [entry["bras"] for entry in group]
        values = [entry["tension"] for entry in group]
        errors = [entry["tension_sem"] for entry in group]
        colours = ["#c1440e" if "K0aut" in name or "K0obs" in name else "#294c60"
                   for name in labels]
        axis.barh(range(len(group)), values, xerr=errors, color=colours,
                  height=0.6, error_kw={"lw": 1.0})
        axis.set_yticks(range(len(group)))
        axis.set_yticklabels(labels, fontsize=8)
        reference = next(
            (entry["tension"] for entry in group if entry["bras"] in ("control", "abl_control")),
            None,
        )
        if reference:
            axis.axvline(reference, color="black", ls="--", lw=1.0)
            axis.text(reference, len(group) - 0.4, " contrôle", fontsize=7, va="top")
        axis.set_xlabel("tension T = K_aut / K_eq")
        axis.set_title(title, fontsize=9)
        axis.grid(True, axis="x", alpha=0.2)
    figure.suptitle(
        "La tension sépare les bras : elle monte quand A monte à K0 fixe, "
        "et revient au contrôle quand K0 est compensé", fontsize=10)
    figure.tight_layout()
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)


#: Groupe de tracé d'un run : ce qui a été fait au système, et non la famille
#: de campagne dont il provient. Deux bras de familles différentes qui tirent
#: le même levier doivent se lire ensemble.
def group_of(row: dict) -> str:
    famille, bras = row["famille"], row["bras"]
    if bras in ("control", "abl_control", "sweep_control"):
        return "contrôle"
    if famille == "campagne":
        if bras == "frac_g060_phi20":
            # γ de configuration 0,5, mais 20 % des entités traitées à γ = 0,6 :
            # le seul bras que le découpage par γ ne classe pas proprement.
            return "campagne — γ mixte"
        if bras.startswith(("all_", "new_")):
            return "campagne — portée globale"
        return "campagne — portée fraction"
    if famille == "ablation K0":
        return "ablation A et K0"
    if famille == "balayage":
        return {"K0": "balayage K0", "delta": "balayage δ",
                "A": "balayage A"}.get(bras.split("_")[0], bras)
    if bras == "burn":
        return "amorçage"
    return "échelle : A×1,5, K0 compensé"


GROUP_STYLE = {
    "contrôle":                   ("#000000", "*", 130),
    "campagne — portée globale":  ("#c1440e", "o", 26),
    "campagne — portée fraction": ("#8c8c8c", "o", 18),
    "campagne — γ mixte":         ("#7a4e9f", "^", 34),
    "ablation A et K0":           ("#3f7d20", "s", 24),
    "balayage K0":                ("#294c60", "o", 26),
    "balayage A":                 ("#d99b1c", "D", 22),
    "balayage δ":                 ("#c1121f", "v", 40),
    "amorçage":                   ("#8c8c8c", "o", 18),
    "échelle : A×1,5, K0 compensé": ("#3f7d20", "s", 24),
}


def figure_collapse(rows: list[dict], path: Path) -> None:
    """Mortalité contre tension, **un panneau par γ**, en axes absolus partagés.

    Aucune droite d'ajustement n'est tracée ici, et c'est délibéré (note du
    relecteur sur la figure 12) :

    * à γ = 0,4 et γ = 0,6, les runs disponibles couvrent une plage de tension
      de 0,6 % et 1,0 % — l'ajustement qui figurait auparavant sur ces deux
      familles n'était qu'une droite passant par du bruit de graine ;
    * la droite « tous γ confondus » ne mesurait pas une réponse à la tension
      mais l'écart entre les trois lignes de base. Elle est retirée du tracé ;
      son exposant reste calculé dans `tension_fit.json`, où le texte le
      compare à l'exposant obtenu à partir des seules bases.

    Les trois panneaux partagent leurs limites : c'est ce qui rend visible le
    fait que chaque γ travaille autour d'une base différente (T = 4,3 / 13,3 /
    88,6). Chaque encart rejoue le panneau en écart à *sa* base, seule façon de
    séparer les bras qui se superposent sur les axes absolus.
    """
    gammas = sorted({round(row["gamma"], 3) for row in rows})
    figure, axes = plt.subplots(1, len(gammas), figsize=(13.5, 4.9), sharex=True,
                                sharey=True)
    axes = np.atleast_1d(axes)

    tensions = [row["tension"] for row in rows]
    rates = [row["death_rate"] for row in rows]
    xlim = (min(tensions) / 1.6, max(tensions) * 1.6)
    ylim = (min(rates) / 1.5, max(rates) * 1.5)

    # Ligne de base de chaque γ, calculée une fois : elle sert de repère dans
    # SON panneau et de rappel (marqueur creux) dans les deux autres.
    baselines = {}
    for gamma in gammas:
        control = [row for row in rows
                   if round(row["gamma"], 3) == gamma and group_of(row) == "contrôle"]
        if control:
            baselines[gamma] = (float(np.mean([row["tension"] for row in control])),
                                float(np.mean([row["death_rate"] for row in control])))

    for axis, gamma in zip(axes, gammas):
        subset = [row for row in rows if round(row["gamma"], 3) == gamma]
        base_T, base_rate = baselines.get(gamma, (float("nan"), float("nan")))
        base = gamma in baselines

        # Les bases des autres γ, en creux : c'est l'ancienne droite « tous γ
        # confondus » rendue visible pour ce qu'elle était — une droite qui
        # joignait ces trois points-là.
        others = [(other, value) for other, value in baselines.items() if other != gamma]
        if others:
            axis.scatter([value[0] for _, value in others],
                         [value[1] for _, value in others],
                         s=110, facecolors="none", edgecolors="#8c8c8c", marker="*",
                         linewidths=0.9, zorder=2,
                         label="bases des autres γ")
        if base:
            axis.axvline(base_T, color="black", ls=":", lw=0.8, alpha=0.5)
            axis.axhline(base_rate, color="black", ls=":", lw=0.8, alpha=0.5)
        for group in sorted({group_of(row) for row in subset}):
            points = [row for row in subset if group_of(row) == group]
            colour, marker, size = GROUP_STYLE.get(group, ("#294c60", "o", 24))
            axis.scatter([row["tension"] for row in points],
                         [row["death_rate"] for row in points],
                         s=size, color=colour, marker=marker, alpha=0.85,
                         linewidths=0, label=group, zorder=3)
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_xlim(*xlim)
        axis.set_ylim(*ylim)
        axis.set_xlabel("tension T = K_aut / K_eq")
        axis.set_title(
            f"γ = {gamma}  —  base : T = {base_T:.2f}, morts/pop = {base_rate:.4f}"
            f"\n{len(subset)} runs, tension de {min(row['tension'] for row in subset):.2f}"
            f" à {max(row['tension'] for row in subset):.2f}",
            fontsize=8.5)
        axis.grid(True, alpha=0.2, which="both")
        axis.legend(fontsize=6.2, loc="upper left", framealpha=0.9,
                    handletextpad=0.3, borderpad=0.3)

        # Encart : le même nuage, mais en écart à la base de CE γ. Sans lui,
        # les familles à γ = 0,4 et 0,6 sont un point unique, et les bras
        # `fraction` de γ = 0,5 sont indiscernables du contrôle.
        near = [row for row in subset if 0.9 < row["tension"] / base_T < 1.1]
        if base and len(near) > 1:
            inset = axis.inset_axes((0.55, 0.10, 0.42, 0.34))
            for group in sorted({group_of(row) for row in near}):
                points = [row for row in near if group_of(row) == group]
                colour, marker, size = GROUP_STYLE.get(group, ("#294c60", "o", 24))
                inset.scatter([row["tension"] / base_T for row in points],
                              [row["death_rate"] / base_rate for row in points],
                              s=size * 0.55, color=colour, marker=marker,
                              alpha=0.85, linewidths=0, zorder=3)
            inset.axvline(1.0, color="black", ls=":", lw=0.7, alpha=0.6)
            inset.axhline(1.0, color="black", ls=":", lw=0.7, alpha=0.6)
            inset.tick_params(labelsize=5.5, length=2, pad=1)
            inset.set_title("écart à la base de ce γ (×)", fontsize=6)
            inset.set_xlabel("T / T_base", fontsize=5.5, labelpad=1)
            inset.set_ylabel("taux / taux_base", fontsize=5.5, labelpad=1)
            inset.grid(True, alpha=0.2)

    axes[0].set_ylabel("morts / population / pas")
    # note [22] demandait aussi la durée de vie : elle est l'inverse EXACT du
    # taux (Σpop/Σmorts contre Σmorts/Σpop), donc un second axe et non un
    # second nuage.
    def reciprocal(value):
        with np.errstate(divide="ignore"):
            return 1.0 / np.asarray(value, dtype=float)

    lifetime = axes[-1].secondary_yaxis("right", functions=(reciprocal, reciprocal))
    lifetime.set_ylabel("durée de vie moyenne (pas)", fontsize=9)
    lifetime.set_yscale("log")
    lifetime.yaxis.set_major_locator(FixedLocator([20, 30, 50, 80, 120, 170]))
    lifetime.yaxis.set_minor_locator(NullLocator())
    lifetime.yaxis.set_major_formatter(FormatStrFormatter("%d"))
    lifetime.tick_params(labelsize=8)

    figure.suptitle(
        "Note [22] : mortalité (et son inverse, la durée de vie) contre la tension, "
        "un panneau par γ et un point par run.\nLes trois familles travaillent autour "
        "de trois bases différentes ; aucun ajustement n'est tracé.",
        fontsize=9.5)
    figure.tight_layout()
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def loglog_fit(rows: list[dict]) -> tuple[float, float]:
    """Ajustement log-log de morts/pop contre tension. Rendu pour le journal
    et pour `tension_fit.json` — plus tracé sur la figure."""
    tension = np.log(np.array([row["tension"] for row in rows]))
    rate = np.log(np.array([row["death_rate"] for row in rows]))
    slope, intercept = np.polyfit(tension, rate, 1)
    residual = rate - (intercept + slope * tension)
    r2 = 1.0 - residual.var() / rate.var() if rate.var() > 0 else float("nan")
    return float(slope), float(r2)


def baseline_exponent(rows: list[dict]) -> dict:
    """Exposant obtenu en ne gardant QUE la ligne de base de chaque γ.

    C'est le contrôle de la droite « tous γ confondus » : si les deux
    exposants coïncident, cette droite ne mesure aucune réponse à la tension,
    seulement le déplacement de la base avec γ.
    """
    bases = {}
    for row in rows:
        if group_of(row) != "contrôle":
            continue
        bases.setdefault(round(row["gamma"], 3), []).append(row)
    gammas = sorted(bases)
    if len(gammas) < 2:
        return {"exposant": float("nan"), "n_bases": len(gammas), "points": {}}
    tension = np.log([np.mean([row["tension"] for row in bases[g]]) for g in gammas])
    rate = np.log([np.mean([row["death_rate"] for row in bases[g]]) for g in gammas])
    slope, _ = np.polyfit(tension, rate, 1)
    return {
        "exposant": float(slope),
        "n_bases": len(gammas),
        "gamma_min": gammas[0],
        "gamma_max": gammas[-1],
        "points": {str(g): {"tension": float(np.exp(t)), "death_rate": float(np.exp(r))}
                   for g, t, r in zip(gammas, tension, rate)},
    }


def figure_trajectories(path: Path) -> None:
    """Trajectoires (tension, mortalité) de trois bras contrastés, graine 0."""
    picks = (
        ("contrôle", ROOT / "results" / "campaign" / "arms" / "control" / "seed0", "#294c60"),
        ("all_A150 (K0 fixe)", ROOT / "results" / "campaign" / "arms" / "all_A150" / "seed0",
         "#c1440e"),
        ("abl_A150_K0aut (K0 compensé)",
         ROOT / "results" / "ablation_k0" / "abl_A150_K0aut" / "seed0", "#3f7d20"),
    )
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    for label, directory, colour in picks:
        aggregate = read_csv(directory / "tension_agg.csv")
        series = read_csv(directory / "series.csv")
        if not aggregate or not series:
            continue
        rate = {int(float(row["t"])): float(row["deaths"]) / float(row["pop"])
                for row in series if float(row["pop"]) > 0}
        steps = [int(float(row["t"])) for row in aggregate]
        tension = [float(row["tension"]) for row in aggregate]
        axes[0].plot(steps, tension, color=colour, lw=0.7, label=label)
        keep = [(step, value) for step, value in zip(steps, tension)
                if step >= 400 and step in rate]
        axes[1].scatter([value for _, value in keep],
                        [rate[step] for step, _ in keep],
                        s=3, color=colour, alpha=0.4, label=label)
    axes[0].axvline(2000, color="black", ls=":", lw=0.9)
    axes[0].text(2000, axes[0].get_ylim()[1], " intervention", fontsize=7, va="top")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("t (pas)")
    axes[0].set_ylabel("tension T (log)")
    axes[0].set_title("évolution de la tension", fontsize=9)
    axes[0].legend(fontsize=7)
    axes[0].grid(True, alpha=0.2)
    axes[1].set_xlabel("tension T")
    axes[1].set_ylabel("morts / population")
    axes[1].set_title("plan (tension, mortalité), t ≥ 400", fontsize=9)
    axes[1].legend(fontsize=7, markerscale=3)
    axes[1].grid(True, alpha=0.2)
    figure.suptitle(
        "Compenser K0 laisse la tension au niveau du contrôle ; "
        "à K0 fixe elle monte, et la mortalité la suit", fontsize=10)
    figure.tight_layout()
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def power_fit(subset: list[dict], key: str) -> dict:
    """Ajuste $\\text{morts/pop} \\propto x^{s}$ et rend les résidus par levier."""
    x = np.log(np.array([row[key] for row in subset]))
    y = np.log(np.array([row["death_rate"] for row in subset]))
    slope, intercept = np.polyfit(x, y, 1)
    deviation = np.exp(y - (intercept + slope * x)) - 1.0
    by_lever = {}
    for lever in sorted({row["levier"] for row in subset}):
        mask = np.array([row["levier"] == lever for row in subset])
        by_lever[lever] = {
            "n": int(mask.sum()),
            "biais": float(deviation[mask].mean()),
            "ecart_max": float(np.abs(deviation[mask]).max()),
        }
    return {
        "cle": key,
        "pente": float(slope),
        "intercept": float(intercept),
        "r2": float(1.0 - (y - (intercept + slope * x)).var() / y.var()),
        "n": len(subset),
        "ecart_median": float(np.median(np.abs(deviation))),
        "ecart_max": float(np.abs(deviation).max()),
        "par_levier": by_lever,
    }


def figure_sweep(rows: list[dict], path: Path) -> dict:
    """La tension suffit-elle à prédire la mortalité ?

    Quatre leviers indépendants ($A$, $K_0$, $\\delta$, et $A$+$K_0$) sont
    appliqués au même état initial. Si la tension est un paramètre d'état,
    tous les points tombent sur une seule courbe dans le plan
    (tension, mortalité), quel que soit le chemin qui y a mené. Le panneau
    de droite oppose à la tension un prédicteur concurrent, l'intensité de
    rotation du crédit.
    """
    subset = [row for row in rows if round(row["gamma"], 3) == 0.5]
    if len(subset) < 10:
        return {}
    levers = sorted({row["levier"] for row in subset})
    colours = dict(zip(levers, ("#294c60", "#c1440e", "#3f7d20", "#7a4e9f",
                                "#e08a3c", "#66757f")))
    markers = dict(zip(levers, ("o", "s", "^", "D", "v", "P")))

    fixed_delta = [row for row in subset if abs(row["delta"] - 0.01) < 1e-12]
    fits = {
        "tension_tous_leviers": power_fit(subset, "tension"),
        "tension_delta_fixe": power_fit(fixed_delta, "tension"),
        "rotation_tous_leviers": power_fit(subset, "turnover"),
    }

    figure, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    panels = (
        (axes[0], "tension", fits["tension_tous_leviers"],
         "tension $T = K_{aut}/K_{eq}$",
         "(a) la tension : les leviers d'échelle s'alignent,\n$\\delta$ non"),
        (axes[1], "turnover", fits["rotation_tous_leviers"],
         "rotation du crédit : volume de prêt / $K_{tot}$",
         "(b) la rotation du crédit : les quatre leviers\ns'alignent"),
    )
    for axis, key, fit, xlabel, title in panels:
        for lever in levers:
            group = [row for row in subset if row["levier"] == lever]
            axis.scatter([row[key] for row in group],
                         [row["death_rate"] for row in group],
                         s=30, color=colours[lever], marker=markers[lever],
                         alpha=0.85, label=lever)
        grid = np.linspace(min(row[key] for row in subset),
                           max(row[key] for row in subset), 200)
        axis.plot(grid, np.exp(fit["intercept"]) * grid ** fit["pente"],
                  color="black", lw=1.1,
                  label=f"$\\propto x^{{{fit['pente']:.2f}}}$, R² = {fit['r2']:.3f}")
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_xlabel(xlabel)
        axis.set_ylabel("morts / population / pas")
        axis.set_title(title, fontsize=9)
        axis.legend(fontsize=6.5)
        axis.grid(True, alpha=0.2, which="both")

    figure.suptitle(
        f"γ = 0,5, {len(subset)} runs, quatre leviers indépendants (A, K₀, δ, A+K₀) "
        "appliqués au même état à t₀ = 2000\n"
        "La tension n'aligne que les leviers d'échelle ; la rotation du crédit les "
        "aligne tous, δ compris.", fontsize=10)
    figure.tight_layout()
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)

    fits["tension_min"] = float(min(row["tension"] for row in subset))
    fits["tension_max"] = float(max(row["tension"] for row in subset))
    fits["n_delta_fixe"] = len(fixed_delta)
    return fits


TABLE_ROWS = (
    ("campagne", "control", "contrôle"),
    ("campagne", "all_A150", "toutes $\\cdot$ $A\\times1{,}5$"),
    ("campagne", "new_A150", "nouvelles $\\cdot$ $A\\times1{,}5$"),
    ("campagne", "frac_A150_phi20", "fraction $\\varphi=0{,}2$ $\\cdot$ $A\\times1{,}5$"),
    ("ablation K0", "abl_K0aut", "$K_0\\times2{,}25$ seul"),
    ("ablation K0", "abl_A150_K0obs", "$A\\times1{,}5$ + $K_0\\times1{,}45$"),
    ("ablation K0", "abl_A150_K0aut", "$A\\times1{,}5$ + $K_0\\times2{,}25$"),
)


def write_table(arms: dict, path: Path) -> None:
    def decimal(value: float, digits: int) -> str:
        return f"{value:.{digits}f}".replace(".", "{,}")

    lines = [
        "\\begin{center}\\footnotesize",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "\\textbf{Bras} & tension $T$ & $K_{\\text{eq}}/\\overline{K}$ "
        "& morts/pop & durée de vie \\\\",
        " & & \\emph{(Jensen)} & \\emph{par pas} & \\emph{moyenne, pas} \\\\",
        "\\midrule",
    ]
    for family, arm, label in TABLE_ROWS:
        entry = arms.get((family, arm))
        if entry is None:
            continue
        lines.append(
            f"{label} & {decimal(entry['tension'], 2)} $\\pm$ "
            f"{decimal(entry['tension_sem'], 2)} & "
            f"{decimal(entry['jensen'], 3)} & "
            f"{decimal(entry['death_rate'], 5)} & "
            f"{decimal(entry['lifetime'], 1)} \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
        "",
        "\\noindent\\footnotesize Régime établi, moyenne sur les 1000 derniers "
        "pas et sur 5 graines ; incertitude = erreur-type sur les graines "
        "(note~\\ref{note:sigma}). $T = \\Kaut/K_{\\text{eq}}$ : plus $T$ est "
        "grand, plus le système tourne loin sous son échelle autarcique. "
        "$K_{\\text{eq}}/\\overline{K}$ mesure la dispersion interne des "
        "capitaux : 1 = capitaux tous égaux.\\normalsize",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


LEVER_ORDER = ("contrôle", "$A$ seul", "$K_0$ seul", "$\\delta$ seul",
               "A (campagne)", "A et K0 (ablation)")


def write_sweep_table(sweep: dict, path: Path) -> None:
    """Un tableau, une question : quel prédicteur tient sur les quatre leviers ?"""
    def pct(value: float, digits: int = 2) -> str:
        return f"{100 * value:+.{digits}f}".replace(".", "{,}") + "\\,\\%"

    lines = [
        "\\begin{center}\\footnotesize",
        "\\begin{tabular}{@{}lrrr@{}}",
        "\\toprule",
        " & \\textbf{tension $T$} & \\textbf{tension $T$} & "
        "\\textbf{rotation du crédit} \\\\",
        " & tous leviers & $\\delta$ fixé & tous leviers \\\\",
        "\\midrule",
    ]
    keys = ("tension_tous_leviers", "tension_delta_fixe", "rotation_tous_leviers")
    fits = [sweep[key] for key in keys]
    lines.append(
        "nombre de runs & "
        + " & ".join(str(fit["n"]) for fit in fits) + " \\\\"
    )
    lines.append(
        "exposant ajusté & "
        + " & ".join(f"{fit['pente']:.3f}".replace(".", "{,}") for fit in fits)
        + " \\\\"
    )
    lines.append(
        "$R^2$ (log-log) & "
        + " & ".join(f"\\textbf{{{fit['r2']:.4f}}}".replace(".", "{,}") for fit in fits)
        + " \\\\"
    )
    lines.append(
        "écart médian & "
        + " & ".join(pct(fit["ecart_median"]).replace("+", "") for fit in fits)
        + " \\\\"
    )
    lines.append("\\midrule")
    lines.append("\\multicolumn{4}{@{}l}{\\emph{biais moyen par levier}} \\\\")
    for lever in LEVER_ORDER:
        cells = []
        for fit in fits:
            entry = fit["par_levier"].get(lever)
            cells.append(pct(entry["biais"]) if entry else "---")
        lines.append(f"\\quad {lever} & " + " & ".join(cells) + " \\\\")
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
        "",
        "\\noindent\\footnotesize Ajustement en loi de puissance du taux de "
        "mortalité, $\\gamma = 0{,}5$, régime établi. Un prédicteur est un "
        "paramètre d'état si le biais est petit \\emph{pour chaque levier} : "
        "un levier qui s'écarte signale que la grandeur ne résume pas ce que "
        "ce levier a changé.\\normalsize",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    apply_style()
    FIGURES.mkdir(parents=True, exist_ok=True)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    rows = collect()
    if not rows:
        print("aucun run avec tension_agg.csv — lancer scripts/tension_figures.py")
        return 1
    arms = by_arm(rows)

    with open(ANALYSIS / "tension_runs.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    ordered = sorted(arms.values(), key=lambda entry: (entry["famille"], entry["bras"]))
    with open(ANALYSIS / "tension_arms.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ordered[0]))
        writer.writeheader()
        writer.writerows(ordered)

    write_table(arms, ROOT / "report" / "tables" / "tension_arms.tex")
    figure_arms(arms, FIGURES / "tension_arms.png")
    figure_collapse(rows, FIGURES / "tension_mortality.png")
    slope, r2 = loglog_fit(rows)
    bases = baseline_exponent(rows)
    figure_trajectories(FIGURES / "tension_trajectoires.png")
    sweep = figure_sweep(rows, FIGURES / "tension_sweep.png")
    if sweep:
        print(f"\nbalayage γ=0,5 : T de {sweep['tension_min']:.2f} à "
              f"{sweep['tension_max']:.2f}")
        for name in ("tension_tous_leviers", "tension_delta_fixe",
                     "rotation_tous_leviers"):
            fit = sweep[name]
            print(f"  {name:24s} n={fit['n']:3d}  pente {fit['pente']:+.3f}  "
                  f"R² {fit['r2']:.4f}  |écart| médian "
                  f"{100*fit['ecart_median']:5.2f} %  max {100*fit['ecart_max']:6.2f} %")
            for lever, entry in fit["par_levier"].items():
                print(f"      {lever:24s} n={entry['n']:3d} "
                      f"biais {100*entry['biais']:+7.2f} % "
                      f"écart max {100*entry['ecart_max']:6.2f} %")
        write_sweep_table(sweep, ROOT / "report" / "tables" / "tension_sweep.tex")

    print(f"{len(rows)} runs, {len(arms)} bras")
    print(f"mortalité ∝ T^{slope:.3f}   (R² log-log, tous γ = {r2:.4f})")
    print(f"  … à comparer à l'exposant tiré des SEULES bases : "
          f"T^{bases['exposant']:.3f}  ({bases['n_bases']} points, "
          f"γ de {bases['gamma_min']} à {bases['gamma_max']})")
    fits = {}
    for gamma in sorted({round(row["gamma"], 3) for row in rows}):
        subset = [row for row in rows if round(row["gamma"], 3) == gamma]
        # Étendue, et non nombre de valeurs distinctes : à γ = 0,4 les neuf
        # runs diffèrent au troisième chiffre, ce qui suffisait à passer
        # l'ancien garde-fou et à produire un ajustement sur du bruit.
        span = max(row["tension"] for row in subset) / min(row["tension"] for row in subset)
        if span < 1.5:
            print(f"  γ = {gamma}: pas d'ajustement — plage de tension de "
                  f"{100 * (span - 1):.1f} % seulement sur {len(subset)} runs")
            continue
        tension = np.log(np.array([row["tension"] for row in subset]))
        rate = np.log(np.array([row["death_rate"] for row in subset]))
        local_slope, intercept = np.polyfit(tension, rate, 1)
        residual = rate - (intercept + local_slope * tension)
        local_r2 = 1.0 - residual.var() / rate.var()
        fits[gamma] = {"slope": float(local_slope), "r2": float(local_r2),
                       "n": len(subset)}
        print(f"  γ = {gamma}: ∝ T^{local_slope:.3f}  (R² = {local_r2:.4f}, "
              f"n = {len(subset)} runs)")
    for entry in ordered:
        print(f"  {entry['famille']:>14} {entry['bras']:<18} n={entry['n']} "
              f"T={entry['tension']:8.3f} ± {entry['tension_sem']:.3f}  "
              f"morts/pop={entry['death_rate']:.5f}  vie={entry['lifetime']:6.2f}  "
              f"[{entry['basis']}]")
    json.dump(
        {"slope_log_log": slope, "r2": r2, "window": WINDOW, "n_runs": len(rows),
         "par_gamma": {str(key): value for key, value in fits.items()},
         "exposant_des_bases": bases,
         "balayage": sweep},
        open(ANALYSIS / "tension_fit.json", "w", encoding="utf-8"),
        indent=2,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
