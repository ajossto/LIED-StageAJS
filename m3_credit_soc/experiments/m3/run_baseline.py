"""Baseline M3 (protocole A) : configuration calibrée du rapport 02,
multi-seed. Snapshots denses sur [T-500, T-479) pour les incréments 1 pas.

Usage : run_baseline.py [--seeds 0 1 2 3 4] [--T 4000]
"""
import argparse

from exp_common import M3Config, run_one

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--T", type=int, default=4000)
    args = ap.parse_args()
    for seed in args.seeds:
        cfg = M3Config(seed=seed, T=args.T)
        run_one(cfg, f"baseline_s{seed}", dense_from=args.T - 500)
