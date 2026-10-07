"""
Benchmark epsilon / duree.

Question : peut-on utiliser un epsilon plus grand pour accelerer les campagnes
sans changer les conclusions macroscopiques ?

On mesure :
  - temps d'execution,
  - apparition du regime,
  - n_alive, actif, densite_fin,
  - n_prets/n_alive, plus sensible a la granularite numerique.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
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


def joint_drop(res: dict) -> tuple[bool, int | None]:
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


def case_params(scenario: str, k: int, epsilon: float) -> dict:
    if scenario == "hom_k4":
        alpha = {"alpha_min": 1.0, "alpha_max": 1.0, "alpha_sigma_brownien": 0.0}
    elif scenario == "het_k3":
        alpha = {"alpha_min": 0.8, "alpha_max": 1.2, "alpha_sigma_brownien": 0.005}
    else:
        raise ValueError(scenario)
    return {**alpha, "n_candidats_pool": k, "epsilon": epsilon}


def _worker(case: dict) -> dict:
    t0 = time.perf_counter()
    res = run_and_collect(
        case_params(case["scenario"], case["k"], case["epsilon"]),
        n_steps=case["steps"],
        seed=case["seed"],
    )
    elapsed = time.perf_counter() - t0
    jd, td = joint_drop(res)
    row = {
        key: value for key, value in res.items()
        if not key.startswith("ts_") and key != "dist_values_regime"
    }
    row.update({
        "case_key": case["case_key"],
        "scenario": case["scenario"],
        "k": case["k"],
        "epsilon": case["epsilon"],
        "steps": case["steps"],
        "elapsed_s": elapsed,
        "joint_drop": jd,
        "t_joint_drop": td,
    })
    return row


def load(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save(path: Path, rows: list[dict]) -> None:
    rows = sorted(rows, key=lambda r: (r["scenario"], r["steps"], r["epsilon"], r["seed"]))
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def aggregate(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["scenario"], r["steps"], r["epsilon"]), []).append(r)
    out = []
    metrics = ["elapsed_s", "joint_drop", "n_alive_mean", "actif_mean", "loan_density_mean", "densite_fin_mean", "gini_actif_mean", "failure_rate_mean"]
    for (scenario, steps, eps), vals in groups.items():
        rec = {"scenario": scenario, "steps": steps, "epsilon": eps, "n": len(vals)}
        for metric in metrics:
            if metric == "joint_drop":
                rec["regime_share"] = sum(1 for v in vals if v.get("joint_drop")) / len(vals)
                continue
            xs = [float(v[metric]) for v in vals if v.get(metric) is not None]
            if xs:
                rec[f"{metric}_mean"] = float(np.mean(xs))
                rec[f"{metric}_std"] = float(np.std(xs))
        out.append(rec)
    return sorted(out, key=lambda r: (r["scenario"], r["steps"], r["epsilon"]))


def plot(agg: list[dict], path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    metrics = [
        ("elapsed_s_mean", "Temps par simulation (s)"),
        ("densite_fin_mean_mean", "Volume prets / actif"),
        ("loan_density_mean_mean", "Prets actifs / entite"),
        ("n_alive_mean_mean", "Entites vivantes"),
    ]
    for ax, (metric, label) in zip(axes.ravel(), metrics):
        for scenario in sorted({r["scenario"] for r in agg}):
            rows = [r for r in agg if r["scenario"] == scenario]
            rows = sorted(rows, key=lambda r: (r["steps"], r["epsilon"]))
            for steps in sorted({r["steps"] for r in rows}):
                sub = [r for r in rows if r["steps"] == steps]
                x = [r["epsilon"] for r in sub]
                y = [r.get(metric, np.nan) for r in sub]
                ax.plot(x, y, marker="o", label=f"{scenario}, {steps} pas")
        ax.set_xscale("log")
        ax.set_xlabel("epsilon")
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.3)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Benchmark epsilon : cout et stabilite des metriques", fontsize=13)
    plt.tight_layout()
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epsilons", type=float, nargs="+", default=[1e-6, 1e-5, 1e-4, 1e-3, 1e-2])
    parser.add_argument("--steps-list", type=int, nargs="+", default=[1000, 1500])
    parser.add_argument("--seeds", type=int, nargs="+", default=[42])
    parser.add_argument("--workers", type=int, default=max(1, min(6, os.cpu_count() or 6)))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result_path = RESULTS_DIR / "epsilon_runtime_probe.json"
    agg_path = RESULTS_DIR / "epsilon_runtime_probe_aggregate.json"
    fig_path = FIGURES_DIR / "epsilon_runtime_probe.pdf"
    rows = load(result_path)
    done = {r["case_key"] for r in rows}

    scenarios = [("hom_k4", 4), ("het_k3", 3)]
    cases = []
    for scenario, k in scenarios:
        for steps in args.steps_list:
            for eps in args.epsilons:
                for seed in args.seeds:
                    key = f"{scenario}|k={k}|steps={steps}|eps={eps:g}|seed={seed}"
                    if key not in done:
                        cases.append({"case_key": key, "scenario": scenario, "k": k, "steps": steps, "epsilon": eps, "seed": seed})

    print(f"{len(done)} cas deja presents, {len(cases)} cas a lancer.")
    with ProcessPoolExecutor(max_workers=args.workers) as exe:
        futures = {exe.submit(_worker, case): case for case in cases}
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            save(result_path, rows)
            print(
                f"{row['scenario']:7s} steps={row['steps']:4d} eps={row['epsilon']:.0e} "
                f"time={row['elapsed_s']:.1f}s joint={row['joint_drop']} "
                f"loan/alive={row['loan_density_mean']:.2f} densite_fin={row['densite_fin_mean']:.3f}"
            )

    agg = aggregate(rows)
    agg_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    plot(agg, fig_path)
    print(f"Resultats : {result_path}")
    print(f"Agregats  : {agg_path}")
    print(f"Figure    : {fig_path}")
