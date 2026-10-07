"""Checkpoint atomique, rétention d'un seul fichier par run (PROMPT_M4_3_FINAL.md
§3, §7 point 4).

Une écriture de checkpoint interrompue par un disque plein (ou un kill du
garde-fou mémoire, §7 point 1) est une CORRUPTION, pas un échec propre — le
prompt est explicite là-dessus. La version naïve (écrire directement sur le
chemin final) écraserait un bon checkpoint par un fichier tronqué en cas
d'interruption pendant l'écriture. Ici : écriture dans un fichier temporaire
sur le MÊME répertoire (garantit que `os.replace` reste un rename atomique,
pas une copie inter-filesystem), puis `os.replace` vers le chemin final —
soit l'ancien checkpoint survit intact, soit le nouveau est complet, jamais
un état intermédiaire visible sous le nom final.
"""

from __future__ import annotations

import os
import pickle
import tempfile
from pathlib import Path
from typing import Any


def save_checkpoint(obj: Any, path: str | Path) -> None:
    """Sauvegarde atomique. `path` est le seul checkpoint conservé pour ce
    run : un appel ultérieur écrase le précédent (rétention à 1, §3)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load_checkpoint(path: str | Path) -> Any:
    with open(path, "rb") as f:
        return pickle.load(f)


def checkpoint_exists(path: str | Path) -> bool:
    return Path(path).exists()
