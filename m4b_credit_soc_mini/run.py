#!/usr/bin/env python3
"""Lance M4B depuis la ligne de commande."""

import argparse
from datetime import datetime
from pathlib import Path

from m4b import Config, run_and_save


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simuler le modèle de crédit M4B")
    parser.add_argument("--output", type=Path, help="dossier du run")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--lambda", dest="lam", type=float, default=10.0)
    parser.add_argument("--sigma", type=float, default=0.25)
    parser.add_argument("--delta", type=float, default=0.05)
    parser.add_argument("--capital-birth", dest="K0", type=float, default=25.0)
    parser.add_argument("--market-sample", dest="k", type=int, default=3)
    parser.add_argument("--population-limit", dest="pop_max", type=int, default=30_000)
    parser.add_argument("--snapshot-every", type=int, default=50)
    parser.add_argument(
        "--individual-every",
        type=int,
        default=1,
        help="fréquence des mesures longitudinales individuelles (0 = désactivées)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or Path("results") / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    config = Config(
        lam=args.lam,
        delta=args.delta,
        sigma=args.sigma,
        K0=args.K0,
        k=args.k,
        seed=args.seed,
        T=args.steps,
        pop_max=args.pop_max,
    )
    _, summary = run_and_save(
        config,
        output,
        snapshot_every=args.snapshot_every,
        individual_every=args.individual_every,
    )
    print(f"Résultats : {output}")
    print(
        f"Statut={summary['status']}  t={summary['t_final']}  "
        f"population={summary['population_final']}  morts={summary['deaths_total']}"
    )


if __name__ == "__main__":
    main()
