"""
sortie.py — Gestion des dossiers de sortie auto-labellisés.

Chaque simulation crée un dossier unique contenant :
  - meta.json          : tous les paramètres + résumé final
  - indicateurs_systemiques.csv
  - snapshots_distributions.csv
  - cascades_faillites.csv
  - distrib_brute_*.csv (une par grandeur, valeurs brutes)
  - tailles_cascades_brutes.csv

Le dossier est nommé automatiquement :
  resultats/YYYYMMDD_HHMMSS_<label>_<hash_params>/
"""

import os
import json
import hashlib
import datetime
from typing import Optional


def creer_dossier_sortie(params: dict, label: str = "", dossier_racine: str = "resultats") -> str:
    """
    Crée et retourne le chemin d'un dossier de sortie unique et informatif.

    Nommage :
      resultats/YYYYMMDD_HHMMSS_<label>_<hash7>/

    Le hash de 7 caractères est basé sur les paramètres, de sorte que deux
    simulations avec des paramètres identiques aient le même hash
    (utile pour détecter des doublons).
    """
    os.makedirs(dossier_racine, exist_ok=True)

    # Timestamp
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Hash court des paramètres (reproductible)
    params_str = json.dumps(params, sort_keys=True)
    hash_court = hashlib.md5(params_str.encode()).hexdigest()[:7]

    # Nom du dossier
    label_propre = label.replace(" ", "_").lower() if label else "sim"
    nom_dossier = f"{ts}_{label_propre}_{hash_court}"

    chemin = os.path.join(dossier_racine, nom_dossier)
    os.makedirs(chemin, exist_ok=True)
    return chemin


def sauvegarder_meta(dossier: str, params: dict, resume: dict, label: str = "", notes: str = ""):
    """
    Sauvegarde les métadonnées complètes de la simulation dans meta.json.

    Contient :
      - label et notes libres
      - tous les paramètres
      - résumé final (entités, faillites, etc.)
      - horodatage
    """
    meta = {
        "label": label,
        "notes": notes,
        "date": datetime.datetime.now().isoformat(),
        "parametres": params,
        "resume": resume,
    }
    chemin_meta = os.path.join(dossier, "meta.json")
    with open(chemin_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"  → meta.json sauvegardé")


def lancer_et_sauvegarder(params: dict,
                           label: str = "",
                           notes: str = "",
                           freq_snapshot: int = 10,
                           verbose: bool = True,
                           dossier_racine: str = "resultats") -> tuple:
    """
    Fonction tout-en-un : crée la simulation, la lance, et sauvegarde tout.

    Retourne (simulation, dossier_sortie).

    Exemple :
        from sortie import lancer_et_sauvegarder
        sim, dossier = lancer_et_sauvegarder(params, label="fragile", freq_snapshot=5)
    """
    # Import ici pour éviter les imports circulaires
    from simulation import Simulation

    # Dossier de sortie
    dossier = creer_dossier_sortie(params, label=label, dossier_racine=dossier_racine)
    if verbose:
        print(f"\nDossier de sortie : {dossier}")

    # Simulation
    sim = Simulation(params, freq_snapshot=freq_snapshot)
    sim.run(verbose=verbose)

    # Export
    resume = sim.resume()
    sauvegarder_meta(dossier, params, resume, label=label, notes=notes)
    print(f"Export des statistiques :")
    sim.exporter_stats_completes(dossier)

    # Stats légères aussi (rétrocompatibilité)
    sim.exporter_csv(os.path.join(dossier, "stats_legeres.csv"))

    if verbose:
        print(f"\nRésumé :")
        for k, v in resume.items():
            print(f"  {k}: {v}")
        print(f"\nDossier complet : {dossier}")

    return sim, dossier


def lire_meta(dossier: str) -> dict:
    """Lit le meta.json d'un dossier de résultats."""
    chemin = os.path.join(dossier, "meta.json")
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def lister_simulations(dossier_racine: str = "resultats") -> list:
    """
    Liste toutes les simulations disponibles dans le dossier racine.
    Retourne une liste de dicts {dossier, label, date, resume}.
    """
    if not os.path.exists(dossier_racine):
        return []
    sims = []
    for nom in sorted(os.listdir(dossier_racine)):
        chemin = os.path.join(dossier_racine, nom)
        if os.path.isdir(chemin):
            meta_path = os.path.join(chemin, "meta.json")
            if os.path.exists(meta_path):
                try:
                    meta = lire_meta(chemin)
                    sims.append({
                        "dossier": chemin,
                        "nom": nom,
                        "label": meta.get("label", ""),
                        "date": meta.get("date", ""),
                        "resume": meta.get("resume", {}),
                    })
                except Exception:
                    pass
    return sims
