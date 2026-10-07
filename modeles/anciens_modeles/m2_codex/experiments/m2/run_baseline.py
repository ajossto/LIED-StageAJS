#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from m2 import M2Config, M2Simulation  # noqa: E402
from m2.plots import (  # noqa: E402
    plot_age_diagnostics,
    plot_cascade_batches,
    plot_distributions,
    plot_exponential_qq,
    plot_macros,
)
from m2.storage import write_run  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulation baseline fidèle de M2")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, default=2_000)
    parser.add_argument("--birth-rate", type=float, default=10.0)
    parser.add_argument("--snapshot-interval", type=int, default=50)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--log-events", action="store_true")
    parser.add_argument(
        "--no-step-invariant-checks",
        action="store_true",
        help="désactive les audits coûteux à chaque pas; un audit final reste exécuté",
    )
    args = parser.parse_args()

    output = args.output or ROOT / "outputs" / f"baseline_seed_{args.seed}"
    config = M2Config(
        alpha=1.0,
        delta=0.05,
        k=6,
        sigma=0.25,
        birth_rate=args.birth_rate,
        w0=30.0,
        d0=28.0,
        steps=args.steps,
        snapshot_interval=args.snapshot_interval,
        log_events=args.log_events,
        check_invariants=not args.no_step_invariant_checks,
    )
    simulation = M2Simulation(config, seed=args.seed)
    run = simulation.run()
    simulation.validate_invariants(require_stable=True)
    write_run(output, config, args.seed, run, command=" ".join(sys.argv))

    timeseries = [row.to_dict() for row in run.timeseries]
    final_rows = run.snapshots[max(run.snapshots)] if run.snapshots else []
    figures = output / "figures"
    plot_macros(timeseries, figures / "macro_timeseries")
    plot_distributions(final_rows, figures / "final_distributions")
    plot_age_diagnostics(final_rows, figures / "age_diagnostics")
    plot_cascade_batches(timeseries, figures / "cascade_batches")
    for variable in ("w", "nw", "income_gross"):
        plot_exponential_qq(
            final_rows, variable, figures / f"qq_exponential_{variable}"
        )

    final = run.timeseries[-1] if run.timeseries else None
    if final:
        print(
            f"run={output} step={final.step} population={final.population} "
            f"contracts={final.active_contracts} failures_total="
            f"{sum(row.failures for row in run.timeseries)}"
        )
    else:
        print(f"run vide écrit dans {output}")


if __name__ == "__main__":
    main()
