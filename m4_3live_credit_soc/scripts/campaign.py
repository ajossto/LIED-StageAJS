"""Campagne §7 — contrôle apparié, plancher de bruit, bras de traitement.

PROTOCOLE (figé avant tout calcul, cf. report/rapport_final.pdf) :

- t₀ = 2000. Justification lue dans les résultats DÉJÀ sur disque, sans
  remesurer la relaxation (interdit par le prompt §7) : les trois graines
  baseline de M4.3 rapportent `t_converge_int_in` = 1016 / 948 / 841
  (`simulation_lab_data/runs/m4_3__d1__baseline__seed*/analysis.json`,
  estimateur de fenêtre adaptative de M4.3 sur sa variable la plus lente),
  et `prod_tot` lui-même est stationnaire par blocs de 500 dès t ≈ 500
  (moyennes de blocs comprises entre 31 300 et 32 100 sur les 3 graines).
  t₀ = 2000 laisse donc un facteur 2 sur la variable la plus lente.
- W = 2000 pas après t₀ : ≈ 2× la relaxation la plus lente et ≈ 38× le
  temps d'autocorrélation intégré de `prod_tot` (52 pas, mesuré sur la
  queue des mêmes séries stockées).
- 5 graines par cellule, amorçage PARTAGÉ : un seul run 0 → t₀ par graine,
  puis tous les bras branchés sur son snapshot (§4). Les bras d'une même
  graine sont donc rigoureusement identiques jusqu'à t₀.
- BRAS `null` : tire la fraction φ et n'applique rien (la valeur assignée
  est la valeur courante, donc `retech` est un no-op — mais le tirage
  consomme le générateur exactement comme un vrai traitement). Le contraste
  contrôle/null mesure le PLANCHER DE BRUIT dû au décalage de flux
  aléatoire ; sans lui, « effet rebond » et « les flux ont divergé » sont
  le même nombre.

Lancement :
    python3 scripts/campaign.py burn      # phase 1 (5 procs)
    python3 scripts/campaign.py arms      # phase 2 (6 procs)
    python3 scripts/campaign.py pilot-cap # pilote du plafond institutionnel
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from m4_3live.live import load_snapshot, save_snapshot, write_series  # noqa: E402
from m4_3live.model import Config, Intervention, Simulation  # noqa: E402

T0 = 2000
WINDOW = 2000
SEEDS = (0, 1, 2, 3, 4)
# 8 cœurs sur la machine cible, on en laisse 2 libres (mémoire du dépôt).
WORKERS = 6

BASE = dict(
    gamma=0.5,
    A=1.0,
    lam=30.0,
    delta=0.01,
    sigma=0.01,
    K0=25.0,
    pop_max=30_000,
    transfer_cap="optimum",
    rate_rule="marginal",
    kernel_policy="exact_lut",
)

RESULTS = ROOT / "results" / "campaign"
BURN_DIR = RESULTS / "burn"
ARM_DIR = RESULTS / "arms"


def intervention(**kwargs) -> dict:
    payload = {"t": T0 + 1, "note": ""}
    payload.update(kwargs)
    return payload


# Bras de la campagne. `A` est le levier PRIMAIRE (§1) ; le bras γ place
# délibérément les paires mixtes dans le régime (c) du noyau (§3.1), qui n'a
# pas de forme fermée — il exerce donc le chemin coûteux de l'institution.
ARMS: dict[str, list[dict]] = {
    "control": [],
    "null": [intervention(param="A", value=1.0, scope="fraction", phi=0.2)],
    "frac_A150_phi20": [intervention(param="A", value=1.5, scope="fraction", phi=0.2)],
    "frac_A125_phi20": [intervention(param="A", value=1.25, scope="fraction", phi=0.2)],
    "frac_A150_phi05": [intervention(param="A", value=1.5, scope="fraction", phi=0.05)],
    "frac_A150_phi50": [intervention(param="A", value=1.5, scope="fraction", phi=0.5)],
    "all_A150": [intervention(param="A", value=1.5, scope="all")],
    "new_A150": [intervention(param="A", value=1.5, scope="new")],
    "frac_g060_phi20": [intervention(param="gamma", value=0.6, scope="fraction", phi=0.2)],
}


def burn_one(seed: int) -> dict:
    directory = BURN_DIR / f"seed{seed}"
    snapshot = directory / f"snapshot_t{T0}.pkl"
    if snapshot.exists():
        return {"seed": seed, "skipped": True, "snapshot": str(snapshot)}
    started = time.time()
    simulation = Simulation(Config(**BASE, seed=seed, T=T0))
    simulation.run()
    write_series(simulation, directory)
    save_snapshot(simulation, snapshot)
    payload = {
        "seed": seed,
        "t": simulation.t,
        "status": simulation.status,
        "wall_seconds": time.time() - started,
        "snapshot": str(snapshot),
        "book_errors": simulation.book.consistency_errors(simulation.population.alive),
    }
    (directory / "burn.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def run_arm(job: tuple[int, str]) -> dict:
    seed, arm = job
    directory = ARM_DIR / arm / f"seed{seed}"
    marker = directory / "summary.json"
    if marker.exists():
        return {"seed": seed, "arm": arm, "skipped": True}
    started = time.time()
    snapshot = BURN_DIR / f"seed{seed}" / f"snapshot_t{T0}.pkl"
    simulation = load_snapshot(snapshot, config=Config(**BASE, seed=seed, T=T0 + WINDOW))
    planned: dict[int, list[Intervention]] = {}
    for entry in ARMS[arm]:
        planned.setdefault(int(entry["t"]), []).append(Intervention.from_dict(entry))
    while simulation.t < simulation.config.T and simulation.status == "ok":
        for item in planned.get(simulation.t + 1, ()):
            simulation.submit(item)
        simulation.step()
    write_series(simulation, directory)
    payload = {
        "seed": seed,
        "arm": arm,
        "t_final": simulation.t,
        "status": simulation.status,
        "wall_seconds": time.time() - started,
        "plan": ARMS[arm],
        "interventions": simulation.intervention_log,
        "kernel": simulation.kernel.describe(),
        "book_errors": simulation.book.consistency_errors(simulation.population.alive),
        "parameters": simulation.config.to_dict(),
    }
    if simulation.intervention_log:
        with open(directory / "interventions.jsonl", "w", encoding="utf-8") as handle:
            for entry in simulation.intervention_log:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    marker.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "seed": seed,
        "arm": arm,
        "status": simulation.status,
        "wall_seconds": payload["wall_seconds"],
    }


def pilot_cap(seed: int = 0, steps: int = 600) -> dict:
    """Pilote du choix institutionnel de plafond (§3.2, §11).

    Le plafond ne peut PAS être piloté sur le contrôle : en régime homogène
    λ* = 1/2, donc l'optimum et l'égalisation coïncident exactement. On le
    pilote sur un bras TRAITÉ, et on lit la liquidité (`roots_liquidity`),
    pas seulement l'extinction.
    """
    out = {}
    for cap in ("optimum", "equalization"):
        config = Config(**{**BASE, "transfer_cap": cap}, seed=seed, T=T0 + steps)
        simulation = load_snapshot(BURN_DIR / f"seed{seed}" / f"snapshot_t{T0}.pkl", config=config)
        simulation.submit(Intervention(param="A", value=1.5, scope="fraction", phi=0.2))
        while simulation.t < config.T and simulation.status == "ok":
            simulation.step()
        window = simulation.series[T0:]
        out[cap] = {
            "status": simulation.status,
            "prod_mean": sum(row["prod_tot"] for row in window) / len(window),
            "pop_final": window[-1]["pop"],
            "roots_liquidity": sum(row["roots_liquidity"] for row in window),
            "roots_insolvency": sum(row["roots_insolvency"] for row in window),
            "deaths": sum(row["deaths"] for row in window),
            "loan_volume": sum(row["loan_volume"] for row in window),
            "blocked_dir": sum(row["mkt_blocked_dir"] for row in window),
            "capped": sum(row["mkt_capped"] for row in window),
            "surplus": sum(row["mkt_surplus"] for row in window),
        }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "pilot_cap.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return out


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "all"
    if command in {"burn", "all"}:
        BURN_DIR.mkdir(parents=True, exist_ok=True)
        started = time.time()
        with mp.Pool(processes=min(len(SEEDS), WORKERS)) as pool:
            for payload in pool.imap_unordered(burn_one, SEEDS):
                print(json.dumps(payload), flush=True)
        print(f"# amorçages terminés en {time.time() - started:.0f} s", flush=True)
    if command in {"pilot-cap"}:
        print(json.dumps(pilot_cap(), indent=2, ensure_ascii=False))
    if command in {"arms", "all"}:
        ARM_DIR.mkdir(parents=True, exist_ok=True)
        jobs = [(seed, arm) for arm in ARMS for seed in SEEDS]
        started = time.time()
        with mp.Pool(processes=WORKERS) as pool:
            done = 0
            for payload in pool.imap_unordered(run_arm, jobs):
                done += 1
                print(f"[{done}/{len(jobs)}] " + json.dumps(payload), flush=True)
        print(f"# bras terminés en {time.time() - started:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
