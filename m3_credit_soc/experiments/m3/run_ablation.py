"""Ablations pré-enregistrées B-J du rapport 02 §7.

Usage : run_ablation.py --which B [--seeds 0 1 2] [--T 2000]
Chaque ablation = baseline calibrée + un seul champ modifié.
"""
import argparse

from exp_common import M3Config, run_one

ABLATIONS = {
    "B": dict(credit=False),
    "C": dict(loan_target="L"),
    "D": dict(claim_loss="compensated"),
    "E": dict(flow_loss="annuity"),
    "F": dict(market_selection="random"),
    "G1a": dict(shock_rho_macro=0.25),
    "G1b": dict(shock_rho_macro=0.5),
    "G2": dict(shock_rho_sector=0.5),
    # exploratoires post-hoc (rapport 05) : F'' topologie sans étouffer le
    # marché ; G2+ corrélation sectorielle renforcée
    "F2": dict(market_selection="random_lender"),
    "G2b": dict(shock_rho_sector=0.8),
    "G2c": dict(shock_rho_sector=0.5, n_sectors=3),
    "H": dict(d0=0.0),
    "I": dict(lam=0.0, n_init=1000),
    "Ja": dict(lam=3.0),
    "Jb": dict(lam=30.0),
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", required=True, choices=sorted(ABLATIONS))
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--T", type=int, default=2000)
    args = ap.parse_args()
    for seed in args.seeds:
        cfg = M3Config(seed=seed, T=args.T, **ABLATIONS[args.which])
        run_one(cfg, f"abl_{args.which}_s{seed}", dense_from=args.T - 500)
