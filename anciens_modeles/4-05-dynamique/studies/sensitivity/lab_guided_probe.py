"""
Petite grille guidee par simulation_lab.

Elle separe trois suspects avant de lancer une grande campagne :
  - k = n_candidats_pool,
  - epsilon numerique,
  - homogeneite / heterogeneite de alpha.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

N_STEPS = 2000
SEED = 42

CASES = [
    {
        "name": "hom_k3_eps1e-6",
        "params": {"alpha_min": 1.0, "alpha_max": 1.0, "alpha_sigma_brownien": 0.0,
                   "n_candidats_pool": 3, "epsilon": 1e-6},
    },
    {
        "name": "hom_k3_eps1e-3",
        "params": {"alpha_min": 1.0, "alpha_max": 1.0, "alpha_sigma_brownien": 0.0,
                   "n_candidats_pool": 3, "epsilon": 0.001},
    },
    {
        "name": "hom_k4_eps1e-6",
        "params": {"alpha_min": 1.0, "alpha_max": 1.0, "alpha_sigma_brownien": 0.0,
                   "n_candidats_pool": 4, "epsilon": 1e-6},
    },
    {
        "name": "hom_k4_eps1e-3",
        "params": {"alpha_min": 1.0, "alpha_max": 1.0, "alpha_sigma_brownien": 0.0,
                   "n_candidats_pool": 4, "epsilon": 0.001},
    },
    {
        "name": "het_k3_eps1e-6",
        "params": {"alpha_min": 0.8, "alpha_max": 1.2, "alpha_sigma_brownien": 0.005,
                   "n_candidats_pool": 3, "epsilon": 1e-6},
    },
    {
        "name": "het_k3_eps1e-3",
        "params": {"alpha_min": 0.8, "alpha_max": 1.2, "alpha_sigma_brownien": 0.005,
                   "n_candidats_pool": 3, "epsilon": 0.001},
    },
]


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


def _worker(case: dict) -> dict:
    res = run_and_collect(case["params"], n_steps=N_STEPS, seed=SEED)
    jd, td = joint_drop(res)
    compact = {
        k: v for k, v in res.items()
        if not k.startswith("ts_") and k != "dist_values_regime"
    }
    compact["case"] = case["name"]
    compact["joint_drop"] = jd
    compact["t_joint_drop"] = td
    compact["probe_params"] = case["params"]
    return compact


if __name__ == "__main__":
    workers = min(len(CASES), os.cpu_count() or 4)
    results = []
    with ProcessPoolExecutor(max_workers=workers) as exe:
        futures = {exe.submit(_worker, case): case["name"] for case in CASES}
        for fut in as_completed(futures):
            row = fut.result()
            results.append(row)
            print(
                f"{row['case']:16s} joint={row['joint_drop']} t_joint={row['t_joint_drop']} "
                f"n_alive={row['n_alive_mean']:.1f} loan/alive={row['loan_density_mean']:.3f} "
                f"densite_fin={row['densite_fin_mean']:.3f}"
            )
    results.sort(key=lambda r: r["case"])
    out = RESULTS_DIR / "lab_guided_probe.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Resultats sauvegardes dans {out}")
