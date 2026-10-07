"""Reprise ciblée des cellules qui ont échoué (MemoryError au checkpoint,
pool à 6 workers) lors de la relance simulation_lab (campaign_relaunch_figures.py,
96 runs, terminée le 2026-08-10 avec 6 non-ok) : K0_2000 (D1, 3/3 graines)
et gamma_comp_0.6667_lam100 (D3, 3/3 graines) --- toutes deux DÉJÀ
rencontrées et résolues une première fois lors de la campagne D1/D3
initiale par la même méthode (JOURNAL.md §17/19 : moins de workers, plus
de marge mémoire chacun). Pas une régression du correctif bins/figures.

Réutilise campaign_relaunch_figures telle quelle (le monkey-patch
génération-figures-avant-nettoyage est déjà appliqué à l'import de ce
module) --- seul changement : N_WORKERS réduit à 2 et specs filtrées aux
deux cellules en échec."""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import campaign_d1 as cd  # noqa: E402
import campaign_relaunch_figures as crf  # noqa: E402  (applique le monkey-patch a l'import)
from safety.disk_preflight import require_disk_preflight  # noqa: E402
from safety.mem_cap import worker_memory_cap  # noqa: E402
from safety.pool_lock import PoolLock  # noqa: E402
from safety.worker_registry import register_workers, clear_workers  # noqa: E402

N_WORKERS = 2
FAILED_LABELS = {"K0_2000", "gamma_comp_0.6667_lam100"}


def main() -> None:
    all_specs = crf._build_specs()
    specs = [s for s in all_specs if s["label"] in FAILED_LABELS]
    print(f"{len(specs)} runs à reprendre : "
          f"{sorted(set(s['label'] for s in specs))}", flush=True)

    for spec in specs:
        results_root = crf.RESULTS_D1 if spec["results_root"] == "d1" else crf.RESULTS_D3
        analysis_path = results_root / spec["label"] / f"seed{spec['seed']}" / "analysis.json"
        if analysis_path.exists():
            import json
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
                for i, result in enumerate(pool.imap_unordered(crf._run_case, specs)):
                    print(f"[{i+1}/{len(specs)}] {result.get('label')} seed={result.get('seed')} "
                          f"status={result.get('status')}", flush=True)
            finally:
                clear_workers()


if __name__ == "__main__":
    main()
