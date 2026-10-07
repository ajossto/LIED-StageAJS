"""Exécute un plan de cellules M4B en parallèle, avec reprise.

Usage :
    run_batch.py <plan> [--workers N] [--phase NOM]

Le plan est un fichier manifests/<plan>.json écrit par lib_runs.save_plan.
Chaque cellule déjà terminée (manifeste valide + summary.json, même hash
moteur) est sautée, ce qui rend le script relançable après interruption.
La machine a 8 cœurs ; on en laisse au moins 2 libres (workers <= 6).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs


def _worker(spec: dict, phase: str) -> dict:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    try:
        manifest = lib_runs.execute(spec, phase=phase)
        return {"ok": True, "manifest": manifest}
    except Exception:
        return {
            "ok": False,
            "run_id": lib_runs.run_id(spec),
            "spec": spec,
            "error": traceback.format_exc(),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--phase", default="")
    args = parser.parse_args()
    workers = max(1, min(args.workers, 6))
    phase = args.phase or args.plan

    cells = lib_runs.load_plan(args.plan)
    pending = [spec for spec in cells if not lib_runs.is_done(spec)]
    print(f"plan={args.plan} cellules={len(cells)} à_faire={len(pending)} workers={workers}")

    failures = []
    started = time.monotonic()
    completed = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, spec, phase): spec for spec in pending}
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if result["ok"]:
                m = result["manifest"]
                print(
                    f"[{completed}/{len(pending)}] {m['run_id']} "
                    f"status={m['model_status']} t={m['t_final']} "
                    f"pop={m['population_final']} {m['duration_seconds']:.1f}s",
                    flush=True,
                )
            else:
                failures.append(result)
                print(f"[{completed}/{len(pending)}] ÉCHEC {result['run_id']}", flush=True)

    print(f"terminé en {time.monotonic() - started:.0f}s ; échecs : {len(failures)}")
    if failures:
        path = lib_runs.MANIFESTS_ROOT / f"{args.plan}.failures.json"
        path.write_text(json.dumps(failures, indent=2, ensure_ascii=False))
        print(f"détails : {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
