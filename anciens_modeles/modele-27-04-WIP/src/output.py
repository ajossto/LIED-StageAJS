"""
output.py — Gestion des dossiers de résultats de simulation.

Chaque simulation produit un dossier horodaté de la forme :
    <root>/simu_YYYYMMDD_HHMMSS_<label>_<hash7>/
      meta.json              — paramètres complets + résumé (reproductibilité)
      csv/                   — données brutes exportées par statistics.Collector
          stats_legeres.csv
          indicateurs_systemiques.csv
          snapshots_distributions.csv
          cascades_faillites.csv
          tailles_cascades_brutes.csv
          distrib_brute_*.csv
          entity_histories.csv
          entity_meta.csv
      figures/               — graphiques PNG produits par analysis.py

Le hash de 7 caractères dans le nom du dossier est un MD5 tronqué de la
configuration sérialisée. Deux runs avec la même config (même seed) produisent
le même hash, facilitant la comparaison.

Usage typique (depuis main.py ou un notebook) :
    from config import SimulationConfig
    from output import run_and_save
    sim, folder = run_and_save(SimulationConfig(), label="mon_scenario")
"""

import datetime
import hashlib
import json
import os
from dataclasses import asdict
from typing import Optional


def create_output_folder(config, label: str = "", root: str = "simulations") -> str:
    """
    Crée la structure de dossiers pour une simulation et retourne son chemin.

    Le nom du dossier encode :
      - l'horodatage (YYYYMMDD_HHMMSS) pour l'ordre chronologique,
      - le label nettoyé (espaces → underscores, minuscules),
      - un hash MD5 court de la config pour détecter les doublons.

    Sous-dossiers créés : figures/ et csv/.
    """
    os.makedirs(root, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    config_str = json.dumps(asdict(config), sort_keys=True)
    hash7 = hashlib.md5(config_str.encode()).hexdigest()[:7]
    label_clean = label.replace(" ", "_").lower() if label else "sim"
    folder_name = f"simu_{ts}_{label_clean}_{hash7}"
    path = os.path.join(root, folder_name)
    os.makedirs(os.path.join(path, "figures"), exist_ok=True)
    os.makedirs(os.path.join(path, "csv"), exist_ok=True)
    return path


def save_meta(folder: str, config, summary: dict, label: str = "", notes: str = ""):
    """
    Sauvegarde un fichier meta.json dans le dossier de sortie.

    Contenu : label, notes libres, horodatage ISO, config complète (via dataclasses.asdict),
    et le résumé statistique produit par Simulation.summary().
    Ce fichier suffit à reproduire exactement la simulation (même seed → même trajectoire).
    """
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
    root: str = "simulations",
    verbose: bool = True,
):
    """
    Lance une simulation complète et sauvegarde tous les résultats.

    Enchaîne :
      1. create_output_folder()  — crée la structure de dossiers
      2. Simulation(config).run() — exécute la simulation
      3. save_meta()              — sauvegarde meta.json
      4. sim.export_stats_csv()   — exporte stats_legeres.csv
      5. collector.export_all()   — exporte tous les CSV statistiques

    Retourne (sim, folder) pour permettre des analyses post-hoc dans un notebook.

    Paramètres :
        config  — SimulationConfig (par défaut : valeurs Bloc 8)
        label   — identifiant lisible du scénario (ex : "scenario_base")
        notes   — texte libre décrivant le scénario
        root    — dossier racine des résultats (relatif au cwd)
        verbose — affiche la progression et le résumé
    """
    from config import SimulationConfig
    from simulation import Simulation

    if config is None:
        config = SimulationConfig()

    folder = create_output_folder(config, label=label, root=root)
    csv_dir = os.path.join(folder, "csv")

    if verbose:
        print(f"\nDossier de sortie : {folder}")

    sim = Simulation(config)
    sim.run(verbose=verbose)

    summary = sim.summary()
    print("\nExport des données :")
    save_meta(folder, config, summary, label=label, notes=notes)
    sim.export_stats_csv(os.path.join(csv_dir, "stats_legeres.csv"))
    print(f"  → stats_legeres.csv ({len(sim.stats)} lignes)")
    sim.collector.export_all(csv_dir, entities=sim.entities, loans=sim.loans)

    if verbose:
        print("\nRésumé :")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        print(f"\nDossier complet : {folder}")

    return sim, folder


def read_meta(folder: str) -> dict:
    """Lit et retourne le contenu de meta.json pour un dossier de simulation."""
    path = os.path.join(folder, "meta.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_simulations(root: str = "simulations") -> list:
    """
    Liste toutes les simulations présentes dans un dossier racine.

    Retourne une liste de dicts :
        [{"folder": ..., "name": ..., "label": ..., "date": ..., "summary": ...}, ...]
    triée par ordre alphabétique (= chronologique grâce à l'horodatage dans le nom).
    Les dossiers sans meta.json valide sont silencieusement ignorés.
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
