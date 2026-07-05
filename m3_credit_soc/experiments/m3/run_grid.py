"""Grille de paramètres M3 : robustesse de la forme et recherche d'une zone
SOC (rapport 02 §9). Axes : sigma, s, c, k, d0. Un seed par cellule au
premier passage (screening) ; cellules intéressantes répliquées ensuite.

Usage : run_grid.py [--axis sigma|s|c|k|d0|all] [--T 2000] [--seeds 0]
"""
import argparse

from exp_common import M3Config, run_one

AXES = {
    "sigma": [("sigma", v) for v in (0.15, 0.20, 0.30, 0.35)],
    "s": [("s", v) for v in (0.5, 0.65, 0.9)],
    "c": [("c", v) for v in (0.02, 0.10)],
    "k": [("k", v) for v in (2, 3, 12)],
    "d0": [("d0", v) for v in (20.0, 25.0, 29.0)],
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--axis", default="all")
    ap.add_argument("--T", type=int, default=2000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    args = ap.parse_args()
    axes = AXES if args.axis == "all" else {args.axis: AXES[args.axis]}
    for axis, cells in axes.items():
        for field, val in cells:
            for seed in args.seeds:
                cfg = M3Config(seed=seed, T=args.T, **{field: val})
                run_one(cfg, f"grid_{field}{val}_s{seed}", log_every=0,
                        snapshot_every=100)
