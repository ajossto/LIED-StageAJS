"""Infrastructure de campagne M4B : identifiants, manifestes, exécution.

Le moteur de référence `m4b_credit_soc_mini/m4b/` est traité en lecture
seule.  Chaque cellule (configuration + graine + options d'enregistrement)
reçoit un identifiant déterministe dérivé du contenu du moteur et de la
configuration complète ; le manifeste JSON écrit à côté des données
primaires permet de vérifier provenance, statut et intégrité sans
réexécuter la simulation.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = Path("/home/anatole/jupyter/modeles/m4b_credit_soc_mini")
RESULTS_ROOT = CAMPAIGN_ROOT / "results" / "runs"
MANIFESTS_ROOT = CAMPAIGN_ROOT / "manifests"

_ENGINE_FILES = ("m4b/model.py", "m4b/io.py", "m4b/__init__.py")

CONFIG_KEYS = ("lam", "delta", "sigma", "K0", "k", "seed", "T", "pop_max")
RECORD_KEYS = ("snapshot_every", "individual_every")
DEFAULTS = {
    "lam": 10.0, "delta": 0.05, "sigma": 0.25, "K0": 25.0, "k": 3,
    "seed": 0, "T": 2000, "pop_max": 30_000,
    "snapshot_every": 0, "individual_every": 0,
}


def engine_hash() -> str:
    digest = hashlib.sha256()
    for name in _ENGINE_FILES:
        digest.update((ENGINE_ROOT / name).read_bytes())
    return digest.hexdigest()[:16]


ENGINE_HASH = engine_hash()


def cell(**overrides) -> dict:
    """Configuration complète d'une cellule, défauts explicites."""
    unknown = set(overrides) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"clés inconnues : {unknown}")
    spec = dict(DEFAULTS)
    spec.update(overrides)
    spec["lam"] = float(spec["lam"])
    spec["delta"] = float(spec["delta"])
    spec["sigma"] = float(spec["sigma"])
    spec["K0"] = float(spec["K0"])
    for key in ("k", "seed", "T", "pop_max", "snapshot_every", "individual_every"):
        spec[key] = int(spec[key])
    return spec


def run_id(spec: dict) -> str:
    payload = {key: spec[key] for key in CONFIG_KEYS + RECORD_KEYS}
    payload["engine"] = ENGINE_HASH
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "m4b_" + hashlib.sha256(canon.encode()).hexdigest()[:12]


def run_dir(spec: dict) -> Path:
    return RESULTS_ROOT / run_id(spec)


def manifest_path(spec: dict) -> Path:
    return run_dir(spec) / "manifest.json"


def is_done(spec: dict) -> bool:
    path = manifest_path(spec)
    if not path.exists():
        return False
    try:
        manifest = json.loads(path.read_text())
    except ValueError:
        return False
    return (
        manifest.get("campaign_status") == "done"
        and manifest.get("engine_hash") == ENGINE_HASH
        and (run_dir(spec) / "summary.json").exists()
    )


def execute(spec: dict, phase: str = "") -> dict:
    """Exécute une cellule (ou la saute si déjà faite) et renvoie son manifeste."""
    directory = run_dir(spec)
    if is_done(spec):
        return json.loads(manifest_path(spec).read_text())

    if str(ENGINE_ROOT) not in sys.path:
        sys.path.insert(0, str(ENGINE_ROOT))
    from m4b import Config, run_and_save  # noqa: E402

    config = Config(**{key: spec[key] for key in CONFIG_KEYS})
    started = time.monotonic()
    simulation, summary = run_and_save(
        config,
        directory,
        snapshot_every=spec["snapshot_every"],
        individual_every=spec["individual_every"],
    )
    duration = time.monotonic() - started

    disk = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
    manifest = {
        "run_id": run_id(spec),
        "phase": phase,
        "engine_version": summary["model_version"],
        "engine_hash": ENGINE_HASH,
        "parameters": {key: spec[key] for key in CONFIG_KEYS},
        "recording": {key: spec[key] for key in RECORD_KEYS},
        "model_status": summary["status"],
        "t_final": summary["t_final"],
        "population_final": summary["population_final"],
        "deaths_total": summary["deaths_total"],
        "births_total": summary["births_total"],
        "avalanches_total": summary["avalanches_total"],
        "branching_ratio": summary["branching_ratio"],
        "book_errors": summary["book_errors"],
        "duration_seconds": round(duration, 3),
        "disk_bytes": disk,
        "data_path": str(directory.relative_to(CAMPAIGN_ROOT)),
        "campaign_status": "done",
        "hostname": os.uname().nodename,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    manifest_path(spec).write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest


def save_plan(name: str, cells: list[dict], notes: str = "") -> Path:
    """Écrit un plan d'exécution (liste de cellules) dans manifests/."""
    MANIFESTS_ROOT.mkdir(parents=True, exist_ok=True)
    path = MANIFESTS_ROOT / f"{name}.json"
    payload = {
        "plan": name,
        "engine_hash": ENGINE_HASH,
        "notes": notes,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cells": [
            {"run_id": run_id(spec), **spec}
            for spec in cells
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return path


def load_plan(name: str) -> list[dict]:
    payload = json.loads((MANIFESTS_ROOT / f"{name}.json").read_text())
    return [cell(**{k: v for k, v in entry.items() if k in DEFAULTS})
            for entry in payload["cells"]]
