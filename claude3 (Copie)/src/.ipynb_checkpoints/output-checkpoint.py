"""
output.py — Gestion des dossiers de sortie auto-labellisés.

Chaque simulation crée un dossier unique contenant :
  - meta.json                       : paramètres + résumé final
  - stats_legeres.csv               : statistiques agrégées par pas
  - indicateurs_systemiques.csv     : indicateurs agrégés du système
  - snapshots_distributions.csv     : statistiques résumées des distributions
  - cascades_faillites.csv          : données détaillées de chaque cascade
  - tailles_cascades_brutes.csv     : volumes bruts pour analyse loi de puissance
  - distrib_brute_*.csv             : valeurs individuelles par entité

Nommage automatique :
  resultats/YYYYMMDD_HHMMSS_<label>_<hash7>/
"""

import datetime
import hashlib
import json
import os
from dataclasses import asdict
from typing import Optional


def create_output_folder(config, label: str = "", root: str = "resultats") -> str:
    """
    Crée et retourne le chemin d'un dossier de sortie unique.
    Le hash de 7 caractères est basé sur la configuration, pour détecter
    les doublons entre simulations aux paramètres identiques.
    """
    os.makedirs(root, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    config_str = json.dumps(asdict(config), sort_keys=True)
    hash7 = hashlib.md5(config_str.encode()).hexdigest()[:7]

    label_clean = label.replace(" ", "_").lower() if label else "sim"
    folder_name = f"{ts}_{label_clean}_{hash7}"

    path = os.path.join(root, folder_name)
    os.makedirs(path, exist_ok=True)
    return path


def save_meta(folder: str, config, summary: dict, label: str = "", notes: str = ""):
    """
    Sauvegarde les métadonnées de la simulation dans meta.json.
    Contient : label, notes, date, configuration complète, résumé final.
    """
    from dataclasses import asdict
    meta = {
        "label": label,
        "notes": notes,
        "date": datetime.datetime.now().isoformat(),
        "config": asdict(config),
        "summary": summary,
    }
    path = os.path.join(folder, "meta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"  → meta.json sauvegardé")


def run_and_save(
    config=None,
    label: str = "",
    notes: str = "",
    root: str = "resultats",
    verbose: bool = True,
):
    """
    Fonction tout-en-un : crée la simulation, la lance, et sauvegarde tout.
    Retourne (simulation, dossier_sortie).

    Exemple :
        from output import run_and_save
        from config import SimulationConfig
        sim, folder = run_and_save(SimulationConfig(), label="scenario_base")
    """
    from config import SimulationConfig
    from simulation import Simulation

    if config is None:
        config = SimulationConfig()

    folder = create_output_folder(config, label=label, root=root)
    if verbose:
        print(f"\nDossier de sortie : {folder}")

    sim = Simulation(config)
    sim.run(verbose=verbose)

    summary = sim.summary()
    print("\nExport des données :")
    save_meta(folder, config, summary, label=label, notes=notes)
    sim.export_stats_csv(os.path.join(folder, "stats_legeres.csv"))
    print(f"  → stats_legeres.csv ({len(sim.stats)} lignes)")
    sim.collector.export_all(folder)

    if verbose:
        print("\nRésumé :")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        print(f"\nDossier complet : {folder}")

    return sim, folder


def read_meta(folder: str) -> dict:
    """Lit le meta.json d'un dossier de résultats."""
    path = os.path.join(folder, "meta.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_simulations(root: str = "resultats") -> list:
    """
    Liste toutes les simulations disponibles dans le dossier racine.
    Retourne une liste de dicts {folder, label, date, summary}.
    """
    if not os.path.exists(root):
        return []
    sims = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if os.path.isdir(path):
            meta_path = os.path.join(path, "meta.json")
            if os.path.exists(meta_path):
                try:
                    meta = read_meta(path)
                    sims.append({
                        "folder": path,
                        "name": name,
                        "label": meta.get("label", ""),
                        "date": meta.get("date", ""),
                        "summary": meta.get("summary", {}),
                    })
                except Exception:
                    pass
    return sims
