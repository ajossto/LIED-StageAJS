"""Campagne M4.2B (exploration + confirmation), protocole figé le
30/07/2026 soir : report/protocole.md. Runner résumable (par cell_id +
seed), parallélisé (8 processus, autorisation utilisateur explicite pour
ce lot nocturne — remplace la convention ≤6).

Chaque cellule = (label, params, T). Chaque run = (cellule, seed). Les
résultats bruts vont sous results/campaign/<label>/seed<seed>/ (schéma
M4.2B standard, réutilisable par simulation_lab/reporting.py) ; l'analyse
post-traitement (avalanches, intérêts par snapshot, décomposition,
renouvellement) est écrite à côté dans analysis.json. Reprise automatique :
un run dont analysis.json existe déjà avec status="ok" n'est pas relancé.
"""

from __future__ import annotations

import json
import math
import multiprocessing as mp
import resource
import sys
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

RESULTS = ROOT / "results" / "campaign"
N_WORKERS = 8
MEM_FRACTION_TOTAL = 0.75  # part de la RAM totale allouable à l'ensemble des workers


def _mem_total_bytes() -> int:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError("MemTotal introuvable dans /proc/meminfo")


def _worker_memory_cap_bytes(n_workers: int) -> int:
    return int(_mem_total_bytes() * MEM_FRACTION_TOTAL / n_workers)


def _init_worker(mem_limit_bytes: int) -> None:
    """Garde-fou (incident du 04/08, JOURNAL.md §9) : borne la mémoire
    virtuelle de CE worker. Un run qui dérape échoue proprement (MemoryError,
    capté par _run_and_analyze -> status="error") au lieu de saturer la RAM
    de la machine entière (et in fine de tuer tmux/le pool avec elle)."""
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit_bytes, mem_limit_bytes))
BURN_FRACTION = 0.25  # burn-in = T/4, conforme à la stationnarité agrégée établie en pilote

BASE_PARAMS = dict(gamma=0.5, delta=0.01, sigma=0.01, K0=25.0, lam=30.0,
                    rho=1.0, eta_beta=1.0, eta_n_ref=1.0, target_rule="arithmetic")
ETA_N_REF_OBSERVED = 1140.0  # moyenne de population stationnaire observée en pilote (baseline)


def _k_aut(gamma: float, delta: float, A: float = 1.0) -> float:
    return ((1.0 - delta) * A / delta) ** (1.0 / (1.0 - gamma))


def build_cells() -> list[dict]:
    cells = []

    def add(label, T=3000, **overrides):
        params = dict(BASE_PARAMS)
        params.update(overrides)
        cells.append({"label": label, "params": params, "T": T})

    # Branche 0 : validation d'horizon étendu (baseline, T=10000)
    add("t10000_baseline", T=10000)

    # Baseline elle-même (T=3000), pour dédupliquer avec toutes les branches
    add("baseline")

    # Branche A : K0
    for K0 in (1.0, 5.0, 100.0, 500.0, 2000.0):
        add(f"K0_{K0:g}", K0=K0)

    # Branche B : gamma non compensé
    for gamma in (1.0 / 3.0, 0.4, 0.6, 2.0 / 3.0):
        add(f"gamma_{gamma:.4f}", gamma=gamma)

    # Branche B' : gamma, K0 compensé pour tenir K0/K*_aut(gamma) constant
    # (= K0/K*_aut(0.5) de la baseline, cf. M4.2)
    ratio_ref = BASE_PARAMS["K0"] / _k_aut(0.5, BASE_PARAMS["delta"])
    for gamma in (1.0 / 3.0, 0.4, 0.6, 2.0 / 3.0):
        K0_comp = ratio_ref * _k_aut(gamma, BASE_PARAMS["delta"])
        add(f"gamma_comp_{gamma:.4f}", gamma=gamma, K0=K0_comp)

    # Branche C : eta non lineaire (beta), eta_n_ref = moyenne pop observee
    for beta in (0.5, 0.75, 1.25, 1.5):
        add(f"beta_{beta:.2f}", eta_beta=beta, eta_n_ref=ETA_N_REF_OBSERVED)

    # Branche D : delta/sigma joints
    for delta, sigma in ((0.02, 0.02), (0.05, 0.05), (0.10, 0.10), (0.05, 0.25)):
        add(f"deltasigma_{delta:g}_{sigma:g}", delta=delta, sigma=sigma)

    # Branche E : rho (eta lineaire)
    for rho in (0.125, 0.25, 0.5, 2.0, 4.0):
        add(f"rho_{rho:g}", rho=rho)

    # Branche F : controle geometrique
    add("control_geometric", target_rule="geometric")

    return cells


def _cell_id(params: dict, T: int) -> str:
    import hashlib
    payload = json.dumps({"params": params, "T": T}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _analyze_run(run_dir: Path, label: str, seed: int, T: int, params: dict,
                  elapsed: float, summary: dict) -> dict:
    """Post-traitement seul (avalanches/intérêts/décomposition/gini/
    renouvellement) sur un run DÉJÀ simulé (series/avalanches/snapshots déjà
    sur disque). Séparé de la simulation pour pouvoir réanalyser sans
    relancer T pas de moteur (ex. après ajout d'un diagnostic dans
    interest_per_snapshot, cf. JOURNAL.md)."""
    import lib_metrics
    import interest_income

    analysis_path = run_dir / "analysis.json"
    try:
        lo = int(BURN_FRACTION * T)
        hi = T
        series = lib_metrics.read_series(run_dir)
        avalanches = lib_metrics.read_avalanches(run_dir)

        out = {
            "status": "ok", "label": label, "seed": seed, "T": T, "params": params,
            "elapsed_s": elapsed, "model_status": summary["status"],
            "population_final": summary["population_final"],
            "loans_final": summary["loans_final"],
            "loan_events_total": summary.get("loan_events_total"),
        }

        pop_mean = None
        if series:
            mask = (series["t"] >= lo) & (series["t"] <= hi)
            pop_mean = float(series["pop"][mask].mean()) if mask.sum() else float("nan")
            wsm = lib_metrics.window_series_metrics(series, lo, hi)
            out["pop_mean_window"] = pop_mean
            out["pop_cv_window"] = wsm.get("pop", {}).get("cv")
            out["market"] = wsm.get("market")
            out["ratios"] = wsm.get("ratios")

        # --- avalanches : compare_laws (repli pure/cutoff DEJA correct) + vuong_trunc_vs_ln
        if avalanches and len(avalanches.get("t", ())):
            mask = (avalanches["t"] >= lo) & (avalanches["t"] <= hi)
            sizes = avalanches["size"][mask]
            laws = lib_metrics.compare_laws(sizes, s_min=2)
            out["avalanches"] = {
                "n_events": laws.get("n_events"), "n_tail": laws.get("n_tail"),
                "identifiable": laws.get("identifiable"),
                "tau_hat": laws.get("tau_hat"), "tau_hat_source": laws.get("tau_hat_source"),
                "s_c_out_of_range": laws.get("s_c_out_of_range"),
                "powerlaw_cutoff": laws.get("powerlaw_cutoff"),
                "lrt_cutoff_vs_pure": laws.get("lrt_cutoff_vs_pure"),
                "size_max": int(sizes.max()) if len(sizes) else None,
            }
            if laws.get("identifiable"):
                vuong = lib_metrics.vuong_trunc_vs_ln(sizes, s_min=2)
                out["avalanches"]["vuong_trunc_vs_ln"] = vuong
            if pop_mean is not None and np.isfinite(pop_mean):
                av_metrics = lib_metrics.window_avalanche_metrics(avalanches, lo, hi, pop_mean, s_min=2)
                out["avalanches"]["branching_ratio"] = av_metrics.get("branching_ratio")

        # --- intérêts : ajustement PAR SNAPSHOT persisté (pas juste la moyenne)
        rows, isummary = interest_income.fit_across_snapshots(run_dir, t_min=lo, t_max=hi, min_n=80)
        out["interest_summary"] = isummary
        out["interest_per_snapshot"] = [
            {
                "t": row["t"], "p0": row.get("p0"), "n_positive": row.get("n_positive"),
                "identifiable": row.get("identifiable"),
                "alpha_density": (row.get("tail_powerlaw") or {}).get("alpha_density"),
                "x_min": (row.get("tail_powerlaw") or {}).get("x_min"),
                "n_tail": (row.get("tail_powerlaw") or {}).get("n_tail"),
                "alpha_density_half_threshold": (
                    (row.get("tail_threshold_stability") or {}).get("x_min_times_0.5") or {}
                ).get("alpha_density"),
                "tail_vs_exponential_z": (row.get("tail_vs_exponential_lr") or {}).get("z"),
                "tail_vs_lognormal_z": (row.get("tail_vs_lognormal_lr") or {}).get("z"),
            }
            for row in rows
        ]

        # --- decomposition reseau (moyennee sur les snapshots de la fenetre)
        net_snaps = interest_income.load_all_network_snapshots(run_dir, t_min=lo, t_max=hi)
        shares_deg, shares_rq, shares_cov = [], [], []
        for _t, net in net_snaps:
            decomp = interest_income.decompose_tail_sources(net)
            lv = decomp.get("log_variance_decomposition")
            if lv:
                shares_deg.append(lv["share_from_deg_out"])
                shares_rq.append(lv["share_from_mean_rq"])
                shares_cov.append(lv["share_from_covariance"])
        out["decomposition"] = {
            "n_snapshots": len(shares_deg),
            "share_from_deg_out_mean": float(np.mean(shares_deg)) if shares_deg else None,
            "share_from_mean_rq_mean": float(np.mean(shares_rq)) if shares_rq else None,
            "share_from_covariance_mean": float(np.mean(shares_cov)) if shares_cov else None,
        }

        # --- Gini(K) trajectoire + renouvellement du top decile (K et revenu)
        entity_snaps = interest_income.load_all_entity_snapshots(run_dir, t_min=lo, t_max=hi)
        ginis = [(t, float(lib_metrics._gini(snap["K"]))) for t, snap in entity_snaps]
        out["gini_K_window"] = {
            "mean": float(np.mean([g for _, g in ginis])) if ginis else None,
            "std": float(np.std([g for _, g in ginis])) if len(ginis) > 1 else None,
            "trajectory": ginis,
        }

        all_snaps = interest_income.load_all_entity_snapshots(run_dir)
        out["renewal"] = _renewal_summary(all_snaps)

        out["book_errors"] = summary.get("book_errors", [])
        analysis_path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
        return out
    except Exception as exc:  # noqa: BLE001
        error_out = {
            "status": "error", "label": label, "seed": seed, "T": T, "params": params,
            "error": str(exc), "traceback": traceback.format_exc(),
        }
        try:
            analysis_path.write_text(json.dumps(error_out, indent=1, ensure_ascii=False))
        except OSError:
            pass
        return error_out


def _run_and_analyze(spec: dict) -> dict:
    label = spec["label"]
    seed = spec["seed"]
    T = spec["T"]
    params = spec["params"]
    results_root = Path(spec["results_root"]) if spec.get("results_root") else RESULTS
    run_dir = results_root / label / f"seed{seed}"
    analysis_path = run_dir / "analysis.json"

    if analysis_path.exists():
        try:
            existing = json.loads(analysis_path.read_text())
            if existing.get("status") == "ok":
                return existing
        except (json.JSONDecodeError, OSError):
            pass

    import gc
    from m4_2b import Config, run_and_save

    cfg = Config(seed=seed, T=T, **params)
    started = time.perf_counter()
    snapshot_every = max(25, T // 120)
    try:
        sim, summary = run_and_save(cfg, run_dir, snapshot_every=snapshot_every, individual_every=0)
    except Exception as exc:  # noqa: BLE001
        # Incident du 05/08 (confirmation) : une MemoryError ici n'etait PAS
        # capturee (contrairement a _analyze_run) et se propageait a travers
        # pool.imap_unordered jusqu'au process principal, qui mourait -
        # perdant le suivi des runs encore en vol dans les AUTRES workers du
        # pool. Desormais degrade proprement en un statut "error" par run.
        error_out = {
            "status": "error", "label": label, "seed": seed, "T": T, "params": params,
            "error": str(exc), "traceback": traceback.format_exc(), "phase": "simulation",
        }
        try:
            analysis_path.write_text(json.dumps(error_out, indent=1, ensure_ascii=False))
        except OSError:
            pass
        return error_out
    elapsed = time.perf_counter() - started
    # _analyze_run ne lit que des fichiers (run_dir) : l'objet Simulation
    # (dont sim.book, potentiellement plusieurs centaines de milliers de
    # prets a K0 eleve) n'a plus d'usage ici mais restait vivant pendant
    # toute la phase d'analyse (JOURNAL.md, garde-fous memoire).
    del sim
    gc.collect()
    return _analyze_run(run_dir, label, seed, T, params, elapsed, summary)


def _reanalyze(spec: dict) -> dict:
    """Recalcule analysis.json d'un run DEJA simule (series/avalanches/
    snapshots/summary.json presents sur disque), sans relancer le moteur.
    Utilise pour backfill un nouveau diagnostic (ex. tail_vs_lognormal_z)
    sur des runs deja termines, sans re-payer T pas de simulation."""
    label = spec["label"]
    seed = spec["seed"]
    T = spec["T"]
    params = spec["params"]
    results_root = Path(spec["results_root"]) if spec.get("results_root") else RESULTS
    run_dir = results_root / label / f"seed{seed}"
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return {"status": "error", "label": label, "seed": seed,
                "error": "summary.json absent, run jamais termine simule"}
    summary = json.loads(summary_path.read_text())
    analysis_path = run_dir / "analysis.json"
    if analysis_path.exists():
        existing = json.loads(analysis_path.read_text())
        elapsed = existing.get("elapsed_s", float("nan"))
    else:
        # Simulation terminee (summary.json present) mais analyse jamais
        # ecrite (ex. incident du 05/08 : pool tue par une MemoryError non
        # capturee dans UN AUTRE worker pendant que celui-ci finissait son
        # analyse). elapsed_s reel perdu (jamais persiste ailleurs) ; NaN,
        # a ne pas utiliser pour une table de cout.
        elapsed = float("nan")
    return _analyze_run(run_dir, label, seed, T, params, elapsed, summary)


def _renewal_summary(snaps: list[tuple[int, dict]]) -> dict | None:
    if len(snaps) < 2:
        return None
    t0, snap0 = snaps[0]
    out = {}
    for field, label in (("nw", "net_worth"), ("K", "capital"), ("income", "income")):
        key = snap0[field]
        threshold = np.quantile(key, 0.90)
        base_ids = set(snap0["id"][key >= threshold].tolist())
        n0 = len(base_ids)
        curve = []
        for t, snap in snaps:
            current_key = snap[field]
            current_threshold = np.quantile(current_key, 0.90)
            current_top = set(snap["id"][current_key >= current_threshold].tolist())
            persistence = len(base_ids & current_top) / max(1, n0)
            curve.append({"t": int(t), "persistence": float(persistence)})
        half_life = None
        for row in curve:
            if row["persistence"] <= 0.5:
                half_life = row["t"] - t0
                break
        out[label] = {"t0": int(t0), "n0": n0, "half_life_steps": half_life,
                       "floor_last5_mean": float(np.mean([c["persistence"] for c in curve[-5:]]))}
    return out


def main() -> None:
    n_seeds_exploration = 3
    cells = build_cells()
    specs = []
    seen_cell_ids = {}
    for cell in cells:
        cid = _cell_id(cell["params"], cell["T"])
        if cid in seen_cell_ids:
            continue  # dedupe : cellule deja presente (memes parametres+T)
        seen_cell_ids[cid] = cell["label"]
        for seed in range(n_seeds_exploration):
            specs.append({"label": cell["label"], "seed": seed, "T": cell["T"], "params": cell["params"]})

    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"{len(cells)} cellules definies, {len(seen_cell_ids)} uniques apres dedup, "
          f"{len(specs)} runs a executer (reprise automatique si deja fait)")
    (RESULTS / "cells_index.json").write_text(
        json.dumps({cid: label for cid, label in seen_cell_ids.items()}, indent=1)
    )

    mem_cap = _worker_memory_cap_bytes(N_WORKERS)
    print(f"Garde-fou memoire : {mem_cap / 1e9:.2f} GB par worker "
          f"({N_WORKERS} workers, {MEM_FRACTION_TOTAL:.0%} de la RAM totale)", flush=True)

    with mp.Pool(processes=N_WORKERS, initializer=_init_worker, initargs=(mem_cap,)) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(_run_and_analyze, specs)):
            results.append(result)
            status = result.get("status")
            print(f"[{i+1}/{len(specs)}] {result.get('label')} seed={result.get('seed')} "
                  f"status={status} elapsed={result.get('elapsed_s')}", flush=True)

    n_errors = sum(1 for r in results if r.get("status") != "ok")
    print(f"\nTerminé : {len(results)} runs, {n_errors} erreurs")


def reanalyze_all() -> None:
    """Recalcule analysis.json pour tous les runs deja simules avec succes
    (summary.json present), sans relancer le moteur. A utiliser apres un
    changement de diagnostic dans _analyze_run (ex. ajout d'un champ)."""
    cells = build_cells()
    specs = []
    seen_cell_ids = {}
    for cell in cells:
        cid = _cell_id(cell["params"], cell["T"])
        if cid in seen_cell_ids:
            continue
        seen_cell_ids[cid] = cell["label"]
        for seed in range(3):
            run_dir = RESULTS / cell["label"] / f"seed{seed}"
            if (run_dir / "summary.json").exists():
                specs.append({"label": cell["label"], "seed": seed, "T": cell["T"], "params": cell["params"]})

    print(f"{len(specs)} runs a reanalyser (summary.json present)", flush=True)
    with mp.Pool(processes=N_WORKERS) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(_reanalyze, specs)):
            results.append(result)
            print(f"[{i+1}/{len(specs)}] {result.get('label')} seed={result.get('seed')} "
                  f"status={result.get('status')}", flush=True)
    n_errors = sum(1 for r in results if r.get("status") != "ok")
    print(f"\nReanalyse terminee : {len(results)} runs, {n_errors} erreurs")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reanalyze":
        reanalyze_all()
    else:
        main()
