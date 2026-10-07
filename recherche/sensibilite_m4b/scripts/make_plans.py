"""Génère les plans d'expérience figés par le protocole.

Usage :
    make_plans.py oat        # courbes un-facteur-à-la-fois + axe de taille
    make_plans.py lhs        # plan global espace-remplissant (graine 20260717)

Les coupes 2D et la confirmation sont générées par des scripts dédiés une
fois le screening dépouillé (le protocole exige que leur choix soit
postérieur et documenté).
"""

from __future__ import annotations

import sys

import numpy as np

import lib_runs as L

EXPLORATION_SEEDS = (1, 2, 3)

OAT_CENTER = dict(lam=30.0, delta=0.05, sigma=0.25, K0=25.0, k=3, T=2000)
OAT_AXES = {
    "delta": [0.02, 0.03, 0.05, 0.07, 0.10],
    "sigma": [0.0, 0.10, 0.15, 0.20, 0.25, 0.325, 0.40, 0.50],
    "K0": [5.0, 10.0, 25.0, 50.0, 100.0],
    "k": [2, 3, 4, 6, 10],
    "lam": [10.0, 30.0, 100.0],
}


def oat_cells() -> list[dict]:
    cells, seen = [], set()
    for axis, values in OAT_AXES.items():
        for value in values:
            spec = dict(OAT_CENTER)
            spec[axis] = value
            for seed in EXPLORATION_SEEDS:
                full = L.cell(seed=seed, **spec)
                rid = L.run_id(full)
                if rid not in seen:
                    seen.add(rid)
                    cells.append(full)
    return cells


LHS_BOUNDS = {"delta": (0.02, 0.10), "sigma": (0.05, 0.50)}
LHS_K0_LOG = (5.0, 100.0)
LHS_K_LEVELS = (2, 3, 4, 6, 10)
LHS_N = 64
LHS_SEED = 20260717


def lhs_points() -> list[dict]:
    """Hypercube latin stratifié sur (delta, sigma, K0-log), k équilibré."""
    rng = np.random.default_rng(LHS_SEED)
    n = LHS_N
    columns = {}
    for name in ("delta", "sigma", "logK0"):
        strata = (np.arange(n) + rng.random(n)) / n
        columns[name] = rng.permutation(strata)
    k_column = np.array([LHS_K_LEVELS[i % len(LHS_K_LEVELS)] for i in range(n)])
    rng.shuffle(k_column)

    points = []
    for i in range(n):
        delta = LHS_BOUNDS["delta"][0] + columns["delta"][i] * (
            LHS_BOUNDS["delta"][1] - LHS_BOUNDS["delta"][0])
        sigma = LHS_BOUNDS["sigma"][0] + columns["sigma"][i] * (
            LHS_BOUNDS["sigma"][1] - LHS_BOUNDS["sigma"][0])
        log_lo, log_hi = np.log(LHS_K0_LOG)
        K0 = float(np.exp(log_lo + columns["logK0"][i] * (log_hi - log_lo)))
        points.append(dict(
            lam=30.0, T=2000,
            delta=round(float(delta), 6),
            sigma=round(float(sigma), 6),
            K0=round(K0, 4),
            k=int(k_column[i]),
        ))
    return points


def lhs_cells() -> list[dict]:
    cells = []
    for point in lhs_points():
        for seed in EXPLORATION_SEEDS:
            cells.append(L.cell(seed=seed, **point))
    return cells


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "oat":
        cells = oat_cells()
        path = L.save_plan("oat", cells, notes=(
            "OAT autour du centre lam=30 delta=0.05 sigma=0.25 K0=25 k=3 T=2000 ; "
            "axes delta/sigma/K0/k + axe de taille lam ; graines 1-3 partagées."))
    elif which == "lhs":
        cells = lhs_cells()
        path = L.save_plan("lhs", cells, notes=(
            f"Hypercube latin stratifié {LHS_N} points (delta lin, sigma lin, K0 log, "
            f"k équilibré {LHS_K_LEVELS}), lam=30, T=2000, graine du plan {LHS_SEED}, "
            "graines simulation 1-3."))
    else:
        sys.exit("usage: make_plans.py oat|lhs")
    print(path, len(cells), "cellules")


if __name__ == "__main__":
    main()
