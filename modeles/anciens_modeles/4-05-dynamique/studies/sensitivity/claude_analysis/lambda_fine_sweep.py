"""
Balayage fin de lambda_creation comme variable continue.

Objectif : localiser la frontiere entre regime borne et croissance non compensee.
Deux centres : k=3 (sous-critique) et k=4 (regime).
lambda in {1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0}
seeds : 42, 7, 123
steps : 1500, epsilon=1e-3
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

RESULTS_FILE = HERE / "results" / "claude_lambda_fine_sweep.json"

LAMBDAS = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
SEEDS = [42, 7, 123]
CENTERS = {
    "k4": {"n_candidats_pool": 4, "epsilon": 1e-3},
    "k3": {"n_candidats_pool": 3, "epsilon": 1e-3},
}
N_STEPS = 1500
N_WORKERS = 6


def _job(center, lam, seed):
    params = {**CENTERS[center], "lambda_creation": lam}
    r = run_and_collect(params, n_steps=N_STEPS, seed=seed)
    r.pop("ts_n_alive", None)
    r.pop("ts_actif", None)
    r.pop("ts_n_loans", None)
    r.pop("ts_failures", None)
    r.pop("ts_densite_fin", None)
    r.pop("ts_gini", None)
    r.pop("dist_values_regime", None)
    r["center"] = center
    r["lambda_creation"] = lam
    return r


def main():
    existing = []
    if RESULTS_FILE.exists():
        existing = json.loads(RESULTS_FILE.read_text())
    done_keys = {(e["center"], e["lambda_creation"], e["seed"]) for e in existing}

    jobs = [
        (center, lam, seed)
        for center in CENTERS
        for lam in LAMBDAS
        for seed in SEEDS
        if (center, lam, seed) not in done_keys
    ]

    print(f"{len(jobs)} simulations a lancer, {len(existing)} deja presentes.")
    if not jobs:
        print("Rien a faire.")
        return

    results = list(existing)
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futures = {ex.submit(_job, c, l, s): (c, l, s) for c, l, s in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            c, l, s = futures[fut]
            try:
                r = fut.result()
                results.append(r)
                bounded = r.get("regime_diagnostics", {}).get("bounded_tail", "?")
                df = r.get("measure_densite_fin_mean", r.get("densite_fin_mean", "?"))
                alive = r.get("measure_n_alive_mean", r.get("n_alive_mean", "?"))
                print(f"[{i}/{len(jobs)}] {c} lambda={l:.2f} seed={s}: bounded={bounded} df={df:.3f} alive={alive:.0f}")
            except Exception as e:
                print(f"[{i}/{len(jobs)}] ERREUR {c} lambda={l:.2f} seed={s}: {e}")
            RESULTS_FILE.write_text(json.dumps(results, indent=2))

    # --- Agrégat ---
    from collections import defaultdict
    import math

    def mean(xs): return sum(xs)/len(xs) if xs else float("nan")
    def std(xs):
        if len(xs) < 2: return 0.0
        m = mean(xs)
        return math.sqrt(sum((x-m)**2 for x in xs)/len(xs))

    groups = defaultdict(list)
    for r in results:
        groups[(r["center"], r["lambda_creation"])].append(r)

    aggregate = []
    for (center, lam), runs in sorted(groups.items()):
        dfs = [r.get("measure_densite_fin_mean", r.get("densite_fin_mean", 0)) for r in runs]
        alives = [r.get("measure_n_alive_mean", r.get("n_alive_mean", 0)) for r in runs]
        bounded = [r.get("regime_diagnostics", {}).get("bounded_tail", False) for r in runs]
        drop5 = [r.get("regime_diagnostics", {}).get("drop_5_detected", False) for r in runs]
        ginis = [r.get("measure_gini_actif_mean", r.get("gini_actif_mean", 0)) for r in runs]
        fail = [r.get("measure_failure_rate_mean", r.get("failure_rate_mean", 0)) for r in runs]
        alive_slopes = [r.get("regime_diagnostics", {}).get("alive_tail_slope_rel", 0) for r in runs]
        aggregate.append({
            "center": center,
            "lambda_creation": lam,
            "n": len(runs),
            "bounded_tail_share": sum(1 for b in bounded if b) / len(bounded),
            "drop_5_detected_share": sum(1 for b in drop5 if b) / len(drop5),
            "densite_fin_mean": mean(dfs),
            "densite_fin_std": std(dfs),
            "n_alive_mean": mean(alives),
            "n_alive_std": std(alives),
            "gini_mean": mean(ginis),
            "failure_rate_mean": mean(fail),
            "alive_tail_slope_rel_mean": mean(alive_slopes),
        })
        print(f"  AGG {center} lambda={lam:.2f}: {sum(1 for b in bounded if b)}/{len(bounded)} bounded, df={mean(dfs):.3f}±{std(dfs):.3f}, alive={mean(alives):.0f}")

    agg_file = RESULTS_FILE.parent / "claude_lambda_fine_sweep_aggregate.json"
    agg_file.write_text(json.dumps(aggregate, indent=2))
    print(f"\nResultats: {RESULTS_FILE}")
    print(f"Agregat: {agg_file}")


if __name__ == "__main__":
    main()
