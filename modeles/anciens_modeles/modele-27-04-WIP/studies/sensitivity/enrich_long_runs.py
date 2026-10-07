"""
enrich_long_runs.py — Génère les artefacts complets (CSVs + figures) pour les
simulations longues k3 σ=0.005 à 10 000 pas déjà enregistrées dans simulation_lab.

Pour chaque seed (0, 1, 2, 3, 7, 123) :
  - Re-lance la simulation avec les mêmes paramètres via run_and_save()
  - Appelle analyze_folder() pour générer toutes les figures
  - Stocke l'output dans legacy_output/ du run existant
  - Met à jour run.json avec la liste complète des artefacts

Usage :
  python enrich_long_runs.py [--workers N] [--seeds S [S ...]] [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

LEGACY_DIR = Path(__file__).resolve().parents[3]
JUPYTER_DIR = LEGACY_DIR.parent.parent
SRC_DIR = LEGACY_DIR / "modele-27-04-WIP" / "src"
LAB_RUNS_DIR = JUPYTER_DIR / "simulation_lab_data" / "runs"

# Paramètres identiques à long_run_k3sigma0005_10k.py
BASELINE = {
    "theta": 0.35,
    "mu": 0.05,
    "lambda_creation": 2.0,
    "n_candidats_pool": 3,
    "fraction_taux_emprunteur": 0.2,
    "seuil_ratio_endettement": 1.0,
    "seuil_ratio_liquide_passif": 0.05,
    "taux_depreciation_endo": 0.05,
    "taux_depreciation_exo": 0.05,
    "fraction_auto_investissement": 0.5,
    "coefficient_reliquefaction": 0.5,
    "actif_liquide_initial": 200.0,
    "passif_inne_initial": 190.0,
    "n_entites_initiales": 100,
}
FIXED_PARAMS = {
    "alpha_min": 1.0,
    "alpha_max": 1.0,
    "alpha_sigma_brownien": 0.0,
    "taux_amortissement": 0.0,
    "log_events": False,
    "freq_snapshot": 50,
}
PARAMS_OVERRIDE = {
    "alpha_sigma_brownien": 0.005,
    "n_candidats_pool": 3,
    "epsilon": 0.001,
}
N_STEPS = 10_000
ALL_SEEDS = [0, 1, 2, 3, 7, 123]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _worker(seed: int) -> dict:
    """Exécuté dans un sous-processus isolé."""
    import matplotlib
    matplotlib.use("Agg")

    # Chargement des modules src/
    sys.path.insert(0, str(SRC_DIR))
    cfg_mod = _load_module(SRC_DIR / "config.py", f"cfg_{seed}")
    out_mod = _load_module(SRC_DIR / "output.py", f"out_{seed}")
    ana_mod = _load_module(SRC_DIR / "analysis.py", f"ana_{seed}")

    SimulationConfig = getattr(cfg_mod, "SimulationConfig")
    run_and_save = getattr(out_mod, "run_and_save")
    analyze_folder = getattr(ana_mod, "analyze_folder")

    params = {**BASELINE, **FIXED_PARAMS, **PARAMS_OVERRIDE, "seed": seed, "duree_simulation": N_STEPS}
    config = SimulationConfig(**params)

    run_id = f"sensitivity_claude_long_run_k3sigma0005_10k_seed{seed}"
    run_dir = LAB_RUNS_DIR / run_id
    legacy_root = run_dir / "legacy_output"

    print(f"[seed={seed}] Démarrage run_and_save…", flush=True)
    t0 = time.perf_counter()
    _, folder = run_and_save(
        config=config,
        label=f"k3_sigma0005_10k_seed{seed}",
        notes="Enrichissement artefacts long run 10k — simulation_lab",
        root=str(legacy_root),
        verbose=False,
    )
    elapsed_run = time.perf_counter() - t0
    print(f"[seed={seed}] run_and_save terminé en {elapsed_run:.0f}s → {folder}", flush=True)

    print(f"[seed={seed}] Analyse figures…", flush=True)
    t1 = time.perf_counter()
    try:
        analyze_folder(folder)
    except Exception as e:
        print(f"[seed={seed}] WARN analyze_folder: {e}", flush=True)
    elapsed_ana = time.perf_counter() - t1
    print(f"[seed={seed}] Figures générées en {elapsed_ana:.0f}s", flush=True)

    return {"seed": seed, "run_id": run_id, "folder": folder, "elapsed_s": time.perf_counter() - t0}


def _update_run_json(run_id: str, folder: str) -> None:
    from simulation_lab.contracts import collect_artifacts

    run_dir = LAB_RUNS_DIR / run_id
    run_json_path = run_dir / "run.json"
    if not run_json_path.exists():
        print(f"  WARN: run.json introuvable pour {run_id}")
        return

    meta = json.loads(run_json_path.read_text(encoding="utf-8"))
    artifacts = [a.to_dict() for a in collect_artifacts(run_dir)]

    # Choisir le meilleur preview (macro_overview > overview)
    preview = None
    for a in artifacts:
        rp = a["relative_path"]
        if "macro_overview.png" in rp:
            preview = rp
            break
    if preview is None:
        for a in artifacts:
            if a.get("kind") == "image":
                preview = a["relative_path"]
                break

    meta["artifacts"] = artifacts
    meta["preview_artifact"] = preview or meta.get("preview_artifact", "overview.png")
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta.setdefault("extra", {})["legacy_output_folder"] = Path(folder).name
    meta["extra"]["enriched_at"] = datetime.now(timezone.utc).isoformat()

    run_json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  run.json mis à jour : {len(artifacts)} artefacts, preview={preview}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 6))
    parser.add_argument("--seeds", type=int, nargs="+", default=ALL_SEEDS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(JUPYTER_DIR))

    print(f"Seeds : {args.seeds}")
    print(f"Workers : {args.workers}")
    print(f"N_STEPS : {N_STEPS}")
    print(f"Runs dir : {LAB_RUNS_DIR}")

    # Vérifier que les run dirs existent
    missing = [s for s in args.seeds
               if not (LAB_RUNS_DIR / f"sensitivity_claude_long_run_k3sigma0005_10k_seed{s}").exists()]
    if missing:
        print(f"WARN: run dirs manquants pour seeds {missing} — seront ignorés")
        args.seeds = [s for s in args.seeds if s not in missing]

    if args.dry_run:
        print("Mode dry-run : rien n'est exécuté.")
        return

    t_global = time.perf_counter()
    results = []

    with ProcessPoolExecutor(max_workers=args.workers) as exe:
        futures = {exe.submit(_worker, seed): seed for seed in args.seeds}
        for fut in as_completed(futures):
            seed = futures[fut]
            try:
                r = fut.result()
                results.append(r)
                print(f"✓ seed={seed} terminé en {r['elapsed_s']:.0f}s")
                print(f"  Mise à jour run.json…")
                _update_run_json(r["run_id"], r["folder"])
            except Exception as e:
                print(f"✗ seed={seed}: {e}")

    elapsed_total = time.perf_counter() - t_global
    print(f"\nTerminé en {elapsed_total:.0f}s ({elapsed_total/60:.1f} min)")
    print(f"Seeds réussies : {sorted(r['seed'] for r in results)}")


if __name__ == "__main__":
    main()
