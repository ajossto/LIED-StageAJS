"""Verrou mono-pool appliqué par le code (PROMPT_M4_3_FINAL.md §7 point 3).

JOURNAL.md de M4.2B §15 : deux pools de simulation indépendants lancés en
même temps, chacun calculant son propre plafond mémoire sans connaissance de
l'autre -> réservation combinée ~50 Go sur une machine à 31 Go. La règle
retenue à l'époque ("ne plus jamais lancer deux pools en même temps") était
humaine, non appliquée par un mécanisme.

Chemin de verrou FIXE (pas dérivé de `sys.argv[0]`) : protège contre un
second pool lancé par N'IMPORTE QUEL processus qui toucherait ce dossier,
pas seulement une seconde invocation du même script. `flock` est advisory
mais tenu par le descripteur de fichier : si le process titulaire meurt
(crash, kill -9), le noyau libère le verrou automatiquement — pas de fichier
de verrou "fantôme" à nettoyer à la main après un incident.
"""

from __future__ import annotations

import errno
import fcntl
import os
import socket
import time
from pathlib import Path

LOCK_PATH = Path(__file__).resolve().parents[2] / "results" / ".pool.lock"


class PoolAlreadyRunningError(RuntimeError):
    pass


class PoolLock:
    """Verrou exclusif, non-bloquant, tenu pour la durée de vie du pool.

    Usage :
        with PoolLock():
            ... lancer le pool ...
    Échec bruyant (exception, pas un log) si un autre pool tient déjà le
    verrou.
    """

    def __init__(self, lock_path: Path = LOCK_PATH):
        self.lock_path = lock_path
        self._fd: int | None = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                holder = self.lock_path.read_text().strip() if self.lock_path.exists() else "?"
                raise PoolAlreadyRunningError(
                    f"un pool de simulation tient déjà le verrou {self.lock_path} "
                    f"(titulaire déclaré : {holder}) — ne pas lancer un second pool, "
                    f"JOURNAL.md M4.2B §15"
                ) from exc
            raise
        os.ftruncate(fd, 0)
        os.write(
            fd,
            f"pid={os.getpid()} host={socket.gethostname()} "
            f"ts={time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode(),
        )
        self._fd = fd

    def release(self) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> "PoolLock":
        self.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()
