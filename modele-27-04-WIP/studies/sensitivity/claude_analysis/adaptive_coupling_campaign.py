"""
Campagne adaptative de couplage avec delta_endo = delta_exo = delta_liquide.

Nouveau principe (simplifié) :
  - delta_endo = delta_exo = delta_liquide (delta unique)
  - Grille grossière initiale : 3 seeds/point
  - Points frontier (0.1 < bounded_rate < 0.9) : +9 seeds (→ 12 total)
  - Points très ambigus (0.2 < bounded_rate < 0.8) : +3 seeds supplémentaires (→ 15 total)

Cartes :
  A. lambda × k  — bornes étendues : k∈[2..8], λ∈[0.5..6.0]
  B. k × mu      — bornes étendues : k∈[2..6], μ∈[0..0.15]
  C. sigma × k   — bornes étendues : σ∈[0..0.10], k∈[2..6]
  D. theta × delta — nouveau delta unique : δ∈[0.01..0.15], θ∈[0.15..0.55]

Résultats dans results/adaptive_*.json
Figures dans figures/adaptive_*.png  (via generate_3d_maps.py)

Usage :
  python adaptive_coupling_campaign.py [--campaign {A,B,C,D,all}] [--dry-run] [--workers N]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent.parent
JUPYTER_DIR = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(JUPYTER_DIR))

from run_simulation import run_and_collect

RESULTS = HERE / "results"
FIGURES = HERE / "figures"
FLOW_THRESHOLD = 0.15
SEED_POOL = [42, 7, 123, 0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12]  # 15 seeds max


# Grilles initiales ──────────────────────────────────────────────────────────

def _delta_override(delta: float) -> dict:
    """Impose delta_endo = delta_exo = delta_liquide."""
    return {
        "taux_depreciation_endo": delta,
        "taux_depreciation_exo": delta,
        "taux_depreciation_liquide": delta,
    }


CAMPAIGNS: dict[str, dict] = {
    "A": {
        "name": "lambda_k_extended",
        "label": "λ × k (étendu, δ unifié)",
        "coarse_grid": [
            {"n_candidats_pool": k, "lambda_creation": lam, "epsilon": 1e-3,
             **_delta_override(0.05)}
            for k in [2, 3, 4, 5, 6, 7, 8]
            for lam in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]
        ],
        "x_param": "lambda_creation", "y_param": "n_candidats_pool",
        "n_steps": 1500,
    },
    "B": {
        "name": "k_mu_extended",
        "label": "k × μ (étendu, δ unifié)",
        "coarse_grid": [
            {"n_candidats_pool": k, "mu": mu, "epsilon": 1e-3,
             **_delta_override(0.05)}
            for k in [2, 3, 4, 5, 6]
            for mu in [0.00, 0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.13, 0.15]
        ],
        "x_param": "n_candidats_pool", "y_param": "mu",
        "n_steps": 1500,
    },
    "C": {
        "name": "sigma_k_extended",
        "label": "σ × k (étendu, δ unifié)",
        "coarse_grid": [
            {"n_candidats_pool": k, "alpha_sigma_brownien": sig, "epsilon": 1e-3,
             **_delta_override(0.05)}
            for k in [2, 3, 4, 5, 6]
            for sig in [0.000, 0.003, 0.007, 0.010, 0.020, 0.035, 0.050, 0.075, 0.100]
        ],
        "x_param": "alpha_sigma_brownien", "y_param": "n_candidats_pool",
        "n_steps": 1500,
    },
    "D": {
        "name": "theta_delta_unified",
        "label": "θ × δ (δ unifié)",
        "coarse_grid": [
            {"theta": theta, "epsilon": 1e-3,
             **_delta_override(delta)}
            for theta in [0.15, 0.20, 0.25, 0.28, 0.32, 0.35, 0.40, 0.45, 0.50, 0.55]
            for delta in [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15]
        ],
        "x_param": "theta", "y_param": "taux_depreciation_endo",
        "n_steps": 1500,
    },
}


def _params_key(params: dict) -> str:
    return "|".join(f"{k}={v}" for k, v in sorted(params.items()))


def _run_one(params: dict, n_steps: int, seed: int) -> dict:
    r = run_and_collect(params, n_steps=n_steps, seed=seed)
    r["_params_key"] = _params_key(params)
    r["_seed"] = seed
    # Strip heavy fields
    for key in ("ts_n_alive", "ts_actif", "ts_n_loans", "ts_failures",
                "ts_densite_fin", "ts_gini", "dist_values_regime"):
        r.pop(key, None)
    return r


def _flow_balanced(r: dict) -> bool:
    flr = r.get("measure_failure_lambda_ratio", 0.0) or 0.0
    return abs(flr - 1.0) < FLOW_THRESHOLD


def _bounded(r: dict) -> bool:
    return bool((r.get("regime_diagnostics") or {}).get("bounded_tail", False))


def _classify(runs: list[dict]) -> str:
    """Classify a parameter point as stable/frontier/ambiguous based on bounded_rate."""
    if not runs:
        return "unknown"
    rate = sum(1 for r in runs if _bounded(r)) / len(runs)
    if rate >= 0.85 or rate <= 0.15:
        return "stable"
    if rate <= 0.20 or rate >= 0.80:
        return "frontier"
    return "ambiguous"


def load_done(fname: Path) -> tuple[list[dict], dict[tuple, list[dict]]]:
    records = json.loads(fname.read_text()) if fname.exists() else []
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        groups[(r["_params_key"], r["_seed"])].append(r)
    return records, groups


def run_adaptive(campaign_key: str, dry_run: bool, n_workers: int) -> None:
    spec = CAMPAIGNS[campaign_key]
    name = spec["name"]
    out = RESULTS / f"adaptive_{name}.json"
    FIGURES.mkdir(exist_ok=True)
    print(f"\n{'='*60}")
    print(f"Campagne {campaign_key}: {spec['label']}")

    records, done_map = load_done(out)

    coarse_grid = spec["coarse_grid"]
    n_steps = spec["n_steps"]

    # Phase 1 : 3 seeds grossières sur toute la grille
    phase1_seeds = SEED_POOL[:3]
    phase1_jobs = [
        (params, seed)
        for params in coarse_grid
        for seed in phase1_seeds
        if (_params_key(params), seed) not in {(k, s) for k, s in done_map}
    ]
    print(f"Phase 1 : {len(phase1_jobs)} jobs ({len(coarse_grid)} pts × {len(phase1_seeds)} seeds)")

    if not dry_run and phase1_jobs:
        _run_jobs(phase1_jobs, n_steps, n_workers, records, out, done_map)

    # Phase 2 : seeds supplémentaires sur les frontières
    groups_by_params: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        groups_by_params[r["_params_key"]].append(r)

    frontier_jobs = []
    ambiguous_jobs = []
    for params in coarse_grid:
        pk = _params_key(params)
        runs = groups_by_params.get(pk, [])
        if len(runs) < 3:
            continue
        classification = _classify(runs)
        done_seeds_for_pt = {r["_seed"] for r in runs}
        remaining = [s for s in SEED_POOL if s not in done_seeds_for_pt]
        if classification == "frontier" and len(runs) < 12:
            needed = 12 - len(runs)
            for s in remaining[:needed]:
                frontier_jobs.append((params, s))
        elif classification == "ambiguous" and len(runs) < 15:
            needed = 15 - len(runs)
            for s in remaining[:needed]:
                ambiguous_jobs.append((params, s))

    print(f"Phase 2a (frontières) : {len(frontier_jobs)} jobs")
    print(f"Phase 2b (ambigus)    : {len(ambiguous_jobs)} jobs")

    if not dry_run and frontier_jobs:
        _run_jobs(frontier_jobs, n_steps, n_workers, records, out, done_map)
    if not dry_run and ambiguous_jobs:
        _run_jobs(ambiguous_jobs, n_steps, n_workers, records, out, done_map)

    # Summary table
    _print_summary(records, spec["x_param"], spec["y_param"])


def _run_jobs(jobs, n_steps, n_workers, records, out, done_map):
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        futures = {ex.submit(_run_one, p, n_steps, s): (p, s) for p, s in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            params, seed = futures[fut]
            try:
                r = fut.result()
                records.append(r)
                bt = _bounded(r)
                fb = _flow_balanced(r)
                print(f"[{i}/{len(jobs)}] {_params_key(params)[:60]}… seed={seed}: bounded={bt} flow={fb}")
            except Exception as e:
                print(f"ERREUR {_params_key(params)} seed={seed}: {e}")
            out.write_text(json.dumps(records, indent=2, ensure_ascii=False))


def _print_summary(records, x_param, y_param):
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        x = r.get("params", {}).get(x_param)
        y = r.get("params", {}).get(y_param)
        if x is not None and y is not None:
            groups[(round(float(x), 6), round(float(y), 6))].append(r)
    xs = sorted(set(k[0] for k in groups))
    ys = sorted(set(k[1] for k in groups))
    print(f"\n{'':>8} " + " ".join(f"{x:>6.3g}" for x in xs))
    for y in ys:
        row = f"{y:>8.3g} "
        for x in xs:
            runs = groups.get((round(x, 6), round(y, 6)), [])
            if not runs:
                row += "   ?  "
                continue
            stat_rate = sum(1 for r in runs if _bounded(r) and _flow_balanced(r)) / len(runs)
            n = len(runs)
            row += f"{stat_rate:>5.2f}({n}) " if stat_rate > 0 else f"  0.0({n}) "
        print(row)
    print("Légende : taux stationnarité (n seeds)")


def _sanitize(v):
    if isinstance(v, dict):
        return {str(k): _sanitize(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize(x) for x in v]
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", default="all", choices=list(CAMPAIGNS) + ["all"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    to_run = list(CAMPAIGNS) if args.campaign == "all" else [args.campaign]
    for key in to_run:
        run_adaptive(key, dry_run=args.dry_run, n_workers=args.workers)

    if not args.dry_run:
        print("\nGénération des figures…")
        import subprocess
        subprocess.run([sys.executable, str(HERE / "claude_analysis" / "generate_3d_maps.py")])


if __name__ == "__main__":
    main()
