"""Balayages M4 : grilles nommées de cellules (config, seeds), exécution
séquentielle avec stats SOC imprimées après chaque run.

Usage : /home/anatole/jupyter/.venv/bin/python3 run_sweep.py <SWEEP> [...]
Sweeps définis dans SWEEPS ; les runs déjà faits (summary.json) sont sautés.

NB : les runs préfixés a1_/a2_/a3_/b_/m4_first (results/) datent du moteur
L/K pré-refonte, archivé dans archive/m4_lk_pre_refonte/ — les sweeps
correspondants ne sont plus définis ici (leurs champs de config n'existent
plus). Les sweeps ci-dessous utilisent le moteur fusionné (refonte
2026-07-14, k=3, cancel+destroy, chocs iid, objectif revenu par défaut).
"""
import json
import sys

from exp_common import run_one, RESULTS
from m4 import M4Config
from soc_stats import soc_stats, _fmt

SEEDS = (0, 1, 2)


def _cells(name, seeds=SEEDS, **fixed):
    return [(f"{name}_s{seed}", {**fixed, "seed": seed}) for seed in seeds]


SWEEPS = {
    # C : le candidat (défauts de config) en scaling de taille de système
    "C": (_cells("c_lam10", lam=10.0)
          + _cells("c_lam30", lam=30.0)
          + _cells("c_lam100", lam=100.0)),
    # CT : robustesse au temps de simulation (piège n°7 du brief)
    "CT": _cells("ct_lam30_T4000", lam=30.0, T=4000),
    # F : campagne confirmatoire de la CONFIG FINALE (défauts du moteur :
    # k=3, cancel+destroy, rounds_div=1 — un round par tête). Scaling en
    # taille de système + robustesse T. NB : les runs c_/ct_/abl_ datent du
    # défaut intermédiaire rounds_div=k (b=0,20) — configs dans leurs
    # config.json respectifs.
    "F": (_cells("f_lam10", lam=10.0)
          + _cells("f_lam30", lam=30.0)
          + _cells("f_lam100", lam=100.0)
          + _cells("f_lam30_T4000", lam=30.0, T=4000)
          + [("f_lam300_s0", dict(lam=300.0, seed=0))]),
    # V : dose-réponse volume de marché -> rapport de branchement b
    # (la courbe-clé du mécanisme ; version moteur des scans prototype)
    "V": (_cells("v_r6", lam=30.0, rounds_div=6)
          + _cells("v_r3", lam=30.0, rounds_div=3)
          + _cells("v_r2", lam=30.0, rounds_div=2)),  # r1 = f_lam30 (sweep F)
    # CABL : ablations à un levier autour du candidat (lam=30)
    "CABL": (
        _cells("abl_cancel_only", lam=30.0, fail_residual="prorata")
        + _cells("abl_destroy_only", lam=30.0, fail_lender_loans="transfer")
        + _cells("abl_m3rule", lam=30.0, fail_lender_loans="transfer",
                 fail_residual="prorata")
        + _cells("abl_wealth", lam=30.0, objective="wealth")
        + _cells("abl_birthloan", lam=30.0, birth_loan=True)
        + _cells("abl_k2", lam=30.0, k=2)
        + _cells("abl_k6", lam=30.0, k=6)
        + _cells("abl_sector", lam=30.0, shock_rho_sector=0.8)
    ),
}


def run_sweep(name):
    cells = SWEEPS[name]
    lines = []
    for run_id, overrides in cells:
        cfg = M4Config(T=overrides.pop("T", 2000), **overrides)
        run_one(cfg, run_id, log_every=1000, snapshot_every=250)
        st = soc_stats(RESULTS / run_id)
        fig_dir = RESULTS / run_id / "figures"
        fig_dir.mkdir(exist_ok=True)
        with open(fig_dir / "soc_stats.json", "w") as fh:
            json.dump(st, fh, indent=2)
        line = _fmt(st)
        print(line, flush=True)
        lines.append(line)
    print(f"\n=== {name} terminé ===")
    for line in lines:
        print(line)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        run_sweep(arg)
