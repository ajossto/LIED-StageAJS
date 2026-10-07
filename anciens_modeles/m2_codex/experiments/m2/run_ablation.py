#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from m2 import M2Config, M2Simulation  # noqa: E402
from m2.analysis import fit_body_distributions, fit_pareto_tail  # noqa: E402
from m2.storage import write_run  # noqa: E402

VARIANTS = {
    "baseline": {},
    "no_credit": {"credit_enabled": False},
    "no_shocks": {"shocks_enabled": False},
    "cancel_failed_claims": {"bankruptcy_transfer": "cancel"},
    "sequential_interest": {"interest_service": "sequential_contract_id"},
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ablations mécanistiques M2")
    parser.add_argument("--steps", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "ablations")
    parser.add_argument("--variants", nargs="+", choices=sorted(VARIANTS))
    args = parser.parse_args()
    summaries = []
    selected = args.variants or list(VARIANTS)
    for name in selected:
        changes = VARIANTS[name]
        config = M2Config(
            steps=args.steps, snapshot_interval=50, check_invariants=False, **changes
        )
        simulation = M2Simulation(config, seed=args.seed)
        run = simulation.run()
        simulation.validate_invariants(require_stable=True)
        output = args.output / f"{name}_seed_{args.seed}"
        write_run(output, config, args.seed, run, command=" ".join(sys.argv))
        final = run.snapshots[max(run.snapshots)] if run.snapshots else []
        pooled = [
            row for step, rows in run.snapshots.items() if step >= 500 for row in rows
        ]
        body = fit_body_distributions([float(row["nw"]) for row in final])
        tail = fit_pareto_tail([float(row["nw"]) for row in pooled])
        summaries.append(
            {
                "variant": name,
                "final_population": (
                    run.timeseries[-1].population if run.timeseries else 0
                ),
                "failures_total": sum(row.failures for row in run.timeseries),
                "body_best_nw": body.get("best_aic"),
                "tail_alpha_nw": tail["alpha"] if tail else "",
                "tail_xmin_nw": tail["xmin"] if tail else "",
            }
        )
        print(name, summaries[-1])
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "ablation_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)


if __name__ == "__main__":
    main()
