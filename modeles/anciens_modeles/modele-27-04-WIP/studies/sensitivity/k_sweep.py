"""
Balayage large de k = n_candidats_pool.

Objectif : tester la transition k=3 -> k=4 observee dans simulation_lab et
chercher un plateau a grand k sur :
  - n_prets_actifs / n_entites,
  - volume_prets / actif_total,
  - taille du systeme,
  - volatilite,
  - distribution des actifs.

Le script est resumable : il relit le JSON existant et saute les cas deja faits.
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

DEFAULT_K_VALUES = [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 50]
DEFAULT_SEEDS = [42, 7, 123]


def regime_joint_drop(res: dict) -> tuple[bool, int | None]:
    alive = res["ts_n_alive"]
    actif = res["ts_actif"]
    n = len(alive)
    skip = min(50, max(5, n // 20))
    peak_alive = max(alive[skip:])
    t_peak = alive.index(peak_alive)
    peak_actif = actif[t_peak]
    for t in range(t_peak + 1, n):
        peak_actif = max(peak_actif, actif[t])
        if alive[t] <= 0.75 * peak_alive and actif[t] <= 0.85 * peak_actif:
            return True, t
    return False, None


def scenario_params(scenario: str) -> dict:
    if scenario == "homogeneous":
        return {"alpha_min": 1.0, "alpha_max": 1.0, "alpha_sigma_brownien": 0.0}
    if scenario == "heterogeneous":
        return {"alpha_min": 0.8, "alpha_max": 1.2, "alpha_sigma_brownien": 0.005}
    raise ValueError(f"Scenario inconnu: {scenario}")


def case_key(scenario: str, k: int, seed: int, epsilon: float, steps: int) -> str:
    return f"{scenario}|k={k}|seed={seed}|eps={epsilon:g}|steps={steps}"


def compact_result(res: dict) -> dict:
    return {
        key: value for key, value in res.items()
        if not key.startswith("ts_") and key != "dist_values_regime"
    }


def _worker(case: dict) -> dict:
    params = {
        **scenario_params(case["scenario"]),
        "n_candidats_pool": case["k"],
        "epsilon": case["epsilon"],
    }
    res = run_and_collect(params, n_steps=case["steps"], seed=case["seed"])
    joint, t_joint = regime_joint_drop(res)
    row = compact_result(res)
    row.update({
        "case_key": case["case_key"],
        "scenario": case["scenario"],
        "k": case["k"],
        "epsilon": case["epsilon"],
        "joint_drop": joint,
        "t_joint_drop": t_joint,
    })
    return row


def load_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, rows: list[dict]) -> None:
    rows = sorted(rows, key=lambda r: (r["scenario"], r["epsilon"], r["k"], r["seed"]))
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def aggregate(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        groups.setdefault((row["scenario"], row["epsilon"], row["k"]), []).append(row)
    out = []
    metrics = [
        "joint_drop", "n_alive_mean", "n_alive_cv", "actif_mean", "actif_cv",
        "loan_density_mean", "densite_fin_mean", "gini_actif_mean",
        "failure_rate_mean", "failure_lambda_ratio",
    ]
    for (scenario, epsilon, k), vals in groups.items():
        rec = {"scenario": scenario, "epsilon": epsilon, "k": k, "n": len(vals)}
        for metric in metrics:
            xs = [float(v[metric]) for v in vals if metric in v and v[metric] is not None]
            if metric == "joint_drop":
                rec["regime_share"] = sum(1.0 for v in vals if v.get("joint_drop")) / len(vals)
            elif xs:
                rec[f"{metric}_mean"] = float(np.mean(xs))
                rec[f"{metric}_std"] = float(np.std(xs))
        out.append(rec)
    return sorted(out, key=lambda r: (r["scenario"], r["epsilon"], r["k"]))


def plot(agg: list[dict], path: Path) -> None:
    if not agg:
        return
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    metrics = [
        ("regime_share", "Part des seeds avec regime"),
        ("loan_density_mean_mean", "Prets actifs / entite"),
        ("densite_fin_mean_mean", "Volume prets / actif"),
        ("n_alive_mean_mean", "Entites vivantes en regime"),
    ]
    scenarios = sorted({r["scenario"] for r in agg})
    for ax, (metric, label) in zip(axes.ravel(), metrics):
        for scenario in scenarios:
            rows = [r for r in agg if r["scenario"] == scenario]
            rows = sorted(rows, key=lambda r: r["k"])
            x = [r["k"] for r in rows]
            y = [r.get(metric, np.nan) for r in rows]
            ax.plot(x, y, marker="o", linewidth=1.3, label=scenario)
        ax.set_xscale("log")
        ax.set_xlabel("k")
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.3)
    axes[0, 0].legend()
    fig.suptitle("Balayage de k : transition et plateau a grand k", fontsize=13)
    plt.tight_layout()
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    parser.add_argument("--k-values", type=int, nargs="+", default=DEFAULT_K_VALUES)
    parser.add_argument("--scenarios", nargs="+", default=["homogeneous", "heterogeneous"])
    parser.add_argument("--epsilon", type=float, default=1e-6)
    parser.add_argument("--workers", type=int, default=max(1, min(6, os.cpu_count() or 6)))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result_path = RESULTS_DIR / f"k_sweep_steps{args.steps}_eps{args.epsilon:g}.json"
    agg_path = RESULTS_DIR / f"k_sweep_steps{args.steps}_eps{args.epsilon:g}_aggregate.json"
    figure_path = FIGURES_DIR / f"k_sweep_steps{args.steps}_eps{args.epsilon:g}.pdf"

    rows = load_existing(result_path)
    done = {r["case_key"] for r in rows}
    cases = []
    for scenario in args.scenarios:
        for k in args.k_values:
            for seed in args.seeds:
                key = case_key(scenario, k, seed, args.epsilon, args.steps)
                if key not in done:
                    cases.append({
                        "case_key": key,
                        "scenario": scenario,
                        "k": k,
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
                f"{row['scenario']:13s} k={row['k']:>3d} seed={row['seed']:>4d} "
                f"joint={row['joint_drop']} loan/alive={row['loan_density_mean']:.3f} "
                f"densite_fin={row['densite_fin_mean']:.3f}"
            )

    agg = aggregate(rows)
    agg_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    plot(agg, figure_path)
    print(f"Resultats : {result_path}")
    print(f"Agregats  : {agg_path}")
    print(f"Figure    : {figure_path}")
