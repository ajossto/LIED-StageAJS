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
    print(f"    alpha                     = {config.alpha}")
    print(f"    seuil_ratio_liquide_passif= {config.seuil_ratio_liquide_passif}")
    print(f"    theta                     = {config.theta}")
    print(f"    mu                        = {config.mu}")
    print(f"    lambda_creation           = {config.lambda_creation}")
    print(f"    passif_inne_initial       = {config.passif_inne_initial}")
    print(f"    taux_depreciation_liquide = {config.taux_depreciation_liquide}")
    print(f"    duree_simulation          = {config.duree_simulation} pas")
    print(f"    taux crédit               = {'prêteur' if config.use_lender_rate_as_offer_rate else 'moyenne'}")
    print()

    sim, folder = run_and_save(
        config=config,
        label="scenario_base",
        notes="Paramètres Claude, durée 3000 pas, taux prêteur, auto-invest sur surplus",
        root="resultats",
        verbose=True,
    )

    print("\nLancement de l'analyse :")
    analyze_folder(folder)


if __name__ == "__main__":
    main()
