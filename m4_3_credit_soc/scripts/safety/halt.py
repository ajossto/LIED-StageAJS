"""Sentinelle de blocage (PROMPT_M4_3_FINAL.md §7 point 1) : posée par
`mem_guard.py` quand la mémoire système est jugée dangereuse, lue par le
lanceur de pool avant CHAQUE nouveau run — pas seulement au démarrage de la
cellule. Un simple fichier (pas un flag en mémoire partagée) pour survivre
au redémarrage d'un composant et rester visible entre processus indépendants.
"""

from __future__ import annotations

import time
from pathlib import Path

HALT_PATH = Path(__file__).resolve().parents[2] / "results" / "HALT"


def raise_halt(reason: str, path: Path = HALT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {reason}\n")


def clear_halt(path: Path = HALT_PATH) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def is_halted(path: Path = HALT_PATH) -> bool:
    return path.exists()


def halt_reason(path: Path = HALT_PATH) -> str | None:
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None
