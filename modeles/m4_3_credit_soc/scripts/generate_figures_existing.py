"""Génère les 28 figures pour les runs pilotes qui ONT DÉJÀ leurs
instantanés bruts sur disque (pas besoin de relancer la simulation) :
baseline_arithmetic x3, control_geometric x3 (déjà fait pour seed0, cf.
JOURNAL.md test d'import), gamma_comp_0.6667_verif x1.

Séparé de campaign_relaunch_figures.py (qui, lui, relance des simulations
sous les 6 garde-fous) car ici il n'y a AUCUNE simulation à faire tourner,
seulement du calcul de figures CPU (pas de risque mémoire) — pas besoin du
pool sous garde-fous mémoire pour ce cas.
"""

from __future__ import annotations

import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "adaptateurs" / "m4_3_credit_soc"))

import reporting  # noqa: E402

TARGETS = [
    ("baseline_arithmetic (pilote)", ROOT / "results" / "pilot" / "baseline_arithmetic" / "seed0"),
    ("baseline_arithmetic (pilote)", ROOT / "results" / "pilot" / "baseline_arithmetic" / "seed1"),
    ("baseline_arithmetic (pilote)", ROOT / "results" / "pilot" / "baseline_arithmetic" / "seed2"),
    ("control_geometric (pilote)", ROOT / "results" / "pilot" / "control_geometric" / "seed1"),
    ("control_geometric (pilote)", ROOT / "results" / "pilot" / "control_geometric" / "seed2"),
    ("gamma_comp_0.6667 (verif D1)", ROOT / "results" / "pilot" / "gamma_comp_0.6667_verif" / "seed0"),
]


def _one(spec):
    title, folder = spec
    if not folder.exists():
        return (str(folder), "absent", [])
    if (folder / "figures" / "macro_overview.png").exists():
        return (str(folder), "deja_fait", [])
    t0 = time.time()
    errors = reporting.generate_run(folder, f"M4.3 — {title}")
    return (str(folder), f"ok en {time.time()-t0:.0f}s", errors)


def main() -> None:
    with mp.Pool(processes=4) as pool:
        for folder, status, errors in pool.imap_unordered(_one, TARGETS):
            print(f"{folder}: {status} errors={errors}", flush=True)


if __name__ == "__main__":
    main()
