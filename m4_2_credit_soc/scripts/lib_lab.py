"""Orchestration de la campagne M4.2 via Simulation Lab.

Décision utilisateur (2026-07-27) : tous les runs de campagne sont des runs
Simulation Lab, visibles dans l'interface ; les 28 figures ne sont générées
que pour la confirmation et les cellules centrales (paramètre ``figures`` de
l'adaptateur). Patron hérité de
recherche/sensibilite_m4b/scripts/run_confirm.py (lot lab par cellule via
``python -m simulation_lab.cli batch``), enrichi :

- identifiant de cellule déterministe (SHA-256 de la configuration complète
  + condensat du moteur), pour la reprise et la traçabilité ;
- index global ``manifests/cells_index.json`` associant chaque cellule à ses
  ``run_id`` lab — un plan qui contient une cellule déjà exécutée (même
  cell_id) la réutilise au lieu de la relancer ;
- manifeste par plan ``manifests/<plan>.manifest.json``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

PYTHON = "/home/anatole/jupyter/.venv/bin/python3"
PROJECT = Path("/home/anatole/jupyter")
MODEL_ID = "m4_2_credit_soc"
ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "manifests"
LAB_RUNS = PROJECT / "simulation_lab_data" / "runs"
ENGINE_FILES = ("m4_2/__init__.py", "m4_2/model.py", "m4_2/io.py")


def engine_hash() -> str:
    """Condensat SHA-256 tronqué des fichiers du moteur (fait foi)."""
    digest = hashlib.sha256()
    for name in ENGINE_FILES:
        digest.update(name.encode())
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()[:16]


def cell_id(cell: dict, engine: str | None = None) -> str:
    """Identifiant déterministe d'une cellule (paramètres + graines + moteur)."""
    payload = {
        "model": MODEL_ID,
        "engine": engine or engine_hash(),
        "parameters": cell["parameters"],
        "n_runs": cell["n_runs"],
        "base_seed": cell["base_seed"],
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _index_path() -> Path:
    return MANIFESTS / "cells_index.json"


def load_index() -> dict:
    path = _index_path()
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_index(index: dict) -> None:
    MANIFESTS.mkdir(exist_ok=True)
    _index_path().write_text(json.dumps(index, indent=1, ensure_ascii=False))


def runs_completed(run_ids: list[str]) -> bool:
    """Vrai si chaque run du lot existe et est au statut « completed »."""
    if not run_ids:
        return False
    for run_id in run_ids:
        meta_path = LAB_RUNS / run_id / "run.json"
        if not meta_path.exists():
            return False
        if json.loads(meta_path.read_text()).get("status") != "completed":
            return False
    return True


def launch_cell(plan_name: str, cell: dict, workers: int, keep: bool = False) -> dict:
    """Exécute une cellule comme lot Simulation Lab et renvoie son entrée."""
    label = f"M4.2 — {plan_name} — {cell['name']}"
    command = [
        PYTHON, "-m", "simulation_lab.cli", "batch",
        "--model", MODEL_ID,
        "--params", json.dumps(cell["parameters"]),
        "--runs", str(cell["n_runs"]),
        "--workers", str(max(1, min(workers, 6))),
        "--base-seed", str(cell["base_seed"]),
        "--label", label,
    ]
    started = time.monotonic()
    result = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{cell['name']}: batch en échec\n{result.stderr[-2000:]}")
    payload = json.loads(result.stdout[result.stdout.index("{"):])
    run_ids = payload.get("run_ids", [])
    if keep:
        for run_id in run_ids:
            subprocess.run(
                [PYTHON, "-m", "simulation_lab.cli", "keep", "--run-id", run_id],
                cwd=PROJECT, capture_output=True, text=True, check=True)
    return {
        "cell": cell["name"],
        "cell_id": cell_id(cell),
        "plan": plan_name,
        "parameters": cell["parameters"],
        "n_runs": cell["n_runs"],
        "base_seed": cell["base_seed"],
        "label": label,
        "keep": keep,
        "engine_hash": engine_hash(),
        "batch_id": payload.get("batch_id"),
        "run_ids": run_ids,
        "duration_seconds": round(time.monotonic() - started, 1),
        "launched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def load_plan(name: str) -> dict:
    return json.loads((MANIFESTS / f"{name}.json").read_text())


def manifest_path(name: str) -> Path:
    return MANIFESTS / f"{name}.manifest.json"


def load_manifest(name: str) -> dict:
    path = manifest_path(name)
    if path.exists():
        return json.loads(path.read_text())
    return {"plan": name, "cells": []}


def save_manifest(name: str, manifest: dict) -> None:
    manifest_path(name).write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False))


def run_dirs(entry: dict) -> list[tuple[int, Path]]:
    """Paires (graine, dossier) des runs d'une entrée de manifeste."""
    pairs = []
    for run_id in entry["run_ids"]:
        meta = json.loads((LAB_RUNS / run_id / "run.json").read_text())
        pairs.append((int(meta.get("seed", -1)), LAB_RUNS / run_id))
    pairs.sort(key=lambda item: item[0])
    return pairs
