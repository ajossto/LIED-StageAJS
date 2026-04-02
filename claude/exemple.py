"""
exemple.py — Exemple d'exécution, d'analyse et de comparaison de scénarios.

Usage : python exemple.py

Produit dans resultats/ :
  - Un dossier par scénario avec tous les CSV et graphiques
  - Un graphique de comparaison multi-scénarios
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import copy
from parametres import PARAMS
from sortie import lancer_et_sauvegarder, lister_simulations
from analyse import analyser_dossier, graphique_comparaison


def scenario_standard():
    p = copy.deepcopy(PARAMS)
    p["nb_pas"] = 200
    p["graine"] = 42
    return p


def scenario_fragile():
    p = copy.deepcopy(PARAMS)
    p["nb_pas"] = 200
    p["graine"] = 1
    p["alpha"] = 0.8
    p["theta"] = 0.85
    p["mu"] = 0.005
    p["seuil_ratio_liquide_passif"] = 0.02
    p["taux_depreciation_endo"] = 0.05
    p["taux_depreciation_exo"] = 0.05
    p["taux_depreciation_liquide"] = 0.04
    p["fraction_auto_investissement"] = 0.45
    p["lambda_creation"] = 1.5
    p["actif_liquide_initial"] = 12.0
    p["passif_inne_initial"] = 8.0
    return p


def scenario_robuste():
    p = copy.deepcopy(PARAMS)
    p["nb_pas"] = 200
    p["graine"] = 2
    p["theta"] = 0.15
    p["mu"] = 0.25
    p["seuil_ratio_liquide_passif"] = 0.20
    p["lambda_creation"] = 0.4
    return p


def scenario_critique():
    """
    Regime proche de la criticalite : cascades de tailles variees.
    C'est ici que les lois de puissance peuvent apparaitre.
    """
    p = copy.deepcopy(PARAMS)
    p["nb_pas"] = 300
    p["graine"] = 7
    p["alpha"] = 0.7
    p["theta"] = 0.65
    p["mu"] = 0.02
    p["seuil_ratio_liquide_passif"] = 0.03
    p["taux_depreciation_endo"] = 0.045
    p["taux_depreciation_exo"] = 0.045
    p["taux_depreciation_liquide"] = 0.03
    p["fraction_auto_investissement"] = 0.4
    p["lambda_creation"] = 1.2
    p["actif_liquide_initial"] = 10.0
    p["passif_inne_initial"] = 7.0
    p["coefficient_reliquefaction"] = 0.4
    return p


def main():
    print("=" * 65)
    print("SIMULATION MULTI-AGENTS — Systeme autocritique de joules")
    print("=" * 65)

    scenarios = [
        ("standard", "Reference — croissance sans crise",        scenario_standard()),
        ("fragile",  "Fragile — cascades recurrentes",           scenario_fragile()),
        ("robuste",  "Robuste — marche restrictif",              scenario_robuste()),
        ("critique", "Critique — recherche de loi de puissance", scenario_critique()),
    ]

    dossiers = []
    labels = []

    for nom, description, params in scenarios:
        print(f"\n{'='*65}")
        print(f"Scenario : {nom.upper()} — {description}")
        print('='*65)

        sim, dossier = lancer_et_sauvegarder(
            params,
            label=nom,
            notes=description,
            freq_snapshot=5,
            verbose=True,
            dossier_racine="resultats"
        )

        analyser_dossier(dossier, verbose=False)

        dossiers.append(dossier)
        labels.append(f"{nom} ({params['nb_pas']} pas)")

    print("\n" + "="*65)
    print("Comparaison multi-scenarios")
    print("="*65)
    graphique_comparaison(dossiers, labels, dossier_sortie="resultats")

    print("\n" + "="*65)
    print("Simulations disponibles dans resultats/ :")
    print("="*65)
    for s in lister_simulations("resultats"):
        r = s.get("resume", {})
        print(f"  {s['nom']}")
        print(f"    Label    : {s['label']}")
        print(f"    Faillites: {r.get('faillites_total','?')}  |  "
              f"Cascade max: {r.get('cascade_max','?')}  |  "
              f"Entites finales: {r.get('entites_vivantes_final','?')}")


if __name__ == "__main__":
    main()
