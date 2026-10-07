"""Figures des deux faits du rapport de résultats qui n'en avaient pas.

1. La justification de $t_0$ et de la fenêtre $W$. Elle repose entièrement
   sur des résultats DÉJÀ sur disque (le prompt interdit de remesurer la
   relaxation) : les trois graines baseline de M4.3 et leur `t_converge`.
   La figure montre ce que le texte affirme — que `prod_tot` est stationnaire
   par blocs bien avant $t_0$ — et d'où vient le temps d'autocorrélation qui
   dimensionne la fenêtre.

2. La réfutation de l'explication par le service d'intérêts. Le service
   monte si on le rapporte au CAPITAL et baisse si on le rapporte à la
   PRODUCTION ; c'est le second dénominateur qui décide si une entité peut
   payer. La figure met les deux côte à côte, parce que c'est précisément
   la confusion de dénominateur qui avait produit une inférence fausse.

    python3 scripts/protocol_figures.py
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

from scripts.campaign import SEEDS, T0, WINDOW  # noqa: E402

FIGDIR = ROOT / "report" / "figures"
OUT = ROOT / "results" / "analysis"
ARMS = ROOT / "results" / "campaign" / "arms"
BASELINE_RUNS = ("m4_3__d1__baseline__seed0", "m4_3__d1__baseline__seed1",
                 "m4_3__d1__baseline__seed2")
BLOCK = 500


def stored_series(run_id: str, column: str = "prod_tot") -> np.ndarray:
    storage = RunStorage()
    with open(Path(storage.run_dir(run_id)) / "series.csv", newline="") as handle:
        return np.array([float(row[column]) for row in csv.DictReader(handle)])


def stored_converge(run_id: str) -> float:
    storage = RunStorage()
    path = Path(storage.run_dir(run_id)) / "analysis.json"
    return json.loads(path.read_text(encoding="utf-8"))["t_converge_int_in"]


def figure_window() -> dict:
    series = {run: stored_series(run) for run in BASELINE_RUNS}
    converge = {run: stored_converge(run) for run in BASELINE_RUNS}
    tail = np.concatenate([values[3000:] for values in series.values()])
    level = float(tail.mean())

    autocorrelation_times = []
    for values in series.values():
        centred = values[4000:] - values[4000:].mean()
        correlation = np.correlate(centred, centred, "full")[len(centred) - 1:]
        correlation /= correlation[0]
        cut = int(np.argmax(correlation < 0.05))
        autocorrelation_times.append(1.0 + 2.0 * correlation[1:cut + 1].sum())

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    colors = ("#294c60", "#c1440e", "#2e7d5b")
    for (run, values), color in zip(series.items(), colors):
        blocks = values[: (len(values) // BLOCK) * BLOCK].reshape(-1, BLOCK)
        centres = np.arange(len(blocks)) * BLOCK + BLOCK / 2
        axes[0].plot(centres, blocks.mean(axis=1), "o-", ms=3.5, color=color, lw=1.2,
                     label=f"{run.split('__')[-1]} (n={BLOCK} pas/bloc)")
        axes[0].axvline(converge[run], color=color, ls=":", lw=1.0)
    axes[0].axhline(level, color="black", ls="--", lw=1.0,
                    label=f"niveau de queue ({level:.0f})")
    axes[0].axvspan(0, 0, color="none")
    axes[0].axvline(T0, color="black", lw=2.0)
    axes[0].text(T0 * 1.03, level * 1.045, "$t_0 = 2000$", fontsize=9)
    axes[0].axvspan(T0, T0 + WINDOW, color="#294c60", alpha=0.07)
    axes[0].text(T0 + WINDOW / 2, level * 0.93, "fenêtre de mesure $W$", fontsize=8,
                 ha="center")
    axes[0].set_xlabel("t (pas)")
    axes[0].set_ylabel("prod_tot moyenné par blocs de 500 pas")
    axes[0].set_title("prod_tot est stationnaire bien avant $t_0$")
    axes[0].set_ylim(level * 0.9, level * 1.09)
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=7)
    axes[0].text(
        150, level * 0.915,
        "traits pointillés : $t_{\\mathrm{converge}}$ de la variable la plus lente\n"
        f"({', '.join(f'{converge[r]:.0f}' for r in BASELINE_RUNS)}), lu dans les\n"
        "analysis.json des runs M4.3 stockés",
        fontsize=6.5,
    )

    for (run, values), color in zip(series.items(), colors):
        centred = values[4000:] - values[4000:].mean()
        correlation = np.correlate(centred, centred, "full")[len(centred) - 1:]
        correlation /= correlation[0]
        axes[1].plot(np.arange(300), correlation[:300], color=color, lw=1.3,
                     label=run.split("__")[-1])
    axes[1].axhline(np.exp(-1.0), color="black", ls=":", lw=1.0, label="1/e")
    axes[1].axhline(0.0, color="black", lw=0.8)
    axes[1].set_xlabel("décalage (pas)")
    axes[1].set_ylabel("autocorrélation de prod_tot")
    axes[1].set_title(
        f"Temps d'autocorrélation intégré ≈ {np.mean(autocorrelation_times):.0f} pas "
        f"→ $W$ = {WINDOW} en vaut {WINDOW / np.mean(autocorrelation_times):.0f}"
    )
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=7)
    figure.suptitle(
        "Choix de $t_0$ et de la fenêtre, à partir des runs M4.3 déjà stockés "
        "(aucune relaxation remesurée)"
    )
    figure.tight_layout()
    figure.savefig(FIGDIR / "window_choice.png", dpi=150, bbox_inches="tight")
    plt.close(figure)
    payload = {
        "t_converge_int_in": converge,
        "niveau_queue": level,
        "temps_autocorrelation_integre": autocorrelation_times,
        "t0": T0,
        "W": WINDOW,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "window_choice.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def arm_matrix(arm: str, column: str) -> np.ndarray:
    out = []
    for seed in SEEDS:
        with open(ARMS / arm / f"seed{seed}" / "series.csv", newline="") as handle:
            rows = list(csv.DictReader(handle))
        out.append(np.array([float(row[column]) for row in rows])[T0 : T0 + WINDOW])
    return np.array(out)


def figure_service() -> dict:
    window = slice(1000, WINDOW)
    payload = {}
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    horizon = np.arange(1, WINDOW + 1)
    kernel = np.ones(101) / 101
    for arm, label, color in (("control", "contrôle", "#66757f"),
                              ("all_A150", "toutes, A×1,5", "#294c60")):
        interest = arm_matrix(arm, "interest_paid")
        capital = arm_matrix(arm, "K_tot")
        production = arm_matrix(arm, "prod_tot")
        for axis, values, title in (
            (axes[0], interest / capital, "service rapporté au CAPITAL"),
            (axes[1], interest / production, "service rapporté à la PRODUCTION"),
        ):
            mean = values.mean(axis=0)
            smoothed = np.convolve(np.pad(mean, 50, mode="edge"), kernel, mode="valid")[: mean.size]
            axis.plot(horizon, smoothed, color=color, lw=1.5, label=label)
            axis.set_title(title)
        payload[arm] = {
            "service_sur_capital": float((interest / capital)[:, window].mean()),
            "service_sur_production": float((interest / production)[:, window].mean()),
            "production_sur_capital": float((production / capital)[:, window].mean()),
        }
    ratio_capital = payload["all_A150"]["service_sur_capital"] / payload["control"]["service_sur_capital"]
    ratio_production = (
        payload["all_A150"]["service_sur_production"] / payload["control"]["service_sur_production"]
    )
    axes[0].set_ylabel("intérêts versés / K_tot")
    axes[0].text(0.03, 0.08, f"$\\times${ratio_capital:.3f} — le service semble s'alourdir",
                 transform=axes[0].transAxes, fontsize=9, color="#a73d3d")
    axes[1].set_ylabel("intérêts versés / prod_tot")
    axes[1].text(0.03, 0.08, f"$\\times${ratio_production:.3f} — le service s'allège en fait",
                 transform=axes[1].transAxes, fontsize=9, color="#2e7d5b")
    for axis in axes:
        axis.set_xlabel("horizon h après $t_0$ (pas)")
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=8)
    figure.suptitle(
        f"Le dénominateur décide de la conclusion (n={len(SEEDS)} graines, "
        "moyennes lissées sur 101 pas)"
    )
    figure.tight_layout()
    figure.savefig(FIGDIR / "service_denominator.png", dpi=150, bbox_inches="tight")
    plt.close(figure)
    payload["rapport_sur_capital"] = ratio_capital
    payload["rapport_sur_production"] = ratio_production
    (OUT / "service_denominator.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def main() -> int:
    apply_style()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    window = figure_window()
    print(f"  figures/window_choice.png — t_converge {window['t_converge_int_in']}")
    service = figure_service()
    print(f"  figures/service_denominator.png — service/K ×{service['rapport_sur_capital']:.3f}, "
          f"service/prod ×{service['rapport_sur_production']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
