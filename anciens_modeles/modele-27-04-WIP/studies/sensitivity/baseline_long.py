"""
Diagnostic long du point central.

But : verifier si le baseline alpha homogene atteint une premiere descente
consequente apres 1000 pas, ou si les metriques observees par le pilote sont
seulement des metriques de fin de fenetre.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

ROOT_WIP = HERE.parents[1]
FIGURES_DIR = HERE / "report" / "figures"
RESULTS_DIR = HERE / "results"
RAW_DIR = ROOT_WIP / "simulations étude de sensibilité paramètres" / "baseline_long"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


def _worker(seed: int, steps: int):
    return run_and_collect({}, n_steps=steps, seed=seed)


def run(seeds: list[int], steps: int, workers: int) -> list[dict]:
    results = []
    with ProcessPoolExecutor(max_workers=workers) as exe:
        futures = {exe.submit(_worker, seed, steps): seed for seed in seeds}
        for fut in as_completed(futures):
            seed = futures[fut]
            res = fut.result()
            results.append(res)
            state = "regime" if res["converged"] else "fallback"
            print(
                f"seed={seed:4d} | t_regime={res['t_regime']:5d} | {state:8s} | "
                f"n_alive={res['n_alive_mean']:.1f} | actif={res['actif_mean']:.0f} | "
                f"loan/alive={res['loan_density_mean']:.3f}"
            )
    return sorted(results, key=lambda r: r["seed"])


def plot(results: list[dict], steps: int) -> None:
    metrics = [
        ("ts_n_alive", "Entites vivantes"),
        ("ts_actif", "Actif total"),
        ("ts_n_loans", "Prets actifs"),
        ("ts_failures", "Faillites par pas"),
        ("ts_densite_fin", "Volume prets / actif"),
        ("ts_gini", "Gini actif"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    axes = axes.ravel()
    for ax, (key, label) in zip(axes, metrics):
        for res in results:
            series = res[key]
            ax.plot(range(1, len(series) + 1), series, linewidth=1.0, label=f"seed {res['seed']}")
            if 0 < res["t_regime"] < len(series):
                ax.axvline(res["t_regime"], linestyle="--", linewidth=0.8, alpha=0.45)
        ax.set_title(label)
        ax.set_xlabel("Pas")
        ax.grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Diagnostic long baseline alpha homogene ({steps} pas)", fontsize=13)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / f"baseline_long_{steps}.pdf", bbox_inches="tight", dpi=150)
    plt.close(fig)


def save(results: list[dict], steps: int) -> None:
    compact = []
    for res in results:
        compact.append({
            k: v for k, v in res.items()
            if not k.startswith("ts_") and k != "dist_values_regime"
        })
    (RESULTS_DIR / f"baseline_long_{steps}.json").write_text(
        json.dumps(compact, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 7, 123])
    p.add_argument("--workers", type=int, default=min(3, os.cpu_count() or 3))
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(f"Diagnostic long : seeds={args.seeds}, steps={args.steps}, workers={args.workers}")
    rows = run(args.seeds, args.steps, args.workers)
    plot(rows, args.steps)
    save(rows, args.steps)
    print("Diagnostic long termine.")
