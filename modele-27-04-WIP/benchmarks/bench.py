"""
bench.py — Protocole de benchmark reproductible.

Mesure pour chaque (taille, seed) :
  - temps total de simulation (perf_counter)
  - temps moyen par pas
  - n entités vivantes (final)
  - n prêts actifs (final)
  - n faillites cumulées
  - n transactions de crédit cumulées
  - len(entities) et len(loans) (taille brute des dicts dynamiques)
  - mémoire pic (via tracemalloc) si --memory

Trois tailles : court (200 pas), moyen (1000 pas), long (3000 pas).
Plusieurs seeds : 42, 7, 123.

Usage :
    python -m modele-27-04-WIP.benchmarks.bench
ou direct :
    /home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/benchmarks/bench.py [--target wip|orig] [--quick] [--memory]

`--target wip` (défaut) lance modele-27-04-WIP/src ;
`--target orig` lance Modèle_sans_banque_wip/src  pour comparaison directe.
"""

from __future__ import annotations

import argparse
import gc
import importlib
import importlib.util
import os
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIP_SRC = ROOT / "modele-27-04-WIP" / "src"
ORIG_SRC = ROOT / "Modèle_sans_banque_wip" / "src"


def _load_modules(src_dir: Path):
    """
    Importe config / models / statistics / simulation depuis `src_dir` en
    isolant les modules sous des noms uniques pour éviter les collisions
    entre les deux versions.
    """
    tag = "wip" if "modele-27-04-WIP" in str(src_dir) else "orig"
    sys.path.insert(0, str(src_dir))
    try:
        for purge in ("config", "models", "statistics", "simulation"):
            sys.modules.pop(purge, None)
            sys.modules.pop(f"{purge}_{tag}", None)
        config = importlib.import_module("config")
        models = importlib.import_module("models")
        statistics = importlib.import_module("statistics")
        simulation = importlib.import_module("simulation")
    finally:
        sys.path.remove(str(src_dir))
    return config, models, statistics, simulation


def run_one(src_dir: Path, n_steps: int, seed: int, measure_memory: bool = False):
    """Lance une simulation et retourne un dict de mesures."""
    config_m, _models_m, _stats_m, sim_m = _load_modules(src_dir)
    cfg = config_m.SimulationConfig(duree_simulation=n_steps, seed=seed)

    gc.collect()
    if measure_memory:
        tracemalloc.start()

    t0 = time.perf_counter()
    sim = sim_m.Simulation(cfg)
    sim.run(verbose=False)
    elapsed = time.perf_counter() - t0

    peak_mb = None
    if measure_memory:
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / (1024 * 1024)

    last = sim.stats[-1] if sim.stats else {}
    result = {
        "n_steps": n_steps,
        "seed": seed,
        "elapsed_s": elapsed,
        "ms_per_step": 1000.0 * elapsed / max(1, n_steps),
        "n_entities_alive_final": last.get("n_entities_alive", 0),
        "n_entities_total": len(sim.entities),
        "n_active_loans_final": last.get("n_prets_actifs", 0),
        "n_loans_total": len(sim.loans),
        "n_failures_total": sum(s["n_failures"] for s in sim.stats),
        "n_transactions_total": sum(s["credit_transactions"] for s in sim.stats),
        "actif_total_systeme_final": last.get("actif_total_systeme", 0.0),
        "passif_total_systeme_final": last.get("passif_total_systeme", 0.0),
        "peak_memory_mb": peak_mb,
    }
    return result


SIZES = {
    "court": 200,
    "moyen": 1000,
    "long": 3000,
}
SEEDS = [42, 7, 123]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=["wip", "orig"], default="wip")
    p.add_argument("--quick", action="store_true",
                   help="Seulement la taille `court` × 1 seed")
    p.add_argument("--memory", action="store_true",
                   help="Active tracemalloc (overhead non-trivial)")
    p.add_argument("--sizes", nargs="*",
                   help="Liste de tailles à tester parmi court/moyen/long")
    p.add_argument("--seeds", nargs="*", type=int,
                   help="Liste de seeds à tester")
    return p.parse_args()


def main():
    args = parse_args()
    src = WIP_SRC if args.target == "wip" else ORIG_SRC
    print(f"# benchmark target = {args.target} ({src})")

    sizes = args.sizes or (["court"] if args.quick else list(SIZES.keys()))
    seeds = args.seeds or ([42] if args.quick else SEEDS)

    header = (
        f"{'size':<6} {'seed':>5} {'n_steps':>7} {'elapsed_s':>10} {'ms/step':>9} "
        f"{'alive':>6} {'tot_e':>6} {'loans':>7} {'tot_l':>7} {'fail':>6} {'tx':>6} "
        f"{'memMB':>7}"
    )
    print(header)
    print("-" * len(header))

    results = []
    for size in sizes:
        n_steps = SIZES[size]
        for seed in seeds:
            r = run_one(src, n_steps=n_steps, seed=seed, measure_memory=args.memory)
            results.append((size, r))
            mem = f"{r['peak_memory_mb']:7.1f}" if r["peak_memory_mb"] else "      -"
            print(
                f"{size:<6} {seed:>5} {r['n_steps']:>7} "
                f"{r['elapsed_s']:>10.3f} {r['ms_per_step']:>9.3f} "
                f"{r['n_entities_alive_final']:>6} {r['n_entities_total']:>6} "
                f"{r['n_active_loans_final']:>7} {r['n_loans_total']:>7} "
                f"{r['n_failures_total']:>6} {r['n_transactions_total']:>6} "
                f"{mem}"
            )
    return results


if __name__ == "__main__":
    main()
