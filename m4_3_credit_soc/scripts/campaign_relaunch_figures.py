"""Relance TOUTES les cellules D1 (28×3) et D3 (4×3) déjà mesurées, cette
fois en générant les 28 figures simulation_lab AVANT le nettoyage post-
analyse (PROMPT_M4_3_FINAL.md §8, gap découvert le 2026-08-09 : le premier
passage de campaign_d1.py/d3_size_check.py supprimait `snapshots/` juste
après l'analyse légère, avant toute génération de figures — aucune des 96
cellules n'avait donc de figures possibles sans re-simulation).

Décision de conception (cf. investigation du 2026-08-09, JOURNAL.md) :
  - `individual_every=0` est CONSERVÉ (inchangé) : c'est la convention
    entière de la campagne M4.2B elle-même (chaque config.json de
    m4_2b_credit_soc/results/campaign/*/seed*/ a individual_every=0) —
    entity_lives() (vies individuelles) est donc légitimement absent, ce
    n'est pas une régression introduite ici.
  - `loan_events.csv.gz` (≈65 % du poids d'un run, 845 Mo à T=8000) N'EST
    UTILISÉ PAR AUCUNE figure (grep confirmé sur reporting.py) : reste
    supprimé après figures, comme avant.
  - Seul changement réel : `snapshots/` n'est supprimé qu'APRÈS
    `reporting.generate_run()`, pas avant (import réel testé sur
    control_geometric/seed0 : 22 PNG, 0 erreur, ~4m20 — cf. JOURNAL.md).

Réutilise campaign_d1._run_and_analyze/_init_worker/build_cells SANS
duplication (monkey-patch de campaign_d1._cleanup_raw pour insérer la
génération de figures juste avant le nettoyage réel, cf. _cleanup_with_figures
ci-dessous) — même patron que d3_size_check.py (bascule de cd.RESULTS par
appel pour distinguer D1/D3)."""

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
sys.path.insert(0, str(ROOT.parent / "modeles-systeme-physicoeconomique" / "m4_3_credit_soc"))

import campaign_d1 as cd  # noqa: E402
import reporting  # noqa: E402
from safety.disk_preflight import require_disk_preflight  # noqa: E402
from safety.mem_cap import worker_memory_cap  # noqa: E402
from safety.pool_lock import PoolLock  # noqa: E402
from safety.worker_registry import register_workers, clear_workers  # noqa: E402

N_WORKERS = 6
RESULTS_D1 = ROOT / "results" / "d1"
RESULTS_D3 = ROOT / "results" / "d3_size"

_real_cleanup = cd._cleanup_raw


def _cleanup_with_figures(run_dir: Path) -> None:
    """Remplace campaign_d1._cleanup_raw : génère les figures AVANT de
    supprimer snapshots/ (le nettoyage réel, inchangé, s'exécute ensuite)."""
    fig_ok_marker = run_dir / "figures" / "macro_overview.png"
    if not fig_ok_marker.exists():
        cell_label = run_dir.parent.name
        t0 = time.time()
        try:
            errors = reporting.generate_run(run_dir, f"M4.3 — {cell_label}/{run_dir.name}")
            (run_dir / "figure_generation.json").write_text(
                json.dumps({"elapsed_s": time.time() - t0, "errors": errors}, indent=1)
            )
        except Exception as exc:  # noqa: BLE001
            (run_dir / "figure_generation_failed.txt").write_text(
                f"{exc}\n\n{traceback.format_exc()}"
            )
    _real_cleanup(run_dir)


cd._cleanup_raw = _cleanup_with_figures


def _run_case(spec: dict) -> dict:
    """Dispatch D1/D3 par le champ spec['results_root'] (bascule cd.RESULTS
    le temps de l'appel, même patron que d3_size_check.py). Force un
    re-run complet si les figures sont absentes, même si analysis.json
    existe déjà en status=ok (le raw a été supprimé au premier passage,
    donc rien à réutiliser sans re-simuler — cf. docstring de ce module)."""
    orig_results = cd.RESULTS
    cd.RESULTS = RESULTS_D1 if spec["results_root"] == "d1" else RESULTS_D3
    try:
        run_dir = cd.RESULTS / spec["label"] / f"seed{spec['seed']}"
        fig_marker = run_dir / "figures" / "macro_overview.png"
        analysis_path = run_dir / "analysis.json"
        if analysis_path.exists() and not fig_marker.exists():
            try:
                existing = json.loads(analysis_path.read_text())
                if existing.get("status") == "ok":
                    analysis_path.unlink()
            except (json.JSONDecodeError, OSError):
                pass
        return cd._run_and_analyze(
            {k: v for k, v in spec.items() if k != "results_root"}
        )
    finally:
        cd.RESULTS = orig_results


def _build_specs() -> list[dict]:
    specs = []
    for cell in cd.build_cells():
        for seed in range(cd.N_SEEDS):
            specs.append({"label": cell["label"], "seed": seed, "T": cd.DEFAULT_T,
                          "params": cell["params"], "results_root": "d1"})

    ratio_ref = cd.BASE_PARAMS["K0"] / cd._k_aut(0.5, cd.BASE_PARAMS["delta"])
    k0_comp_twothirds = ratio_ref * cd._k_aut(2.0 / 3.0, cd.BASE_PARAMS["delta"])
    d3_cells = {
        "baseline": dict(cd.BASE_PARAMS),
        "gamma_comp_0.6667": dict(cd.BASE_PARAMS, gamma=2.0 / 3.0, K0=k0_comp_twothirds),
    }
    for cell_label, params in d3_cells.items():
        for lam in (10.0, 100.0):
            p = dict(params, lam=lam)
            label = f"{cell_label}_lam{lam:g}"
            for seed in range(cd.N_SEEDS):
                specs.append({"label": label, "seed": seed, "T": cd.DEFAULT_T,
                              "params": p, "results_root": "d3"})
    return specs


def main() -> None:
    specs = _build_specs()
    RESULTS_D1.mkdir(parents=True, exist_ok=True)
    RESULTS_D3.mkdir(parents=True, exist_ok=True)
    print(f"{len(specs)} runs à traiter (D1 {sum(1 for s in specs if s['results_root']=='d1')} "
          f"+ D3 {sum(1 for s in specs if s['results_root']=='d3')}), figures avant nettoyage",
          flush=True)

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
                results = []
                for i, result in enumerate(pool.imap_unordered(_run_case, specs)):
                    results.append(result)
                    print(f"[{i+1}/{len(specs)}] {result.get('label')} seed={result.get('seed')} "
                          f"status={result.get('status')}", flush=True)
            finally:
                clear_workers()

    n_errors = sum(1 for r in results if r.get("status") != "ok")
    print(f"\nTerminé : {len(results)} runs, {n_errors} non-ok", flush=True)


if __name__ == "__main__":
    main()
