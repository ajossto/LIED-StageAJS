"""Extension de la campagne de confirmation (report/rapport_interim.md
§6) : 3 cellules identifiées a posteriori comme les plus fortes sur les
deux motifs de selection du protocole non exploites dans
`scripts/confirmation.py` (stabilite de seuil, effet gamma une fois
l'echelle K0/K*_aut controlee) :
- deltasigma_0.1_0.1 : seule cellule du grid d'exploration a sortir du
  bruit sur threshold_reldiff_frac_under_20pct (9,2% vs ~0% partout
  ailleurs) ;
- gamma_comp_0.3333, gamma_comp_0.6667 : extremes de la branche gamma
  compensee (K0/K*_aut constant), effet quasi monotone sur alpha_density
  (4,86 a 3,31) contre un effet plat sur la branche brute.

Meme mecanisme que confirmation.py (results_root separe, reprise
automatique), mais pool de workers reduit (3, pas 8) : tourne EN MEME
TEMPS que confirmation.py sur la meme machine (8 coeurs), qui a deja
reserve 8 workers pour les 6 cellules initiales. Ecrit sous
results/confirmation/ (meme dossier, cellules disjointes -> pas de
collision).

A traiter explicitement comme une extension, pas le protocole initial :
ces cellules n'etaient pas dans la selection figee avant le lancement de
la confirmation (JOURNAL.md, report/selection_confirmation.md).
"""

from __future__ import annotations

import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from campaign import (  # noqa: E402
    _init_worker,
    _run_and_analyze,
    _worker_memory_cap_bytes,
    build_cells,
)

CONFIRM_RESULTS = ROOT / "results" / "confirmation"
SEEDS = (10, 11, 12, 13, 14)
SELECTED_LABELS = {"deltasigma_0.1_0.1", "gamma_comp_0.3333", "gamma_comp_0.6667"}
N_WORKERS_EXTRA = 6  # convention "<=6 processus" du projet ; tourne seule sur la machine
                      # (plus de confirmation.py concurrente depuis l'incident du 05/08,
                      # JOURNAL.md SS15 -- plus besoin de reduire pour un partage CPU/memoire)


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
    print(f"{len(SELECTED_LABELS)} cellules (extension), {len(specs)} runs "
          f"(graines {SEEDS}, {N_WORKERS_EXTRA} workers, reprise automatique)", flush=True)

    mem_cap = _worker_memory_cap_bytes(N_WORKERS_EXTRA)
    print(f"Garde-fou memoire : {mem_cap / 1e9:.2f} GB par worker", flush=True)

    with mp.Pool(processes=N_WORKERS_EXTRA, initializer=_init_worker, initargs=(mem_cap,)) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(_run_and_analyze, specs)):
            results.append(result)
            print(f"[{i + 1}/{len(specs)}] {result.get('label')} seed={result.get('seed')} "
                  f"status={result.get('status')} elapsed={result.get('elapsed_s')}", flush=True)

    n_errors = sum(1 for r in results if r.get("status") != "ok")
    print(f"\nExtension terminee : {len(results)} runs, {n_errors} erreurs")


if __name__ == "__main__":
    main()
