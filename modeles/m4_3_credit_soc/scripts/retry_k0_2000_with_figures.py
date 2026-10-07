"""Reprise ciblée de K0_2000 dans la relance simulation_lab (§24-26) :
même échec mémoire déjà rencontré et résolu une première fois
(JOURNAL.md §17/19, retry_k0_2000.py, 2 workers au lieu de 6) --- reproduit
à l'identique par campaign_relaunch_figures.py (3/3 graines
`MemoryError` au checkpoint, pool à 6 workers). Retenté ici avec 2
workers pour plus de marge chacun, EN CONSERVANT la génération de
figures avant nettoyage (monkey-patch de campaign_d1._cleanup_raw, même
patron que campaign_relaunch_figures.py --- ne pas réutiliser
retry_k0_2000.py tel quel, qui daterait le nettoyage AVANT les figures)."""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT.parent / "adaptateurs" / "m4_3_credit_soc"))

import campaign_d1 as cd  # noqa: E402
import reporting  # noqa: E402
from safety.disk_preflight import require_disk_preflight  # noqa: E402
from safety.mem_cap import worker_memory_cap  # noqa: E402
from safety.pool_lock import PoolLock  # noqa: E402
from safety.worker_registry import register_workers, clear_workers  # noqa: E402

N_WORKERS = 2

_real_cleanup = cd._cleanup_raw


def _cleanup_with_figures(run_dir: Path) -> None:
    fig_ok_marker = run_dir / "figures" / "macro_overview.png"
    if not fig_ok_marker.exists():
        t0 = time.time()
        try:
            errors = reporting.generate_run(run_dir, f"M4.3 — {run_dir.parent.name}/{run_dir.name}")
            (run_dir / "figure_generation.json").write_text(
                json.dumps({"elapsed_s": time.time() - t0, "errors": errors}, indent=1)
            )
        except Exception as exc:  # noqa: BLE001
            (run_dir / "figure_generation_failed.txt").write_text(
                f"{exc}\n\n{traceback.format_exc()}"
            )
    _real_cleanup(run_dir)


cd._cleanup_raw = _cleanup_with_figures


def main() -> None:
    params = dict(cd.BASE_PARAMS, K0=2000.0)
    specs = [{"label": "K0_2000", "seed": seed, "T": cd.DEFAULT_T, "params": params}
             for seed in range(cd.N_SEEDS)]

    for spec in specs:
        analysis_path = cd.RESULTS / spec["label"] / f"seed{spec['seed']}" / "analysis.json"
        if analysis_path.exists():
            try:
                existing = json.loads(analysis_path.read_text())
                if existing.get("status") != "ok":
                    analysis_path.unlink()
            except (json.JSONDecodeError, OSError):
                pass

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
                          f"status={result.get('status')}", flush=True)
            finally:
                clear_workers()


if __name__ == "__main__":
    main()
