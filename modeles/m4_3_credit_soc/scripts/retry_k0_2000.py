"""Reprise ciblée de K0_2000 (JOURNAL.md §15) : les 3 graines ont échoué
dans le pool principal (6 workers, plafond 4,43 Go/worker) avec une
`ArrayMemoryError` sur une petite allocation — signe que le plafond
VIRTUEL était déjà presque atteint. Retenté ici avec MOINS de workers pour
beaucoup plus de marge chacun (le verrou mono-pool §7.3 empêche de toute
façon de le lancer en même temps que le pool principal — déjà terminé).
Réutilise `campaign_d1._run_and_analyze` telle quelle, RIEN de récrit."""

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

N_WORKERS = 2


def main() -> None:
    params = dict(cd.BASE_PARAMS, K0=2000.0)
    specs = [{"label": "K0_2000", "seed": seed, "T": cd.DEFAULT_T, "params": params}
             for seed in range(cd.N_SEEDS)]

    # _run_and_analyze ne saute que status="ok" -> les analysis.json
    # d'echec deja ecrits seront correctement retentes, pas skippes.
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
                for i, result in enumerate(pool.imap_unordered(cd._run_and_analyze, specs)):
                    print(f"[{i+1}/{len(specs)}] seed={result.get('seed')} "
                          f"status={result.get('status')} dagum_c={result.get('dagum_c')}",
                          flush=True)
            finally:
                clear_workers()


if __name__ == "__main__":
    main()
