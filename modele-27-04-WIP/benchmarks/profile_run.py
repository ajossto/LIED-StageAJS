"""
profile_run.py — Lance un cProfile sur la simulation puis dump le top des
fonctions par cumtime / tottime / ncalls.

Usage :
    /home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/benchmarks/profile_run.py \
        [--target wip|orig] [--n-steps 1000] [--seed 42] \
        [--top 30] [--out modele-27-04-WIP/profiling/run.prof]
"""

from __future__ import annotations

import argparse
import cProfile
import importlib
import io
import pstats
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIP_SRC = ROOT / "modele-27-04-WIP" / "src"
ORIG_SRC = ROOT / "Modèle_sans_banque_wip" / "src"


def _load(src_dir: Path):
    sys.path.insert(0, str(src_dir))
    try:
        for purge in ("config", "models", "statistics", "simulation"):
            sys.modules.pop(purge, None)
        config = importlib.import_module("config")
        simulation = importlib.import_module("simulation")
    finally:
        sys.path.remove(str(src_dir))
    return config, simulation


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=["wip", "orig"], default="wip")
    p.add_argument("--n-steps", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--out", type=str,
                   default=str(ROOT / "modele-27-04-WIP" / "profiling" / "run.prof"))
    args = p.parse_args()

    src = WIP_SRC if args.target == "wip" else ORIG_SRC
    config_m, sim_m = _load(src)
    cfg = config_m.SimulationConfig(duree_simulation=args.n_steps, seed=args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pr = cProfile.Profile()
    pr.enable()
    sim = sim_m.Simulation(cfg)
    sim.run(verbose=False)
    pr.disable()
    pr.dump_stats(str(out_path))

    print(f"# Profil sauvé dans : {out_path}")
    print(f"# Simulation : target={args.target}, n_steps={args.n_steps}, seed={args.seed}")
    print()
    for sort_key in ("cumulative", "tottime"):
        buf = io.StringIO()
        ps = pstats.Stats(pr, stream=buf).strip_dirs().sort_stats(sort_key)
        ps.print_stats(args.top)
        print(f"\n{'=' * 60}\n  TOP {args.top} par {sort_key}\n{'=' * 60}")
        print(buf.getvalue())


if __name__ == "__main__":
    main()
