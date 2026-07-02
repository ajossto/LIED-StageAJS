#!/usr/bin/env python3
"""Campagnes statistiques pour Wright (2009), modèle CSA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import recoding


def mean_ci(values: list[float]) -> dict[str, float]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"mean": float("nan"), "std": float("nan"), "ci95_low": float("nan"), "ci95_high": float("nan"), "n": 0}
    m = float(np.mean(x))
    s = float(np.std(x, ddof=1)) if len(x) > 1 else 0.0
    return {"mean": m, "std": s, "ci95_low": float(m - 1.96 * s / np.sqrt(len(x))), "ci95_high": float(m + 1.96 * s / np.sqrt(len(x))), "n": int(len(x))}


def metrics(out: dict, n: int) -> dict[str, float]:
    class_counts = np.asarray(out["class_counts"], dtype=float)
    firms = np.asarray(out["firm_sizes_monthly"], dtype=float)
    wage_share = np.asarray(out["wage_share"], dtype=float)
    demises = np.asarray(out["demises_monthly"], dtype=float)
    profits = np.asarray(out["profit_rates"], dtype=float)
    growth = np.asarray(out["firm_growth_emp"], dtype=float)
    return {
        "workers_pct": float(np.mean(class_counts[:, 0]) / n),
        "capitalists_pct": float(np.mean(class_counts[:, 1]) / n),
        "unemployed_pct": float(np.mean(class_counts[:, 2]) / n),
        "firm_size_alpha": recoding.fit_power_alpha_discrete(firms, xmin=1),
        "wage_share": float(np.nanmean(wage_share)),
        "demises_per_month": float(np.nanmean(demises)),
        "profit_median": float(np.nanmedian(profits[np.isfinite(profits)])),
        "growth_abs_median": float(np.nanmedian(np.abs(growth[np.isfinite(growth)]))) if len(growth) else float("nan"),
    }


def run_campaign(args: argparse.Namespace, checkpoint: Path) -> list[dict]:
    rows = []
    specs = []
    for n in [1000]:
        specs.append({"label": f"N={n}, base", "n": n, "initial_money": 10.0, "initial_expectation": 10.0})
    for expectation in [5.0, 10.0, 20.0]:
        specs.append({"label": f"eta0={expectation}", "n": 1000, "initial_money": 10.0, "initial_expectation": expectation})
    for money in [5.0, 10.0, 20.0]:
        specs.append({"label": f"m0={money}", "n": 1000, "initial_money": money, "initial_expectation": 10.0})

    # Déduplication volontaire du cas central.
    unique = []
    seen = set()
    for s in specs:
        key = (s["n"], s["initial_money"], s["initial_expectation"])
        if key not in seen:
            unique.append(s)
            seen.add(key)

    for spec in unique:
        run_metrics = []
        for rep in range(args.reps):
            local = argparse.Namespace(
                n=spec["n"],
                initial_money=spec["initial_money"],
                initial_expectation=spec["initial_expectation"],
                seed=args.seed + 1000 * rep + int(spec["n"] + 10 * spec["initial_money"] + spec["initial_expectation"]),
                years=args.years,
                burn_years=args.burn_years,
            )
            out = recoding.run_simulation(local)
            run_metrics.append(metrics(out, spec["n"]))
            print(f"CSA {spec['label']}: répétition {rep + 1}/{args.reps} terminée", flush=True)
        row = dict(spec)
        for key in run_metrics[0]:
            row[key] = mean_ci([m[key] for m in run_metrics])
        rows.append(row)
        checkpoint.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    return rows


def plot(rows: list[dict], figures: Path) -> None:
    labels = [r["label"] for r in rows]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    specs = [
        ("workers_pct", "part travailleurs"),
        ("unemployed_pct", "part chômeurs"),
        ("wage_share", "part salariale"),
        ("firm_size_alpha", r"$\alpha$ tailles firmes"),
    ]
    for ax, (key, title) in zip(axes.flat, specs):
        y = np.array([r[key]["mean"] for r in rows])
        lo = np.array([r[key]["ci95_low"] for r in rows])
        hi = np.array([r[key]["ci95_high"] for r in rows])
        ax.errorbar(x, y, yerr=[y - lo, hi - y], fmt="o", capsize=3)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures / "stat_csa_parameter_sweep.pdf")
    fig.savefig(figures / "stat_csa_parameter_sweep.png", dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--years", type=int, default=130)
    parser.add_argument("--burn-years", type=int, default=30)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    figures = root / "figures"
    results = root / "results"
    figures.mkdir(exist_ok=True)
    results.mkdir(exist_ok=True)
    rows = run_campaign(args, results / "statistical_checkpoint.json")
    plot(rows, figures)
    summary = {"seed": args.seed, "reps": args.reps, "years": args.years, "burn_years": args.burn_years, "rows": rows}
    (results / "statistical_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
