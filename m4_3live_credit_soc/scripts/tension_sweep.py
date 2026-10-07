"""La tension est-elle un paramètre d'état ? — balayage à trois leviers.

QUESTION. L'ablation K0 a produit quatre niveaux de tension seulement, tous
obtenus en bougeant `A` et `K0`. La relation mortalité ↔ tension y est nette
(∝ T^0,62, R² = 0,99), mais quatre points ne font pas une loi, et rien ne dit
que la relation ne dépend pas du levier employé.

PLAN. Trois leviers indépendants, appliqués au même t₀ = 2000 sur les mêmes
snapshots d'amorçage que la campagne §7, donc directement comparables :

  * `K0` seul       — le capital de naissance, de 3 à 400 (base 25).
  * `delta` seul    — la dépréciation, de 0,005 à 0,04 (base 0,01). Elle entre
                      DANS la définition de K_aut = [A(1-δ)/δ]^{1/(1-γ)}
                      autant que dans la dynamique : c'est le levier le plus
                      exigeant pour la thèse.
  * `A` seul        — déjà couvert par la campagne et l'ablation, repris ici
                      pour deux valeurs supplémentaires.

VERDICT ATTENDU. Si la tension est un paramètre d'état, les points des trois
leviers tombent sur UNE courbe dans le plan (tension, mortalité). Sinon, ils
se séparent par levier — et la tension n'est qu'un indicateur parmi d'autres.

Aucune modification du moteur : ce script ne fait que le piloter.

    python3 scripts/tension_sweep.py run
    python3 scripts/tension_sweep.py analyse
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/anatole/jupyter")

from m4_3live.live import load_snapshot, write_series  # noqa: E402
from m4_3live.model import Config, Intervention  # noqa: E402

from scripts.campaign import BASE, T0, WINDOW, WORKERS  # noqa: E402

OUT = ROOT / "results" / "tension_sweep"
BURN = ROOT / "results" / "campaign" / "burn"

SEEDS = (0, 1, 2)

K0_VALUES = (3.0, 6.25, 12.5, 56.25, 125.0, 400.0)
DELTA_VALUES = (0.005, 0.02, 0.04)
A_VALUES = (0.75, 1.25, 2.0)


def step(**kwargs) -> dict:
    payload = {"t": T0 + 1, "note": ""}
    payload.update(kwargs)
    return payload


def build_arms() -> dict[str, list[dict]]:
    arms: dict[str, list[dict]] = {"sweep_control": []}
    for value in K0_VALUES:
        arms[f"K0_{value:g}"] = [step(param="K0", value=value, scope="all")]
    for value in DELTA_VALUES:
        arms[f"delta_{value:g}"] = [step(param="delta", value=value, scope="all")]
    for value in A_VALUES:
        arms[f"A_{value:g}"] = [step(param="A", value=value, scope="all")]
    return arms


ARMS = build_arms()

LEVER = {}
for name in ARMS:
    LEVER[name] = ("contrôle" if name == "sweep_control" else name.split("_")[0])


def run_arm(job: tuple[int, str]) -> dict:
    seed, arm = job
    directory = OUT / arm / f"seed{seed}"
    if (directory / "summary.json").exists():
        return {"seed": seed, "arm": arm, "skipped": True}
    started = time.time()
    config = Config(**BASE, seed=seed, T=T0 + WINDOW)
    simulation = load_snapshot(BURN / f"seed{seed}" / f"snapshot_t{T0}.pkl", config=config)
    planned: dict[int, list[Intervention]] = {}
    for entry in ARMS[arm]:
        planned.setdefault(int(entry["t"]), []).append(Intervention.from_dict(entry))
    while simulation.t < config.T and simulation.status == "ok":
        for item in planned.get(simulation.t + 1, ()):
            simulation.submit(item)
        simulation.step()
    write_series(simulation, directory)
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "seed": seed,
                "arm": arm,
                "lever": LEVER[arm],
                "t_final": simulation.t,
                "status": simulation.status,
                "wall_seconds": time.time() - started,
                "plan": ARMS[arm],
                "interventions": simulation.intervention_log,
                "parameters": simulation.config.to_dict(),
                "book_errors": simulation.book.consistency_errors(simulation.population.alive),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    from scripts.tension_figures import plot_tension

    plot_tension(directory, simulation.config.delta)
    return {"seed": seed, "arm": arm, "status": simulation.status,
            "wall_seconds": round(time.time() - started, 1)}


def main(argv: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(seed, arm) for arm in ARMS for seed in SEEDS]
    started = time.time()
    with mp.Pool(processes=WORKERS) as pool:
        done = 0
        for payload in pool.imap_unordered(run_arm, jobs):
            done += 1
            print(f"[{done}/{len(jobs)}] " + json.dumps(payload), flush=True)
    print(f"# balayage terminé en {time.time() - started:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
