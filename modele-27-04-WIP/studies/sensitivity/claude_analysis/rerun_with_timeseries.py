"""
Rerun complet des simulations des couplages en conservant les time-series.

Pour chaque combinaison de paramètres des 4 couplages, relance run_and_collect()
mais GARDE les ts_* (time-series compactes). Exporte chaque run dans Simulation Lab
avec un compact_timeseries.json et un overview figure.

Conforme à la règle de traçabilité scientifique :
  toute simulation qui informe une conclusion conserve ses données brutes
  et est exportable dans Simulation Lab.

Usage :
  python rerun_with_timeseries.py [--dry-run] [--campaign <nom>] [--workers N]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

RESULTS_DIR = HERE / "results"
JUPYTER_DIR = HERE.parents[2]
LAB_RUNS_DIR = JUPYTER_DIR / "simulation_lab_data" / "runs"
MODEL_ID = "etude_sensibilite_27_04_wip"

# ── Grilles de paramètres (identiques aux scripts originaux) ─────────────────

CAMPAIGNS = {
    "coupling_lambda_k": {
        "keys": ["n_candidats_pool", "lambda_creation"],
        "grid": [
            {"n_candidats_pool": k, "lambda_creation": lam, "epsilon": 1e-3}
            for k in [2, 3, 4, 5, 6]
            for lam in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
        ],
        "seeds": [42, 7, 123],
        "n_steps": 1500,
        "study_group": "couplages",
        "description": "Couplage λ × k, time-series complètes.",
    },
    "coupling_k_mu": {
        "keys": ["n_candidats_pool", "mu"],
        "grid": [
            {"n_candidats_pool": k, "mu": mu, "epsilon": 1e-3}
            for k in [2, 3, 4, 5]
            for mu in [0.00, 0.01, 0.03, 0.05, 0.10]
        ],
        "seeds": [42, 7, 123],
        "n_steps": 1500,
        "study_group": "couplages",
        "description": "Couplage k × μ, time-series complètes.",
    },
    "coupling_sigma_k": {
        "keys": ["n_candidats_pool", "alpha_sigma_brownien"],
        "grid": [
            {"n_candidats_pool": k, "alpha_sigma_brownien": sig, "epsilon": 1e-3}
            for k in [2, 3, 4, 5]
            for sig in [0.000, 0.003, 0.010, 0.020, 0.050]
        ],
        "seeds": [42, 7, 123],
        "n_steps": 1500,
        "study_group": "couplages",
        "description": "Couplage σ × k, time-series complètes.",
    },
    "coupling_theta_depr": {
        "keys": ["theta", "taux_depreciation_endo", "n_candidats_pool"],
        "grid": [
            {"theta": theta, "taux_depreciation_endo": depr, "n_candidats_pool": k, "epsilon": 1e-3}
            for k in [3, 4]
            for theta in [0.20, 0.28, 0.35, 0.42, 0.50]
            for depr in [0.02, 0.05, 0.10]
        ],
        "seeds": [42, 7, 123],
        "n_steps": 1500,
        "study_group": "couplages",
        "description": "Couplage θ × δ_endo, time-series complètes.",
    },
}


def _job(params_override: dict, n_steps: int, seed: int) -> dict:
    r = run_and_collect(params_override, n_steps=n_steps, seed=seed)
    return r


def run_campaign(name: str, spec: dict, dry_run: bool, n_workers: int) -> list[str]:
    grid = spec["grid"]
    seeds = spec["seeds"]
    n_steps = spec["n_steps"]
    study_group = spec["study_group"]
    description = spec["description"]

    # Check what's already done
    done_file = RESULTS_DIR / f"rerun_ts_{name}.json"
    done_records: list[dict] = json.loads(done_file.read_text()) if done_file.exists() else []
    done_keys = {(r["_params_key"], r["seed"]) for r in done_records}

    jobs = [
        (params, seed)
        for params in grid
        for seed in seeds
        if (_params_key(params), seed) not in done_keys
    ]
    print(f"[{name}] {len(jobs)} sims à lancer, {len(done_records)} déjà présentes.")
    if dry_run:
        return []

    results = list(done_records)
    exported: list[str] = []

    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        futures = {ex.submit(_job, params, n_steps, seed): (params, seed) for params, seed in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            params, seed = futures[fut]
            try:
                r = fut.result()
                r["_params_key"] = _params_key(params)
                r["_campaign"] = name
                results.append(r)
                bt = (r.get("regime_diagnostics") or {}).get("bounded_tail", "?")
                df = r.get("measure_densite_fin_mean", 0)
                print(f"  [{i}/{len(jobs)}] {_params_key(params)} seed={seed}: bounded={bt} df={df:.3f}")
            except Exception as e:
                print(f"  ERREUR {_params_key(params)} seed={seed}: {e}")
            # Save incrementally
            done_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    # Export to Simulation Lab
    print(f"[{name}] Export vers Simulation Lab...")
    for r in results:
        run_id = _lab_run_id(name, r)
        run_dir = LAB_RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        # compact_timeseries.json
        ts_rows = _make_compact_ts(r)
        if ts_rows:
            (run_dir / "compact_timeseries.json").write_text(
                json.dumps({"rows": ts_rows}, indent=2), encoding="utf-8"
            )
        # Strip heavy fields before saving record.json
        record = {k: v for k, v in r.items()
                  if not k.startswith("ts_") and k != "dist_values_regime"}
        (run_dir / "record.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        # Overview figure
        _plot_overview(r, run_dir / "overview.png")
        # run.json metadata
        _write_run_json(run_id, name, spec, r, run_dir)
        exported.append(run_id)

    print(f"[{name}] {len(exported)} runs exportés dans {LAB_RUNS_DIR}")
    return exported


def _params_key(params: dict) -> str:
    return "|".join(f"{k}={v}" for k, v in sorted(params.items()))


def _lab_run_id(campaign: str, r: dict) -> str:
    parts = ["sensitivity_ts", campaign]
    for key in ["n_candidats_pool", "lambda_creation", "mu", "alpha_sigma_brownien",
                "theta", "taux_depreciation_endo"]:
        if key in (r.get("params") or {}):
            v = r["params"][key]
            parts.append(f"{key[:4]}{_fmt(v)}")
    if r.get("seed") is not None:
        parts.append(f"s{r['seed']}")
    return "_".join(parts)[:180]


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:g}".replace(".", "p").replace("-", "m")
    return str(v)


def _make_compact_ts(r: dict) -> list[dict]:
    n_alive = r.get("ts_n_alive", [])
    actif = r.get("ts_actif", [])
    n_loans = r.get("ts_n_loans", [])
    densite = r.get("ts_densite_fin", [])
    gini = r.get("ts_gini", [])
    n = min(len(n_alive), len(actif), len(n_loans), len(densite), len(gini))
    if n == 0:
        return []
    return [
        {"t": t, "alive": n_alive[t], "actif": actif[t],
         "loans": n_loans[t], "densite_fin": densite[t], "gini": gini[t]}
        for t in range(n)
    ]


def _plot_overview(r: dict, out: Path) -> None:
    ts_alive = r.get("ts_n_alive", [])
    ts_actif = r.get("ts_actif", [])
    ts_densite = r.get("ts_densite_fin", [])
    ts_gini = r.get("ts_gini", [])
    n = min(len(ts_alive), len(ts_actif), len(ts_densite), len(ts_gini))
    if n == 0:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Pas de time-series disponible", ha="center", va="center")
        fig.savefig(out, dpi=100)
        plt.close(fig)
        return
    t = list(range(n))
    fig, axes = plt.subplots(2, 2, figsize=(12, 6), constrained_layout=True)
    for ax, series, label, color in [
        (axes[0, 0], ts_alive[:n],   "n_alive",     "#4e9af1"),
        (axes[0, 1], ts_actif[:n],   "actif total", "#57a64b"),
        (axes[1, 0], ts_densite[:n], "densité fin.", "#e07b39"),
        (axes[1, 1], ts_gini[:n],    "Gini actif",  "#b07aa1"),
    ]:
        ax.plot(t, series, color=color, linewidth=0.8)
        ax.set_ylabel(label)
        ax.set_xlabel("pas")
        ax.grid(alpha=0.2)
        bt = (r.get("regime_diagnostics") or {}).get("bounded_tail")
        t_r = r.get("t_regime")
        if t_r:
            ax.axvline(t_r, color="red", linewidth=0.7, linestyle="--", alpha=0.6)
    params = r.get("params") or {}
    title_bits = []
    for k in ["n_candidats_pool", "lambda_creation", "mu", "alpha_sigma_brownien",
               "theta", "taux_depreciation_endo"]:
        if k in params:
            title_bits.append(f"{k[:5]}={params[k]}")
    title_bits.append(f"seed={r.get('seed', '?')}")
    bt = (r.get("regime_diagnostics") or {}).get("bounded_tail")
    title_bits.append(f"borné={bt}")
    fig.suptitle(" | ".join(title_bits), fontsize=9)
    fig.savefig(out, dpi=120)
    plt.close(fig)


def _write_run_json(run_id: str, campaign: str, spec: dict, r: dict, run_dir: Path) -> None:
    from simulation_lab.contracts import collect_artifacts
    params = dict(r.get("params") or {})
    params["_campaign"] = campaign
    params["exported_at_local"] = datetime.now(timezone.utc).astimezone().isoformat()
    if r.get("executed_at_local"):
        params["executed_at_local"] = r["executed_at_local"]
    diag = r.get("regime_diagnostics") or {}
    summary = {
        "bounded_tail": diag.get("bounded_tail"),
        "drop_5_detected": r.get("converged"),
        "densite_fin_mean": r.get("measure_densite_fin_mean"),
        "n_alive_mean": r.get("measure_n_alive_mean"),
        "t_regime": r.get("t_regime"),
        "has_timeseries": True,
    }
    meta = {
        "run_id": run_id,
        "model_id": MODEL_ID,
        "parameters": _sanitize(params),
        "seed": r.get("seed"),
        "label": f"ts | {campaign} | {r.get('_params_key', '')} | seed={r.get('seed')}",
        "batch_id": f"rerun_ts_{campaign}",
        "study_group": spec["study_group"],
        "status": "completed",
        "keep": True,
        "important": False,
        "trashed": False,
        "trashed_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": _sanitize(summary),
        "artifacts": [a.to_dict() for a in collect_artifacts(run_dir)],
        "preview_artifact": "overview.png",
        "message": spec["description"],
        "comment": "",
        "extra": {"source": "rerun_with_timeseries", "campaign": campaign},
    }
    (run_dir / "run.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _sanitize(v):
    if isinstance(v, dict):
        return {str(k): _sanitize(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize(x) for x in v]
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Liste les sims sans les lancer.")
    parser.add_argument("--campaign", default=None, help="Nom de la campagne (défaut: toutes).")
    parser.add_argument("--workers", type=int, default=6, help="Nombre de workers parallèles.")
    args = parser.parse_args()

    LAB_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    campaigns = {args.campaign: CAMPAIGNS[args.campaign]} if args.campaign else CAMPAIGNS

    total_exported: list[str] = []
    for name, spec in campaigns.items():
        exported = run_campaign(name, spec, dry_run=args.dry_run, n_workers=args.workers)
        total_exported.extend(exported)

    if not args.dry_run:
        print(f"\nTotal : {len(total_exported)} runs exportés vers Simulation Lab.")


if __name__ == "__main__":
    main()
