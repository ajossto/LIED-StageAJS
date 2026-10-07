"""Baseline M2 : paramètres du rapport (§8.1 du brief), 3 seeds, T=2000.
alpha=1, delta=0.05, k=6, sigma=0.25, lam=10, w0=30, d0=28, N(0)=0.
Snapshots denses sur [1500,1521) pour les incréments 1 pas (seed 0 à 2)."""
from exp_common import M2Config, run_one

SEEDS = (0, 1, 2)

if __name__ == "__main__":
    for seed in SEEDS:
        cfg = M2Config(seed=seed, T=2000)
        run_one(cfg, f"baseline_s{seed}", dense_from=1500)
