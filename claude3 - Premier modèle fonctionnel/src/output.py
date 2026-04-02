"""
output.py — Gestion des dossiers de sortie.

Structure :
  simulations/simu_YYYYMMDD_HHMMSS_<label>_<hash7>/
    meta.json          — paramètres + résumé (reproductibilité)
    figures/           — graphiques PNG
    csv/               — données CSV
"""

import datetime
import hashlib
import json
import os
from dataclasses import asdict
from typing import Optional


def create_output_folder(config, label: str = "", root: str = "simulations") -> str:
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
    sim.collector.export_all(csv_dir, entities=sim.entities)

    if verbose:
        print("\nRésumé :")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        print(f"\nDossier complet : {folder}")

    return sim, folder


def read_meta(folder: str) -> dict:
    path = os.path.join(folder, "meta.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_simulations(root: str = "simulations") -> list:
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
