"""Probe nouveau H x X1 x G2 : plancher contractuel, revenu, secteurs.

La condition de conclusion pré-run est consignée dans NOTES.md.
"""
import argparse

from exp_common import run_one
from m4 import M4Config


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--T", type=int, default=1000)
    args = ap.parse_args()
    cfg = M4Config(seed=args.seed, T=args.T)
    run_one(cfg, f"probe_hx1g2_T{args.T}_s{args.seed}", log_every=500,
            snapshot_every=100)
