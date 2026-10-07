"""D3 : robustesse de taille du candidat D2 `gamma_comp_0.6667`
(JOURNAL.md §16), via λ PAS via K0 (§5 — méthodologie M4B, taille
contrôlée indépendamment des paramètres testés). Question : le motif
(queue plus épaisse ET b plus élevé que baseline) mesuré à λ=30 tient-il
à λ∈{10,100} aussi, ou est-ce un artefact de la population particulière
atteinte à λ=30 (§16 : gamma_comp fait varier K0 par construction, donc
la population, même modérément) ?

4 cellules nouvelles (λ=30 déjà couvert par D1, réutilisé tel quel — pas
rerun) : {baseline, gamma_comp_0.6667} × {lam=10, lam=100}, 3 graines
chacune. Réutilise `campaign_d1._run_and_analyze`/`_init_worker` SANS
modification (§5/§8)."""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import campaign_d1 as cd  # noqa: E402
from safety.disk_preflight import require_disk_preflight  # noqa: E402
from safety.mem_cap import worker_memory_cap  # noqa: E402
from safety.pool_lock import PoolLock  # noqa: E402
from safety.worker_registry import register_workers, clear_workers  # noqa: E402

N_WORKERS = 6
RESULTS_D3 = ROOT / "results" / "d3_size"

# K0 compense pour gamma=2/3 : meme formule que campaign_d1.build_cells,
# valeur reprise identique (pas recalculee -> pas de risque de divergence
# d'arrondi avec la cellule D1 deja mesuree a lam=30).
_ratio_ref = cd.BASE_PARAMS["K0"] / cd._k_aut(0.5, cd.BASE_PARAMS["delta"])
_K0_COMP_TWOTHIRDS = _ratio_ref * cd._k_aut(2.0 / 3.0, cd.BASE_PARAMS["delta"])

CELLS = {
    "baseline": dict(cd.BASE_PARAMS),
    "gamma_comp_0.6667": dict(cd.BASE_PARAMS, gamma=2.0 / 3.0, K0=_K0_COMP_TWOTHIRDS),
}
LAMBDAS = (10.0, 100.0)  # lam=30 deja couvert par D1 (results/d1/{baseline,gamma_comp_0.6667})


def _run_and_analyze_d3(spec: dict) -> dict:
    """Identique a campaign_d1._run_and_analyze mais ecrit sous
    results/d3_size/ au lieu de results/d1/ (cellules differentes,
    collision de nom sinon avec les cellules D1 deja faites a lam=30)."""
    orig_results = cd.RESULTS
    cd.RESULTS = RESULTS_D3
    try:
        return cd._run_and_analyze(spec)
    finally:
        cd.RESULTS = orig_results


def main() -> None:
    specs = []
    for cell_label, params in CELLS.items():
        for lam in LAMBDAS:
            p = dict(params, lam=lam)
            label = f"{cell_label}_lam{lam:g}"
            for seed in range(cd.N_SEEDS):
                specs.append({"label": label, "seed": seed, "T": cd.DEFAULT_T, "params": p})

    RESULTS_D3.mkdir(parents=True, exist_ok=True)
    print(f"{len(specs)} runs (D3, taille via lambda)", flush=True)

    require_disk_preflight(remaining_runs=N_WORKERS, per_run_bytes=cd.PER_RUN_PEAK_BYTES, margin=3.0)

    with PoolLock():
        cap = worker_memory_cap(n_workers=N_WORKERS)
        print(cap.message(), flush=True)
        with mp.Pool(processes=N_WORKERS, initializer=cd._init_worker,
                     initargs=(cap.cap_per_worker_bytes,)) as pool:
            worker_pids = [p.pid for p in pool._pool]
            register_workers(worker_pids, pool_pid=os.getpid())
            print(f"workers enregistrés : {worker_pids}", flush=True)
            try:
                for i, result in enumerate(pool.imap_unordered(_run_and_analyze_d3, specs)):
                    print(f"[{i+1}/{len(specs)}] {result.get('label')} seed={result.get('seed')} "
                          f"status={result.get('status')} dagum_c={result.get('dagum_c')} "
                          f"b={((result.get('avalanche') or {}).get('branching_ratio'))}",
                          flush=True)
            finally:
                clear_workers()


if __name__ == "__main__":
    main()
