"""Premier run simple de M4 : baseline G2b (chocs sectoriels corrélés
rho_sector=0.8) + X1 revenu (objective="income"), mêmes paramètres hérités
que la baseline M3 sinon (s=0.75, c=0.10, T=2000).

Usage : /home/anatole/jupyter/.venv/bin/python3 experiments/m4/run_first.py
"""
from exp_common import run_one
from m4 import M4Config

if __name__ == "__main__":
    cfg = M4Config(seed=0, T=2000)
    run_one(cfg, "m4_first_s0", log_every=500)
