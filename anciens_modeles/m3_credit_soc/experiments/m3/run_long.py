"""Run long M3 : stabilité de queue par fenêtres sur horizon étendu.

Usage : run_long.py [--seeds 0 1] [--T 10000] [--variant baseline|B]
"""
import argparse

from exp_common import M3Config, run_one

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    ap.add_argument("--T", type=int, default=10000)
    ap.add_argument("--variant", default="baseline", choices=["baseline", "B"])
    args = ap.parse_args()
    for seed in args.seeds:
        kw = dict(credit=False) if args.variant == "B" else {}
        cfg = M3Config(seed=seed, T=args.T, **kw)
        run_one(cfg, f"long_{args.variant}_s{seed}", snapshot_every=100)
