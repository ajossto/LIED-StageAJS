"""Préflight disque, budgété sur la cellule entière (PROMPT_M4_3_FINAL.md §3,
§7 point 4).

Un préflight qui ne regarde que le run sur le point de démarrer passe
plusieurs fois de suite avant que le disque ne se remplisse au milieu d'une
cellule à plusieurs graines (leçon M4.2B, JOURNAL.md, disque jamais rempli
mais mécanisme identique à l'incident mémoire §15 : garde-fou raisonnant sur
l'unité isolée plutôt que sur le tout). Aucun seuil n'est codé en dur sur une
mesure d'aujourd'hui : `shutil.disk_usage` est interrogé à chaque appel.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

MARGIN = 3.0


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    free_bytes: int
    required_bytes: int
    remaining_runs: int
    per_run_bytes: int
    margin: float

    def message(self) -> str:
        free_gb = self.free_bytes / 1e9
        required_gb = self.required_bytes / 1e9
        status = "OK" if self.ok else "REFUSE"
        return (
            f"préflight disque [{status}] : {free_gb:.1f} Go libres, "
            f"{required_gb:.1f} Go requis ({self.remaining_runs} runs restants "
            f"× {self.per_run_bytes / 1e9:.2f} Go/run × marge {self.margin:g})"
        )


def check_disk_preflight(
    remaining_runs: int,
    per_run_bytes: int,
    path: str | Path = "/home",
    margin: float = MARGIN,
) -> PreflightResult:
    """Vérifie que l'espace libre couvre au moins `margin`× le volume estimé
    pour TOUS les runs restants de la cellule en cours (pas le seul run qui
    démarre). `remaining_runs` doit compter les graines non encore lancées de
    la cellule, `per_run_bytes` doit inclure le checkpoint complet (§3)."""
    if remaining_runs < 1:
        raise ValueError("remaining_runs doit être >= 1 (au moins le run qui démarre)")
    if per_run_bytes < 1:
        raise ValueError("per_run_bytes doit être une estimation positive")

    free_bytes = shutil.disk_usage(path).free
    required_bytes = int(remaining_runs * per_run_bytes * margin)
    return PreflightResult(
        ok=free_bytes >= required_bytes,
        free_bytes=free_bytes,
        required_bytes=required_bytes,
        remaining_runs=remaining_runs,
        per_run_bytes=per_run_bytes,
        margin=margin,
    )


def require_disk_preflight(
    remaining_runs: int,
    per_run_bytes: int,
    path: str | Path = "/home",
    margin: float = MARGIN,
) -> PreflightResult:
    """Comme `check_disk_preflight`, mais lève `RuntimeError` si insuffisant —
    à appeler avant tout lancement de run, jamais en mode silencieux."""
    result = check_disk_preflight(remaining_runs, per_run_bytes, path, margin)
    if not result.ok:
        raise RuntimeError(result.message())
    return result
