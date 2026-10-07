#!/usr/bin/env python3
"""
regen_all_graphs.py — Régénère les figures de toutes les simulations qui ont déjà un CSV.

Usage :
    python3 regen_all_graphs.py [--workers N] [--dry-run]

workers : nombre de processus parallèles (défaut : 4)
dry-run : liste les dossiers sans régénérer
"""

import argparse
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

JUPYTER_ROOT = Path(__file__).resolve().parent.parent
LEGACY_ROOT = JUPYTER_ROOT / "anciens_modeles"
MSB_SRC  = LEGACY_ROOT / "Modèle_sans_banque" / "src"
WIP_SRC  = LEGACY_ROOT / "modele-27-04-WIP" / "src"
CV2_SRC  = LEGACY_ROOT / "claude3-v2" / "src"
RUNS_DIR = JUPYTER_ROOT / "simulation_lab_data" / "runs"

MODEL_ID_TO_SRC = {
    "modele_sans_banque_wip":      MSB_SRC,
    "modele_27_04_wip":            WIP_SRC,
    "etude_sensibilite_27_04_wip": WIP_SRC,
}


def _find_simu_folders(root: Path) -> list:
    folders = []
    for child in root.glob("simu_*"):
        if child.is_dir() and (child / "csv").exists():
            folders.append(child)
    return sorted(folders)


def _collect_jobs() -> list:
    jobs = []

    # Simulations legacy hors simulation_lab_data
    for resultats_dir in [MSB_SRC.parent / "resultats", MSB_SRC / "resultats"]:
        if resultats_dir.exists():
            for folder in _find_simu_folders(resultats_dir):
                jobs.append((folder, MSB_SRC))

    resultats_v2 = CV2_SRC / "resultats"
    if resultats_v2.exists():
        for folder in _find_simu_folders(resultats_v2):
            jobs.append((folder, CV2_SRC))

    # Simulations simulation_lab_data — model_id → analysis.py
    if RUNS_DIR.exists():
        for run_dir in sorted(RUNS_DIR.iterdir()):
            run_json = run_dir / "run.json"
            if not run_json.exists():
                continue
            try:
                model_id = json.loads(run_json.read_text(encoding="utf-8"))["model_id"]
            except Exception:
                continue
            src_dir = MODEL_ID_TO_SRC.get(model_id)
            if src_dir is None:
                continue
            legacy_out = run_dir / "legacy_output"
            if not legacy_out.exists():
                continue
            for child in sorted(legacy_out.iterdir()):
                if child.is_dir() and (child / "csv").exists():
                    jobs.append((child, src_dir))

    return jobs


def _regen_one(args):
    folder_str, src_dir_str = args
    folder = Path(folder_str)
    src_dir = Path(src_dir_str)
    sys.path.insert(0, str(src_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            f"analysis_{folder.name}", src_dir / "analysis.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.analyze_folder(str(folder))
        return (folder_str, "OK", None)
    except Exception as exc:
        return (folder_str, "ERROR", str(exc))
    finally:
        try:
            sys.path.remove(str(src_dir))
        except ValueError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    jobs = _collect_jobs()
    print(f"{len(jobs)} dossiers à traiter :")
    for folder, src in jobs:
        print(f"  [{src.parent.name}]  {folder.name}")

    if args.dry_run or not jobs:
        return

    print(f"\nRégénération avec {args.workers} worker(s)…")
    t0 = time.time()
    serializable = [(str(f), str(s)) for f, s in jobs]

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_regen_one, job): job[0] for job in serializable}
        ok = 0
        errors = []
        for future in as_completed(futures):
            folder_str, status, err = future.result()
            name = Path(folder_str).name
            if status == "OK":
                ok += 1
                print(f"  ✓  {name}")
            else:
                errors.append((name, err))
                print(f"  ✗  {name}  →  {err}")

    elapsed = time.time() - t0
    print(f"\n{ok}/{len(jobs)} OK en {elapsed:.0f}s")
    if errors:
        print("Erreurs :")
        for name, err in errors:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()
