"""Cartographie D1 (PROMPT_M4_3_FINAL.md §1) : remesure l'espace déjà
couvert par M4.2B (η, γ, K0, δ, σ, target_rule — `build_cells()` ci-dessous
est une copie de `m4_2b_credit_soc/scripts/campaign.py::build_cells`,
paramètres INCHANGÉS, §5/§8) avec la méthodologie propre à ce prompt :
fenêtre positionnée par run sur son temps de relaxation propre (§3,
`int_in`, pas un burn-in fixe T/4) et la statistique de queue GELÉE
(`dagum_3p` c, JOURNAL.md §11 — PAS l'ancien α̂ de Hill/Pareto de M4.2B).

Pool multiprocessing (patron `m4_2b_credit_soc/scripts/campaign.py`, déjà
validé sur 87+45 runs, 0 crash après les correctifs JOURNAL.md M4.2B
§10/§12/§15), avec les six garde-fous §7 câblés en plus :
  - verrou mono-pool (§7.3) tenu pour la durée de vie du POOL entier ;
  - plafond mémoire calculé sur MemAvailable réel pour N_WORKERS (§7.2) ;
  - PID de tous les workers enregistrés pour le garde-fou mémoire (§7.1) ;
  - préflight disque avant le lancement ET avant chaque run individuel
    (§7.4) — le calcul est différent de `run_pilot.py` : le nettoyage
    post-analyse (voir plus bas) fait qu'au plus N_WORKERS runs ont leurs
    fichiers bruts en vol simultanément, pas la totalité du backlog ;
  - checkpoint atomique par run (§7.4, `on_progress`).

Nettoyage APRÈS ANALYSE (pas seulement en fin de programme, §7.6 avait ce
principe pour M4.2B a posteriori — ici intégré dès le départ, exigé par
l'arithmétique disque : 87 runs bruts ~1,3 Go chacun ≈ 113 Go, > 97 Go
libres) : supprime `loan_events.csv.gz`/`snapshots/`/`checkpoint.pkl`
après écriture réussie de `analysis.json`, garde tout le reste (~44 Mo/run,
largement soutenable sur 87 runs)."""

from __future__ import annotations

import gc
import json
import multiprocessing as mp
import os
import resource
import shutil
import sys
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from m4_3 import Config  # noqa: E402
from m4_3.io import run_and_save  # noqa: E402
import lib_metrics  # noqa: E402
import interest_income  # noqa: E402
import families  # noqa: E402
from renewal_relaxation_all_runs import persistence_curve, fit_fopdt  # noqa: E402
from safety.disk_preflight import require_disk_preflight  # noqa: E402
from safety.mem_cap import worker_memory_cap  # noqa: E402
from safety.pool_lock import PoolLock  # noqa: E402
from safety.checkpoint import save_checkpoint  # noqa: E402
from safety.halt import is_halted, halt_reason  # noqa: E402
from safety.worker_registry import register_workers, clear_workers  # noqa: E402

RESULTS = ROOT / "results" / "d1"
N_WORKERS = 6
N_SEEDS = 3
DEFAULT_T = 8000
PER_RUN_PEAK_BYTES = int(1.5e9)  # observé : 736 Mo (arithmetic) a 1,3 Go (geometric)
CHECKPOINT_EVERY = 200

BASE_PARAMS = dict(gamma=0.5, delta=0.01, sigma=0.01, K0=25.0, lam=30.0,
                    rho=1.0, eta_beta=1.0, eta_n_ref=1.0, target_rule="arithmetic")
ETA_N_REF_OBSERVED = 1140.0  # moyenne de population stationnaire observee en pilote M4.2B (baseline)


def _k_aut(gamma: float, delta: float, A: float = 1.0) -> float:
    return ((1.0 - delta) * A / delta) ** (1.0 / (1.0 - gamma))


def build_cells() -> list[dict]:
    """Copie exacte de m4_2b_credit_soc/scripts/campaign.py::build_cells
    (mêmes valeurs de paramètres, §5/§8) — SANS T (géré séparément ici,
    voir DEFAULT_T et le principe adaptatif §3)."""
    cells = []

    def add(label, **overrides):
        params = dict(BASE_PARAMS)
        params.update(overrides)
        cells.append({"label": label, "params": params})

    add("baseline")

    for K0 in (1.0, 5.0, 100.0, 500.0, 2000.0):
        add(f"K0_{K0:g}", K0=K0)

    for gamma in (1.0 / 3.0, 0.4, 0.6, 2.0 / 3.0):
        add(f"gamma_{gamma:.4f}", gamma=gamma)

    ratio_ref = BASE_PARAMS["K0"] / _k_aut(0.5, BASE_PARAMS["delta"])
    for gamma in (1.0 / 3.0, 0.4, 0.6, 2.0 / 3.0):
        K0_comp = ratio_ref * _k_aut(gamma, BASE_PARAMS["delta"])
        add(f"gamma_comp_{gamma:.4f}", gamma=gamma, K0=K0_comp)

    for beta in (0.5, 0.75, 1.25, 1.5):
        add(f"beta_{beta:.2f}", eta_beta=beta, eta_n_ref=ETA_N_REF_OBSERVED)

    for delta, sigma in ((0.02, 0.02), (0.05, 0.05), (0.10, 0.10), (0.05, 0.25)):
        add(f"deltasigma_{delta:g}_{sigma:g}", delta=delta, sigma=sigma)

    for rho in (0.125, 0.25, 0.5, 2.0, 4.0):
        add(f"rho_{rho:g}", rho=rho)

    add("control_geometric", target_rule="geometric")

    return cells


class HaltRequested(Exception):
    pass


def _own_t_converge(run_dir: Path, field: str = "int_in") -> float | None:
    snaps = interest_income.load_all_entity_snapshots(run_dir)
    if len(snaps) < 5:
        return None
    t0 = snaps[0][0]
    t, y = persistence_curve(snaps, field)
    fit = fit_fopdt(t, y, t0)
    if not fit["ok"]:
        return None
    return t0 + fit["t_delay"] + 3 * fit["tau"]


def _pooled_post_convergence_int_in(run_dir: Path, t_converge: float) -> np.ndarray:
    snaps = interest_income.load_all_entity_snapshots(run_dir, t_min=int(np.ceil(t_converge)))
    return np.concatenate([s["int_in"] for _t, s in snaps]) if snaps else np.array([])


def _analyze(run_dir: Path, T: int) -> dict:
    """Analyse LÉGÈRE (statistique gelée seule, pas le ladder complet de
    `freeze_tail_statistic.py` qui a servi à la geler) : un seul fit
    dagum_3p, pas les ~10 modèles du ladder AIC — inutile une fois la
    statistique choisie, et le ladder complet est le poste de temps
    dominant de l'analyse (voir JOURNAL.md §11)."""
    out: dict = {}
    t_conv = _own_t_converge(run_dir)
    out["t_converge_int_in"] = t_conv
    out["severe_nonstationary"] = (t_conv is None) or (t_conv > 0.9 * T)

    if t_conv is not None and not out["severe_nonstationary"]:
        pooled = _pooled_post_convergence_int_in(run_dir, t_conv)
        p0, positive = interest_income.zero_mass_and_positive(pooled)
        out["n_pooled"] = int(len(pooled))
        out["p0"] = p0
        if len(positive) >= 30:
            dagum = families.fit_dagum_3p(positive)
            if dagum and dagum.get("params"):
                c, d, loc, scale = dagum["params"][:4]
                out["dagum_c"] = float(c)
                out["dagum_d"] = float(d)
            else:
                out["dagum_c"] = None
        else:
            out["dagum_c"] = None
    else:
        out["dagum_c"] = None

    series = lib_metrics.read_series(run_dir)
    avalanches = lib_metrics.read_avalanches(run_dir)
    lo = int(np.ceil(t_conv)) if t_conv is not None else int(0.25 * T)
    hi = T
    mask = (series["t"] >= lo) & (series["t"] <= hi)
    pop_mean = float(series["pop"][mask].mean()) if mask.sum() else float("nan")
    av_metrics = lib_metrics.window_avalanche_metrics(avalanches, lo, hi, pop_mean, s_min=2)
    out["avalanche"] = {
        "branching_ratio": av_metrics.get("branching_ratio"),
        "tau_hat": av_metrics.get("tau_hat"),
        "tau_hat_source": av_metrics.get("tau_hat_source"),
        "s_c_out_of_range": av_metrics.get("s_c_out_of_range"),
        "n_tail": av_metrics.get("n_tail"),
        "size_max": av_metrics.get("size_max"),
        "identifiable": av_metrics.get("identifiable", True),
    }
    out["lo"] = lo
    out["hi"] = hi
    out["pop_mean"] = pop_mean
    return out


RAW_FILES_TO_DROP = ("loan_events.csv.gz", "checkpoint.pkl")


def _cleanup_raw(run_dir: Path) -> None:
    for name in RAW_FILES_TO_DROP:
        p = run_dir / name
        if p.exists():
            p.unlink()
    snaps = run_dir / "snapshots"
    if snaps.exists():
        shutil.rmtree(snaps)


def _init_worker(mem_limit_bytes: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit_bytes, mem_limit_bytes))


def _run_and_analyze(spec: dict) -> dict:
    label, seed, T, params = spec["label"], spec["seed"], spec["T"], spec["params"]
    run_dir = RESULTS / label / f"seed{seed}"
    analysis_path = run_dir / "analysis.json"

    if analysis_path.exists():
        try:
            existing = json.loads(analysis_path.read_text())
            if existing.get("status") == "ok":
                return existing
        except (json.JSONDecodeError, OSError):
            pass

    if is_halted():
        return {"status": "halted_before_start", "label": label, "seed": seed,
                "reason": halt_reason()}
    try:
        require_disk_preflight(remaining_runs=1, per_run_bytes=PER_RUN_PEAK_BYTES)
    except RuntimeError as exc:
        return {"status": "error", "label": label, "seed": seed, "phase": "preflight",
                "error": str(exc)}

    cfg = Config(seed=seed, T=T, **params)
    checkpoint_path = run_dir / "checkpoint.pkl"

    def on_progress(sim) -> None:
        if is_halted():
            raise HaltRequested(halt_reason() or "HALT")
        if sim.t % CHECKPOINT_EVERY == 0:
            save_checkpoint(sim, checkpoint_path)

    started = time.perf_counter()
    try:
        sim, summary = run_and_save(cfg, run_dir, snapshot_every=max(25, T // 120),
                                     individual_every=0, on_progress=on_progress)
    except HaltRequested as exc:
        error_out = {"status": "halted_mid_run", "label": label, "seed": seed,
                      "T": T, "params": params, "reason": str(exc)}
        analysis_path.write_text(json.dumps(error_out, indent=1, ensure_ascii=False))
        return error_out
    except Exception as exc:  # noqa: BLE001
        error_out = {"status": "error", "label": label, "seed": seed, "T": T, "params": params,
                      "phase": "simulation", "error": str(exc), "traceback": traceback.format_exc()}
        try:
            analysis_path.write_text(json.dumps(error_out, indent=1, ensure_ascii=False))
        except OSError:
            pass
        return error_out
    elapsed = time.perf_counter() - started
    del sim
    gc.collect()

    try:
        analysis = _analyze(run_dir, T)
        analysis.update({"status": "ok", "label": label, "seed": seed, "T": T,
                          "params": params, "elapsed_s": elapsed,
                          "population_final": summary["population_final"],
                          "loans_final": summary["loans_final"]})
        analysis_path.write_text(json.dumps(analysis, indent=1, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        error_out = {"status": "error", "label": label, "seed": seed, "T": T, "params": params,
                      "phase": "analysis", "error": str(exc), "traceback": traceback.format_exc()}
        analysis_path.write_text(json.dumps(error_out, indent=1, ensure_ascii=False))
        return error_out

    _cleanup_raw(run_dir)
    return analysis


def main() -> None:
    cells = build_cells()
    specs = [
        {"label": cell["label"], "seed": seed, "T": DEFAULT_T, "params": cell["params"]}
        for cell in cells for seed in range(N_SEEDS)
    ]
    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"{len(cells)} cellules, {len(specs)} runs (reprise automatique)", flush=True)

    require_disk_preflight(remaining_runs=N_WORKERS, per_run_bytes=PER_RUN_PEAK_BYTES, margin=3.0)

    with PoolLock():
        cap = worker_memory_cap(n_workers=N_WORKERS)
        print(cap.message(), flush=True)

        with mp.Pool(processes=N_WORKERS, initializer=_init_worker,
                     initargs=(cap.cap_per_worker_bytes,)) as pool:
            worker_pids = [p.pid for p in pool._pool]
            register_workers(worker_pids, pool_pid=os.getpid())
            print(f"workers enregistrés : {worker_pids}", flush=True)
            try:
                results = []
                for i, result in enumerate(pool.imap_unordered(_run_and_analyze, specs)):
                    results.append(result)
                    print(f"[{i+1}/{len(specs)}] {result.get('label')} seed={result.get('seed')} "
                          f"status={result.get('status')} dagum_c={result.get('dagum_c')} "
                          f"b={((result.get('avalanche') or {}).get('branching_ratio'))}",
                          flush=True)
            finally:
                clear_workers()

    n_errors = sum(1 for r in results if r.get("status") != "ok")
    n_severe = sum(1 for r in results if r.get("severe_nonstationary"))
    print(f"\nTerminé : {len(results)} runs, {n_errors} non-ok, "
          f"{n_severe} sévère/non-stationnaire (t_converge>0.9T ou non identifiable)")


if __name__ == "__main__":
    main()
