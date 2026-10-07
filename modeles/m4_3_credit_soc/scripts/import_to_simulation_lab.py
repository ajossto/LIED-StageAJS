"""Enregistre les runs M4.3 déjà terminés (figures générées) auprès de
`simulation_lab` (`simulation_lab_data/runs/`), pour qu'ils apparaissent
dans `list-runs`/le GUI --- répond au constat utilisateur du 2026-08-09 :
« je ne peux pas voir les nouvelles simulations faites dans
simulation_lab ». Root cause : `run_pilot.py`/`campaign_relaunch_figures.py`
écrivent directement dans `m4_3_credit_soc/results/`, sans jamais passer
par `RunStorage.create_run()`/`finalize_run()` --- `simulation_lab` n'a
donc aucune connaissance de ces runs (mécanisme confirmé en lisant
`simulation_lab/runs/storage.py` : le seul chemin de découverte externe,
`list_external_runs()`, cherche un fichier `meta.json` avec un schéma
différent, pas adapté sans modifier du code partagé).

Choix : SYMLINK (pas copie) de chaque dossier de run dans
`simulation_lab_data/runs/<run_id>/`, avec un `run.json` écrit dedans au
format managé standard (mêmes clés que `RunStorage.create_run()`/
`finalize_run()`). Vérifié avant d'adopter ce choix : `delete_run()`
utilise `shutil.move` sur le dossier top-level (déplace le lien, pas la
cible) et `empty_trash()`/`collect_artifacts()` n'descendent jamais dans
un lien symbolique de façon destructive --- supprimer un run importé
depuis le GUI ne touche donc jamais les données M4.3 réelles, seulement
le lien. Pas de duplication disque (les 96 runs D1+D3 pèsent déjà
plusieurs Go cumulés après figures).

Idempotent : peut être relancé à tout moment (ex. à chaque avancée de
`campaign_relaunch_figures.py`) --- ne recrée rien qui existe déjà, mais
rafraîchit `run.json` (artefacts, résumé) à chaque passage."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUPYTER_ROOT = ROOT.parent.parent
sys.path.insert(0, str(JUPYTER_ROOT))

from simulation_lab.contracts import collect_artifacts  # noqa: E402
from simulation_lab.settings import RUNS_DIR, ensure_directories  # noqa: E402

MODEL_ID = "m4_3_credit_soc"

# (sous-dossier sous results/, préfixe d'étiquette)
PHASES = (
    ("pilot", "pilote"),
    ("d1", "D1"),
    ("d3_size", "D3"),
)


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _run_id_for(phase_dir: str, cell: str, seed_name: str) -> str:
    safe_cell = cell.replace("/", "_")
    return f"m4_3__{phase_dir}__{safe_cell}__{seed_name}"


def _import_one(run_dir: Path, phase_dir: str, phase_label: str, cell: str) -> str:
    seed_name = run_dir.name  # "seed0", "seed1", ...
    run_id = _run_id_for(phase_dir, cell, seed_name)
    link_path = RUNS_DIR / run_id

    if not link_path.exists():
        link_path.symlink_to(run_dir.resolve(), target_is_directory=True)

    config = _load_json(run_dir / "config.json")
    parameters = config.get("parameters", config)
    summary = _load_json(run_dir / "summary.json")
    analysis = _load_json(run_dir / "analysis.json")
    merged_summary = {**summary, **{f"analysis_{k}": v for k, v in analysis.items()
                                     if k not in ("params", "label")}}

    mtime = (run_dir / "summary.json").stat().st_mtime if (run_dir / "summary.json").exists() \
        else run_dir.stat().st_mtime
    created_at = _iso(mtime)

    seed = parameters.get("seed")
    if seed is None:
        try:
            seed = int(seed_name.replace("seed", ""))
        except ValueError:
            seed = 0

    metadata = {
        "run_id": run_id,
        "model_id": MODEL_ID,
        "parameters": parameters,
        "seed": seed,
        "label": f"{phase_label}/{cell}/{seed_name}",
        "batch_id": None,
        "status": "completed",
        "keep": False,
        "important": False,
        "trashed": False,
        "trashed_at": None,
        "archived": False,
        "created_at": created_at,
        "updated_at": _iso(datetime.now(timezone.utc).timestamp()),
        "summary": merged_summary,
        "artifacts": [artifact.to_dict() for artifact in collect_artifacts(run_dir)],
        "message": f"Importé depuis {run_dir.relative_to(JUPYTER_ROOT)}",
        "extra": {"source_path": str(run_dir)},
    }
    (run_dir / "run.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return run_id


def main() -> None:
    ensure_directories()
    imported, skipped = 0, 0
    for phase_dir, phase_label in PHASES:
        phase_root = ROOT / "results" / phase_dir
        if not phase_root.exists():
            continue
        for cell_dir in sorted(phase_root.iterdir()):
            if not cell_dir.is_dir():
                continue
            for seed_dir in sorted(cell_dir.glob("seed*")):
                if not (seed_dir / "figures" / "macro_overview.png").exists():
                    skipped += 1
                    continue
                run_id = _import_one(seed_dir, phase_dir, phase_label, cell_dir.name)
                imported += 1
                print(f"  {run_id}", flush=True)
    print(f"\n{imported} runs enregistrés (symlink + run.json), "
          f"{skipped} ignorés (figures pas encore générées).")


if __name__ == "__main__":
    main()
