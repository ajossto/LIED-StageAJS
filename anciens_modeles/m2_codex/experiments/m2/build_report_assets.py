#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from m2.storage import read_csv_numeric  # noqa: E402

REPORT = ROOT / "reports" / "04_validation_report"
TABLES = REPORT / "tables"
FIGURES = REPORT / "figures"
WINDOWS = ("[500,1000)", "[1000,1500)", "[1500,2000)")


def save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}.png", dpi=180, bbox_inches="tight")
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def write_csv(name: str, rows: list[dict]) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    with (TABLES / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    analyses = []
    baseline_rows = []
    tail_rows = []
    for seed in range(3):
        run_dir = ROOT / "outputs" / f"baseline_seed_{seed}"
        analysis = json.loads((run_dir / "analysis.json").read_text(encoding="utf-8"))
        metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        timeseries = read_csv_numeric(run_dir / "timeseries.csv")
        analyses.append(analysis)
        body = analysis["body"]["nw"]["0.95"]
        exponential = next(
            item for item in body["fits"] if item["name"] == "exponential"
        )
        baseline_rows.append(
            {
                "seed": seed,
                "final_population": metadata["summary"]["final_population"],
                "failures_total": metadata["summary"]["failures_total"],
                "active_contracts_final": int(timeseries[-1]["active_contracts"]),
                "population_relative_slope_per_1000": analysis["stationarity"][
                    "variables"
                ]["population"]["relative_slope_per_1000_steps"],
                "capital_relative_slope_per_1000": analysis["stationarity"][
                    "variables"
                ]["total_capital"]["relative_slope_per_1000_steps"],
                "body_best_nw": body["best_aic"],
                "exponential_delta_aic_nw": exponential["delta_aic"],
                "body_median_mean_nw": body["median_mean_ratio"],
                "age_log_nw_pearson": analysis["cohort"]["pearson_age_log_nw"],
                "top_recent_fraction_1000": analysis["cohort"]["top_recent_fraction"],
                "top_mortality_1000_to_2000": analysis["top_mortality"][
                    "mortality_fraction"
                ],
                "mean_body_nw_increment": analysis["nw_increment_mechanism"][
                    "mean_increment"
                ],
                "B0_over_A0": analysis["nw_increment_mechanism"]["B0_over_A0"],
            }
        )
        for variable in ("nw", "w", "income_gross"):
            for window in WINDOWS:
                result = analysis["tail"][variable]["windows"][window]
                free = result["free_xmin"]
                fixed = result["fixed_xmin"]
                comparison = result["pareto_vs_lognormal"]
                bootstrap = result["block_bootstrap"]
                tail_rows.append(
                    {
                        "seed": seed,
                        "variable": variable,
                        "window": window,
                        "alpha_free": free["alpha"],
                        "xmin_free": free["xmin"],
                        "n_tail": free["n_tail"],
                        "alpha_fixed_xmin": fixed["alpha"],
                        "common_xmin": fixed["xmin"],
                        "lr_pareto_minus_lognormal": comparison[
                            "log_likelihood_ratio_pareto_minus_lognormal"
                        ],
                        "lr_p": comparison["p"],
                        "bootstrap_alpha_low": bootstrap["alpha_ci_025"],
                        "bootstrap_alpha_high": bootstrap["alpha_ci_975"],
                    }
                )
    write_csv("baseline_summary.csv", baseline_rows)
    write_csv("tail_summary.csv", tail_rows)

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for seed in range(3):
        rows = read_csv_numeric(
            ROOT / "outputs" / f"baseline_seed_{seed}" / "timeseries.csv"
        )
        step = [int(row["step"]) for row in rows]
        axes[0].plot(
            step, [float(row["population"]) for row in rows], label=f"seed {seed}", lw=1
        )
        axes[1].plot(
            step,
            [float(row["total_capital"]) for row in rows],
            label=f"seed {seed}",
            lw=1,
        )
    axes[0].set_ylabel("Population")
    axes[1].set_ylabel("Capital total")
    axes[1].set_xlabel("Pas")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend()
    fig.suptitle("Baseline M2 : trajectoires multi-seed")
    save(fig, "baseline_multiseed")

    nw_tails = [row for row in tail_rows if row["variable"] == "nw"]
    fig, axis = plt.subplots(figsize=(9, 4.8))
    offsets = (-0.18, 0.0, 0.18)
    for seed, offset in zip(range(3), offsets, strict=True):
        rows = [row for row in nw_tails if row["seed"] == seed]
        x = np.arange(3) + offset
        y = np.asarray([float(row["alpha_free"]) for row in rows])
        low = np.asarray([float(row["bootstrap_alpha_low"]) for row in rows])
        high = np.asarray([float(row["bootstrap_alpha_high"]) for row in rows])
        axis.errorbar(
            x, y, yerr=[y - low, high - y], fmt="o-", capsize=3, label=f"seed {seed}"
        )
    axis.set_xticks(range(3), WINDOWS)
    axis.set_ylabel("Exposant de densité Pareto estimé")
    axis.set_xlabel("Fenêtre")
    axis.grid(alpha=0.25)
    axis.legend()
    axis.set_title("Queue de NW : stabilité conditionnelle à l'estimateur CSN")
    save(fig, "tail_alpha_windows")

    fig, axis = plt.subplots(figsize=(6.5, 4.5))
    axis.bar(
        [str(row["seed"]) for row in baseline_rows],
        [float(row["exponential_delta_aic_nw"]) for row in baseline_rows],
    )
    axis.axhline(2, color="black", ls="--", lw=1, label="seuil ΔAIC=2")
    axis.set_xlabel("Seed")
    axis.set_ylabel("ΔAIC exponentielle, corps de NW")
    axis.set_title("Réfutation du corps exponentiel (quantile 95 %)")
    axis.legend()
    axis.grid(alpha=0.25, axis="y")
    save(fig, "body_exponential_delta_aic")

    grid_rows: list[dict] = []
    for path in sorted((ROOT / "outputs" / "grid_screen").glob("grid_summary_*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            grid_rows.extend(dict(row) for row in csv.DictReader(handle))
    grid_rows.sort(
        key=lambda row: (
            int(row["k"]),
            float(row["sigma"]),
            float(row["epsilon_ratio"]),
        )
    )
    write_csv("grid_screen.csv", grid_rows)

    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    for axis, k in zip(axes.flat, (2, 3, 4, 6), strict=True):
        subset = [row for row in grid_rows if int(row["k"]) == k]
        matrix = np.full((3, 3), np.nan)
        for row in subset:
            i = (0.15, 0.25, 0.35).index(float(row["sigma"]))
            j = (0.05, 0.25, 0.5).index(float(row["epsilon_ratio"]))
            matrix[i, j] = float(row["population_change_last_500"])
        image = axis.imshow(matrix, aspect="auto", cmap="magma")
        axis.set_xticks(range(3), ("0,05", "0,25", "0,50"))
        axis.set_yticks(range(3), ("0,15", "0,25", "0,35"))
        axis.set_xlabel(r"$\varepsilon_0/w_0$")
        axis.set_ylabel(r"$\sigma$")
        axis.set_title(f"k={k}")
        for i in range(3):
            for j in range(3):
                axis.text(
                    j,
                    i,
                    f"{matrix[i,j]:.0f}",
                    ha="center",
                    va="center",
                    color="white" if matrix[i, j] > 1800 else "black",
                    fontsize=8,
                )
        fig.colorbar(image, ax=axis, shrink=0.75)
    fig.suptitle("Grille T=600 : croissance de population entre t=100 et t=600")
    save(fig, "grid_population_growth")

    ablation_path = ROOT / "outputs" / "ablations_screen" / "ablation_summary.csv"
    with ablation_path.open(encoding="utf-8", newline="") as handle:
        ablations = list(csv.DictReader(handle))
    write_csv("ablation_summary.csv", ablations)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    labels = [row["variant"].replace("_", "\n") for row in ablations]
    axes[0].bar(labels, [float(row["final_population"]) for row in ablations])
    axes[1].bar(labels, [float(row["failures_total"]) for row in ablations])
    axes[0].set_ylabel("Population finale")
    axes[1].set_ylabel("Faillites cumulées")
    for axis in axes:
        axis.tick_params(axis="x", labelsize=8)
        axis.grid(alpha=0.25, axis="y")
    fig.suptitle("Ablations à T=600")
    save(fig, "ablation_population_failures")

    cascade_rows = []
    fig, axis = plt.subplots(figsize=(6.5, 4.8))
    for k in (2, 3, 4, 6):
        run_dir = ROOT / "outputs" / "grid_screen" / f"k{k}_sigma0.25_eps0.05_seed0"
        rows = read_csv_numeric(run_dir / "timeseries.csv")
        sizes = np.asarray(
            [float(row["failures"]) for row in rows if float(row["failures"]) > 0]
        )
        ordered = np.sort(sizes)
        ccdf = (len(ordered) - np.arange(len(ordered))) / len(ordered)
        axis.loglog(ordered, ccdf, marker=".", ls="none", label=f"k={k}")
        hhi = np.asarray([float(row["credit_hhi"]) for row in rows[:-1]])
        next_failures = np.asarray([float(row["failures"]) for row in rows[1:]])
        rho = float(stats.spearmanr(hhi, next_failures).statistic)
        cascade_rows.append(
            {
                "k": k,
                "positive_steps": len(sizes),
                "mean_batch": float(np.mean(sizes)),
                "q90_batch": float(np.quantile(sizes, 0.9)),
                "max_batch": float(np.max(sizes)),
                "spearman_hhi_previous_vs_failures": rho,
            }
        )
    axis.set_xlabel("Faillites par pas (lot de cascade)")
    axis.set_ylabel("CCDF")
    axis.grid(alpha=0.25, which="both")
    axis.legend()
    axis.set_title(
        r"Lots de faillites selon $k$ ($\sigma=0{,}25$, $\varepsilon_0/w_0=0{,}05$)"
    )
    save(fig, "cascade_batches_by_k")
    write_csv("cascade_by_k.csv", cascade_rows)

    no_credit_dir = ROOT / "outputs" / "ablations_long" / "no_credit_seed_0"
    no_credit = json.loads(
        (no_credit_dir / "analysis.json").read_text(encoding="utf-8")
    )
    long_ablation = []
    for label, analysis in (
        ("baseline_seed_0", analyses[0]),
        ("no_credit_seed_0", no_credit),
    ):
        body = analysis["body"]["nw"]["0.95"]
        exponential = next(
            item for item in body["fits"] if item["name"] == "exponential"
        )
        long_ablation.append(
            {
                "run": label,
                "population_relative_slope_per_1000": analysis["stationarity"][
                    "variables"
                ]["population"]["relative_slope_per_1000_steps"],
                "body_best_nw": body["best_aic"],
                "exponential_delta_aic_nw": exponential["delta_aic"],
                "age_log_nw": analysis["cohort"]["pearson_age_log_nw"],
                "top_mortality": analysis["top_mortality"]["mortality_fraction"],
                "mean_body_nw_increment": analysis["nw_increment_mechanism"][
                    "mean_increment"
                ],
                "tail_alphas": ";".join(
                    f"{analysis['tail']['nw']['windows'][window]['free_xmin']['alpha']:.4f}"
                    for window in WINDOWS
                ),
                "tail_lrs_pl_minus_ln": ";".join(
                    f"{analysis['tail']['nw']['windows'][window]['pareto_vs_lognormal']['log_likelihood_ratio_pareto_minus_lognormal']:.4f}"
                    for window in WINDOWS
                ),
            }
        )
    write_csv("long_no_credit_comparison.csv", long_ablation)

    fig, axis = plt.subplots(figsize=(7.5, 4.8))
    for offset, (label, analysis) in zip(
        (-0.08, 0.08),
        (("baseline", analyses[0]), ("sans crédit", no_credit)),
        strict=True,
    ):
        y = [
            analysis["tail"]["nw"]["windows"][window]["free_xmin"]["alpha"]
            for window in WINDOWS
        ]
        axis.plot(np.arange(3) + offset, y, "o-", label=label)
    axis.set_xticks(range(3), WINDOWS)
    axis.set_ylabel("Exposant de densité estimé")
    axis.set_xlabel("Fenêtre")
    axis.grid(alpha=0.25)
    axis.legend()
    axis.set_title("Queue de NW : baseline contre ablation sans crédit")
    save(fig, "baseline_vs_no_credit_tail")


if __name__ == "__main__":
    main()
