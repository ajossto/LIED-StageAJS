#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from m2 import M2Config, M2Simulation  # noqa: E402
from m2.analysis import fit_body_distributions, fit_pareto_tail  # noqa: E402
from m2.storage import write_run  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Grille structurelle M2")
    parser.add_argument("--steps", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--birth-rate", type=float, default=10.0)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "grid")
    parser.add_argument(
        "--max-cases", type=int, help="limite explicite pour un essai partiel"
    )
    parser.add_argument("--case-start", type=int, default=0)
    parser.add_argument("--case-stop", type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = list(itertools.product((2, 3, 4, 6), (0.15, 0.25, 0.35), (0.05, 0.25, 0.5)))
    cases = cases[args.case_start : args.case_stop]
    if args.max_cases is not None:
        cases = cases[: args.max_cases]
    summaries = []
    for k, sigma, epsilon_ratio in cases:
        d0 = 30.0 * (1.0 - epsilon_ratio)
        label = f"k{k}_sigma{sigma:.2f}_eps{epsilon_ratio:.2f}_seed{args.seed}"
        output = args.output / label
        config = M2Config(
            k=k,
            sigma=sigma,
            birth_rate=args.birth_rate,
            w0=30,
            d0=d0,
            steps=args.steps,
            snapshot_interval=50,
            check_invariants=False,
        )
        simulation = M2Simulation(config, seed=args.seed)
        run = simulation.run()
        simulation.validate_invariants(require_stable=True)
        write_run(output, config, args.seed, run, command=" ".join(sys.argv))
        final = run.snapshots[max(run.snapshots)] if run.snapshots else []
        body = fit_body_distributions([float(row["nw"]) for row in final])
        pooled = [
            row for step, rows in run.snapshots.items() if step >= 500 for row in rows
        ]
        tail = fit_pareto_tail([float(row["nw"]) for row in pooled])
        summaries.append(
            {
                "case": label,
                "k": k,
                "sigma": sigma,
                "epsilon_ratio": epsilon_ratio,
                "final_population": (
                    run.timeseries[-1].population if run.timeseries else 0
                ),
                "population_change_last_500": (
                    run.timeseries[-1].population - run.timeseries[-501].population
                    if len(run.timeseries) > 500
                    else ""
                ),
                "failures_total": sum(row.failures for row in run.timeseries),
                "body_best_nw": body.get("best_aic"),
                "body_exponential_delta_aic": next(
                    (
                        fit["delta_aic"]
                        for fit in body.get("fits", [])
                        if fit["name"] == "exponential"
                    ),
                    "",
                ),
                "tail_alpha_nw": tail["alpha"] if tail else "",
                "tail_xmin_nw": tail["xmin"] if tail else "",
            }
        )
        print(label, summaries[-1])
    suffix = (
        f"_{args.case_start}_{args.case_stop if args.case_stop is not None else 'end'}"
    )
    with (args.output / f"grid_summary{suffix}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(summaries[0]) if summaries else []
        )
        if summaries:
            writer.writeheader()
            writer.writerows(summaries)


if __name__ == "__main__":
    main()
