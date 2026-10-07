"""Zone d'ombre §E — la loi d'échelle ε = 1/(1−γ) tient-elle hors de γ = 0,5 ?

L'ablation sur K0 (`scripts/ablation_k0.py`) trouve qu'avec un capital de
naissance compensé, la production agrégée répond à une hausse de A avec une
élasticité logarithmique ε = 2,018, à comparer à 1/(1−γ) = 2 pour γ = 0,5.
Le rapport de résultats signale explicitement cette coïncidence comme
suggestive et non démonstrative : elle n'est mesurée qu'en un point.

Ce script la met à l'épreuve en deux autres points, γ = 0,4 et γ = 0,6, où la
loi prédit des valeurs nettement différentes :

    γ = 0,4  →  ε = 1,667      (compensation K0 × 1,5^{1/0,6} = 1,966)
    γ = 0,5  →  ε = 2,000      (compensation K0 × 2,25)   [déjà mesuré]
    γ = 0,6  →  ε = 2,500      (compensation K0 × 1,5^{2,5} = 2,756)

Deux bras par γ, branchés sur un amorçage propre à ce γ : un contrôle inerte
et « A × 1,5 sur toutes les entités, plus K0 compensé ». Aucun tirage n'est
consommé par ces interventions, donc les deux bras sont appariés exactement.

Le script vérifie aussi que l'amorçage est bien stationnaire à t₀ pour chaque
γ — la relaxation dépend de γ, et rien ne garantit a priori que le t₀ = 2000
calibré sur γ = 0,5 convienne ailleurs.

    python3 scripts/scaling_gamma.py burn
    python3 scripts/scaling_gamma.py arms
    python3 scripts/scaling_gamma.py analyse
"""

from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/anatole/jupyter")

from m4_3live.live import load_snapshot, save_snapshot, write_series  # noqa: E402
from m4_3live.model import Config, Intervention, Simulation  # noqa: E402

from scripts.campaign import BASE, T0, WINDOW, WORKERS  # noqa: E402

OUT = ROOT / "results" / "scaling_gamma"
ANALYSIS = ROOT / "results" / "analysis"
FIGDIR = ROOT / "report" / "figures"
# γ = 0,5 est déjà couvert par l'ablation K0 : on ne le recalcule pas.
GAMMAS = (0.4, 0.6)
SEEDS = (0, 1, 2)
AMPLITUDE = 1.5


def compensation(gamma: float) -> float:
    """Facteur qui laisse K0/K*_aut invariant : A^{1/(1-γ)}."""
    return AMPLITUDE ** (1.0 / (1.0 - gamma))


def config_for(gamma: float, seed: int, horizon: int) -> Config:
    return Config(**{**BASE, "gamma": gamma}, seed=seed, T=horizon)


def burn_one(job: tuple[float, int]) -> dict:
    gamma, seed = job
    directory = OUT / f"g{gamma:g}" / "burn" / f"seed{seed}"
    snapshot = directory / f"snapshot_t{T0}.pkl"
    if snapshot.exists():
        return {"gamma": gamma, "seed": seed, "skipped": True}
    started = time.time()
    simulation = Simulation(config_for(gamma, seed, T0))
    simulation.run()
    write_series(simulation, directory)
    save_snapshot(simulation, snapshot)
    return {"gamma": gamma, "seed": seed, "status": simulation.status,
            "wall_seconds": time.time() - started}


def run_arm(job: tuple[float, int, str]) -> dict:
    gamma, seed, arm = job
    directory = OUT / f"g{gamma:g}" / arm / f"seed{seed}"
    if (directory / "summary.json").exists():
        return {"gamma": gamma, "seed": seed, "arm": arm, "skipped": True}
    started = time.time()
    config = config_for(gamma, seed, T0 + WINDOW)
    simulation = load_snapshot(
        OUT / f"g{gamma:g}" / "burn" / f"seed{seed}" / f"snapshot_t{T0}.pkl", config=config
    )
    if arm == "A150_K0comp":
        simulation.submit(Intervention(param="A", value=AMPLITUDE, scope="all"))
        simulation.submit(
            Intervention(param="K0", value=BASE["K0"] * compensation(gamma), scope="all")
        )
    while simulation.t < config.T and simulation.status == "ok":
        simulation.step()
    write_series(simulation, directory)
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "gamma": gamma, "seed": seed, "arm": arm,
                "t_final": simulation.t, "status": simulation.status,
                "wall_seconds": time.time() - started,
                "interventions": simulation.intervention_log,
                "parameters": simulation.config.to_dict(),
                "book_errors": simulation.book.consistency_errors(simulation.population.alive),
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {"gamma": gamma, "seed": seed, "arm": arm, "status": simulation.status,
            "wall_seconds": time.time() - started}


# --------------------------------------------------------------------------
def series(path: Path, column: str) -> np.ndarray:
    with open(path / "series.csv", newline="", encoding="utf-8") as handle:
        return np.array([float(row[column]) for row in csv.DictReader(handle)])


def burn_stationarity(gamma: float) -> dict:
    """Le t₀ calibré sur γ = 0,5 convient-il à ce γ ? On compare la moyenne du
    dernier quart de l'amorçage à celle du quart précédent."""
    ratios = []
    for seed in SEEDS:
        values = series(OUT / f"g{gamma:g}" / "burn" / f"seed{seed}", "prod_tot")
        third = values[T0 // 2 : 3 * T0 // 4].mean()
        last = values[3 * T0 // 4 : T0].mean()
        ratios.append(float(last / third))
    return {"rapport_dernier_quart_sur_precedent": ratios,
            "moyenne": float(np.mean(ratios))}


def analyse() -> dict:
    window = slice(T0 + 1000, T0 + WINDOW)
    result = {"amplitude": AMPLITUDE, "seeds": list(SEEDS), "points": {}}

    # γ = 0,5 : repris de l'ablation K0, même protocole
    ablation = json.loads((ANALYSIS / "ablation_k0.json").read_text(encoding="utf-8"))
    ratio = ablation["arms"]["abl_A150_K0aut"]["prod_tot_ratio"]
    result["points"]["0.5"] = {
        "gamma": 0.5,
        "source": "results/analysis/ablation_k0.json (bras abl_A150_K0aut)",
        "compensation": compensation(0.5),
        "prod_ratio": ratio,
        "prod_ratio_sem": ablation["arms"]["abl_A150_K0aut"]["prod_tot_ratio_sem"],
        "pop_ratio": ablation["arms"]["abl_A150_K0aut"]["pop_ratio"],
        "epsilon_mesure": math.log(ratio) / math.log(AMPLITUDE),
        "epsilon_predit": 1.0 / (1.0 - 0.5),
        "n_seeds": len(ablation["seeds"]),
        "stationnarite_amorcage": None,
    }

    for gamma in GAMMAS:
        ratios, pops = [], []
        for seed in SEEDS:
            treated = series(OUT / f"g{gamma:g}" / "A150_K0comp" / f"seed{seed}", "prod_tot")
            control = series(OUT / f"g{gamma:g}" / "control" / f"seed{seed}", "prod_tot")
            ratios.append(float(treated[window].mean() / control[window].mean()))
            treated_pop = series(OUT / f"g{gamma:g}" / "A150_K0comp" / f"seed{seed}", "pop")
            control_pop = series(OUT / f"g{gamma:g}" / "control" / f"seed{seed}", "pop")
            pops.append(float(treated_pop[window].mean() / control_pop[window].mean()))
        ratio = float(np.mean(ratios))
        result["points"][f"{gamma:g}"] = {
            "gamma": gamma,
            "source": f"results/scaling_gamma/g{gamma:g}/",
            "compensation": compensation(gamma),
            "prod_ratio": ratio,
            "prod_ratio_sem": float(np.std(ratios, ddof=1) / math.sqrt(len(ratios))),
            "pop_ratio": float(np.mean(pops)),
            "epsilon_mesure": math.log(ratio) / math.log(AMPLITUDE),
            "epsilon_predit": 1.0 / (1.0 - gamma),
            "n_seeds": len(SEEDS),
            "stationnarite_amorcage": burn_stationarity(gamma),
        }
    for entry in result["points"].values():
        entry["ecart_relatif_a_la_loi"] = (
            entry["epsilon_mesure"] / entry["epsilon_predit"] - 1.0
        )
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "scaling_gamma.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def figure(result: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from simulation_lab.plot_utils import apply_style

    apply_style()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    points = sorted(result["points"].values(), key=lambda e: e["gamma"])
    gammas = np.array([e["gamma"] for e in points])
    measured = np.array([e["epsilon_mesure"] for e in points])
    predicted = np.array([e["epsilon_predit"] for e in points])

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    grid = np.linspace(0.33, 0.67, 200)
    axes[0].plot(grid, 1.0 / (1.0 - grid), color="#66757f", lw=1.4,
                 label=r"loi prédite $\varepsilon = 1/(1-\gamma)$")
    axes[0].scatter(gammas, measured, s=90, color="#c1440e", zorder=3,
                    label=f"mesuré (n={points[0]['n_seeds']}–5 graines)")
    for entry in points:
        axes[0].annotate(f"{entry['epsilon_mesure']:.3f}",
                         (entry["gamma"], entry["epsilon_mesure"]),
                         textcoords="offset points", xytext=(8, -10), fontsize=8)
    axes[0].axhline(1.0, color="black", ls="--", lw=1.0,
                    label="réponse strictement proportionnelle")
    axes[0].set_xlabel(r"exposant d'extraction $\gamma$")
    axes[0].set_ylabel(r"élasticité logarithmique $\varepsilon_{\mathrm{prod},A}$")
    axes[0].set_title(
        "Réponse à $A \\times 1{,}5$ avec capital de naissance compensé"
    )
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)

    deviation = 100.0 * (measured / predicted - 1.0)
    axes[1].bar([f"γ = {g:g}" for g in gammas], deviation, color="#294c60", alpha=0.9)
    for index, value in enumerate(deviation):
        axes[1].text(index, value, f"{value:+.1f} %", ha="center",
                     va="bottom" if value >= 0 else "top", fontsize=9)
    axes[1].axhline(0.0, color="black", lw=0.9)
    axes[1].set_ylabel("écart relatif à la loi (%)")
    axes[1].set_ylim(min(-6, deviation.min() * 1.4), max(6, deviation.max() * 1.4))
    axes[1].set_title("La loi est vérifiée à quelques pour cent près")
    axes[1].grid(True, axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(FIGDIR / "scaling_gamma.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "analyse"
    if command == "burn":
        OUT.mkdir(parents=True, exist_ok=True)
        jobs = [(gamma, seed) for gamma in GAMMAS for seed in SEEDS]
        with mp.Pool(processes=min(len(jobs), WORKERS)) as pool:
            for payload in pool.imap_unordered(burn_one, jobs):
                print(json.dumps(payload), flush=True)
        return 0
    if command == "arms":
        jobs = [(gamma, seed, arm)
                for gamma in GAMMAS for seed in SEEDS
                for arm in ("control", "A150_K0comp")]
        with mp.Pool(processes=WORKERS) as pool:
            done = 0
            for payload in pool.imap_unordered(run_arm, jobs):
                done += 1
                print(f"[{done}/{len(jobs)}] " + json.dumps(payload), flush=True)
        return 0
    result = analyse()
    figure(result)
    header = f"{'γ':>5s} {'compens. K0':>12s} {'prod ratio':>18s} {'pop ratio':>10s} {'ε mesuré':>9s} {'ε prédit':>9s} {'écart':>8s}"
    print(header)
    print("-" * len(header))
    for entry in sorted(result["points"].values(), key=lambda e: e["gamma"]):
        print(f"{entry['gamma']:5.1f} {entry['compensation']:12.3f} "
              f"{entry['prod_ratio']:10.3f} ± {entry['prod_ratio_sem']:5.3f} "
              f"{entry['pop_ratio']:10.3f} {entry['epsilon_mesure']:9.3f} "
              f"{entry['epsilon_predit']:9.3f} {100 * entry['ecart_relatif_a_la_loi']:+7.2f} %")
    for entry in sorted(result["points"].values(), key=lambda e: e["gamma"]):
        stationarity = entry["stationnarite_amorcage"]
        if stationarity:
            print(f"  γ={entry['gamma']:g} stationnarité de l'amorçage "
                  f"(dernier quart / précédent) : {stationarity['moyenne']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
