#!/usr/bin/env python3
"""Campagnes statistiques pour Wright (2004), modèle SR."""

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
    profits = np.asarray(out["profit_rates"], dtype=float)
    growth = np.asarray(out["gdp_growth"], dtype=float)
    recessions = []
    k = 0
    for g in growth:
        if g < 0:
            k += 1
        elif k:
            recessions.append(k)
            k = 0
    if k:
        recessions.append(k)
    return {
        "workers_pct": float(np.mean(class_counts[:, 0]) / n),
        "capitalists_pct": float(np.mean(class_counts[:, 1]) / n),
        "unemployed_pct": float(np.mean(class_counts[:, 2]) / n),
        "firm_size_alpha": recoding.fit_power_alpha(firms, xmin=1),
        "wage_share": float(np.nanmean(wage_share)),
        "profit_median": float(np.nanmedian(profits[np.isfinite(profits)])),
        "profit_mean": float(np.nanmean(profits[np.isfinite(profits)])),
        "recession_mean_duration": float(np.mean(recessions)) if recessions else float("nan"),
    }


def run_campaign(args: argparse.Namespace, checkpoint: Path) -> list[dict]:
    rows = []
    specs = [
        {"label": "omega=[10,90]", "wage_min": 10, "wage_max": 90, "n": args.n, "total_money": args.total_money},
        {"label": "omega=[20,80]", "wage_min": 20, "wage_max": 80, "n": args.n, "total_money": args.total_money},
        {"label": "omega=[5,95]", "wage_min": 5, "wage_max": 95, "n": args.n, "total_money": args.total_money},
        {"label": "M/N=50", "wage_min": 10, "wage_max": 90, "n": args.n, "total_money": 50 * args.n},
        {"label": "M/N=200", "wage_min": 10, "wage_max": 90, "n": args.n, "total_money": 200 * args.n},
    ]
    for spec in specs:
        run_metrics = []
        for rep in range(args.reps):
            local = argparse.Namespace(
                n=spec["n"],
                total_money=spec["total_money"],
                wage_min=spec["wage_min"],
                wage_max=spec["wage_max"],
                seed=args.seed + 1000 * rep + spec["wage_min"] * 17 + int(spec["total_money"] / spec["n"]),
                years=args.years,
                burn_years=args.burn_years,
            )
            out = recoding.run_simulation(local)
            run_metrics.append(metrics(out, spec["n"]))
            print(f"SR {spec['label']}: répétition {rep + 1}/{args.reps} terminée", flush=True)
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
        ("wage_share", "part salariale"),
        ("firm_size_alpha", r"$\alpha$ tailles firmes"),
        ("profit_median", "profit médian (%)"),
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
    fig.savefig(figures / "stat_sr_parameter_sweep.pdf")
    fig.savefig(figures / "stat_sr_parameter_sweep.png", dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--total-money", type=float, default=100000.0)
    parser.add_argument("--years", type=int, default=100)
    parser.add_argument("--burn-years", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    figures = root / "figures"
    results = root / "results"
    figures.mkdir(exist_ok=True)
    results.mkdir(exist_ok=True)
    rows = run_campaign(args, results / "statistical_checkpoint.json")
    plot(rows, figures)
    summary = {"seed": args.seed, "reps": args.reps, "n": args.n, "years": args.years, "burn_years": args.burn_years, "rows": rows}
    (results / "statistical_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
