"""Phase confirmatoire : lance chaque cellule comme lot Simulation Lab.

Chaque cellule confirmatoire est exécutée en lot de 5 graines {11..15}
(10 graines {11..20} pour la cellule d'extinction à lambda=2), horizon
T=4000 (T=2000 pour l'extinction), instantanés tous les 100 pas, table
longitudinale désactivée. Les runs sont marqués « à conserver » dans le
lab. La correspondance cellule -> run_ids est écrite dans
manifests/confirm_lab.json.

Usage : run_confirm.py [--only NOM[,NOM...]] [--workers N]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PYTHON = "/home/anatole/jupyter/.venv/bin/python3"
PROJECT = Path("/home/anatole/jupyter")
MANIFEST = Path(__file__).resolve().parents[1] / "manifests" / "confirm_lab.json"

BASE = dict(delta=0.05, sigma=0.25, K0=25.0, k=3, T=4000, pop_max=30_000,
            snapshot_every=100, individual_every=0)

CELLS: dict[str, dict] = {
    "ref_lam10": dict(BASE, lam=10.0),
    "centre_lam30": dict(BASE, lam=30.0),
    "lam100": dict(BASE, lam=100.0),
    "sigma0": dict(BASE, lam=30.0, sigma=0.0),
    "sigma010": dict(BASE, lam=30.0, sigma=0.10),
    "sigma050": dict(BASE, lam=30.0, sigma=0.50),
    "delta002": dict(BASE, lam=30.0, delta=0.02),
    "delta010": dict(BASE, lam=30.0, delta=0.10),
    "K0_5": dict(BASE, lam=30.0, K0=5.0),
    "K0_100": dict(BASE, lam=30.0, K0=100.0),
    "k2": dict(BASE, lam=30.0, k=2),
    "k10": dict(BASE, lam=30.0, k=10),
    # extinction initiale : probabilité e^-lambda au premier pas
    "lam2_ext": dict(BASE, lam=2.0, T=2000),
    # interactions retenues après les coupes 2D (voir JOURNAL 2026-07-18) :
    # bas-sigma : delta module b uniquement dans le régime corrélé
    "sigma005_k2": dict(BASE, lam=30.0, sigma=0.05, k=2),
    "sigma005_delta010": dict(BASE, lam=30.0, sigma=0.05, delta=0.10),
    # évasement du Gini : sigma amplifie l'inégalité seulement à petit k
    "sigma050_k2": dict(BASE, lam=30.0, sigma=0.50, k=2),
}
RUNS = {"lam2_ext": 10}          # défaut : 5
BASE_SEED = 11


def launch(name: str, params: dict, workers: int) -> dict:
    n_runs = RUNS.get(name, 5)
    label = f"Sensibilité M4B — confirmation {name}"
    command = [
        PYTHON, "-m", "simulation_lab.cli", "batch",
        "--model", "m4b_credit_soc_mini",
        "--params", json.dumps(params),
        "--runs", str(n_runs),
        "--workers", str(workers),
        "--base-seed", str(BASE_SEED),
        "--label", label,
    ]
    started = time.monotonic()
    result = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{name}: batch en échec\n{result.stderr[-2000:]}")
    payload = json.loads(result.stdout[result.stdout.index("{"):])
    run_ids = payload.get("run_ids", [])
    for run_id in run_ids:
        subprocess.run(
            [PYTHON, "-m", "simulation_lab.cli", "keep", "--run-id", run_id],
            cwd=PROJECT, capture_output=True, text=True, check=True)
    return {
        "cell": name,
        "parameters": params,
        "n_runs": n_runs,
        "base_seed": BASE_SEED,
        "label": label,
        "batch_id": payload.get("batch_id"),
        "run_ids": run_ids,
        "duration_seconds": round(time.monotonic() - started, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    selected = [s for s in args.only.split(",") if s] or list(CELLS)

    existing = {}
    if MANIFEST.exists():
        existing = {entry["cell"]: entry
                    for entry in json.loads(MANIFEST.read_text())["cells"]}

    for name in selected:
        if name in existing:
            print(f"{name}: déjà lancé ({len(existing[name]['run_ids'])} runs) — sauté")
            continue
        print(f"{name}: lancement ({RUNS.get(name, 5)} graines)…", flush=True)
        entry = launch(name, CELLS[name], max(1, min(args.workers, 6)))
        existing[name] = entry
        MANIFEST.write_text(json.dumps(
            {"created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
             "cells": list(existing.values())},
            indent=2, ensure_ascii=False))
        print(f"{name}: {len(entry['run_ids'])} runs en "
              f"{entry['duration_seconds']:.0f}s", flush=True)
    print("confirmation terminée")


if __name__ == "__main__":
    main()
