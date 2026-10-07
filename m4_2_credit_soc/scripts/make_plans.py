"""Écrit les plans de campagne M4.2 (manifests/<plan>.json).

Les volets et leurs cellules sont ceux du protocole pré-enregistré
(report/protocole.pdf, version 1 du 27 juillet 2026). Les cellules λ=30,
T=4000 du volet taille_finie sont identiques à celles des pilotes : le
cell_id déterministe fait que run_campaign les réutilise sans les relancer.

Usage : make_plans.py [--confirm g033,g067] (le plan confirm n'est généré
qu'après les pilotes, avec les γ retenus passés en argument).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MANIFESTS = Path(__file__).resolve().parents[1] / "manifests"

GAMMA_GRID = {
    "g033": 1.0 / 3.0,
    "g040": 0.4,
    "g050": 0.5,
    "g060": 0.6,
    "g067": 2.0 / 3.0,
}
DELTA = 0.05
# Ablation d'échelle : A_norm(γ) = (δ/(1-δ))·K_ref^(1-γ), K_ref = 361 = 19².
A_NORM = {name: (DELTA / (1.0 - DELTA)) * 361.0 ** (1.0 - g)
          for name, g in GAMMA_GRID.items()}

BASE = dict(A=1.0, lam=30.0, delta=DELTA, sigma=0.25, K0=25.0,
            pop_max=30_000, snapshot_every=0, individual_every=0,
            figures=False)


def cell(name: str, n_runs: int = 3, base_seed: int = 1, **params) -> dict:
    parameters = dict(BASE)
    parameters.update(params)
    return {"name": name, "parameters": parameters,
            "n_runs": n_runs, "base_seed": base_seed}


def write(name: str, cells: list[dict], note: str) -> None:
    MANIFESTS.mkdir(exist_ok=True)
    payload = {"plan": name, "note": note, "cells": cells}
    (MANIFESTS / f"{name}.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False))
    print(f"{name}: {len(cells)} cellules")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", default="",
                        help="γ retenus pour la confirmation (noms, virgules)")
    args = parser.parse_args()

    write("benchmark", [
        cell("bench_g033", n_runs=1, gamma=GAMMA_GRID["g033"], T=4000),
        cell("bench_g067", n_runs=1, gamma=GAMMA_GRID["g067"], T=4000),
    ], "Volet 0 : calibrage du coût réel M4.2 aux γ extrêmes (graine 1).")

    pilote_cells = [
        cell(name, gamma=g, T=4000) for name, g in GAMMA_GRID.items()
    ] + [cell("g075_sonde", n_runs=1, gamma=0.75, T=4000)]
    write("pilotes", pilote_cells,
          "Volet 1 (exploratoire) : grille γ, λ=30, T=4000, graines 1-3 "
          "+ sonde γ=0,75 (1 graine).")

    taille_cells = []
    for name, g in GAMMA_GRID.items():
        taille_cells.append(cell(f"{name}_lam10", gamma=g, lam=10.0, T=8000))
        taille_cells.append(cell(f"{name}_lam30", gamma=g, lam=30.0, T=4000))
        taille_cells.append(cell(f"{name}_lam100", gamma=g, lam=100.0, T=4000))
    write("taille_finie", taille_cells,
          "Volet 2 : γ × λ∈{10,30,100}, graines 1-3. Les cellules λ=30 "
          "sont réutilisées des pilotes (même cell_id).")

    write("horizon_double", [
        cell(f"{name}_T8000", gamma=GAMMA_GRID[name], T=8000)
        for name in ("g033", "g050", "g067")
    ], "Volet 3 : robustesse à l'horizon (λ=30, T=8000, graines 1-3).")

    write("ablation_A", [
        cell(f"{name}_Anorm", gamma=GAMMA_GRID[name], A=A_NORM[name], T=4000)
        for name in ("g033", "g060", "g067")
    ], "Volet 5 : contrôle d'échelle apparié A_norm(γ)=19^(1-2γ), "
       "K_ref=361 J, graines 1-3. g060 ajouté le 27/07 (décision datée "
       "avant les runs : contrôle d'échelle du pic τ̂(γ=0,6) élevé au rang "
       "de contraste confirmatoire).")

    write("mecanisme", [
        cell(f"{name}_meca", n_runs=1, gamma=g, T=4000,
             snapshot_every=50, individual_every=5, figures=True)
        for name, g in GAMMA_GRID.items()
    ], "Volet 6 : instantanés denses pour la chaîne causale (graine 1, "
       "figures activées — cellules centrales).")

    write("hypothese_K0", [
        cell("k0_match_g033", gamma=0.5, K0=108.7, T=4000),
        cell("k0_match_g067", gamma=0.5, K0=1.31, T=4000),
    ], "Hypothèse structurelle (27/07, datée avant runs) : τ̂ piloté par "
       "K0/K*_aut. À γ=1/2 fixe, K0 reproduit les rapports des cellules "
       "extrêmes (0,301 et 0,0036). Prédictions si vraie : τ̂≈1,89 et ≈1,99.")

    if args.confirm:
        names = [s for s in args.confirm.split(",") if s]
        confirm_cells = [
            cell(f"{name}_confirm", n_runs=5, base_seed=11,
                 gamma=GAMMA_GRID[name], T=4000,
                 snapshot_every=100, figures=True)
            for name in names
        ]
        write("confirm", confirm_cells,
              "Volet 4 : graines confirmatoires 11-15, figures et keep "
              "(exécuter run_campaign --plan confirm --keep "
              "--cell-workers 5 --parallel-cells 1).")


if __name__ == "__main__":
    main()
