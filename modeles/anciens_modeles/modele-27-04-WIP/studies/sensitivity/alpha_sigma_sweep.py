"""
Balayage de alpha_sigma_brownien en conservant alpha_min=alpha_max=1.

Ce script corrige une ambiguite importante : on ne compare pas une population
heterogene en alpha a une population homogene. Toutes les entites naissent avec
alpha=1 ; seule la volatilite brownienne ulterieure varie.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

RESULTS_DIR = HERE / "results"
FIGURES_DIR = HERE / "report" / "figures"
RESULTS_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SIGMAS = [0.0, 0.001, 0.003, 0.005, 0.01, 0.02, 0.05, 0.1]
DEFAULT_K_VALUES = [3, 4]
DEFAULT_SEEDS = [42, 7, 123]


def case_key(k: int, sigma: float, seed: int, epsilon: float, steps: int) -> str:
    return f"hom_alpha_sigma|k={k}|sigma={sigma:g}|seed={seed}|eps={epsilon:g}|steps={steps}"


def compact_result(res: dict) -> dict:
    return {
        key: value for key, value in res.items()
        if not key.startswith("ts_") and key != "dist_values_regime"
    }


def _worker(case: dict) -> dict:
    params = {
        "alpha_min": 1.0,
        "alpha_max": 1.0,
        "alpha_sigma_brownien": case["sigma"],
        "n_candidats_pool": case["k"],
        "epsilon": case["epsilon"],
    }
    res = run_and_collect(params, n_steps=case["steps"], seed=case["seed"])
    row = compact_result(res)
    diag = row.get("regime_diagnostics", {})
    row.update({
        "case_key": case["case_key"],
        "k": case["k"],
        "alpha_sigma_brownien": case["sigma"],
        "epsilon": case["epsilon"],
        "drop_5_detected": bool(diag.get("drop_5_detected", False)),
        "bounded_tail": bool(diag.get("bounded_tail", False)),
        "alive_tail_slope_rel": diag.get("alive_tail_slope_rel"),
        "actif_tail_slope_rel": diag.get("actif_tail_slope_rel"),
        "failures_tail_slope_abs": diag.get("failures_tail_slope_abs"),
        "tail_failure_rate": diag.get("tail_failure_rate"),
        "corr_alive_actif_tail": diag.get("corr_alive_actif_tail"),
        "corr_alive_loans_tail": diag.get("corr_alive_loans_tail"),
        "corr_actif_loans_tail": diag.get("corr_actif_loans_tail"),
    })
    return row


def load(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save(path: Path, rows: list[dict]) -> None:
    rows = sorted(rows, key=lambda r: (r["k"], r["alpha_sigma_brownien"], r["seed"]))
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def aggregate(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[int, float], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["k"], row["alpha_sigma_brownien"]), []).append(row)
    metrics = [
        "drop_5_detected", "bounded_tail",
        "measure_n_alive_mean", "measure_n_alive_cv",
        "measure_densite_fin_mean", "measure_loan_density_mean",
        "measure_failure_rate_mean", "alive_tail_slope_rel", "actif_tail_slope_rel",
        "failures_tail_slope_abs", "cascade_event_rate", "cascade_size_mean",
        "cascade_size_max", "cascade_ratio_contagion_mean",
        "corr_alive_actif_tail", "corr_alive_loans_tail", "corr_actif_loans_tail",
    ]
    out = []
    for (k, sigma), vals in groups.items():
        rec = {"k": k, "alpha_sigma_brownien": sigma, "n": len(vals)}
        for metric in metrics:
            if metric in {"drop_5_detected", "bounded_tail"}:
                rec[f"{metric}_share"] = sum(1 for v in vals if v.get(metric)) / len(vals)
                continue
            xs = [float(v[metric]) for v in vals if v.get(metric) is not None]
            if xs:
                rec[f"{metric}_mean"] = float(np.mean(xs))
                rec[f"{metric}_std"] = float(np.std(xs))
        out.append(rec)
    return sorted(out, key=lambda r: (r["k"], r["alpha_sigma_brownien"]))


def plot(agg: list[dict], path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    metrics = [
        ("bounded_tail_share", "Part queue bornee"),
        ("measure_densite_fin_mean_mean", "Volume prets / actif"),
        ("measure_loan_density_mean_mean", "Prets actifs / entite"),
        ("measure_n_alive_mean_mean", "Entites vivantes"),
        ("measure_failure_rate_mean_mean", "Faillites / pas"),
        ("corr_alive_actif_tail_mean", "Corr. n_alive / actif"),
    ]
    for ax, (metric, label) in zip(axes.ravel(), metrics):
        for k in sorted({r["k"] for r in agg}):
            rows = sorted([r for r in agg if r["k"] == k], key=lambda r: r["alpha_sigma_brownien"])
            x = [r["alpha_sigma_brownien"] for r in rows]
            y = [r.get(metric, np.nan) for r in rows]
            ax.plot(x, y, marker="o", linewidth=1.3, label=f"k={k}")
        ax.set_xscale("symlog", linthresh=0.001)
        ax.set_xlabel("alpha_sigma_brownien")
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.3)
    axes[0, 0].legend()
    fig.suptitle("Homogene alpha=1 : effet de la volatilite brownienne", fontsize=13)
    plt.tight_layout()
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--epsilon", type=float, default=1e-3)
    parser.add_argument("--sigmas", type=float, nargs="+", default=DEFAULT_SIGMAS)
    parser.add_argument("--k-values", type=int, nargs="+", default=DEFAULT_K_VALUES)
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    parser.add_argument("--workers", type=int, default=max(1, min(6, os.cpu_count() or 6)))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result_path = RESULTS_DIR / f"alpha_sigma_sweep_steps{args.steps}_eps{args.epsilon:g}.json"
    agg_path = RESULTS_DIR / f"alpha_sigma_sweep_steps{args.steps}_eps{args.epsilon:g}_aggregate.json"
    fig_path = FIGURES_DIR / f"alpha_sigma_sweep_steps{args.steps}_eps{args.epsilon:g}.pdf"

    rows = load(result_path)
    done = {r["case_key"] for r in rows}
    cases = []
    for k in args.k_values:
        for sigma in args.sigmas:
            for seed in args.seeds:
                key = case_key(k, sigma, seed, args.epsilon, args.steps)
                if key not in done:
                    cases.append({
                        "case_key": key,
                        "k": k,
                        "sigma": sigma,
                        "seed": seed,
                        "epsilon": args.epsilon,
                        "steps": args.steps,
                    })

    print(f"{len(done)} cas deja presents, {len(cases)} cas a lancer.")
    with ProcessPoolExecutor(max_workers=args.workers) as exe:
        futures = {exe.submit(_worker, case): case for case in cases}
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            save(result_path, rows)
            print(
                f"k={row['k']:>2d} sigma={row['alpha_sigma_brownien']:<7g} seed={row['seed']:>4d} "
                f"bounded={row['bounded_tail']} drop5={row['drop_5_detected']} "
                f"dens={row['measure_densite_fin_mean']:.3f} "
                f"fail={row['measure_failure_rate_mean']:.3f} "
                f"cascade={row['cascade_size_mean']:.2f}"
            )

    agg = aggregate(rows)
    agg_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    plot(agg, fig_path)
    print(f"Resultats : {result_path}")
    print(f"Agregats  : {agg_path}")
    print(f"Figure    : {fig_path}")
