"""
exemple.py — Exemple minimal d'exécution et d'analyse de la simulation.

Usage : python exemple.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from simulation import Simulation
from parametres import PARAMS
import copy


def main():
    print("=" * 60)
    print("SIMULATION MULTI-AGENTS — Système autocritique de joules")
    print("=" * 60)

    # --------------------------------------------------------
    # Scénario 1 : Simulation standard
    # --------------------------------------------------------
    print("\n--- Scénario 1 : Paramètres standard ---")
    params = copy.deepcopy(PARAMS)
    params["nb_pas"] = 2500
    params["graine"] = 42

    sim = Simulation(params)
    stats = sim.run(verbose=True)

    sim.exporter_csv("resultats_scenario1.csv")
    resume = sim.resume()
    print("\nRésumé final :")
    for k, v in resume.items():
        print(f"  {k}: {v}")

    # --------------------------------------------------------
    # Scénario 2 : Système fragile (fort levier)
    # --------------------------------------------------------
    print("\n--- Scénario 2 : Système fragile (theta élevé, mu bas) ---")
    params2 = copy.deepcopy(PARAMS)
    params2["nb_pas"] = 100
    params2["graine"] = 1
    params2["theta"] = 0.9        # emprunteurs très gourmands
    params2["mu"] = 0.01          # critère d'acceptation très lâche
    params2["seuil_ratio_liquide_passif"] = 0.02  # marché très ouvert

    sim2 = Simulation(params2)
    stats2 = sim2.run(verbose=True)
    resume2 = sim2.resume()
    print("\nRésumé final (fragile) :")
    for k, v in resume2.items():
        print(f"  {k}: {v}")

    # --------------------------------------------------------
    # Scénario 3 : Système robuste (prudent)
    # --------------------------------------------------------
    print("\n--- Scénario 3 : Système robuste (theta bas, mu élevé) ---")
    params3 = copy.deepcopy(PARAMS)
    params3["nb_pas"] = 100
    params3["graine"] = 2
    params3["theta"] = 0.2        # emprunteurs prudents
    params3["mu"] = 0.2           # critère exigeant
    params3["seuil_ratio_liquide_passif"] = 0.15  # marché restrictif

    sim3 = Simulation(params3)
    stats3 = sim3.run(verbose=True)
    resume3 = sim3.resume()
    print("\nRésumé final (robuste) :")
    for k, v in resume3.items():
        print(f"  {k}: {v}")

    # --------------------------------------------------------
    # Comparaison des cascades
    # --------------------------------------------------------
    print("\n--- Comparaison des cascades ---")
    print(f"{'Scénario':<20} {'Faillites total':>16} {'Cascade max':>12} {'Entités finales':>16}")
    print("-" * 68)
    for label, r in [("Standard", resume), ("Fragile", resume2), ("Robuste", resume3)]:
        print(f"{label:<20} {r['faillites_total']:>16} {r['cascade_max']:>12} {r['entites_vivantes_final']:>16}")

    # --------------------------------------------------------
    # Analyse statistique basique des faillites
    # --------------------------------------------------------
    print("\n--- Distribution des tailles de cascade (Scénario 1) ---")
    cascades = [s["nb_faillites"] for s in stats if s["nb_faillites"] > 0]
    if cascades:
        print(f"  Nombre de pas avec au moins 1 faillite : {len(cascades)}")
        print(f"  Taille moyenne des cascades             : {sum(cascades)/len(cascades):.2f}")
        print(f"  Taille maximale                         : {max(cascades)}")
        # Distribution
        from collections import Counter
        dist = Counter(cascades)
        print("  Distribution :")
        for taille in sorted(dist.keys())[:15]:
            barre = "#" * dist[taille]
            print(f"    {taille:4d} faillite(s) : {barre} ({dist[taille]})")
    else:
        print("  Aucune faillite enregistrée.")

    # --------------------------------------------------------
    # Évolution temporelle (ASCII simple)
    # --------------------------------------------------------
    print("\n--- Évolution du nombre d'entités (Scénario 1) ---")
    max_entites = max(s["nb_entites_vivantes"] for s in stats) or 1
    largeur = 40
    for i, s in enumerate(stats):
        if (i + 1) % 10 == 0:
            n = s["nb_entites_vivantes"]
            barre = "#" * int(n / max_entites * largeur)
            print(f"  Pas {s['pas']:4d} | {barre:<{largeur}} {n}")

    # --------------------------------------------------------
    # Scénario 4 : Régime avec cascades (calibré pour faillites)
    # --------------------------------------------------------
    print("\n--- Scénario 4 : Régime avec cascades de faillites ---")
    params4 = copy.deepcopy(PARAMS)
    params4["nb_pas"] = 150
    params4["graine"] = 42
    params4["alpha"] = 0.5                        # extraction faible
    params4["taux_depreciation_endo"] = 0.08      # dépréciation forte
    params4["taux_depreciation_exo"] = 0.08
    params4["taux_depreciation_liquide"] = 0.05
    params4["fraction_auto_investissement"] = 0.5
    params4["theta"] = 0.8
    params4["mu"] = 0.01
    params4["seuil_ratio_liquide_passif"] = 0.02
    params4["lambda_creation"] = 0.8
    params4["actif_liquide_initial"] = 8.0
    params4["passif_inne_initial"] = 10.0

    sim4 = Simulation(params4)
    stats4 = sim4.run(verbose=True)
    sim4.exporter_csv("resultats_scenario4_cascades.csv")
    resume4 = sim4.resume()
    print("\nRésumé final (cascades) :")
    for k, v in resume4.items():
        print(f"  {k}: {v}")

    print("\n--- Distribution des tailles de cascade (Scénario 4) ---")
    cascades4 = [s["nb_faillites"] for s in stats4 if s["nb_faillites"] > 0]
    if cascades4:
        from collections import Counter
        print(f"  Pas avec au moins 1 faillite : {len(cascades4)}")
        print(f"  Taille moyenne des cascades  : {sum(cascades4)/len(cascades4):.2f}")
        print(f"  Taille maximale              : {max(cascades4)}")
        dist4 = Counter(cascades4)
        print("  Distribution :")
        for taille in sorted(dist4.keys()):
            barre = "#" * dist4[taille]
            print(f"    {taille:4d} faillite(s) : {barre} ({dist4[taille]})")

    print("\nFichiers exportés : resultats_scenario1.csv, resultats_scenario4_cascades.csv")
    print("Simulation terminée.")


if __name__ == "__main__":
    main()
