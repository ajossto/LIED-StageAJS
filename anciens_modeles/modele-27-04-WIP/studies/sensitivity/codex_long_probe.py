"""
Sonde longue Codex sur les cas ambigus du screening OAT.

Chaque cas est choisi pour eclairer une zone grise:
  - entree tardive en regime,
  - densite forte mais queue non bornee a 1500 pas,
  - sortie de regime autour du centre k=4,
  - robustesse numerique epsilon.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

RESULTS_DIR = HERE / "results"
FIGURES_DIR = HERE / "report" / "figures"
RESULTS_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

BASE = {"alpha_min": 1.0, "alpha_max": 1.0, "epsilon": 1e-3}

CASES = [
    {
        "case": "k3_sigma0005_late_entry",
        "question": "k=3 sigma=0.005 entre tardivement en regime a 1500 pas",
        "params": {**BASE, "n_candidats_pool": 3, "alpha_sigma_brownien": 0.005},
    },
    {
        "case": "k3_sigma002_dense_unbounded",
        "question": "k=3 sigma=0.02 est dense mais parfois non borne a 1500 pas",
        "params": {**BASE, "n_candidats_pool": 3, "alpha_sigma_brownien": 0.02},
    },
    {
        "case": "k3_mu0_dense",
        "question": "mu=0 declenche un regime dense sous k=3",
        "params": {**BASE, "n_candidats_pool": 3, "alpha_sigma_brownien": 0.0, "mu": 0.0},
    },
    {
        "case": "k3_theta05_dense",
        "question": "theta=0.5 peut faire basculer k=3",
        "params": {**BASE, "n_candidats_pool": 3, "alpha_sigma_brownien": 0.0, "theta": 0.5},
    },
    {
        "case": "k4_theta02_exit",
        "question": "theta=0.2 sort du regime autour de k=4",
        "params": {**BASE, "n_candidats_pool": 4, "alpha_sigma_brownien": 0.0, "theta": 0.2},
    },
    {
        "case": "k4_lambda4_growth",
        "question": "lambda=4 peut imposer une croissance non compensee",
        "params": {**BASE, "n_candidats_pool": 4, "alpha_sigma_brownien": 0.0, "lambda_creation": 4.0},
    },
    {
        "case": "k4_depr_endo002_slow",
        "question": "depreciation endo faible augmente le volume mais peut etre lentement non stationnaire",
        "params": {**BASE, "n_candidats_pool": 4, "alpha_sigma_brownien": 0.0, "taux_depreciation_endo": 0.02},
    },
    {
        "case": "k4_actif400_exit",
        "question": "dotation initiale forte peut retarder ou empecher le regime",
        "params": {**BASE, "n_candidats_pool": 4, "alpha_sigma_brownien": 0.0, "actif_liquide_initial": 400.0},
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42])
    parser.add_argument("--workers", type=int, default=max(1, min(6, os.cpu_count() or 6)))
    args = parser.parse_args()

    result_path = RESULTS_DIR / f"codex_long_probe_steps{args.steps}_seeds{'-'.join(map(str, args.seeds))}.json"
    agg_path = RESULTS_DIR / f"codex_long_probe_steps{args.steps}_seeds{'-'.join(map(str, args.seeds))}_aggregate.json"
    fig_path = FIGURES_DIR / f"codex_long_probe_steps{args.steps}_seeds{'-'.join(map(str, args.seeds))}.pdf"

    rows = load(result_path)
    done = {row["case_key"] for row in rows}
    cases = []
    for spec in CASES:
        for seed in args.seeds:
            key = f"long|case={spec['case']}|seed={seed}|steps={args.steps}"
            if key in done:
                continue
            cases.append({**spec, "case_key": key, "seed": seed, "steps": args.steps})

    print(f"{len(done)} cas deja presents, {len(cases)} cas a lancer.")
    with ProcessPoolExecutor(max_workers=args.workers) as exe:
        futures = {exe.submit(worker, case): case for case in cases}
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            save(result_path, rows)
            print(
                f"{row['case']:28s} seed={row['seed']} bounded={row['bounded_tail']} "
                f"tail={row['t_measure']} dens={row['measure_densite_fin_mean']:.3f} "
                f"loans={row['measure_loan_density_mean']:.1f} alive={row['measure_n_alive_mean']:.0f} "
                f"slopeN={row['alive_tail_slope_rel']:.3f}"
            )

    agg = aggregate(rows)
    agg_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    plot(rows, fig_path)
    print(f"Resultats : {result_path}")
    print(f"Agregats  : {agg_path}")
    print(f"Figure    : {fig_path}")


def worker(case: dict[str, Any]) -> dict[str, Any]:
    res = run_and_collect(case["params"], n_steps=case["steps"], seed=case["seed"])
    row = {k: v for k, v in res.items() if k != "dist_values_regime"}
    diag = row.get("regime_diagnostics", {})
    row.update({
        "dataset": "codex_long_probe",
        "case": case["case"],
        "case_key": case["case_key"],
        "question": case["question"],
        "seed": case["seed"],
        "steps": case["steps"],
        "k": row.get("params", {}).get("n_candidats_pool"),
        "epsilon": row.get("params", {}).get("epsilon"),
        "alpha_sigma_brownien": row.get("params", {}).get("alpha_sigma_brownien"),
        "bounded_tail": bool(diag.get("bounded_tail", False)),
        "drop_5_detected": bool(diag.get("drop_5_detected", False)),
        "alive_tail_slope_rel": diag.get("alive_tail_slope_rel"),
        "actif_tail_slope_rel": diag.get("actif_tail_slope_rel"),
        "densite_fin_tail_slope_rel": diag.get("densite_fin_tail_slope_rel"),
        "tail_failure_rate": diag.get("tail_failure_rate"),
        "corr_alive_actif_tail": diag.get("corr_alive_actif_tail"),
        "corr_alive_loans_tail": diag.get("corr_alive_loans_tail"),
        "corr_actif_loans_tail": diag.get("corr_actif_loans_tail"),
    })
    return row


def load(path: Path) -> list[dict[str, Any]]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save(path: Path, rows: list[dict[str, Any]]) -> None:
    rows = sorted(rows, key=lambda r: (r["case"], r["seed"]))
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["case"], []).append(row)
    metrics = [
        "bounded_tail",
        "measure_densite_fin_mean",
        "measure_loan_density_mean",
        "measure_n_alive_mean",
        "measure_failure_rate_mean",
        "cascade_size_mean",
        "alive_tail_slope_rel",
        "actif_tail_slope_rel",
        "corr_alive_actif_tail",
    ]
    out = []
    for case, vals in groups.items():
        rec: dict[str, Any] = {
            "case": case,
            "question": vals[0].get("question"),
            "n": len(vals),
            "params": vals[0].get("params"),
        }
        for metric in metrics:
            if metric == "bounded_tail":
                rec["bounded_tail_share"] = sum(1 for v in vals if v.get(metric)) / len(vals)
            else:
                xs = [float(v[metric]) for v in vals if v.get(metric) is not None]
                if xs:
                    rec[f"{metric}_mean"] = float(np.mean(xs))
                    rec[f"{metric}_std"] = float(np.std(xs))
        out.append(rec)
    return sorted(out, key=lambda r: r["case"])


def plot(rows: list[dict[str, Any]], path: Path) -> None:
    rows = sorted(rows, key=lambda r: r["case"])
    fig, axes = plt.subplots(len(rows), 4, figsize=(16, max(2.0 * len(rows), 4)), squeeze=False)
    for row_axes, row in zip(axes, rows):
        t = list(range(len(row["ts_n_alive"])))
        series = [
            (row["ts_n_alive"], "n_alive", "tab:blue"),
            (row["ts_actif"], "actif", "tab:green"),
            (row["ts_densite_fin"], "densite", "tab:orange"),
            ([l / n if n else 0.0 for l, n in zip(row["ts_n_loans"], row["ts_n_alive"])], "prets/entite", "tab:red"),
        ]
        for ax, (values, ylabel, color) in zip(row_axes, series):
            ax.plot(t, values, color=color, linewidth=1.0)
            ax.axvline(row.get("t_measure", 0), color="black", linewidth=0.8, alpha=0.5)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(alpha=0.25)
            ax.tick_params(labelsize=8)
        row_axes[0].set_title(f"{row['case']} | bounded={row['bounded_tail']}", loc="left", fontsize=8)
    for ax in axes[-1]:
        ax.set_xlabel("pas")
    fig.suptitle("Sonde longue Codex: trajectoires et debut de fenetre mesuree")
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
