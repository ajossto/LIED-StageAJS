#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from m2.analysis import (  # noqa: E402
    block_bootstrap_tail,
    cohort_diagnostics,
    compare_pareto_lognormal,
    fit_body_distributions,
    fit_pareto_at_xmin,
    fit_pareto_tail,
    increment_diagnostics,
    top_decile_turnover,
)
from m2.plots import plot_exponential_qq  # noqa: E402
from m2.storage import read_csv_numeric, read_snapshots  # noqa: E402

WINDOWS = [(500, 1_000), (1_000, 1_500), (1_500, 2_000)]
VARIABLES = ("w", "nw", "income_gross", "income_net")


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(type(value).__name__)


def _stationarity(timeseries: list[dict]) -> dict:
    selected = [row for row in timeseries if int(row["step"]) >= 1_000]
    if len(selected) < 20:
        return {"status": "insufficient_data", "n": len(selected)}
    x = np.asarray([int(row["step"]) for row in selected])
    result = {}
    for variable in ("population", "total_capital", "loan_volume"):
        y = np.asarray([float(row[variable]) for row in selected])
        regression = stats.linregress(x, y)
        result[variable] = {
            "slope_per_step": float(regression.slope),
            "p_slope": float(regression.pvalue),
            "mean": float(np.mean(y)),
            "relative_slope_per_1000_steps": (
                float(1_000 * regression.slope / np.mean(y)) if np.mean(y) else None
            ),
            "warning": "OLS descriptif; l'autocorrélation rend la p-valeur optimiste",
        }
    return {"status": "ok", "n": len(selected), "variables": result}


def _top_mortality(rows_a: list[dict], rows_b: list[dict]) -> dict:
    positive = [row for row in rows_a if float(row["nw"]) > 0]
    if not positive:
        return {"status": "insufficient_data"}
    cutoff = float(np.quantile([float(row["nw"]) for row in positive], 0.9))
    top = {int(row["entity_id"]) for row in positive if float(row["nw"]) >= cutoff}
    alive_later = {int(row["entity_id"]) for row in rows_b}
    deaths = top - alive_later
    return {
        "status": "ok",
        "top_initial": len(top),
        "dead_by_later_snapshot": len(deaths),
        "mortality_fraction": len(deaths) / len(top) if top else None,
    }


def analyze_run(run_dir: Path, bootstrap: int) -> dict:
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    seed = int(metadata["seed"])
    snapshots = read_snapshots(run_dir)
    timeseries = read_csv_numeric(run_dir / "timeseries.csv")
    if not snapshots:
        raise ValueError(f"aucun snapshot dans {run_dir}")
    final_step = max(snapshots)
    final_rows = snapshots[final_step]
    analysis: dict = {
        "run_dir": str(run_dir),
        "seed": seed,
        "final_step": final_step,
        "stationarity": _stationarity(timeseries),
        "body": {},
        "tail": {},
        "cohort": cohort_diagnostics(final_rows, recent_horizon=1_000),
    }

    for variable in VARIABLES:
        analysis["body"][variable] = {
            str(quantile): fit_body_distributions(
                [float(row[variable]) for row in final_rows], body_quantile=quantile
            )
            for quantile in (0.9, 0.95, 0.975)
        }

    window_rows: dict[str, list[dict]] = {}
    for start, end in WINDOWS:
        label = f"[{start},{end})"
        window_rows[label] = [
            row
            for step, rows in snapshots.items()
            if start <= step < end
            for row in rows
        ]

    for variable in VARIABLES:
        variable_result: dict = {"windows": {}}
        free_fits = []
        for label, rows in window_rows.items():
            values = [float(row[variable]) for row in rows]
            fit = fit_pareto_tail(values)
            comparison = (
                compare_pareto_lognormal(values, fit["xmin"], fit["alpha"])
                if fit
                else None
            )
            bootstrap_result = (
                block_bootstrap_tail(
                    rows,
                    variable,
                    np.random.default_rng(seed + 10_000),
                    repetitions=bootstrap,
                )
                if fit and bootstrap > 0
                else None
            )
            variable_result["windows"][label] = {
                "free_xmin": fit,
                "pareto_vs_lognormal": comparison,
                "block_bootstrap": bootstrap_result,
            }
            if fit:
                free_fits.append(fit)
        common_xmin = (
            float(np.median([fit["xmin"] for fit in free_fits])) if free_fits else None
        )
        variable_result["common_xmin"] = common_xmin
        if common_xmin is not None:
            for label, rows in window_rows.items():
                values = [float(row[variable]) for row in rows]
                fixed = fit_pareto_at_xmin(values, common_xmin, min_tail=100)
                variable_result["windows"][label]["fixed_xmin"] = fixed
                variable_result["windows"][label]["fixed_comparison"] = (
                    compare_pareto_lognormal(values, common_xmin, fixed["alpha"])
                    if fixed
                    else None
                )
        analysis["tail"][variable] = variable_result

    increments = [row for rows in window_rows.values() for row in rows]
    analysis["nw_increment_mechanism"] = increment_diagnostics(increments)
    ordered_steps = sorted(snapshots)
    if len(ordered_steps) >= 2:
        first_candidates = [step for step in ordered_steps if step >= 1_000]
        first_step = first_candidates[0] if first_candidates else ordered_steps[0]
        analysis["top_turnover"] = top_decile_turnover(
            snapshots[first_step], snapshots[ordered_steps[-1]]
        )
        analysis["top_mortality"] = _top_mortality(
            snapshots[first_step], snapshots[ordered_steps[-1]]
        )

    pooled_last = window_rows.get("[1500,2000)", [])
    age_controlled = {}
    for lo, hi in ((50, 150), (150, 400)):
        selected = [row for row in pooled_last if lo <= int(row["age"]) < hi]
        age_controlled[f"[{lo},{hi})"] = {
            variable: fit_pareto_tail([float(row[variable]) for row in selected])
            for variable in ("nw", "w")
        }
        age_controlled[f"[{lo},{hi})"]["n"] = len(selected)
    analysis["age_controlled_tails"] = age_controlled

    output = run_dir / "analysis.json"
    output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    (run_dir / "tables").mkdir(exist_ok=True)
    with (run_dir / "tables" / "tail_windows.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["variable", "window", "xmin", "alpha", "n_tail", "lr_pl_minus_ln", "p"]
        )
        for variable, result in analysis["tail"].items():
            for window, values in result["windows"].items():
                fit = values["free_xmin"]
                comparison = values["pareto_vs_lognormal"]
                writer.writerow(
                    [
                        variable,
                        window,
                        fit["xmin"] if fit else "",
                        fit["alpha"] if fit else "",
                        fit["n_tail"] if fit else "",
                        (
                            comparison["log_likelihood_ratio_pareto_minus_lognormal"]
                            if comparison
                            else ""
                        ),
                        comparison["p"] if comparison else "",
                    ]
                )
    for variable in ("w", "nw", "income_gross"):
        plot_exponential_qq(
            final_rows, variable, run_dir / "figures" / f"qq_exponential_{variable}"
        )
    return analysis


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validation statistique d'un ou plusieurs runs M2"
    )
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--bootstrap", type=int, default=100)
    args = parser.parse_args()
    summaries = []
    for run_dir in args.run_dirs:
        result = analyze_run(run_dir, args.bootstrap)
        summaries.append(
            {
                "run_dir": str(run_dir),
                "seed": result["seed"],
                "final_step": result["final_step"],
                "body_best_nw": result["body"]["nw"]["0.95"].get("best_aic"),
                "age_log_nw": result["cohort"].get("pearson_age_log_nw"),
            }
        )
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
