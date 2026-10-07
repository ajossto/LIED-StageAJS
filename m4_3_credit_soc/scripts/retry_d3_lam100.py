"""Reprise ciblée de gamma_comp_0.6667_lam100 (3 graines, échec mémoire
dans d3_size_check.py à 6 workers/4,52 Go — même motif que K0_2000,
JOURNAL.md §15/§18 : K0 compensé (2475) + lam=100 fait un système parmi
les plus gros du programme). Moins de workers, plus de marge chacun."""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import campaign_d1 as cd  # noqa: E402
import d3_size_check as d3  # noqa: E402
from safety.disk_preflight import require_disk_preflight  # noqa: E402
from safety.mem_cap import worker_memory_cap  # noqa: E402
from safety.pool_lock import PoolLock  # noqa: E402
from safety.worker_registry import register_workers, clear_workers  # noqa: E402

N_WORKERS = 2


def main() -> None:
    params = dict(d3.CELLS["gamma_comp_0.6667"], lam=100.0)
    specs = [{"label": "gamma_comp_0.6667_lam100", "seed": seed, "T": cd.DEFAULT_T, "params": params}
             for seed in range(cd.N_SEEDS)]

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
                for i, result in enumerate(pool.imap_unordered(d3._run_and_analyze_d3, specs)):
                    print(f"[{i+1}/{len(specs)}] seed={result.get('seed')} "
                          f"status={result.get('status')} dagum_c={result.get('dagum_c')}",
                          flush=True)
            finally:
                clear_workers()


if __name__ == "__main__":
    main()
