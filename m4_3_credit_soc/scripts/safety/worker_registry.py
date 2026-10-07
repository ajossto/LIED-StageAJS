"""Registre des PID du pool courant, lu par le garde-fou mémoire indépendant
(`mem_guard.py`, PROMPT_M4_3_FINAL.md §7 point 1) pour savoir quels processus
terminer en cas de dépassement de seuil. Écrit par le lanceur de pool au
démarrage ; un seul registre actif à la fois (protégé par le même dossier que
`pool_lock.py`, sous le même verrou mono-pool).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "results" / ".pool_workers.json"


def register_workers(pids: list[int], pool_pid: int | None = None, path: Path = REGISTRY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pool_pid": pool_pid or os.getpid(), "worker_pids": list(pids)}
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(payload))
    os.replace(tmp, path)


def read_workers(path: Path = REGISTRY_PATH) -> dict:
    if not path.exists():
        return {"pool_pid": None, "worker_pids": []}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"pool_pid": None, "worker_pids": []}


def clear_workers(path: Path = REGISTRY_PATH) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
