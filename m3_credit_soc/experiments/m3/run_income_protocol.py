"""Mini-protocole X1 : règle de maximisation du revenu net (post-M3, exploratoire
devenu protocole dédié — voir reports/07_income_rule).

L'emprunteuse vise K*(r) au lieu de K*(r+delta) ; avec le taux en moyenne
géométrique, K*(r) = sqrt(K_l * K_b) (égalisation des capitaux par le crédit).
L'ablation sans crédit de X1 est IDENTIQUE à l'ablation B de M3 (l'objectif
n'intervient que dans run_market, inerte quand credit=False) : elle n'est pas
relancée, on compare aux runs abl_B_s*.

Cellules : baseline X1 (3 seeds) + scan de robustesse (sigma, k, s ; 3 seeds).
Usage : run_income_protocol.py [--T 2000] [--seeds 0 1 2]
"""
import argparse

from exp_common import M3Config, run_one

CELLS = {
    "x1_base": dict(),
    "x1_sig02": dict(sigma=0.20),
    "x1_sig03": dict(sigma=0.30),
    "x1_k3": dict(k=3),
    "x1_k12": dict(k=12),
    "x1_ret09": dict(s=0.9),
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--T", type=int, default=2000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--cells", nargs="+", default=sorted(CELLS))
    args = ap.parse_args()
    for cell in args.cells:
        for seed in args.seeds:
            cfg = M3Config(seed=seed, T=args.T, objective="income",
                           **CELLS[cell])
            run_one(cfg, f"{cell}_s{seed}", dense_from=args.T - 500,
                    log_every=0)
