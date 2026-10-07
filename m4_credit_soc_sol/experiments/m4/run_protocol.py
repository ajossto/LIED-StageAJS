"""Campagnes M4 reproductibles sur le moteur sans d0."""
import argparse

from exp_common import run_one
from m4 import M4Config


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("sector", "iid", "sector_destroy",
                                         "sector_adaptive", "sector_concentrated",
                                         "sector_liquid", "sector_capital",
                                         "sector_capital30"),
                    required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--T", type=int, default=4000)
    ap.add_argument("--lam", type=float, default=10.0)
    args = ap.parse_args()
    rho = 0.8 if args.variant != "iid" else 0.0
    residual = "destroy" if args.variant == "sector_destroy" else "prorata"
    adaptive = args.variant == "sector_adaptive"
    concentrated = args.variant == "sector_concentrated"
    liquid = args.variant == "sector_liquid"
    capital = args.variant in ("sector_capital", "sector_capital30")
    capital_ratio = 0.30 if args.variant == "sector_capital30" else 0.10
    cfg = M4Config(seed=args.seed, T=args.T, lam=args.lam,
                   shock_rho_sector=rho, fail_residual=residual,
                   adaptive_credit=adaptive,
                   portfolio_limit=3 if concentrated else 0,
                   loan_target="L" if liquid else "K",
                   capital_ratio=capital_ratio if capital else 0.0)
    lam_tag = str(args.lam).replace(".", "p")
    run_id = f"m4_contract_{args.variant}_T{args.T}_lam{lam_tag}_s{args.seed}"
    run_one(cfg, run_id, log_every=1000, snapshot_every=100)
