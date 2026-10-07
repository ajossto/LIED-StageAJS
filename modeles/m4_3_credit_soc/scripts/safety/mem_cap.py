"""Plafond mémoire par worker (PROMPT_M4_3_FINAL.md §7 point 2).

M4.2B calculait 75 % de la RAM TOTALE ÷ n_workers (`scripts/campaign.py`),
une formule qui ignore la mémoire déjà consommée par d'autres usages de la
machine au moment du lancement. Ici le plafond est calculé sur
`MemAvailable` (`/proc/meminfo`, déjà la mémoire récupérable — cache/tampons
inclus dans le sens inverse, i.e. MemAvailable les exclut déjà comme non
réservables) mesuré AU LANCEMENT, moins une réserve fixe pour le système et
la phase d'analyse qui suit chaque run, divisée par n_workers.
"""

from __future__ import annotations

from dataclasses import dataclass

RESERVE_BYTES_DEFAULT = 4 * 1024**3  # 4 GiB, ordre de grandeur du §7.2
FLOOR_BYTES = 512 * 1024**2  # plancher : un plafond dérisoire est un bug, pas une prudence


def _read_mem_available_bytes() -> int:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable absent de /proc/meminfo (noyau trop ancien ?)")


@dataclass(frozen=True)
class MemCapResult:
    mem_available_bytes: int
    reserve_bytes: int
    n_workers: int
    cap_per_worker_bytes: int

    def message(self) -> str:
        return (
            f"MemAvailable={self.mem_available_bytes / 1e9:.2f} Go, "
            f"réserve={self.reserve_bytes / 1e9:.2f} Go, "
            f"n_workers={self.n_workers} -> "
            f"plafond/worker={self.cap_per_worker_bytes / 1e9:.2f} Go"
        )


def worker_memory_cap(
    n_workers: int,
    reserve_bytes: int = RESERVE_BYTES_DEFAULT,
    mem_available_bytes: int | None = None,
) -> MemCapResult:
    """Calcule le plafond RLIMIT_AS par worker. `mem_available_bytes` est
    injectable pour les tests ; en usage réel, lu depuis /proc/meminfo au
    moment de l'appel (pas mis en cache, pas calculé sur la RAM totale)."""
    if n_workers < 1:
        raise ValueError("n_workers doit être >= 1")
    available = (
        _read_mem_available_bytes() if mem_available_bytes is None else mem_available_bytes
    )
    usable = max(available - reserve_bytes, 0)
    cap = usable // n_workers
    if cap < FLOOR_BYTES:
        raise RuntimeError(
            f"plafond mémoire calculé ({cap / 1e6:.0f} Mo/worker) sous le plancher "
            f"({FLOOR_BYTES / 1e6:.0f} Mo) — MemAvailable trop bas ou n_workers trop "
            f"élevé pour lancer maintenant, ne pas démarrer le pool"
        )
    return MemCapResult(
        mem_available_bytes=available,
        reserve_bytes=reserve_bytes,
        n_workers=n_workers,
        cap_per_worker_bytes=cap,
    )
