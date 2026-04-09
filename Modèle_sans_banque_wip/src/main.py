"""
main.py — Point d'entrée principal de la simulation.

Utilisation rapide :
    python main.py

Ou depuis un notebook / script Python :
    from config import SimulationConfig
    from output import run_and_save
    sim, folder = run_and_save(SimulationConfig(), label="mon_scenario")
"""

import sys
import os

# Assurer que src/ est dans le path si lancé depuis la racine du projet
sys.path.insert(0, os.path.dirname(__file__))

from config import SimulationConfig
from output import run_and_save
from analysis import analyze_folder


def main():
    config = SimulationConfig()

    print("=" * 60)
    print("  Simulation multi-agents — Système autocritique de joules")
    print("=" * 60)
    print(f"  Paramètres principaux :")
    print(f"    alpha                     = [{config.alpha_min}, {config.alpha_max}]")
    print(f"    alpha_sigma_brownien      = {config.alpha_sigma_brownien}")
    print(f"    seuil_ratio_liquide_passif= {config.seuil_ratio_liquide_passif}")
    print(f"    theta                     = {config.theta}")
    print(f"    mu                        = {config.mu}")
    print(f"    fraction_taux_emprunteur  = {config.fraction_taux_emprunteur:.2f}")
    print(f"    taux_amortissement        = {config.taux_amortissement}")
    print(f"    n_candidats_pool          = {config.n_candidats_pool}")
    print(f"    lambda_creation           = {config.lambda_creation}")
    print(f"    n_entites_initiales       = {config.n_entites_initiales}")
    print(f"    passif_inne_initial       = {config.passif_inne_initial}")
    print(f"    taux_depreciation_liquide = {config.taux_depreciation_liquide}")
    print(f"    duree_simulation          = {config.duree_simulation} pas")
    print()

    sim, folder = run_and_save(
        config=config,
        label="scenario_base",
        notes="Bloc 8 — matching aléatoire pool=3, theta=0.35, lambda=2 : régime SOC avec intermédiaires et cascades",
        root="resultats",
        verbose=True,
    )

    print("\nLancement de l'analyse :")
    analyze_folder(folder)


if __name__ == "__main__":
    main()
