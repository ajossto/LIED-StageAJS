"""
Campagne OAT autour de deux centres alpha homogenes.

Centres:
  - subcritical_k3 : k=3, alpha_min=alpha_max=1, epsilon=1e-3
  - regime_k4      : k=4, alpha_min=alpha_max=1, epsilon=1e-3

Le script est resumable: les cas deja presents dans le JSON sont sautes.
Par defaut il fait un screening a seed=42. Passer --seeds 42 7 123 pour la
campagne de robustesse.
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
from run_simulation import BASELINE, run_and_collect

RESULTS_DIR = HERE / "results"
FIGURES_DIR = HERE / "report" / "figures"
RESULTS_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

CENTERS = {
    "subcritical_k3": {"n_candidats_pool": 3, "alpha_sigma_brownien": 0.0, "epsilon": 1e-3},
    "regime_k4": {"n_candidats_pool": 4, "alpha_sigma_brownien": 0.0, "epsilon": 1e-3},
}

# Chaque entree contient les valeurs a tester. La valeur centrale est retiree
# automatiquement pour eviter de relancer le meme point pour chaque parametre.
OAT_VALUES = {
    "theta": [0.20, 0.35, 0.50],
    "mu": [0.00, 0.05, 0.10],
    "lambda_creation": [1.0, 2.0, 4.0],
    "n_candidats_pool": {"subcritical_k3": [2, 3, 4], "regime_k4": [3, 4, 5]},
    "fraction_taux_emprunteur": [0.0, 0.2, 0.5],
    "seuil_ratio_endettement": [0.5, 1.0, 1.5],
    "seuil_ratio_liquide_passif": [0.02, 0.05, 0.10],
    "taux_depreciation_endo": [0.02, 0.05, 0.10],
    "taux_depreciation_exo": [0.02, 0.05, 0.10],
    "fraction_auto_investissement": [0.25, 0.50, 0.75],
    "coefficient_reliquefaction": [0.25, 0.50, 0.75],
    "actif_liquide_initial": [100.0, 200.0, 400.0],
    "n_entites_initiales": [50, 100, 200],
    "alpha_sigma_brownien": [0.0, 0.005, 0.02],
    "epsilon": [1e-6, 1e-3, 1e-2],
}

SUMMARY_METRICS = [
    "measure_densite_fin_mean",
    "measure_loan_density_mean",
    "measure_n_alive_mean",
    "measure_failure_rate_mean",
    "measure_gini_actif_mean",
    "cascade_event_rate",
    "cascade_size_mean",
    "bounded_tail",
    "drop_5_detected",
    "alive_tail_slope_rel",
    "actif_tail_slope_rel",
    "corr_alive_actif_tail",
    "corr_alive_loans_tail",
]


def center_params(center: str) -> dict[str, Any]:
    return dict(CENTERS[center])


def values_for(center: str, parameter: str) -> list[Any]:
    values = OAT_VALUES[parameter]
    if isinstance(values, dict):
        return list(values[center])
    return list(values)


def baseline_value(center: str, parameter: str) -> Any:
    params = {**BASELINE, **center_params(center)}
    return params[parameter]


def case_key(center: str, parameter: str, value: Any, seed: int, steps: int) -> str:
    return f"oat|center={center}|param={parameter}|value={format_token(value)}|seed={seed}|steps={steps}"


def center_key(center: str, seed: int, steps: int) -> str:
    return f"oat|center={center}|param=__center__|value=center|seed={seed}|steps={steps}"


def build_cases(steps: int, seeds: list[int], parameters: list[str]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for center in CENTERS:
        for seed in seeds:
            cases.append({
                "case_key": center_key(center, seed, steps),
                "center": center,
                "parameter": "__center__",
                "value": None,
                "direction": "center",
                "seed": seed,
                "steps": steps,
                "params": center_params(center),
            })
            for parameter in parameters:
                base = baseline_value(center, parameter)
                for value in values_for(center, parameter):
                    if same_value(value, base):
                        continue
                    params = center_params(center)
                    params[parameter] = value
                    if parameter == "actif_liquide_initial":
                        params["passif_inne_initial"] = float(value) - 10.0
                    direction = "high" if float(value) > float(base) else "low"
                    cases.append({
                        "case_key": case_key(center, parameter, value, seed, steps),
                        "center": center,
                        "parameter": parameter,
                        "value": value,
                        "baseline_value": base,
                        "direction": direction,
                        "seed": seed,
                        "steps": steps,
                        "params": params,
                    })
    return cases


def same_value(a: Any, b: Any) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        return abs(float(a) - float(b)) <= 1e-12
    return a == b


def _worker(case: dict[str, Any]) -> dict[str, Any]:
    res = run_and_collect(case["params"], n_steps=case["steps"], seed=case["seed"])
    row = compact_result(res)
    diag = row.get("regime_diagnostics", {})
    row.update({
        "case_key": case["case_key"],
        "dataset": "oat_screen",
        "center": case["center"],
        "parameter": case["parameter"],
        "value": case["value"],
        "baseline_value": case.get("baseline_value"),
        "direction": case["direction"],
        "seed": case["seed"],
        "steps": case["steps"],
        "k": row.get("params", {}).get("n_candidats_pool"),
        "epsilon": row.get("params", {}).get("epsilon"),
        "alpha_sigma_brownien": row.get("params", {}).get("alpha_sigma_brownien"),
        "drop_5_detected": bool(diag.get("drop_5_detected", False)),
        "bounded_tail": bool(diag.get("bounded_tail", False)),
        "alive_tail_slope_rel": diag.get("alive_tail_slope_rel"),
        "actif_tail_slope_rel": diag.get("actif_tail_slope_rel"),
        "densite_fin_tail_slope_rel": diag.get("densite_fin_tail_slope_rel"),
        "failures_tail_slope_abs": diag.get("failures_tail_slope_abs"),
        "tail_failure_rate": diag.get("tail_failure_rate"),
        "corr_alive_actif_tail": diag.get("corr_alive_actif_tail"),
        "corr_alive_loans_tail": diag.get("corr_alive_loans_tail"),
        "corr_actif_loans_tail": diag.get("corr_actif_loans_tail"),
        "corr_alive_failures_tail": diag.get("corr_alive_failures_tail"),
        "corr_actif_failures_tail": diag.get("corr_actif_failures_tail"),
    })
    return row


def compact_result(res: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in res.items()
        if not key.startswith("ts_") and key != "dist_values_regime"
    }


def load(path: Path) -> list[dict[str, Any]]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save(path: Path, rows: list[dict[str, Any]]) -> None:
    rows = sorted(rows, key=lambda r: (r["center"], r["parameter"], str(r.get("value")), r["seed"]))
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["center"], row["parameter"], format_token(row.get("value")), row["direction"])
        groups.setdefault(key, []).append(row)

    out = []
    for (center, parameter, value_token, direction), vals in groups.items():
        rec: dict[str, Any] = {
            "center": center,
            "parameter": parameter,
            "value": vals[0].get("value"),
            "value_token": value_token,
            "direction": direction,
            "n": len(vals),
        }
        for metric in SUMMARY_METRICS:
            if metric in {"bounded_tail", "drop_5_detected"}:
                rec[f"{metric}_share"] = sum(1 for v in vals if v.get(metric)) / len(vals)
                continue
            xs = [float(v[metric]) for v in vals if is_number(v.get(metric))]
            if xs:
                rec[f"{metric}_mean"] = float(np.mean(xs))
                rec[f"{metric}_std"] = float(np.std(xs))
        out.append(rec)
    return sorted(out, key=lambda r: (r["center"], r["parameter"], r["direction"], str(r["value"])))


def sensitivity_table(agg: list[dict[str, Any]]) -> list[dict[str, Any]]:
    centers = {
        row["center"]: row for row in agg
        if row["parameter"] == "__center__" and row["direction"] == "center"
    }
    out = []
    for row in agg:
        if row["parameter"] == "__center__":
            continue
        center_row = centers.get(row["center"])
        if not center_row:
            continue
        rec = {
            "center": row["center"],
            "parameter": row["parameter"],
            "value": row["value"],
            "direction": row["direction"],
            "n": row["n"],
        }
        for metric in [
            "measure_densite_fin_mean_mean",
            "measure_loan_density_mean_mean",
            "measure_n_alive_mean_mean",
            "measure_failure_rate_mean_mean",
            "bounded_tail_share",
            "cascade_size_mean_mean",
            "corr_alive_actif_tail_mean",
        ]:
            if metric in row and metric in center_row:
                rec[f"delta_{metric}"] = row[metric] - center_row[metric]
                denom = abs(center_row[metric])
                if denom > 1e-12:
                    rec[f"rel_delta_{metric}"] = (row[metric] - center_row[metric]) / denom
        out.append(rec)
    return sorted(
        out,
        key=lambda r: abs(r.get("delta_measure_densite_fin_mean_mean", 0.0)) + abs(r.get("delta_bounded_tail_share", 0.0)),
        reverse=True,
    )


def plot(agg: list[dict[str, Any]], effects: list[dict[str, Any]], path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 9))
    for ax, center in zip(axes[:, 0], CENTERS):
        rows = [r for r in effects if r["center"] == center]
        rows = sorted(rows, key=lambda r: abs(r.get("delta_measure_densite_fin_mean_mean", 0.0)), reverse=True)[:18]
        labels = [f"{r['parameter']}\n{r['direction']}" for r in rows]
        vals = [r.get("delta_measure_densite_fin_mean_mean", 0.0) for r in rows]
        colors = ["#376795" if v >= 0 else "#e15759" for v in vals]
        ax.bar(range(len(vals)), vals, color=colors)
        ax.set_xticks(range(len(vals)), labels, rotation=75, ha="right", fontsize=7)
        ax.set_ylabel("Delta densite financiere")
        ax.set_title(center)
        ax.grid(axis="y", alpha=0.25)

    for ax, center in zip(axes[:, 1], CENTERS):
        rows = [r for r in effects if r["center"] == center]
        rows = sorted(rows, key=lambda r: abs(r.get("delta_measure_n_alive_mean_mean", 0.0)), reverse=True)[:18]
        labels = [f"{r['parameter']}\n{r['direction']}" for r in rows]
        vals = [r.get("delta_measure_n_alive_mean_mean", 0.0) for r in rows]
        colors = ["#59a14f" if v >= 0 else "#f28e2b" for v in vals]
        ax.bar(range(len(vals)), vals, color=colors)
        ax.set_xticks(range(len(vals)), labels, rotation=75, ha="right", fontsize=7)
        ax.set_ylabel("Delta n_alive")
        ax.set_title(center)
        ax.grid(axis="y", alpha=0.25)

    fig.suptitle("OAT screening Codex: effets univariés autour des deux centres", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42])
    parser.add_argument("--workers", type=int, default=max(1, min(6, os.cpu_count() or 6)))
    parser.add_argument("--parameters", nargs="+", default=list(OAT_VALUES))
    return parser.parse_args()


def format_token(value: Any) -> str:
    if value is None:
        return "center"
    if isinstance(value, float):
        return f"{value:g}".replace("-", "m").replace(".", "p")
    return str(value).replace("-", "m").replace(".", "p")


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(float(value))


if __name__ == "__main__":
    args = parse_args()
    result_path = RESULTS_DIR / f"codex_oat_screen_steps{args.steps}_seeds{'-'.join(map(str, args.seeds))}.json"
    agg_path = RESULTS_DIR / f"codex_oat_screen_steps{args.steps}_seeds{'-'.join(map(str, args.seeds))}_aggregate.json"
    effects_path = RESULTS_DIR / f"codex_oat_screen_steps{args.steps}_seeds{'-'.join(map(str, args.seeds))}_effects.json"
    fig_path = FIGURES_DIR / f"codex_oat_screen_steps{args.steps}_seeds{'-'.join(map(str, args.seeds))}.pdf"

    rows = load(result_path)
    done = {r["case_key"] for r in rows}
    cases = [case for case in build_cases(args.steps, args.seeds, args.parameters) if case["case_key"] not in done]

    print(f"{len(done)} cas deja presents, {len(cases)} cas a lancer.")
    with ProcessPoolExecutor(max_workers=args.workers) as exe:
        futures = {exe.submit(_worker, case): case for case in cases}
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            save(result_path, rows)
            print(
                f"{row['center']:14s} {row['parameter']:30s} {str(row.get('value')):>8s} "
                f"seed={row['seed']:>4d} bounded={row['bounded_tail']} "
                f"dens={row['measure_densite_fin_mean']:.3f} "
                f"loans={row['measure_loan_density_mean']:.2f} "
                f"alive={row['measure_n_alive_mean']:.0f}"
            )

    agg = aggregate(rows)
    effects = sensitivity_table(agg)
    agg_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    effects_path.write_text(json.dumps(effects, indent=2, ensure_ascii=False), encoding="utf-8")
    plot(agg, effects, fig_path)
    print(f"Resultats : {result_path}")
    print(f"Agregats  : {agg_path}")
    print(f"Effets    : {effects_path}")
    print(f"Figure    : {fig_path}")
