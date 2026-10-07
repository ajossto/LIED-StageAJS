"""Campagne de confirmation M4.2B (report/protocole.md, etape 3) : 6
cellules selectionnees a partir de l'exploration (results/campaign/,
87/87 runs), 5 graines disjointes jamais vues en exploration (10-14),
T=3000. Resultats sous results/confirmation/<label>/seed<seed>/,
independants de results/campaign/. Reprise automatique (meme mecanisme
que campaign.py : analysis.json status="ok" -> run non relance).

Selection (rationale complet : report/selection_confirmation.md) :
- rho_0.125, rho_4 : extremes de la branche E (eta lineaire, "levier
  privilegie" du prompt complet, §7-8) -> effet le plus net sur
  share_from_mean_rq (+0.159 / -0.093 vs baseline) et sur la criticalite
  des avalanches (branching_ratio 0.480 / 0.891 vs baseline 0.786).
- K0_1, K0_2000 : extremes de la branche A (K0, "branche prioritaire"
  du protocole, mecanisme deg_out/rq) -> effet oppose sur
  share_from_mean_rq (+0.117 / -0.124), population finale x19 (387 a
  7247), alpha_density le plus bas observe (K0_2000, 2.79).
- gamma_0.6667 : effet le plus net de la branche B (gamma non
  compensee, +0.088 sur share_from_mean_rq).
- control_geometric : pas retenue par la taille de l'effet (-0.073, au
  milieu du classement) mais necessaire pour la question 1 du rapport
  final (§21) : comparaison institutionnelle cible arithmetique vs
  geometrique, ne peut etre obtenue par aucune autre cellule.
"""

from __future__ import annotations

import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from campaign import (  # noqa: E402
    N_WORKERS,
    _init_worker,
    _run_and_analyze,
    _worker_memory_cap_bytes,
    build_cells,
)

CONFIRM_RESULTS = ROOT / "results" / "confirmation"
SEEDS = (10, 11, 12, 13, 14)  # disjointes des graines d'exploration (0-2)
SELECTED_LABELS = {
    "rho_0.125", "rho_4", "K0_1", "K0_2000", "gamma_0.6667", "control_geometric",
}


def main() -> None:
    cells = build_cells()
    by_label = {c["label"]: c for c in cells}
    missing = SELECTED_LABELS - set(by_label)
    if missing:
        raise RuntimeError(f"labels absents de build_cells() : {missing}")

    specs = []
    for label in sorted(SELECTED_LABELS):
        cell = by_label[label]
        for seed in SEEDS:
            specs.append({
                "label": cell["label"], "seed": seed, "T": cell["T"],
                "params": cell["params"], "results_root": str(CONFIRM_RESULTS),
            })

    CONFIRM_RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"{len(SELECTED_LABELS)} cellules de confirmation, {len(specs)} runs "
          f"(graines {SEEDS}, reprise automatique)", flush=True)

    mem_cap = _worker_memory_cap_bytes(N_WORKERS)
    print(f"Garde-fou memoire : {mem_cap / 1e9:.2f} GB par worker "
          f"({N_WORKERS} workers)", flush=True)

    with mp.Pool(processes=N_WORKERS, initializer=_init_worker, initargs=(mem_cap,)) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(_run_and_analyze, specs)):
            results.append(result)
            print(f"[{i + 1}/{len(specs)}] {result.get('label')} seed={result.get('seed')} "
                  f"status={result.get('status')} elapsed={result.get('elapsed_s')}", flush=True)

    n_errors = sum(1 for r in results if r.get("status") != "ok")
    print(f"\nConfirmation terminee : {len(results)} runs, {n_errors} erreurs")


if __name__ == "__main__":
    main()
