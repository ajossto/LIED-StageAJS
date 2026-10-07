"""Contrôle d'échelle apparié A_norm (volet 5 du protocole).

Décompose, pour chaque γ d'ablation, l'effet total de γ (à A=1) en :
- effet total     : Δτ̂ = τ̂(γ, A=1) − τ̂(1/2, A=1) ;
- effet résiduel  : Δτ̂ = τ̂(γ, A_norm(γ)) − τ̂(1/2, A=1),
  à point fixe autarcique égalisé (K_ref = 361 J) ;
- part d'échelle  : total − résiduel.

Contrastes appariés par graine (mêmes graines {1,2,3} d'exploration ; le
volet confirmatoire éventuel utilise {11..15}). Même décomposition pour
les observables d'échelle (K/tête, taux médian, N/λ) afin de vérifier que
l'ablation égalise bien ce qu'elle prétend égaliser.

Sortie : results/tables/ablation_A.csv + résumé imprimé.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_lab

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "results" / "metrics"
TABLES = ROOT / "results" / "tables"


def load_cell(plan: str, cell: str) -> dict[int, dict]:
    if not lib_lab.manifest_path(plan).exists():
        return {}
    for entry in lib_lab.load_manifest(plan)["cells"]:
        if entry["cell"] == cell:
            out = {}
            for seed, run_dir in lib_lab.run_dirs(entry):
                path = METRICS / f"{run_dir.name}.json"
                if path.exists():
                    out[seed] = json.loads(path.read_text())
            return out
    return {}


def value(metrics: dict, kind: str) -> float | None:
    window = metrics["windows"].get("burn0.25", {})
    if kind == "tau_hat":
        return window.get("avalanches", {}).get("tau_hat")
    if kind == "s_c":
        cut = window.get("avalanches", {}).get("powerlaw_cutoff") or {}
        return cut.get("cutoff")
    if kind == "branching":
        return window.get("avalanches", {}).get("branching_ratio")
    if kind == "K_per_capita":
        return window.get("series", {}).get("intensive", {}).get("K_per_capita")
    if kind == "N_over_lambda":
        return metrics.get("N_over_lambda")
    if kind == "rate_median":
        snap = metrics.get("final_snapshot", {})
        return (snap.get("network", {}) or {}).get("rate_median")
    raise ValueError(kind)


def paired(cell_a: dict[int, dict], cell_b: dict[int, dict], kind: str):
    seeds = sorted(set(cell_a) & set(cell_b))
    diffs = [value(cell_a[s], kind) - value(cell_b[s], kind)
             for s in seeds
             if value(cell_a[s], kind) is not None
             and value(cell_b[s], kind) is not None]
    if not diffs:
        return None
    arr = np.asarray(diffs, dtype=float)
    return {"mean": float(arr.mean()),
            "sd": float(arr.std(ddof=1)) if len(arr) > 1 else None,
            "n": len(arr)}


def main() -> None:
    center = load_cell("pilotes", "g050") or load_cell("taille_finie", "g050_lam30")
    if not center:
        raise SystemExit("cellule centre g050 introuvable (volet 1 requis)")

    rows = []
    kinds = ("tau_hat", "s_c", "branching", "K_per_capita", "N_over_lambda",
             "rate_median")
    print(f"{'γ':>8}{'grandeur':>16}{'effet total':>14}{'résiduel':>12}"
          f"{'part échelle':>14}")
    for name in ("g033", "g060", "g067"):
        total_cell = load_cell("pilotes", name) or load_cell(
            "taille_finie", f"{name}_lam30")
        residual_cell = load_cell("ablation_A", f"{name}_Anorm")
        if not total_cell or not residual_cell:
            print(f"{name}: cellules manquantes — volet 5 incomplet")
            continue
        gamma = next(iter(total_cell.values()))["parameters"]["gamma"]
        for kind in kinds:
            total = paired(total_cell, center, kind)
            residual = paired(residual_cell, center, kind)
            if not total or not residual:
                continue
            scale_part = total["mean"] - residual["mean"]
            rows.append({"cell": name, "gamma": gamma, "quantity": kind,
                         "total_mean": total["mean"], "total_sd": total["sd"],
                         "residual_mean": residual["mean"],
                         "residual_sd": residual["sd"],
                         "scale_part": scale_part,
                         "n_seeds": min(total["n"], residual["n"]),
                         "same_sign": int(np.sign(total["mean"])
                                          == np.sign(residual["mean"]))})
            print(f"{gamma:>8.3f}{kind:>16}{total['mean']:>+14.4f}"
                  f"{residual['mean']:>+12.4f}{scale_part:>+14.4f}")

    if rows:
        TABLES.mkdir(parents=True, exist_ok=True)
        with (TABLES / "ablation_A.csv").open("w", newline="",
                                              encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\ntable écrite : {TABLES / 'ablation_A.csv'}")


if __name__ == "__main__":
    main()
