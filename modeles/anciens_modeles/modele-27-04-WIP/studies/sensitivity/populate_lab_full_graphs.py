"""
Ajoute les graphiques complets du modele aux runs exportes dans Simulation Lab.

export_to_simulation_lab.py cree des runs legers a partir des metriques de
l'etude. Pour obtenir les memes artefacts que les simulations lancees depuis le
lab (macro_overview.png, cascades_rank_size.png, figures d'entites, CSV bruts),
il faut relancer le modele avec output.run_and_save puis analysis.analyze_folder.

Ce script est resumable : il ignore par defaut les runs qui contiennent deja
legacy_output/**/figures/macro_overview.png.
"""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import os
import shutil
import sys
import traceback
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STUDY_DIR = Path(__file__).resolve().parent
JUPYTER_DIR = STUDY_DIR.parents[4]
PROJECT_DIR = STUDY_DIR.parents[1]
SRC_DIR = PROJECT_DIR / "src"
LAB_RUNS_DIR = JUPYTER_DIR / "simulation_lab_data" / "runs"
MODEL_ID = "etude_sensibilite_27_04_wip"

PREVIEW_NAMES = [
    "macro_overview.png",
    "indicateurs_systemiques.png",
    "market_overview.png",
    "trajectory.png",
    "distribution.png",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab-runs-dir", type=Path, default=LAB_RUNS_DIR)
    parser.add_argument("--dataset", default="", help="Filtre: alpha_sigma, k_sweep, epsilon_runtime, pilot, lab_guided_probe.")
    parser.add_argument("--run-id", action="append", default=[], help="Run ID exact a traiter; repetable.")
    parser.add_argument("--limit", type=int, default=0, help="Nombre maximum de runs a traiter.")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--force", action="store_true", help="Supprime et regenere legacy_output.")
    parser.add_argument("--keep-csv", action="store_true", help="Conserve les CSV bruts apres generation des figures.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_dirs = select_run_dirs(args.lab_runs_dir, dataset=args.dataset, run_ids=args.run_id)
    if args.limit > 0:
        run_dirs = run_dirs[: args.limit]

    todo = []
    for run_dir in run_dirs:
        if args.force or not has_full_graphs(run_dir) or needs_postprocess(run_dir, keep_csv=args.keep_csv):
            todo.append(run_dir)

    print(f"Runs candidats: {len(run_dirs)} ; a traiter: {len(todo)}")
    for path in todo[:20]:
        print(f"  - {path.name}")
    if len(todo) > 20:
        print(f"  ... +{len(todo) - 20}")
    if args.dry_run or not todo:
        return

    tasks = [(str(path), args.force, args.keep_csv) for path in todo]
    if args.workers <= 1:
        results = [run_one_task(task) for task in tasks]
    else:
        with mp.Pool(processes=args.workers) as pool:
            results = list(pool.imap_unordered(run_one_task, tasks))

    ok = sum(1 for result in results if result["status"] == "ok")
    failed = [result for result in results if result["status"] != "ok"]
    print(f"Termine: {ok} ok, {len(failed)} echecs.")
    for result in failed[:10]:
        print(f"ECHEC {result['run_id']}: {result['error']}")


def select_run_dirs(lab_runs_dir: Path, *, dataset: str, run_ids: list[str]) -> list[Path]:
    if run_ids:
        return [lab_runs_dir / run_id for run_id in run_ids if (lab_runs_dir / run_id / "run.json").exists()]
    prefix = "sensitivity_"
    if dataset:
        prefix += dataset
    run_dirs = []
    for run_dir in sorted(lab_runs_dir.glob(f"{prefix}*")):
        if not run_dir.is_dir():
            continue
        if run_dir.name.endswith("_aggregate") or run_dir.name == "sensitivity_manifest":
            continue
        if not (run_dir / "record.json").exists():
            continue
        meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        if meta.get("model_id") != MODEL_ID:
            continue
        run_dirs.append(run_dir)
    return run_dirs


def has_full_graphs(run_dir: Path) -> bool:
    return any(run_dir.glob("legacy_output/*/figures/macro_overview.png"))


def needs_postprocess(run_dir: Path, *, keep_csv: bool) -> bool:
    if not (run_dir / "compact_timeseries.json").exists() and any(run_dir.glob("legacy_output/*/csv/indicateurs_systemiques.csv")):
        return True
    if not keep_csv and any(run_dir.glob("legacy_output/*/csv/*.csv")):
        return True
    return False


def run_one_task(task: tuple[str, bool, bool]) -> dict[str, str]:
    run_dir = Path(task[0])
    force = task[1]
    keep_csv = task[2]
    run_id = run_dir.name
    try:
        metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        if force:
            shutil.rmtree(run_dir / "legacy_output", ignore_errors=True)
        if has_full_graphs(run_dir):
            write_compact_series(run_dir)
            if not keep_csv:
                delete_csv_files(run_dir)
            refresh_metadata(run_dir)
            return {"run_id": run_id, "status": "ok", "error": ""}

        params = dict(metadata.get("parameters") or {})
        seed = metadata.get("seed")
        if seed is not None:
            params["seed"] = int(seed)
        label = short_label(metadata.get("label") or run_id)
        folder = execute_legacy_run(params, run_dir / "legacy_output", label=label)
        write_compact_series(run_dir)
        if not keep_csv:
            delete_csv_files(run_dir)
        refresh_metadata(run_dir, completed_folder=folder)
        return {"run_id": run_id, "status": "ok", "error": ""}
    except Exception as exc:
        error_path = run_dir / "full_graphs_error.log"
        error_path.write_text(traceback.format_exc(), encoding="utf-8")
        return {"run_id": run_id, "status": "failed", "error": str(exc)}


def execute_legacy_run(params: dict[str, Any], root: Path, *, label: str) -> str:
    sys.path.insert(0, str(SRC_DIR))
    old_cwd = os.getcwd()
    try:
        os.chdir(str(PROJECT_DIR))
        for module_name in ["config", "models", "statistics", "simulation", "output", "analysis"]:
            sys.modules.pop(module_name, None)
        from config import SimulationConfig
        from output import run_and_save
        from analysis import analyze_folder

        allowed = {field.name for field in fields(SimulationConfig)}
        clean_params = {key: value for key, value in params.items() if key in allowed}
        config = SimulationConfig(**clean_params)
        _, folder = run_and_save(
            config=config,
            label=label,
            notes="Graphiques complets regeneres pour Simulation Lab depuis studies/sensitivity.",
            root=str(root),
            verbose=True,
        )
        analyze_folder(folder, label=label)
        return str(folder)
    finally:
        os.chdir(old_cwd)
        try:
            sys.path.remove(str(SRC_DIR))
        except ValueError:
            pass


def refresh_metadata(run_dir: Path, completed_folder: str | None = None) -> None:
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    artifacts = collect_artifacts(run_dir)
    metadata["artifacts"] = artifacts
    preview = select_preview(artifacts)
    metadata["preview_artifact"] = preview["relative_path"] if preview else None
    metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
    metadata.setdefault("extra", {})
    metadata["extra"]["full_graphs"] = True
    if completed_folder:
        metadata["extra"]["full_graphs_folder"] = completed_folder
    metadata["message"] = (metadata.get("message") or "") + "\nGraphiques complets regeneres pour Simulation Lab."
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def write_compact_series(run_dir: Path) -> None:
    """Garde une petite trajectoire JSON avant suppression des CSV lourds."""
    paths = sorted(run_dir.glob("legacy_output/*/csv/indicateurs_systemiques.csv"))
    if not paths:
        return
    stats_path = paths[-1]
    rows = []
    with stats_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(line for line in f if not line.startswith("#"))
        for row in reader:
            step = parse_float(row.get("step"))
            alive = parse_float(row.get("nb_entites"))
            loans = parse_float(row.get("nb_prets"))
            actif = parse_float(row.get("actif_total"))
            volume = parse_float(row.get("volume_prets"))
            rows.append({
                "step": step,
                "alive": alive,
                "actif": actif,
                "volume_prets": volume,
                "densite_fin": parse_float(row.get("densite_financiere")) if row.get("densite_financiere") else safe_ratio(volume, actif),
                "loan_density": safe_ratio(loans, alive),
                "failures": parse_float(row.get("nb_faillites")),
                "gini": parse_float(row.get("gini_actif_total")),
            })
    out = run_dir / "compact_timeseries.json"
    out.write_text(json.dumps({"source": str(stats_path.relative_to(run_dir)), "rows": rows}, ensure_ascii=False), encoding="utf-8")


def delete_csv_files(run_dir: Path) -> None:
    for csv_path in run_dir.glob("legacy_output/*/csv/*.csv"):
        csv_path.unlink(missing_ok=True)
    for csv_dir in run_dir.glob("legacy_output/*/csv"):
        try:
            csv_dir.rmdir()
        except OSError:
            pass


def collect_artifacts(run_dir: Path) -> list[dict[str, str]]:
    artifacts = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(run_dir)
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        if path.name == "run.json":
            continue
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".gif"}:
            kind = "image"
        elif suffix == ".csv":
            kind = "csv"
        elif suffix in {".json", ".txt", ".md", ".log"}:
            kind = "text"
        else:
            kind = "file"
        artifacts.append({
            "relative_path": str(rel),
            "kind": kind,
            "label": path.name,
            "description": "",
        })
    return artifacts


def select_preview(artifacts: list[dict[str, str]]) -> dict[str, str] | None:
    images = [artifact for artifact in artifacts if artifact.get("kind") == "image"]
    for name in PREVIEW_NAMES:
        for artifact in images:
            if artifact.get("label") == name:
                return artifact
    return images[0] if images else None


def short_label(label: str) -> str:
    keep = []
    for char in label.lower():
        if char.isalnum():
            keep.append(char)
        elif char in {" ", "_", "-", ".", "="}:
            keep.append("_")
    text = "".join(keep).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    return text[:60] or "sensitivity"


def parse_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        result = float(value)
        return result if result == result and abs(result) != float("inf") else 0.0
    except ValueError:
        return 0.0


def safe_ratio(num: float, den: float) -> float:
    return num / den if den else 0.0


if __name__ == "__main__":
    main()
