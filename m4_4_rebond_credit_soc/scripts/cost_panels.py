"""Porte du lot A — MESURER le prix de l'instrumentation, avant de le choisir.

Le plan §8 (décision 4) refuse qu'on fixe le pas d'échantillonnage `k` des
panneaux par goût : « à mesurer, pas à choisir ». Le §4.2 exige la même chose
de l'empreinte disque. Ce script produit les deux, dans le RÉGIME DE LA
CAMPAGNE — même amorçage à t₀ = 2000, même fenêtre de 2000 pas — et non sur
un run jouet où la population serait dix fois plus petite.

Quatre cellules, même graine, même amorçage, branchées sur le même snapshot :

| cellule | drapeaux |
|---|---|
| `nu` | aucun — c'est la référence de coût, celle des 153 runs de v2 |
| `events` | décès + avalanches + arêtes de perte |
| `panels_k1` | idem + un panneau à CHAQUE pas |
| `panels_k10` | idem + un panneau tous les 10 pas |

Ce qu'on en tire : le surcoût des événements, le surcoût d'un panneau (par
différence entre k=1 et k=10, donc sans supposer que le reste est gratuit),
l'octet par panneau et par run, et la taille d'un checkpoint avec et sans
les listes d'événements.

Sorties : `results/analysis/lotA_cost.csv` (une ligne par cellule et par
fichier) et `results/analysis/lotA_cost.json` (les dérivées).

    python3 scripts/cost_panels.py [--seed 0] [--t0 2000] [--window 2000]
"""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from m4_4.live import load_snapshot, save_snapshot, write_series  # noqa: E402
from m4_4.model import Config, Simulation  # noqa: E402

ANALYSIS = ROOT / "results" / "analysis"
PILOT = ROOT / "results" / "cost_panels"

#: Régime de la campagne (`scripts/campaign.py`, BASE).
BASE = dict(gamma=0.5, A=1.0, lam=30.0, delta=0.01, sigma=0.01, K0=25.0,
            pop_max=30_000, rate_rule="marginal", kernel_policy="exact_lut")

CELLS = {
    "nu": {},
    "events": dict(record_deaths=True, record_avalanches=True, record_loss_edges=True),
    "panels_k1": dict(record_deaths=True, record_avalanches=True,
                      record_loss_edges=True, panel_every=1),
    "panels_k10": dict(record_deaths=True, record_avalanches=True,
                       record_loss_edges=True, panel_every=10),
    # Le coefficient de Gini du bassin de marché, à chaque pas : c'est la
    # sonde par laquelle le plan §3.1 exige que Ḡ soit mesuré
    # INDÉPENDAMMENT de la rotation (le déduire de `rotation = ρ·Ḡ` referait
    # une identité). Elle trie la population à chaque pas, donc O(N log N) —
    # d'où la mesure séparée.
    "market": dict(record_deaths=True, record_avalanches=True,
                   record_loss_edges=True, panel_every=10,
                   record_market_stats=True),
}


def burn(seed: int, t0: int) -> Path:
    """Amorçage NON instrumenté, partagé par les quatre cellules."""
    snapshot = PILOT / f"burn_seed{seed}_t{t0}.pkl"
    if snapshot.exists():
        return snapshot
    started = time.time()
    simulation = Simulation(Config(**BASE, seed=seed, T=t0))
    simulation.run()
    save_snapshot(simulation, snapshot)
    print(f"# amorçage seed={seed} jusqu'à t={t0} : {time.time() - started:.0f} s, "
          f"{simulation.series[-1]['pop']} entités", flush=True)
    return snapshot


def run_cell(job: tuple[str, Path, int, int, int]) -> dict:
    name, snapshot, seed, t0, window = job
    directory = PILOT / name
    if directory.exists():
        shutil.rmtree(directory)
    config = Config(**BASE, **CELLS[name], seed=seed, T=t0 + window)
    simulation = load_snapshot(snapshot, config=config)
    started = time.time()
    while simulation.t < config.T and simulation.status == "ok":
        simulation.step()
    wall = time.time() - started

    started = time.time()
    write_series(simulation, directory)
    wall_write = time.time() - started

    full = save_snapshot(simulation, directory / "checkpoint_full.pkl", records=True)
    light = save_snapshot(simulation, directory / "checkpoint_light.pkl", records=False)

    sizes = {
        path.name: path.stat().st_size
        for path in sorted(directory.iterdir())
        if path.is_file()
    }
    return {
        "cell": name,
        "seed": seed,
        "steps": window,
        "panel_every": config.panel_every,
        "n_panels": len(simulation.panels),
        "n_deaths": len(simulation.deaths),
        "n_avalanches": len(simulation.avalanches),
        "n_loss_edges": len(simulation.loss_edges),
        "pop_final": simulation.series[-1]["pop"],
        "wall_seconds": wall,
        "wall_write_seconds": wall_write,
        "checkpoint_full_bytes": full.stat().st_size,
        "checkpoint_light_bytes": light.stat().st_size,
        "sizes": sizes,
        "total_bytes": sum(
            size for name_, size in sizes.items() if not name_.startswith("checkpoint_")
        ),
    }


def derive(rows: list[dict], window: int, n_runs: int) -> dict:
    """Les dérivées : surcoût des événements, prix d'un panneau, empreinte."""
    by_cell = {row["cell"]: row for row in rows}
    nu = by_cell["nu"]["wall_seconds"]
    events = by_cell["events"]["wall_seconds"]
    k1, k10 = by_cell["panels_k1"], by_cell["panels_k10"]
    # Le prix d'UN panneau, par différence entre deux cellules qui ne
    # diffèrent QUE par le nombre de panneaux : tout le reste s'annule.
    panel_seconds = (k1["wall_seconds"] - k10["wall_seconds"]) / (
        k1["n_panels"] - k10["n_panels"]
    )
    panel_bytes = (
        k1["sizes"].get("panels.npz", 0) - k10["sizes"].get("panels.npz", 0)
    ) / (k1["n_panels"] - k10["n_panels"])
    events_bytes = by_cell["events"]["total_bytes"] - by_cell["nu"]["total_bytes"]
    market = by_cell.get("market")
    market_overhead = (
        market["wall_seconds"] / k10["wall_seconds"] - 1.0 if market else None
    )
    return {
        "window": window,
        "n_runs_campagne": n_runs,
        "wall_nu_seconds": nu,
        "wall_events_seconds": events,
        "events_overhead_share": events / nu - 1.0,
        "events_bytes_per_run": events_bytes,
        "panel_seconds": panel_seconds,
        "panel_bytes": panel_bytes,
        "panel_pop": k1["pop_final"],
        # Surcoût de la sonde de Gini, à instrumentation ÉGALE par ailleurs
        # (`market` et `panels_k10` ne diffèrent que par elle).
        "market_stats_overhead_share": market_overhead,
        "market_stats_bytes": (
            market["sizes"].get("market_stats.csv", 0) if market else None
        ),
        "budget": {
            f"k={k}": {
                "n_panels_par_run": window // k,
                "surcout_seconds_par_run": panel_seconds * (window // k),
                "octets_par_run": panel_bytes * (window // k) + events_bytes,
                "gio_campagne": (panel_bytes * (window // k) + events_bytes)
                * n_runs / 2**30,
            }
            for k in (1, 2, 5, 10, 20, 25, 50)
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--t0", type=int, default=2000)
    parser.add_argument("--window", type=int, default=2000)
    parser.add_argument("--runs", type=int, default=96,
                        help="taille de la campagne visée, pour l'empreinte totale")
    args = parser.parse_args(argv[1:])

    PILOT.mkdir(parents=True, exist_ok=True)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    snapshot = burn(args.seed, args.t0)

    jobs = [(name, snapshot, args.seed, args.t0, args.window) for name in CELLS]
    started = time.time()
    with mp.Pool(processes=len(jobs)) as pool:
        rows = list(pool.imap_unordered(run_cell, jobs))
    rows.sort(key=lambda row: list(CELLS).index(row["cell"]))
    print(f"# {len(jobs)} cellules en {time.time() - started:.0f} s", flush=True)

    flat = []
    for row in rows:
        for filename, size in row["sizes"].items():
            flat.append({
                "cell": row["cell"], "panel_every": row["panel_every"],
                "n_panels": row["n_panels"], "wall_seconds": round(row["wall_seconds"], 2),
                "file": filename, "bytes": size,
            })
    with open(ANALYSIS / "lotA_cost.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)

    payload = {"cells": rows, "derived": derive(rows, args.window, args.runs)}
    (ANALYSIS / "lotA_cost.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(payload["derived"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
