"""Analyse de la campagne §7 : courbes de réponse appariées, plancher de
bruit, intensité de traitement observée, élasticité, verdict.

APPARIEMENT — le point méthodologique central, à ne pas perdre de vue :

- Les bras de portée `fraction` TIRENT leur cohorte avec le générateur de la
  simulation (exigence du prompt §2). Ce tirage consomme le flux aléatoire,
  donc dès le pas de l'intervention un bras `fraction` n'a plus le même flux
  qu'un contrôle inerte : leurs naissances diffèrent immédiatement. La
  référence appariée correcte d'un bras `fraction` est donc le bras `null`,
  qui tire la MÊME cohorte (même état du générateur, même appel
  `permutation`) et ne lui applique rien. Contre `null`, la différence à
  l'horizon 1 est exactement l'effet mécanique du changement de A, sans
  aucune contamination de flux.
- Les bras `all` et `new` ne consomment AUCUN tirage : leur référence
  appariée est le contrôle, exactement.
- Le contraste contrôle ↔ null ne contient, lui, AUCUN traitement : c'est le
  PLANCHER DE BRUIT dû au seul décalage de flux. Toute réponse qui ne sort
  pas de cette bande n'est pas interprétable.

    python3 scripts/analyse.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/anatole/jupyter")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from simulation_lab.plot_utils import apply_style  # noqa: E402

from scripts.campaign import ARMS, SEEDS, T0, WINDOW  # noqa: E402

CAMPAIGN = ROOT / "results" / "campaign"
ARM_DIR = CAMPAIGN / "arms"
OUT = ROOT / "results" / "analysis"
FIGDIR = ROOT / "report" / "figures"

# Référence appariée de chaque bras (voir la docstring).
REFERENCE = {
    "null": "control",
    "frac_A150_phi20": "null",
    "frac_A125_phi20": "null",
    "frac_A150_phi05": "null",
    "frac_A150_phi50": "null",
    "frac_g060_phi20": "null",
    "all_A150": "control",
    "new_A150": "control",
}
# Amplitude multiplicative du levier : rapport entre la production d'une
# entité traitée et celle qu'elle aurait au MÊME capital sans traitement.
# Pour un levier sur A c'est exactement le facteur imposé. Pour un levier sur
# γ il vaut K^{Δγ} et dépend donc du capital : `None` demande de le MESURER à
# l'horizon 1, où les capitaux sont encore identiques à ceux de la référence
# appariée (voir `effective_amplitude`).
AMPLITUDE = {
    "control": 1.0,
    "null": 1.0,
    "frac_A150_phi20": 1.5,
    "frac_A125_phi20": 1.25,
    "frac_A150_phi05": 1.5,
    "frac_A150_phi50": 1.5,
    "frac_g060_phi20": None,
    "all_A150": 1.5,
    "new_A150": 1.5,
}


def ex_ante_share(share_post: np.ndarray, amplitude: float) -> np.ndarray:
    """Part de production des entités traitées AVANT traitement.

    `tech_series` mesure la part APRÈS application du levier : une entité dont
    la production est multipliée par m pèse m fois plus dans le total. Si p est
    la part ex ante, la part observée vaut s = m p / (1 + (m-1) p), d'où

        p = s / (m - (m-1) s).

    Utiliser s au lieu de p dans le dénominateur de l'élasticité la sous-estime
    d'un facteur (1 + (m-1)p) — ici jusqu'à 10 %.
    """
    if amplitude <= 1.0:
        return np.zeros_like(share_post)
    return share_post / (amplitude - (amplitude - 1.0) * share_post)


def effective_amplitude(relative_h1: float, share_post_h1: float) -> float:
    """Amplitude effective mesurée à l'horizon 1.

    À h = 1 les capitaux sont encore exactement ceux de la référence appariée
    (l'intervention ne touche que la technologie), donc l'écart relatif observé
    EST l'effet mécanique. Avec s = part observée et r = écart relatif :
    p = s(1+r) − r, puis m = s(1+r)/p.
    """
    numerator = share_post_h1 * (1.0 + relative_h1)
    denominator = numerator - relative_h1
    if denominator <= 1e-9:
        return float("nan")
    return numerator / denominator


LABELS = {
    "control": "contrôle",
    "null": "null (tire φ=0,2, n'applique rien)",
    "frac_A150_phi20": "fraction φ=0,2, A×1,5",
    "frac_A125_phi20": "fraction φ=0,2, A×1,25",
    "frac_A150_phi05": "fraction φ=0,05, A×1,5",
    "frac_A150_phi50": "fraction φ=0,5, A×1,5",
    "frac_g060_phi20": "fraction φ=0,2, γ 0,5→0,6 (régime c)",
    "all_A150": "toutes, A×1,5",
    "new_A150": "nouvelles, A×1,5",
}
COLORS = {
    "null": "#8a8a8a",
    "frac_A150_phi20": "#c1440e",
    "frac_A125_phi20": "#e08a3c",
    "frac_A150_phi05": "#7aa6c2",
    "frac_A150_phi50": "#6b2d5c",
    "frac_g060_phi20": "#2e7d5b",
    "all_A150": "#294c60",
    "new_A150": "#1f77b4",
}

# Seuil au-dessous duquel l'élasticité normalisée n'est plus interprétable :
# la réponse proportionnelle attendue tombe alors sous le plancher de bruit
# des moyennes de fenêtre (≈ 1 % de prod_tot, mesuré sur le contraste
# contrôle ↔ null).
MIN_EXPECTED = 0.02

WINDOWS = {
    "impact (h≤50)": (1, 50),
    "court (51–300)": (51, 300),
    "moyen (301–1000)": (301, 1000),
    "établi (1001–2000)": (1001, WINDOW),
}


def read_series(path: Path) -> dict[str, np.ndarray]:
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    columns = {}
    for name in rows[0]:
        columns[name] = np.array([float(row[name]) for row in rows])
    return columns


def read_tech(path: Path) -> dict[int, dict[str, np.ndarray]]:
    """Renvoie, par pas, la part de production et d'effectif des technologies
    TRAITÉES (tout identifiant de technologie autre que 0, la technologie de
    naissance d'origine)."""
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    per_t: dict[int, dict[str, float]] = {}
    for row in rows:
        t = int(row["t"])
        entry = per_t.setdefault(t, {"prod": 0.0, "prod_treated": 0.0, "n": 0.0, "n_treated": 0.0,
                                     "K": 0.0, "K_treated": 0.0})
        entry["prod"] += float(row["prod"])
        entry["n"] += float(row["n_alive"])
        entry["K"] += float(row["K"])
        if int(row["tech"]) != 0:
            entry["prod_treated"] += float(row["prod"])
            entry["n_treated"] += float(row["n_alive"])
            entry["K_treated"] += float(row["K"])
    return per_t


def arm_matrix(arm: str, column: str) -> np.ndarray:
    """Matrice (graines × horizon) d'une colonne, sur la fenêtre post-t₀."""
    out = []
    for seed in SEEDS:
        series = read_series(ARM_DIR / arm / f"seed{seed}" / "series.csv")
        out.append(series[column][T0 : T0 + WINDOW])
    return np.array(out)


def treated_share_matrix(arm: str, key: str = "prod") -> np.ndarray:
    out = []
    for seed in SEEDS:
        per_t = read_tech(ARM_DIR / arm / f"seed{seed}" / "tech_series.csv")
        row = []
        for h in range(1, WINDOW + 1):
            entry = per_t.get(T0 + h)
            if entry is None or entry[key] <= 0:
                row.append(0.0)
            else:
                row.append(entry[f"{key}_treated"] / entry[key])
        out.append(row)
    return np.array(out)


def smooth(values: np.ndarray, width: int = 101) -> np.ndarray:
    if width <= 1 or values.size < width:
        return values
    kernel = np.ones(width) / width
    padded = np.pad(values, (width // 2, width // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")[: values.size]


def mean_sem(matrix: np.ndarray, axis: int = 0):
    mean = matrix.mean(axis=axis)
    sem = matrix.std(axis=axis, ddof=1) / math.sqrt(matrix.shape[axis])
    return mean, sem


def check_integrity() -> dict:
    """Refuse d'analyser des runs tronqués ou incohérents.

    Un bras qui se termine en `explosion` ou `extinction` produit une série
    plus courte ; sans ce contrôle, `np.array` fabriquerait un tableau ragged
    et toutes les moyennes en aval seraient silencieusement fausses. On
    vérifie aussi que `transfer_cap="optimum"` s'est bien propagé à travers
    le snapshot (aucune transaction plafonnée) et que le carnet est sain.
    """
    summary = {"runs": 0, "capped_total": 0, "statuses": {}}
    problems = []
    for arm in ARMS:
        for seed in SEEDS:
            directory = ARM_DIR / arm / f"seed{seed}"
            marker = directory / "summary.json"
            if not marker.exists():
                problems.append(f"{arm}/seed{seed} : summary.json absent")
                continue
            payload = json.loads(marker.read_text(encoding="utf-8"))
            summary["runs"] += 1
            summary["statuses"][payload["status"]] = summary["statuses"].get(payload["status"], 0) + 1
            if payload["status"] != "ok":
                problems.append(f"{arm}/seed{seed} : statut {payload['status']}")
            if payload["t_final"] != T0 + WINDOW:
                problems.append(
                    f"{arm}/seed{seed} : t_final {payload['t_final']} ≠ {T0 + WINDOW}"
                )
            if payload["book_errors"]:
                problems.append(f"{arm}/seed{seed} : carnet incohérent {payload['book_errors'][:2]}")
            if payload["parameters"]["transfer_cap"] != "optimum":
                problems.append(f"{arm}/seed{seed} : transfer_cap inattendu")
            series = read_series(directory / "series.csv")
            if series["t"].size != T0 + WINDOW:
                problems.append(f"{arm}/seed{seed} : série de {series['t'].size} lignes")
            summary["capped_total"] += int(series["mkt_capped"].sum())
    if summary["capped_total"] != 0:
        problems.append(f"{summary['capped_total']} transactions plafonnées sous transfer_cap=optimum")
    if problems:
        raise SystemExit("Intégrité de la campagne : " + " | ".join(problems[:10]))
    return summary


def collect() -> dict:
    data = {}
    for arm in ARMS:
        data[arm] = {
            "prod": arm_matrix(arm, "prod_tot"),
            "K": arm_matrix(arm, "K_tot"),
            "pop": arm_matrix(arm, "pop"),
            "loan_volume": arm_matrix(arm, "loan_volume"),
            "blocked_dir": arm_matrix(arm, "mkt_blocked_dir"),
            "rounds": arm_matrix(arm, "mkt_rounds"),
            "deaths": arm_matrix(arm, "deaths"),
            "defaults": arm_matrix(arm, "defaults"),
            "surplus": arm_matrix(arm, "mkt_surplus"),
            "interest": arm_matrix(arm, "interest_paid"),
            "share_prod": treated_share_matrix(arm, "prod"),
            "share_n": treated_share_matrix(arm, "n"),
            "share_K": treated_share_matrix(arm, "K"),
        }
    return data


def analyse(data: dict) -> dict:
    result = {
        "t0": T0,
        "window": WINDOW,
        "seeds": list(SEEDS),
        "reference": REFERENCE,
        "arms": {},
    }
    for arm, reference in REFERENCE.items():
        difference = data[arm]["prod"] - data[reference]["prod"]
        relative = difference / data[reference]["prod"]
        mean, sem = mean_sem(difference)
        rel_mean, rel_sem = mean_sem(relative)
        share_mean, _ = mean_sem(data[arm]["share_prod"])
        relative_h1 = float(relative[:, 0].mean())
        share_h1 = float(data[arm]["share_prod"][:, 0].mean())
        measured = effective_amplitude(relative_h1, share_h1) if share_h1 > 1e-3 else float("nan")
        amplitude = AMPLITUDE[arm]
        if amplitude is None:
            amplitude = measured
        entry = {
            "reference": reference,
            "label": LABELS[arm],
            "amplitude": amplitude,
            "amplitude_source": "imposée" if AMPLITUDE[arm] is not None else "mesurée à h=1",
            "amplitude_measured_h1": measured,
            "impact_h1": {
                "delta_prod": float(difference[:, 0].mean()),
                "delta_prod_sem": float(difference[:, 0].std(ddof=1) / math.sqrt(len(SEEDS))),
                "relative": relative_h1,
                "share_prod_treated_post": share_h1,
                "share_prod_treated_ante": float(
                    ex_ante_share(np.array([share_h1]), amplitude)[0]
                ) if amplitude and amplitude > 1.0 else 0.0,
            },
            "windows": {},
        }
        for name, (lo, hi) in WINDOWS.items():
            sl = slice(lo - 1, hi)
            window_rel = relative[:, sl].mean(axis=1)
            window_share = data[arm]["share_prod"][:, sl].mean(axis=1)
            entry["windows"][name] = {
                "delta_prod": float(difference[:, sl].mean()),
                "delta_prod_sem": float(
                    difference[:, sl].mean(axis=1).std(ddof=1) / math.sqrt(len(SEEDS))
                ),
                "relative": float(window_rel.mean()),
                "relative_sem": float(window_rel.std(ddof=1) / math.sqrt(len(SEEDS))),
                "share_prod_treated": float(window_share.mean()),
                "prod_arm": float(data[arm]["prod"][:, sl].mean()),
                "prod_reference": float(data[reference]["prod"][:, sl].mean()),
                "K_relative": float(
                    ((data[arm]["K"][:, sl] - data[reference]["K"][:, sl])
                     / data[reference]["K"][:, sl]).mean()
                ),
                "pop_relative": float(
                    ((data[arm]["pop"][:, sl] - data[reference]["pop"][:, sl])
                     / data[reference]["pop"][:, sl]).mean()
                ),
                "loan_volume_relative": float(
                    ((data[arm]["loan_volume"][:, sl] - data[reference]["loan_volume"][:, sl])
                     / data[reference]["loan_volume"][:, sl]).mean()
                ),
                "blocked_dir_share": float(
                    (data[arm]["blocked_dir"][:, sl] / data[arm]["rounds"][:, sl]).mean()
                ),
                "deaths_relative": float(
                    ((data[arm]["deaths"][:, sl] - data[reference]["deaths"][:, sl])
                     / np.maximum(1.0, data[reference]["deaths"][:, sl])).mean()
                ),
            }
            # prod_tot = pop × production moyenne par entité. Publier les deux
            # facteurs évite qu'une élasticité agrégée soit lue comme une
            # affirmation par entité que les données n'isolent pas.
            population_ratio = (
                data[arm]["pop"][:, sl].mean(axis=1) / data[reference]["pop"][:, sl].mean(axis=1)
            )
            production_ratio = (
                data[arm]["prod"][:, sl].mean(axis=1) / data[reference]["prod"][:, sl].mean(axis=1)
            )
            entry["windows"][name]["pop_factor"] = float(population_ratio.mean())
            entry["windows"][name]["per_entity_factor"] = float(
                (production_ratio / population_ratio).mean()
            )
            entry["windows"][name]["sigma"] = (
                float(window_rel.mean() / (window_rel.std(ddof=1) / math.sqrt(len(SEEDS))))
                if window_rel.std(ddof=1) > 0
                else float("inf")
            )
            # Élasticité normalisée : 1 = réponse exactement proportionnelle à
            # l'intensité de traitement EX ANTE et à l'amplitude du levier.
            # Par construction elle vaut 1 à l'horizon 1 (effet purement
            # mécanique) : tout écart à 1 au-delà est la réponse dynamique.
            if arm != "null" and amplitude and amplitude > 1.0:
                window_share_ante = ex_ante_share(window_share, amplitude)
                entry["windows"][name]["share_prod_treated_ante"] = float(window_share_ante.mean())
                expected = (amplitude - 1.0) * window_share_ante
                usable = expected > 1e-4
                if usable.any():
                    ratios = window_rel[usable] / expected[usable]
                    entry["windows"][name]["elasticity"] = float(ratios.mean())
                    entry["windows"][name]["elasticity_sem"] = (
                        float(ratios.std(ddof=1) / math.sqrt(len(ratios))) if len(ratios) > 1 else None
                    )
                    entry["windows"][name]["elasticity_n_seeds"] = int(usable.sum())
        # Statistique SANS FENÊTRE : réponse cumulée sur tout l'horizon,
        # rapportée à la réponse strictement proportionnelle cumulée. Elle ne
        # dépend d'aucun découpage et répond directement au « réponse non
        # proportionnelle » du §1 du prompt. Elle mélange en revanche le pic
        # initial et la longue décroissance : à lire avec la courbe, pas seule.
        if amplitude and amplitude > 1.0:
            share_ante = ex_ante_share(data[arm]["share_prod"], amplitude)
            numerator = difference.sum(axis=1)
            denominator = (
                (amplitude - 1.0) * share_ante * data[reference]["prod"]
            ).sum(axis=1)
            usable = denominator > 0
            if usable.any():
                ratios = numerator[usable] / denominator[usable]
                entry["cumulative_elasticity"] = float(ratios.mean())
                entry["cumulative_elasticity_sem"] = (
                    float(ratios.std(ddof=1) / math.sqrt(len(ratios))) if len(ratios) > 1 else None
                )
        entry["curve"] = {
            "delta_mean": smooth(mean).tolist(),
            "delta_sem": smooth(sem).tolist(),
            "relative_mean": smooth(rel_mean).tolist(),
            "relative_sem": smooth(rel_sem).tolist(),
            "share_prod": smooth(share_mean).tolist(),
        }
        result["arms"][arm] = entry

    # Élasticité « globale » à A, dans le régime établi : tout le monde a A=1,5.
    for arm in ("all_A150", "new_A150"):
        established = result["arms"][arm]["windows"]["établi (1001–2000)"]
        ratio = established["prod_arm"] / established["prod_reference"]
        result["arms"][arm]["log_elasticity_prod_A"] = math.log(ratio) / math.log(1.5)
        result["arms"][arm]["log_elasticity_K_A"] = math.log(
            1.0 + established["K_relative"]
        ) / math.log(1.5)
    return result


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------
def figure_noise_floor(data, result):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    difference = data["null"]["prod"] - data["control"]["prod"]
    horizon = np.arange(1, WINDOW + 1)
    for index, seed in enumerate(SEEDS):
        axes[0].plot(horizon, difference[index] / data["control"]["prod"][index],
                     lw=0.5, alpha=0.5, label=f"graine {seed}")
    mean, sem = mean_sem(difference / data["control"]["prod"])
    axes[0].plot(horizon, smooth(mean), color="black", lw=1.8, label="moyenne 5 graines (lissée)")
    axes[0].axhline(0, color="black", lw=0.6, ls=":")
    axes[0].set_xlabel("horizon h après t₀ (pas)")
    axes[0].set_ylabel("écart relatif de prod_tot")
    axes[0].set_title(f"Plancher de bruit : null − contrôle (n={len(SEEDS)} graines)")
    axes[0].legend(fontsize=7)

    band = np.abs(smooth(mean)) + smooth(sem)
    axes[1].plot(horizon, band, color="black", lw=1.2)
    axes[1].set_xlabel("horizon h après t₀ (pas)")
    axes[1].set_ylabel("|biais| + erreur-type")
    axes[1].set_title("Bande de bruit utilisée comme seuil d'interprétation")
    axes[1].set_yscale("log")
    for axis in axes:
        axis.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGDIR / "noise_floor.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return float(np.median(band)), float(band.max())


def figure_response(data, result):
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    horizon = np.arange(1, WINDOW + 1)
    groups = (
        ("Portée fraction (référence appariée : bras null)",
         ["frac_A150_phi05", "frac_A150_phi20", "frac_A150_phi50", "frac_A125_phi20",
          "frac_g060_phi20"]),
        ("Portées globales (référence appariée : contrôle)", ["all_A150", "new_A150"]),
    )
    noise_mean, noise_sem = mean_sem(
        (data["null"]["prod"] - data["control"]["prod"]) / data["control"]["prod"]
    )
    noise = smooth(np.abs(noise_mean)) + smooth(noise_sem)
    for axis, (title, arms) in zip(axes, groups):
        axis.fill_between(horizon, -noise, noise, color="0.85",
                          label="bande de bruit (null − contrôle)")
        for arm in arms:
            reference = REFERENCE[arm]
            relative = (data[arm]["prod"] - data[reference]["prod"]) / data[reference]["prod"]
            mean, sem = mean_sem(relative)
            mean, sem = smooth(mean), smooth(sem)
            axis.plot(horizon, mean, color=COLORS[arm], lw=1.5, label=LABELS[arm])
            axis.fill_between(horizon, mean - sem, mean + sem, color=COLORS[arm], alpha=0.18)
        axis.axhline(0, color="black", lw=0.6, ls=":")
        axis.set_title(f"{title} — n={len(SEEDS)} graines, moyenne lissée sur 101 pas")
        axis.set_ylabel("écart relatif de prod_tot")
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=8, loc="best")
    axes[1].set_xlabel("horizon h après l'intervention à t₀ = %d (pas)" % T0)
    fig.tight_layout()
    fig.savefig(FIGDIR / "response_prod.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def figure_share_and_elasticity(data, result):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    horizon = np.arange(1, WINDOW + 1)
    arms = ["frac_A150_phi05", "frac_A150_phi20", "frac_A150_phi50", "frac_A125_phi20",
            "frac_g060_phi20", "all_A150", "new_A150"]
    for arm in arms:
        mean, _ = mean_sem(data[arm]["share_prod"])
        axes[0].plot(horizon, smooth(mean, 51), color=COLORS[arm], lw=1.4, label=LABELS[arm])
    axes[0].set_xlabel("horizon h (pas)")
    axes[0].set_ylabel("part de prod_tot détenue par les entités traitées")
    axes[0].set_title(f"Intensité de traitement OBSERVÉE (n={len(SEEDS)} graines)")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=7)

    for arm in arms:
        amplitude = result["arms"][arm]["amplitude"]
        if not amplitude or amplitude <= 1.0:
            continue
        reference = REFERENCE[arm]
        relative = (data[arm]["prod"] - data[reference]["prod"]) / data[reference]["prod"]
        expected = (amplitude - 1.0) * ex_ante_share(data[arm]["share_prod"], amplitude)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(expected > 1e-4, relative / expected, np.nan)
        mean = smooth(np.nanmean(ratio, axis=0), 101)
        # Le rapport n'a de sens que là où le dénominateur — la réponse
        # strictement proportionnelle attendue — dépasse nettement le bruit
        # de mesure. Quand la cohorte traitée s'éteint, il tend vers 0/0 :
        # on coupe la courbe plutôt que d'afficher du bruit amplifié.
        meaningful = expected.mean(axis=0) > MIN_EXPECTED
        axes[1].plot(
            horizon[meaningful], mean[meaningful], color=COLORS[arm], lw=1.4, label=LABELS[arm]
        )
    axes[1].axhline(1.0, color="black", lw=0.9, ls="--", label="réponse proportionnelle (=1)")
    axes[1].set_xlabel("horizon h (pas)")
    axes[1].set_ylabel("réponse observée / réponse proportionnelle")
    axes[1].set_ylim(-0.5, 3.5)
    axes[1].set_title(
        "Élasticité normalisée par l'intensité ex ante\n"
        f"(tracée seulement là où la réponse attendue dépasse {MIN_EXPECTED:.0%} de prod_tot)"
    )
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / "share_elasticity.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def figure_channels(data, result):
    # Le panneau « morts par pas » a été retiré : à l'état stationnaire le
    # flux de morts est fixé par le flux de naissances (λ), il ne peut donc
    # rien apprendre. C'est le TAUX qui compte, et il est traité au §4.4 et
    # au §5. Le panneau des paires refusées est conservé alors même que la
    # règle du sens du prêt est appelée à disparaître : tant qu'elle existe,
    # ce canal est réel.
    panels = [
        ("loan_volume", "volume de prêt", True),
        ("blocked_dir", "paires refusées par le sens du prêt (part des rounds)", False),
        ("K", "capital agrégé K_tot", True),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    horizon = np.arange(1, WINDOW + 1)
    arms = ["frac_A150_phi20", "frac_A150_phi50", "frac_g060_phi20", "all_A150", "new_A150"]
    for axis, (key, title, relative_mode) in zip(axes.ravel(), panels):
        for arm in arms:
            reference = REFERENCE[arm]
            if key == "blocked_dir":
                values = data[arm]["blocked_dir"] / data[arm]["rounds"]
                mean, _ = mean_sem(values)
                axis.plot(horizon, smooth(mean), color=COLORS[arm], lw=1.3, label=LABELS[arm])
            else:
                denominator = np.maximum(1e-9, data[reference][key])
                values = (data[arm][key] - data[reference][key]) / denominator
                mean, _ = mean_sem(values)
                axis.plot(horizon, smooth(mean), color=COLORS[arm], lw=1.3, label=LABELS[arm])
        if key == "blocked_dir":
            reference_share, _ = mean_sem(data["control"]["blocked_dir"] / data["control"]["rounds"])
            axis.plot(horizon, smooth(reference_share), color="black", lw=1.0, ls=":",
                      label="contrôle (homogène)")
            axis.set_ylabel("part des rounds")
        else:
            axis.axhline(0, color="black", lw=0.6, ls=":")
            axis.set_ylabel("écart relatif au bras apparié")
        axis.set_title(title)
        axis.set_xlabel("horizon h (pas)")
        axis.grid(True, alpha=0.25)
        if key != "K":
            axis.legend(fontsize=7)
        if key == "K":
            # Presque tout se joue sous +0,7 : on coupe le haut et on met la
            # vue d'ensemble en encart, si petite soit-elle (note [24]). La
            # légende est portée par les deux premiers panneaux, mêmes
            # couleurs : on libère la place.
            low, high = axis.get_ylim()
            axis.set_ylim(low, min(high, 0.7))
            inset = axis.inset_axes((0.46, 0.50, 0.50, 0.42))
            for arm in arms:
                reference = REFERENCE[arm]
                denominator = np.maximum(1e-9, data[reference][key])
                values = (data[arm][key] - data[reference][key]) / denominator
                mean, _ = mean_sem(values)
                inset.plot(horizon, smooth(mean), color=COLORS[arm], lw=0.8)
            inset.axhline(0, color="black", lw=0.5, ls=":")
            inset.axhline(0.7, color="#c1440e", lw=0.7, ls="--")
            inset.tick_params(labelsize=5)
            inset.text(0.02, 0.96, "vue d'ensemble (échelle entière)",
                       transform=inset.transAxes, fontsize=5.5, va="top")
            inset.grid(True, alpha=0.2)
            axis.text(0.02, 0.02, "mêmes couleurs que les panneaux de gauche",
                      transform=axis.transAxes, fontsize=6, color="#66757f")
    fig.suptitle(f"Canaux de propagation (n={len(SEEDS)} graines, moyenne lissée 101 pas)")
    fig.tight_layout()
    fig.savefig(FIGDIR / "channels.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def figure_levels(data, result):
    fig, axis = plt.subplots(figsize=(10, 4.6))
    arms = [arm for arm in ARMS if arm != "control"]
    window = "établi (1001–2000)"
    positions = np.arange(len(arms))
    values = [result["arms"][arm]["windows"][window]["relative"] * 100 for arm in arms]
    errors = [result["arms"][arm]["windows"][window]["relative_sem"] * 100 for arm in arms]
    colours = [COLORS[arm] for arm in arms]
    axis.bar(positions, values, yerr=errors, capsize=4, color=colours, alpha=0.9)
    axis.axhline(0, color="black", lw=0.8)
    axis.set_xticks(positions)
    axis.set_xticklabels([LABELS[arm] for arm in arms], rotation=25, ha="right", fontsize=8)
    axis.set_ylabel("écart relatif de prod_tot (%)")
    axis.set_title(
        f"Régime établi h ∈ [1001, 2000] — écart au bras apparié (n={len(SEEDS)} graines, ±1 erreur-type)"
    )
    axis.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGDIR / "levels_established.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    apply_style()
    OUT.mkdir(parents=True, exist_ok=True)
    FIGDIR.mkdir(parents=True, exist_ok=True)
    integrity = check_integrity()
    data = collect()
    result = analyse(data)
    result["integrity"] = integrity
    median_noise, max_noise = figure_noise_floor(data, result)
    result["noise_floor"] = {"median": median_noise, "max": max_noise}
    figure_response(data, result)
    figure_share_and_elasticity(data, result)
    figure_channels(data, result)
    figure_levels(data, result)
    (OUT / "metrics.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    with open(OUT / "windows.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["bras", "reference", "fenetre", "delta_prod", "delta_prod_sem", "relatif",
             "relatif_sem", "part_traitee_post", "part_traitee_ante", "amplitude",
             "elasticite", "K_relatif", "pop_relatif",
             "volume_relatif", "part_bloquee_sens", "morts_relatif"]
        )
        for arm, entry in result["arms"].items():
            for name, window in entry["windows"].items():
                writer.writerow(
                    [arm, entry["reference"], name,
                     f"{window['delta_prod']:.6g}", f"{window['delta_prod_sem']:.6g}",
                     f"{window['relative']:.6g}", f"{window['relative_sem']:.6g}",
                     f"{window['share_prod_treated']:.6g}",
                     f"{window.get('share_prod_treated_ante', 0.0):.6g}",
                     f"{entry['amplitude'] if entry['amplitude'] else float('nan'):.6g}",
                     f"{window.get('elasticity', float('nan')):.6g}",
                     f"{window['K_relative']:.6g}", f"{window['pop_relative']:.6g}",
                     f"{window['loan_volume_relative']:.6g}",
                     f"{window['blocked_dir_share']:.6g}", f"{window['deaths_relative']:.6g}"]
                )
    print(json.dumps({k: v for k, v in result.items() if k != "arms"}, indent=2, ensure_ascii=False))
    for arm, entry in result["arms"].items():
        window = entry["windows"]["établi (1001–2000)"]
        print(
            f"{arm:20s} vs {entry['reference']:8s} | établi : "
            f"{window['relative']*100:+7.2f} % ± {window['relative_sem']*100:.2f} "
            f"| part traitée {window['share_prod_treated']:.3f} "
            f"({window['sigma']:+5.1f} σ) "
            f"| part ex ante {window.get('share_prod_treated_ante', 0.0):.3f} "
            f"| élasticité {window.get('elasticity', float('nan')):.3f} "
            f"| pop ×{window['pop_factor']:.3f} × par entité ×{window['per_entity_factor']:.3f}"
        )
        if "cumulative_elasticity" in entry:
            print(
                f"{'':20s}    cumulée sur h=1..{WINDOW} : "
                f"{entry['cumulative_elasticity']:.3f} ± "
                f"{entry.get('cumulative_elasticity_sem') or float('nan'):.3f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
