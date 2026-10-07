"""Dépouillement de la phase confirmatoire (lots Simulation Lab).

1. Extrait les métriques de chaque run confirmatoire (graines 11-15,
   T=4000) vers results/metrics_confirm/ et une table plate
   results/summary/confirm.csv.
2. Valide les effets exploratoires : contrastes appariés cellule-centre
   sur le panel confirmatoire, comparés aux contrastes exploratoires
   (même définition, graines 1-3, T=2000) — signe, ordre de grandeur,
   IC à 95 % (t de Student sur les 5 contrastes appariés).
3. Contrôles : statuts (pop_max ? extinction ?), intégrité comptable,
   robustesse au burn-in (T/8 vs T/4 vs T/2), demi-fenêtres.
4. Cellule lam2_ext : fréquence d'extinction initiale vs e^-lambda.

Sorties : results/summary/confirm.csv, confirm_contrasts.csv,
figures/confirm_validation.png ; impression d'un rapport texte.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_runs as L
from extract_metrics import flat_row

LAB_RUNS = Path("/home/anatole/jupyter/simulation_lab_data/runs")
MANIFEST = L.CAMPAIGN_ROOT / "manifests" / "confirm_lab.json"
METRICS_DIR = L.CAMPAIGN_ROOT / "results" / "metrics_confirm"
SUMMARY = L.CAMPAIGN_ROOT / "results" / "summary"

KEY_METRICS = [
    "N_over_lambda", "deaths_rate", "age_death_mean", "K_per_capita",
    "loans_per_capita", "debt_to_K", "gini_K", "branching_ratio",
    "alpha_pl", "susceptibility", "av_max_over_pop", "cutoff_sc",
]


def _extract(run_id: str) -> dict:
    import lib_metrics
    path = METRICS_DIR / f"{run_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    metrics = lib_metrics._to_jsonable(
        lib_metrics.compute_run_metrics(LAB_RUNS / run_id))
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=1, ensure_ascii=False))
    return metrics


def exploration_value(params: dict, metric: str) -> list[float]:
    """Valeurs exploratoires (graines 1-3, T=2000) pour la même cellule
    microscopique, depuis les métriques de campagne."""
    values = []
    for seed in (1, 2, 3):
        spec = L.cell(lam=params["lam"], delta=params["delta"],
                      sigma=params["sigma"], K0=params["K0"], k=params["k"],
                      seed=seed, T=2000)
        path = L.CAMPAIGN_ROOT / "results" / "metrics" / f"{L.run_id(spec)}.json"
        if not path.exists():
            continue
        row = flat_row(json.loads(path.read_text()))
        value = row.get(metric)
        if value is not None and np.isfinite(value):
            values.append(float(value))
    return values


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    cells = {entry["cell"]: entry for entry in manifest["cells"]}

    all_rows = []
    by_cell: dict[str, dict[int, dict]] = defaultdict(dict)
    run_ids = [(name, rid) for name, entry in cells.items()
               for rid in entry["run_ids"]]
    with ProcessPoolExecutor(max_workers=6) as pool:
        metrics_list = list(pool.map(_extract, [rid for _, rid in run_ids]))
    statuses = []
    for (name, rid), metrics in zip(run_ids, metrics_list):
        row = flat_row(metrics)
        row["cell"] = name
        row["lab_run_id"] = rid
        all_rows.append(row)
        by_cell[name][int(row["seed"])] = row
        statuses.append((name, rid, row["status"], row["balance_residual"],
                         row["n_book_errors"]))

    with (SUMMARY / "confirm.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0].keys()))
        writer.writeheader(); writer.writerows(all_rows)

    print("=== statuts et intégrité ===")
    bad = [s for s in statuses if s[2] != "ok" and not s[0].startswith("lam2")]
    ext = [s for s in statuses if s[0] == "lam2_ext" and s[2] == "extinction"]
    residuals = [s[3] for s in statuses if s[3] is not None]
    print(f"runs: {len(statuses)} ; non-ok hors lam2_ext: {len(bad)} ; "
          f"résidu comptable max: {max(residuals):.2e} ; "
          f"erreurs de carnet: {sum(s[4] for s in statuses)}")
    for s in bad:
        print("  ANOMALIE:", s)
    n_ext_runs = sum(1 for s in statuses if s[0] == "lam2_ext")
    if n_ext_runs:
        p_hat = len(ext) / n_ext_runs
        low, high = stats.beta.ppf([0.025, 0.975],
                                   len(ext) + 0.5, n_ext_runs - len(ext) + 0.5)
        print(f"lam2_ext : {len(ext)}/{n_ext_runs} extinctions "
              f"(p̂={p_hat:.2f}, IC95 Jeffreys [{low:.2f},{high:.2f}], "
              f"attendu e^-2=0.135)")
        for s in statuses:
            if s[0] == "lam2_ext":
                print("   ", s[1], s[2])

    # ---- contrastes appariés vs centre (panel confirmatoire) ----
    center = by_cell.get("centre_lam30", {})
    center_params = cells["centre_lam30"]["parameters"]
    contrast_rows = []
    print("\n=== validation des contrastes (cellule - centre) ===")
    print(f"{'cellule':20s} {'métrique':16s} {'Δ_confirm':>10s} {'IC95':>21s} "
          f"{'Δ_explo':>10s} {'verdict':10s}")
    for name, entry in cells.items():
        if name in ("centre_lam30", "lam2_ext"):
            continue
        params = entry["parameters"]
        for metric in KEY_METRICS:
            pairs = []
            for seed, row in by_cell[name].items():
                if seed in center:
                    a, b = row.get(metric), center[seed].get(metric)
                    if a is not None and b is not None and np.isfinite(a) and np.isfinite(b):
                        pairs.append(a - b)
            if len(pairs) < 3:
                continue
            pairs = np.asarray(pairs)
            mean = pairs.mean()
            half = stats.t.ppf(0.975, len(pairs) - 1) * pairs.std(ddof=1) / np.sqrt(len(pairs))
            explo_cell = exploration_value(params, metric)
            explo_center = exploration_value(center_params, metric)
            d_explo = (np.mean(explo_cell) - np.mean(explo_center)
                       if explo_cell and explo_center else np.nan)
            ci_excludes_zero = (mean - half) * (mean + half) > 0
            same_sign = np.isfinite(d_explo) and d_explo * mean > 0
            magnitude_ok = (np.isfinite(d_explo) and abs(d_explo) > 0
                            and 0.5 <= abs(mean) / abs(d_explo) <= 2.0)
            if not np.isfinite(d_explo) or abs(d_explo) < 1e-12:
                verdict = "sans-explo"
            elif ci_excludes_zero and same_sign and magnitude_ok:
                verdict = "CONFIRMÉ"
            elif ci_excludes_zero and same_sign:
                verdict = "signe-ok"
            elif not ci_excludes_zero and abs(d_explo) < 2 * half:
                verdict = "nul-cohérent"
            else:
                verdict = "NON-CONF"
            contrast_rows.append({
                "cell": name, "metric": metric,
                "delta_confirm": mean, "ci_half": half,
                "delta_explo": d_explo, "verdict": verdict,
                "n_pairs": len(pairs),
            })
            if metric in ("N_over_lambda", "gini_K", "branching_ratio",
                          "alpha_pl", "debt_to_K"):
                print(f"{name:20s} {metric:16s} {mean:+10.4f} "
                      f"[{mean-half:+8.4f},{mean+half:+8.4f}] "
                      f"{d_explo:+10.4f} {verdict:10s}")

    with (SUMMARY / "confirm_contrasts.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(contrast_rows[0].keys()))
        writer.writeheader(); writer.writerows(contrast_rows)

    verdicts = defaultdict(int)
    for row in contrast_rows:
        verdicts[row["verdict"]] += 1
    print("\nbilan verdicts :", dict(verdicts))

    # ---- robustesse fenêtre sur le panel confirmatoire ----
    print("\n=== robustesse burn-in (T/8 vs T/4 vs T/2) ===")
    worst = defaultdict(float)
    for (name, rid), metrics in zip(run_ids, metrics_list):
        w = metrics["windows"]
        try:
            p = w["burn0.25"]["series"]["pop"]["mean"]
            p8 = w["burn0.125"]["series"]["pop"]["mean"]
            p2 = w["burn0.5"]["series"]["pop"]["mean"]
            worst["pop"] = max(worst["pop"], abs(p8 - p) / p, abs(p2 - p) / p)
            a = w["burn0.25"]["avalanches"].get("powerlaw")
            a2 = w["burn0.5"]["avalanches"].get("powerlaw")
            if a and a2:
                worst["alpha"] = max(worst["alpha"], abs(a2["alpha"] - a["alpha"]))
            b1 = w["burn0.25"]["avalanches"].get("branching_ratio")
            b2 = w["burn0.5"]["avalanches"].get("branching_ratio")
            if b1 is not None and b2 is not None:
                worst["b"] = max(worst["b"], abs(b2 - b1))
        except (KeyError, TypeError):
            continue
    print(f"écart max pop (relatif): {worst['pop']:.4f} ; "
          f"écart max alpha: {worst['alpha']:.4f} ; écart max b: {worst['b']:.4f}")


if __name__ == "__main__":
    main()
