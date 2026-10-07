"""Enchaîne plusieurs runs pilotes SÉQUENTIELLEMENT (un sous-process
`run_pilot.py` à la fois — le verrou mono-pool §7.3 empêcherait de toute
façon deux runs simultanés, c'est le comportement voulu, pas une
limitation contournée ici). Reprise automatique : un run dont
`summary.json` porte déjà `status="ok"` n'est pas relancé.

Usage : liste de cellules codée en dur ci-dessous (pas de CLI généraliste —
la phase pilote n'a pas encore besoin d'un vrai campaign.py multi-worker,
§4/§9 : le premier geometrique, puis 2 graines de plus pour geler la
statistique de queue §2, puis l'arithmétique équivalent pour la
comparaison §4)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
PYTHON = "/home/anatole/jupyter/.venv/bin/python3"

# (label, seed, target_rule, steps)
# Phase 1 (control_geometric seed1, baseline_arithmetic seed0) a validé
# T=8000 pour les deux régimes (JOURNAL.md §10 : t_converge(int_in)
# arithmetic~1016, geometric 3006-4174 sur 2 graines — les deux tiennent
# largement dans T=8000). Phase 2 : compléter à 3 graines par cellule pour
# (a) geler la statistique de queue §2 (reproductibilité inter-graines),
# (b) la comparaison geometric/arithmetic §4 avec barres d'erreur.
CELLS = [
    ("control_geometric", 1, "geometric", 8000),
    ("baseline_arithmetic", 0, "arithmetic", 8000),
    ("control_geometric", 2, "geometric", 8000),
    ("baseline_arithmetic", 1, "arithmetic", 8000),
    ("baseline_arithmetic", 2, "arithmetic", 8000),
]


def already_done(label: str, seed: int) -> bool:
    summary_path = RESULTS / "pilot" / label / f"seed{seed}" / "summary.json"
    if not summary_path.exists():
        return False
    try:
        return json.loads(summary_path.read_text()).get("status") == "ok"
    except (json.JSONDecodeError, OSError):
        return False


def main() -> None:
    for label, seed, target_rule, steps in CELLS:
        if already_done(label, seed):
            print(f"[skip] {label}/seed{seed} déjà terminé (status=ok)", flush=True)
            continue
        print(f"[start] {label}/seed{seed} target_rule={target_rule} T={steps} "
              f"à {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        result = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "run_pilot.py"),
             "--label", label, "--seed", str(seed), "--steps", str(steps),
             "--target-rule", target_rule],
            cwd=str(ROOT),
        )
        if result.returncode != 0:
            print(f"[ERREUR] {label}/seed{seed} a échoué (code {result.returncode}) — "
                  f"arrêt du lot (pas de run suivant lancé automatiquement après un échec).",
                  flush=True)
            sys.exit(1)
        print(f"[done] {label}/seed{seed} terminé à {time.strftime('%Y-%m-%d %H:%M:%S')}",
              flush=True)

    print("Lot terminé : tous les runs demandés sont à status=ok.", flush=True)


if __name__ == "__main__":
    main()
