"""Extrait les métriques de tous les runs d'un plan et construit une table plate.

Usage :
    extract_metrics.py <plan> [<plan> ...]

Produit results/metrics/<run_id>.json (une fois par run, mis en cache) et
results/summary/<plan>.csv : une ligne par run avec les colonnes scalaires
utiles au screening. Les structures complètes restent dans les JSON.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs

METRICS_DIR = lib_runs.CAMPAIGN_ROOT / "results" / "metrics"
SUMMARY_DIR = lib_runs.CAMPAIGN_ROOT / "results" / "summary"


def _extract_one(directory_str: str) -> str:
    import lib_metrics
    directory = Path(directory_str)
    run_id = directory.name
    path = METRICS_DIR / f"{run_id}.json"
    manifest = json.loads((directory / "manifest.json").read_text())
    if path.exists():
        cached = json.loads(path.read_text())
        if cached.get("engine_hash") == manifest.get("engine_hash"):
            return run_id
    lib_metrics.save_run_metrics(directory, METRICS_DIR)
    return run_id


def _get(mapping, *keys, default=None):
    value = mapping
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def flat_row(metrics: dict) -> dict:
    p = metrics["parameters"]
    w = metrics["windows"].get("burn0.25", {})
    ws = w.get("series", {})
    wa = w.get("avalanches", {})
    wd = w.get("deaths", {})
    snap = metrics.get("final_snapshot", {})
    row = {
        "run_id": metrics["run_id"],
        "lam": p["lam"], "delta": p["delta"], "sigma": p["sigma"],
        "K0": p["K0"], "k": p["k"], "seed": p["seed"], "T": p["T"],
        "pop_max": p["pop_max"],
        "status": metrics["model_status"],
        "t_final": metrics["t_final"],
        "pop_final": metrics["population_final"],
        "censored": int(metrics["censored_by_pop_max"]),
        "extinct": int(metrics["extinct"]),
        "window_valid": int(bool(ws.get("valid"))),
        # démographie
        "pop_mean": _get(ws, "pop", "mean"),
        "pop_cv": _get(ws, "pop", "cv"),
        "pop_rel_drift": _get(ws, "pop", "rel_drift_window"),
        "pop_slope_per_step": _get(ws, "pop", "slope_per_step"),
        "pop_slope_se": _get(ws, "pop", "slope_se"),
        "pop_tau_int": _get(ws, "pop", "tau_int"),
        "N_over_lambda": metrics.get("N_over_lambda"),
        "births_mean": ws.get("births_mean"),
        "deaths_mean": ws.get("deaths_mean"),
        "age_death_mean": wd.get("age_mean"),
        "age_death_median": wd.get("age_median"),
        "cause_liquidity": _get(wd, "cause_shares", "liquidity"),
        "cause_insolvency": _get(wd, "cause_shares", "insolvency"),
        "cause_cascade": _get(wd, "cause_shares", "cascade"),
        # stationnarité
        "stat_rel_diff": _get(metrics, "stationarity", "rel_diff"),
        "stat_diff_sd": _get(metrics, "stationarity", "diff_in_sd"),
        "K_rel_diff_halves": _get(metrics, "stationarity", "K_rel_diff"),
        # macro / crédit
        "K_tot_mean": ws.get("K_tot_mean"),
        "K_per_capita": _get(ws, "intensive", "K_per_capita"),
        "prod_per_capita": _get(ws, "intensive", "prod_per_capita"),
        "loans_per_capita": _get(ws, "intensive", "loans_per_capita"),
        "deaths_rate": _get(ws, "intensive", "deaths_rate"),
        "interest_to_K": _get(ws, "ratios", "interest_to_K"),
        "new_credit_to_K": _get(ws, "ratios", "new_credit_to_K"),
        "losses_to_K": _get(ws, "ratios", "losses_to_K"),
        "defaults_mean": ws.get("defaults_mean"),
        # avalanches
        "av_n_events": wa.get("n_events"),
        "av_n_tail": wa.get("n_tail"),
        "av_identifiable": int(bool(wa.get("identifiable"))),
        "av_rate": wa.get("rate_per_step"),
        "av_size_q90": wa.get("size_q90"),
        "av_size_q99": wa.get("size_q99"),
        "av_size_max": wa.get("size_max"),
        "av_max_over_pop": wa.get("size_max_over_pop"),
        "susceptibility": wa.get("susceptibility"),
        "branching_ratio": wa.get("branching_ratio"),
        "depth_mean": wa.get("depth_mean"),
        "depth_max": wa.get("depth_max"),
        "alpha_pl": _get(wa, "powerlaw", "alpha"),
        "alpha_pl_se": _get(wa, "powerlaw", "se"),
        "alpha_cut": _get(wa, "powerlaw_cutoff", "alpha"),
        "cutoff_sc": _get(wa, "powerlaw_cutoff", "cutoff"),
        "lrt_cutoff_p": _get(wa, "lrt_cutoff_vs_pure", "p_value"),
        "vuong_z": _get(wa, "vuong_pl_vs_ln", "z"),
        "volume_mean_j": wa.get("volume_mean_j"),
        # distributions (instantané final)
        "snap_n": snap.get("n_entities"),
        "gini_K": _get(snap, "K", "gini_nonneg"),
        "top10_K": _get(snap, "K", "top10_share"),
        "K_log_std": _get(snap, "K", "log_std"),
        "gini_income": _get(snap, "income", "gini_nonneg"),
        "debt_to_K": snap.get("debt_to_K"),
        "frac_borrowers": snap.get("frac_borrowers"),
        "deg_in_mean": snap.get("deg_in_mean"),
        "deg_out_mean": snap.get("deg_out_mean"),
        "nw_negative_frac": snap.get("nw_negative_frac"),
        "age_K_spearman": snap.get("age_K_spearman"),
        "principal_gini": _get(snap, "network", "principal_gini"),
        "principal_top1": _get(snap, "network", "principal_top1pct_share"),
        "rate_mean": _get(snap, "network", "rate_mean"),
        # intégrité
        "balance_residual": _get(metrics, "integrity", "balance_max_rel_residual"),
        "n_book_errors": len(_get(metrics, "integrity", "book_errors", default=[])),
        # robustesse fenêtre : burn T/8 et T/2
        "pop_mean_burn8": _get(metrics, "windows", "burn0.125", "series", "pop", "mean"),
        "pop_mean_burn2": _get(metrics, "windows", "burn0.5", "series", "pop", "mean"),
        "alpha_pl_burn2": _get(metrics, "windows", "burn0.5", "avalanches", "powerlaw", "alpha"),
        "branching_burn2": _get(metrics, "windows", "burn0.5", "avalanches", "branching_ratio"),
    }
    return row


def main() -> None:
    plans = sys.argv[1:]
    if not plans:
        sys.exit("usage: extract_metrics.py <plan> [...]")
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    for plan in plans:
        cells = lib_runs.load_plan(plan)
        directories = []
        for spec in cells:
            directory = lib_runs.run_dir(spec)
            if (directory / "manifest.json").exists():
                directories.append(str(directory))
        with ProcessPoolExecutor(max_workers=6) as pool:
            run_ids = list(pool.map(_extract_one, directories))
        rows = []
        for run_id in run_ids:
            metrics = json.loads((METRICS_DIR / f"{run_id}.json").read_text())
            rows.append(flat_row(metrics))
        if rows:
            path = SUMMARY_DIR / f"{plan}.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            print(f"{plan}: {len(rows)} runs -> {path}")
        else:
            print(f"{plan}: aucun run exécuté")


if __name__ == "__main__":
    main()
