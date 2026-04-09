import argparse
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def sd(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


SCRIPT_TEMPLATE = r"""
from config import SimulationConfig
from simulation import Simulation
import math, json

cfg = SimulationConfig(duree_simulation={steps}, seed={seed})
sim = Simulation(cfg)
sim.run(n_steps={steps}, verbose=False)
alive = sim.active_entities()
pvals = [e.passif_total for e in alive if e.passif_total > 0]
alphas = [e.alpha for e in alive if e.passif_total > 0 and hasattr(e, "alpha")]
prod = [e.alpha * math.sqrt(e.passif_total) for e in alive if e.passif_total > 0 and hasattr(e, "alpha")]
esqrt = sum(math.sqrt(p) for p in pvals) / len(pvals) if pvals else None
sqrtmean = math.sqrt(sum(pvals) / len(pvals)) if pvals else None
baralpha = sum(alphas) / len(alphas) if alphas else None
effprod = sum(prod) / len(prod) if prod else None
lifespans = [e.death_step - e.creation_step for e in sim.entities.values() if e.death_step is not None]
censored = [cfg.duree_simulation - e.creation_step for e in sim.entities.values() if e.death_step is None]
out = {{
  "seed": {seed},
  "steps": sim.current_step,
  "entities_total": len(sim.entities),
  "alive_final": len(alive),
  "failures_total": sum(s["n_failures"] for s in sim.stats),
  "mean_extraction": sum(s["extraction_total"] for s in sim.stats) / len(sim.stats),
  "mean_credit_tx": sum(s["credit_transactions"] for s in sim.stats) / len(sim.stats),
  "mean_active_loans": sum(s["n_prets_actifs"] for s in sim.stats) / len(sim.stats),
  "mean_failures_per_step": sum(s["n_failures"] for s in sim.stats) / len(sim.stats),
  "jensen_ratio_final_alive": (esqrt / sqrtmean if pvals and sqrtmean and sqrtmean > 0 else None),
  "pi_eff_over_baralpha_sqrtp": (effprod / (baralpha * sqrtmean) if prod and baralpha and sqrtmean and sqrtmean > 0 else None),
  "mean_alpha_final_alive": baralpha,
  "mean_lifespan_failed": (sum(lifespans) / len(lifespans) if lifespans else None),
  "median_lifespan_failed": (sorted(lifespans)[len(lifespans)//2] if lifespans else None),
  "mean_observed_censored_lifespan": (sum(censored) / len(censored) if censored else None),
  "max_failures_one_step": max(s["n_failures"] for s in sim.stats),
}}
print(json.dumps(out))
"""


def run_seed(src_dir: Path, steps: int, seed: int):
    src_dir = src_dir.resolve()
    with tempfile.NamedTemporaryFile("w", suffix=".py", dir=src_dir, delete=False) as handle:
        handle.write(SCRIPT_TEMPLATE.format(steps=steps, seed=seed))
        temp_path = Path(handle.name)
    try:
        result = subprocess.run(
            ["python3", temp_path.name],
            cwd=src_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout.strip())
    finally:
        temp_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-dir", required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    args = parser.parse_args()

    src_dir = Path(args.src_dir)
    runs = [run_seed(src_dir, args.steps, seed) for seed in args.seeds]
    keys = [
        "alive_final",
        "failures_total",
        "mean_extraction",
        "mean_credit_tx",
        "mean_active_loans",
        "mean_failures_per_step",
        "jensen_ratio_final_alive",
        "pi_eff_over_baralpha_sqrtp",
        "mean_alpha_final_alive",
        "mean_lifespan_failed",
        "median_lifespan_failed",
        "mean_observed_censored_lifespan",
        "max_failures_one_step",
    ]
    aggregate = {key: {"mean": mean([run[key] for run in runs]), "sd": sd([run[key] for run in runs])} for key in keys}
    print(json.dumps({"runs": runs, "aggregate": aggregate}, indent=2))


if __name__ == "__main__":
    main()
