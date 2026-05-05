"""
Simulation longue k3 sigma=0.005 à 10 000 pas.

Étend les résultats existants (5000 pas) jusqu'à 10 000 pas pour déterminer si le
comportement d'oscillation lente observé est robuste ou transitoire.

Watchdog : arrêt si > 400 ms/pas en moyenne glissante sur 200 derniers pas.

Seeds testées : 7, 123, 0, 1 (non-divergentes à 5000 pas), + 2, 3 (nouvelles).
Seed 42 est exclue (population explose dès step 1401).

Usage :
  python long_run_k3sigma0005_10k.py [--dry-run] [--workers N]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent.parent
JUPYTER_DIR = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(JUPYTER_DIR))

OUT_JSON = HERE / "results" / "long_run_k3sigma0005_10k.json"
LAB_RUNS_DIR = JUPYTER_DIR / "simulation_lab_data" / "runs"

PARAMS_OVERRIDE = {
    "alpha_sigma_brownien": 0.005,
    "n_candidats_pool": 3,
    "epsilon": 0.001,
}
N_STEPS = 10_000
SEEDS = [7, 123, 0, 1, 2, 3]
SLOW_THRESHOLD_MS = 400
PROBE_INTERVAL = 200


def _run_job(seed: int) -> dict:
    """Utilise run_and_collect() qui gère lui-même le chargement des modules."""
    from run_simulation import run_and_collect, _safe_mean
    t0 = time.perf_counter()
    r = run_and_collect(PARAMS_OVERRIDE, n_steps=N_STEPS, seed=seed)
    elapsed = time.perf_counter() - t0

    diag = r.get("regime_diagnostics") or {}
    lambda_c = r.get("params", {}).get("lambda_creation", 2.0)
    tail_start = int(r.get("t_measure") or 0)
    flr = r.get("measure_failure_lambda_ratio", 0.0) or 0.0
    flow_balanced = abs(flr - 1.0) < 0.15 if lambda_c > 0 else False
    bounded_tail = bool(diag.get("bounded_tail", False))
    stationary = bounded_tail and flow_balanced

    # Compact probes for overview figure from full time-series
    ts_alive = r.get("ts_n_alive", [])
    ts_loans = r.get("ts_n_loans", [])
    ts_densite = r.get("ts_densite_fin", [])
    ts_gini = r.get("ts_gini", [])
    n = len(ts_alive)
    probe = [{"step": t, "alive": ts_alive[t], "loans": ts_loans[t] if t < len(ts_loans) else 0}
             for t in range(0, n, PROBE_INTERVAL)]

    print(f"  seed={seed}: n_steps={n} bounded={bounded_tail} flow={flow_balanced} "
          f"stat={stationary} alive_final={ts_alive[-1] if ts_alive else '?'} "
          f"elapsed={elapsed:.0f}s", flush=True)

    return {
        "seed": seed,
        "n_steps_requested": N_STEPS,
        "n_steps_done": n,
        "stopped_early": False,
        "total_wall_s": round(elapsed, 2),
        "avg_ms_per_step": round(elapsed * 1000 / n, 2) if n > 0 else 0,
        "max_ms_per_step": 0,
        "final_alive": ts_alive[-1] if ts_alive else 0,
        "final_loans": ts_loans[-1] if ts_loans else 0,
        "final_densite_fin": ts_densite[-1] if ts_densite else 0,
        "final_gini": ts_gini[-1] if ts_gini else 0,
        "bounded_tail": bounded_tail,
        "flow_balanced": flow_balanced,
        "stationary": stationary,
        "failure_lambda_ratio": round(flr, 4),
        "alive_tail_slope_rel": diag.get("alive_tail_slope_rel"),
        "actif_tail_slope_rel": diag.get("actif_tail_slope_rel"),
        "alive_tail_iqr_rel": diag.get("alive_tail_iqr_rel"),
        "tail_start": tail_start,
        "probe": probe,
        "ts_alive": ts_alive,
        "ts_loans_series": ts_loans,
        "ts_densite": ts_densite,
        "ts_gini": ts_gini,
        "params": PARAMS_OVERRIDE,
        "executed_at_local": datetime.now(timezone.utc).astimezone().isoformat(),
    }


def _sanitize(v):
    if isinstance(v, dict):
        return {str(k): _sanitize(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize(x) for x in v]
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def export_to_lab(r: dict) -> str:
    from simulation_lab.contracts import collect_artifacts
    seed = r["seed"]
    run_id = f"sensitivity_claude_long_run_k3sigma0005_10k_seed{seed}"
    run_dir = LAB_RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Compact timeseries
    probe = r.get("probe", [])
    ts_alive = r.get("ts_alive", [])
    ts_loans = r.get("ts_loans_series", [])
    ts_densite = r.get("ts_densite", [])
    ts_gini = r.get("ts_gini", [])
    n = min(len(ts_alive), len(ts_loans), len(ts_densite), len(ts_gini))
    if n > 0:
        rows = [{"t": t, "alive": ts_alive[t], "actif": 0, "loans": ts_loans[t],
                 "densite_fin": ts_densite[t], "gini": ts_gini[t]}
                for t in range(n)]
        (run_dir / "compact_timeseries.json").write_text(
            json.dumps({"rows": rows}, indent=2), encoding="utf-8")

    # Overview figure
    _plot_overview(r, run_dir / "overview.png")

    # Strip heavy timeseries from run.json record
    record = {k: v for k, v in r.items()
              if k not in ("ts_alive", "ts_loans_series", "ts_densite", "ts_gini", "probe")}
    (run_dir / "record.json").write_text(
        json.dumps(_sanitize(record), indent=2, ensure_ascii=False), encoding="utf-8")

    # run.json metadata
    artifacts = [a.to_dict() for a in collect_artifacts(run_dir)]
    status_label = "stationary" if r["stationary"] else ("stopped_early" if r["stopped_early"] else "running_not_stationary")
    meta = {
        "run_id": run_id,
        "model_id": "etude_sensibilite_27_04_wip",
        "parameters": _sanitize({
            **r["params"],
            "_campaign": "claude_long_run_k3sigma0005_10k",
            "executed_at_local": r.get("executed_at_local", ""),
        }),
        "seed": seed,
        "label": f"k3 σ=0.005 long run 10k | seed={seed} | {status_label}",
        "batch_id": "claude_long_run_k3sigma0005_10k",
        "study_group": "long_runs",
        "status": "completed",
        "keep": True,
        "important": True,
        "trashed": False,
        "trashed_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": _sanitize({
            "bounded_tail": r["bounded_tail"],
            "flow_balanced": r["flow_balanced"],
            "stationary": r["stationary"],
            "failure_lambda_ratio": r["failure_lambda_ratio"],
            "n_steps_done": r["n_steps_done"],
            "stopped_early": r["stopped_early"],
            "final_alive": r["final_alive"],
            "has_timeseries": n > 0,
        }),
        "artifacts": artifacts,
        "preview_artifact": "overview.png",
        "message": "Simulation longue k3 sigma=0.005 à 10 000 pas. Watchdog 400ms/pas.",
        "comment": "",
        "extra": {"source": "long_run_k3sigma0005_10k"},
    }
    (run_dir / "run.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_id


def _plot_overview(r: dict, out: Path) -> None:
    ts_alive = r.get("ts_alive", [])
    ts_loans = r.get("ts_loans_series", [])
    ts_densite = r.get("ts_densite", [])
    ts_gini = r.get("ts_gini", [])
    n = min(len(ts_alive), len(ts_loans), len(ts_densite), len(ts_gini))
    t = list(range(n))
    fig, axes = plt.subplots(2, 2, figsize=(12, 6), constrained_layout=True)
    for ax, series, label, color in [
        (axes[0, 0], ts_alive[:n],   "n vivantes",    "#4e9af1"),
        (axes[0, 1], ts_loans[:n],   "n prêts",       "#57a64b"),
        (axes[1, 0], ts_densite[:n], "densité fin.",  "#e07b39"),
        (axes[1, 1], ts_gini[:n],    "Gini actif",    "#b07aa1"),
    ]:
        ax.plot(t, series, color=color, linewidth=0.7)
        ax.set_ylabel(label)
        ax.set_xlabel("pas")
        ax.grid(alpha=0.2)
    bounded = r.get("bounded_tail", False)
    stat = r.get("stationary", False)
    flr = r.get("failure_lambda_ratio", 0)
    title = (f"k=3 σ=0.005 | seed={r['seed']} | {r['n_steps_done']} pas"
             f" | bounded={bounded} stat={stat} flr={flr:.3f}")
    if r.get("stopped_early"):
        title += " [ARRÊT PRÉCOCE]"
    fig.suptitle(title, fontsize=9)
    fig.savefig(out, dpi=120)
    plt.close(fig)


def _plot_comparison(results: list[dict], out: Path) -> None:
    """Trajectoires n_alive superposées pour toutes les seeds."""
    COLORS = ["#4e9af1", "#e07b39", "#57a64b", "#b07aa1", "#e05c5c", "#5cb8b0"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
    series_map = [
        ("ts_alive",        "n vivantes",   "#4e9af1"),
        ("ts_loans_series", "n prêts",      "#57a64b"),
        ("ts_densite",      "densité fin.", "#e07b39"),
        ("ts_gini",         "Gini actif",   "#b07aa1"),
    ]
    for ax, (key, label, _) in zip(axes.flat, series_map):
        for i, r in enumerate(results):
            ts = r.get(key, [])
            if ts:
                ls = "--" if r.get("stopped_early") else "-"
                ax.plot(ts, linewidth=0.7, linestyle=ls,
                        color=COLORS[i % len(COLORS)],
                        label=f"seed={r['seed']}{' [stop]' if r.get('stopped_early') else ''}")
        ax.set_ylabel(label)
        ax.set_xlabel("pas")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7)
    fig.suptitle("k=3 σ=0.005 — 10 000 pas — trajectoires comparées", fontsize=10)
    fig.savefig(out, dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    LAB_RUNS_DIR.mkdir(parents=True, exist_ok=True)

    existing = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else []
    done_seeds = {e["seed"] for e in existing}
    results = list(existing)

    jobs = [s for s in SEEDS if s not in done_seeds]
    print(f"Seeds à lancer : {jobs}  (déjà faites : {sorted(done_seeds)})")
    if args.dry_run or not jobs:
        print("Mode dry-run ou rien à faire.")
        return

    for seed in jobs:
        try:
            r = _run_job(seed)
            results.append(r)
            OUT_JSON.write_text(json.dumps(_sanitize(results), indent=2, ensure_ascii=False))
            print(f"✓ seed={seed} bounded={r['bounded_tail']} stat={r['stationary']} "
                  f"flr={r['failure_lambda_ratio']:.3f} alive={r['final_alive']}")
        except Exception as e:
            print(f"✗ seed={seed}: {e}")

    # Export all results to simulation_lab
    print("\nExport vers simulation_lab…")
    for r in results:
        run_id = export_to_lab(r)
        print(f"  → {run_id}")

    # Comparison figure
    fig_out = HERE / "results" / "long_run_k3sigma0005_10k_comparison.png"
    _plot_comparison(results, fig_out)
    print(f"\nFigure comparative : {fig_out}")

    # Summary
    print("\nRésumé :")
    for r in sorted(results, key=lambda x: x["seed"]):
        stop = "[STOP]" if r["stopped_early"] else ""
        print(f"  seed={r['seed']}: bounded={r['bounded_tail']} stat={r['stationary']} "
              f"flr={r['failure_lambda_ratio']:.3f} alive={r['final_alive']} "
              f"avg={r['avg_ms_per_step']:.0f}ms {stop}")


if __name__ == "__main__":
    main()
