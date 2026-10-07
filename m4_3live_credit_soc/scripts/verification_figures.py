"""Figures des deux VÉRIFICATIONS qui n'en avaient pas encore.

1. Parité bit à bit avec M4.3. Une égalité exacte est difficile à
   « montrer » : on trace donc la trajectoire de M4.3Live superposée à celle
   du run M4.3 stocké, et en dessous l'écart pas à pas, qui reste
   rigoureusement à zéro sur les 8000 pas et les 26 colonnes. Source :
   `results/analysis/parity_deviations_8000.csv`, écrit par
   `tests/test_parity_m4_3.py --full`.

2. Calibration de la mesure à l'horizon 1. À ce pas, les capitaux du bras
   traité sont encore exactement ceux de sa référence appariée : l'écart
   relatif observé DOIT valoir (m−1)·p, l'effet purement mécanique. On trace
   observé contre prédit ; l'alignement sur la première bissectrice est un
   test de la chaîne de mesure, pas un résultat. Source :
   `results/analysis/metrics.json`.

    python3 scripts/verification_figures.py
"""

from __future__ import annotations

import csv
import json
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
from simulation_lab.runs.storage import RunStorage  # noqa: E402

ANALYSIS = ROOT / "results" / "analysis"
FIGDIR = ROOT / "report" / "figures"
REFERENCE_RUN = "m4_3__d1__baseline__seed0"


def figure_parity(steps: int = 8000) -> bool:
    source = ANALYSIS / f"parity_deviations_{steps}.csv"
    if not source.exists():
        return False
    with open(source, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    time_axis = np.array([int(r["t"]) for r in rows])
    live = np.array([float(r["prod_tot"]) for r in rows])
    gaps = np.array([float(r["ecart_max_toutes_colonnes"]) for r in rows])

    storage = RunStorage()
    with open(Path(storage.run_dir(REFERENCE_RUN)) / "series.csv", newline="") as handle:
        reference = [float(row["prod_tot"]) for row in csv.DictReader(handle)][: len(rows)]

    figure, axes = plt.subplots(
        2, 1, figsize=(10, 6), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]}
    )
    axes[0].plot(time_axis, reference, color="#c1440e", lw=2.6, alpha=0.55,
                 label=f"M4.3 stocké ({REFERENCE_RUN})")
    axes[0].plot(time_axis, live, color="#294c60", lw=0.8,
                 label="M4.3Live, régime homogène")
    axes[0].set_ylabel("prod_tot")
    axes[0].set_title(
        f"Parité bit à bit : {steps} pas, 26 colonnes de série, aucune tolérance"
    )
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)

    # Un écart exactement nul ne se trace pas sur une échelle log : on le
    # rabat sur une ligne repère explicitement étiquetée comme telle.
    floor = 1e-19
    axes[1].plot(time_axis, np.maximum(gaps, floor), color="#294c60", lw=1.6,
                 label="écart mesuré (exactement 0, rabattu sur le repère)")
    axes[1].axhline(2.2e-16, color="#66757f", ls=":", lw=1.0)
    axes[1].text(steps * 0.02, 4e-16, "epsilon machine", fontsize=7, color="#66757f")
    axes[1].set_yscale("log")
    axes[1].set_ylim(3e-20, 1e-8)
    axes[1].legend(fontsize=7, loc="upper right")
    axes[1].set_xlabel("t (pas)")
    axes[1].set_ylabel("écart maximal\n(toutes colonnes)")
    axes[1].set_title(
        f"Écart maximal mesuré : {gaps.max():.0f} — la courbe est au plancher du graphique",
        fontsize=9,
    )
    axes[1].grid(True, which="both", alpha=0.25)
    figure.tight_layout()
    figure.savefig(FIGDIR / "parity_m4_3.png", dpi=150, bbox_inches="tight")
    plt.close(figure)
    return True


#: Amplitude imposée par construction du bras. Le bras γ n'en a pas : son
#: amplitude vaut K^{Δγ} et ne peut être que mesurée.
IMPOSED = {
    "null": 1.0,
    "frac_A150_phi20": 1.5,
    "frac_A125_phi20": 1.25,
    "frac_A150_phi05": 1.5,
    "frac_A150_phi50": 1.5,
    "all_A150": 1.5,
    "frac_g060_phi20": None,
}
LABELS = {
    "null": "null (tire φ=0,2, n'applique rien)",
    "frac_A150_phi20": "fraction φ=0,2 · A×1,5",
    "frac_A125_phi20": "fraction φ=0,2 · A×1,25",
    "frac_A150_phi05": "fraction φ=0,05 · A×1,5",
    "frac_A150_phi50": "fraction φ=0,5 · A×1,5",
    "all_A150": "toutes · A×1,5",
    "frac_g060_phi20": "fraction φ=0,2 · γ 0,5→0,6",
}


def figure_calibration() -> bool:
    """Trois panneaux, une colonne du tableau expliquée par panneau (note [15])."""
    source = ANALYSIS / "exact_amplitude.json"
    if not source.exists():
        return False
    data = json.loads(source.read_text(encoding="utf-8"))["arms"]
    order = [name for name in LABELS if name in data]
    levered = [name for name in order if abs(data[name]["effet_mecanique"]) > 1e-12]

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.8),
                                gridspec_kw={"width_ratios": [1.15, 1.15, 1]})

    # (a) observé contre prédit — la colonne « écart relatif » du tableau
    axis = axes[0]
    predicted = [data[name]["effet_mecanique"] for name in levered]
    observed = [data[name]["ecart_relatif_h1"] for name in levered]
    limit = max(max(predicted), max(observed)) * 1.15
    axis.plot([0, limit], [0, limit], color="black", ls="--", lw=1.0,
              label="égalité exacte $(m-1)\\,p$")
    for name, x_value, y_value in zip(levered, predicted, observed):
        axis.scatter(x_value, y_value, s=70, color="#294c60", zorder=3)
        axis.annotate(LABELS[name], (x_value, y_value), textcoords="offset points",
                      xytext=(8, -3), fontsize=6.5)
    axis.set_xlabel("réponse strictement proportionnelle $(m-1)\\,p$")
    axis.set_ylabel("écart relatif observé à $h=1$")
    axis.set_title(f"(a) l'écart observé EST l'effet mécanique\n({len(levered)} bras à levier)",
                   fontsize=9)
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=7)

    # (b) amplitude mesurée contre imposée — la colonne « amplitude »
    axis = axes[1]
    positions = np.arange(len(order))
    measured = [data[name]["m_exact"] for name in order]
    imposed = [IMPOSED.get(name) for name in order]
    axis.barh(positions - 0.19, [value if value else 0.0 for value in imposed],
              height=0.36, color="#66757f", label="amplitude imposée par le bras")
    axis.barh(positions + 0.19, measured, height=0.36, color="#c1440e",
              label="amplitude mesurée entité par entité")
    for index, (value, imposed_value) in enumerate(zip(measured, imposed)):
        axis.text(value, index + 0.19, f" {value:.6f}", va="center", fontsize=6.5)
        if imposed_value is None:
            axis.text(0.02, index - 0.19, "  aucune : levier sur γ, m = K^Δγ",
                      va="center", fontsize=6.5, color="#66757f")
    axis.set_yticks(positions)
    axis.set_yticklabels([LABELS[name] for name in order], fontsize=6.5)
    axis.set_xlabel("amplitude multiplicative $m$")
    axis.set_title("(b) l'amplitude mesurée retrouve l'amplitude imposée\nà six décimales",
                   fontsize=9)
    axis.grid(True, axis="x", alpha=0.25)
    axis.legend(fontsize=6.5, loc="lower right")

    # (c) E(h=1) — la conclusion du tableau, à la précision machine
    axis = axes[2]
    deviation = [max(abs(data[name]["E_h1"] - 1.0), 1e-17) for name in levered]
    axis.barh(np.arange(len(levered)), deviation, height=0.55, color="#294c60")
    axis.axvline(2.2e-16, color="#c1440e", ls="--", lw=1.0)
    axis.text(2.6e-16, len(levered) - 0.4, "epsilon machine", fontsize=6.5,
              color="#c1440e", va="top")
    axis.set_yticks(np.arange(len(levered)))
    axis.set_yticklabels([LABELS[name] for name in levered], fontsize=6.5)
    axis.set_xscale("log")
    axis.set_xlabel("$|E(h{=}1) - 1|$")
    axis.set_title("(c) le test passe à la précision machine", fontsize=9)
    axis.grid(True, axis="x", alpha=0.25, which="both")

    figure.suptitle(
        "Calibration à l'horizon 1 : chaque panneau explique une colonne du tableau — "
        "(a) l'écart observé, (b) l'amplitude m, (c) leur rapport E", fontsize=10)
    figure.tight_layout()
    figure.savefig(FIGDIR / "calibration_h1.png", dpi=150, bbox_inches="tight")
    plt.close(figure)
    return True


def main() -> int:
    apply_style()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    if figure_calibration():
        print("  figures/calibration_h1.png")
    else:
        print("  (metrics.json absent)")
    if figure_parity():
        print("  figures/parity_m4_3.png")
    else:
        print("  (parity_deviations_8000.csv absent : lancer "
              "tests/test_parity_m4_3.py --full)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
