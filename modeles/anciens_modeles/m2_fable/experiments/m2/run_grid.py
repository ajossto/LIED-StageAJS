"""Grille de robustesse §6.5 + balayage k (SOC).

Grille : sigma in {0.15, 0.25, 0.35} x eps0/w0 in {0.05, 0.25, 0.5}
         x k in {3, 6}, w0=30 fixe (d0 = w0*(1-ratio)), 1 seed, T=2000.
Balayage k : k in {2, 3, 4, 6} à la baseline (k=6 déjà couvert par baseline_s0,
k=3 par la grille) — cases k=2 et k=4 ajoutées ici.
"""
from exp_common import M2Config, run_one

SIGMAS = (0.15, 0.25, 0.35)
EPS_RATIOS = (0.05, 0.25, 0.5)
KS = (3, 6)

if __name__ == "__main__":
    for sigma in SIGMAS:
        for ratio in EPS_RATIOS:
            for k in KS:
                d0 = 30.0 * (1.0 - ratio)
                cfg = M2Config(seed=0, T=2000, sigma=sigma, k=k, w0=30.0, d0=d0)
                rid = f"grid_sig{sigma:g}_eps{ratio:g}_k{k}"
                run_one(cfg, rid, log_every=1000)
    for k in (2, 4):
        cfg = M2Config(seed=0, T=2000, k=k)
        run_one(cfg, f"ksweep_k{k}", log_every=1000)
