"""Tables τ(γ,λ) et scalings de taille finie (volets 1-3 du protocole).

Lit results/metrics/<run_id>.json des plans pilotes, taille_finie et
horizon_double, et produit :
- results/tables/avalanches_runs.csv — une ligne par run × fenêtre :
  métrique primaire tau_hat (avec source et drapeau hors-portée), fits
  pur/tronqué/scan, b, susceptibilité, singletons, extrêmes ;
- results/tables/avalanches_cells.csv — agrégation par cellule (moyenne ±
  écart-type inter-graines, fits par graine, jamais de pooling) sur la
  fenêtre par défaut ;
- results/tables/observables_cells.csv — démographie, crédit, réseau,
  marché η par cellule ;
- results/tables/scaling_lambda.csv — pentes log-log de ŝ_c, s_max, χ et
  ⟨s²⟩/⟨s⟩ en λ, par γ (3 points, exploratoire) ;
- un résumé imprimé τ(γ) par λ et fenêtre.

Toutes les valeurs de ce script sont EXPLORATOIRES (graines 1-3) ; la
confirmation relève d'analyze_confirm.py.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_lab

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "results" / "metrics"
TABLES = ROOT / "results" / "tables"

PLANS = ("pilotes", "taille_finie", "horizon_double", "ablation_A",
         "hypothese_K0")
WINDOWS = ("burn0.125", "burn0.25", "burn0.5")


def load_runs() -> list[dict]:
    rows = []
    seen = set()
    for plan in PLANS:
        manifest = lib_lab.load_manifest(plan)
        for entry in manifest["cells"]:
            for seed, run_dir in lib_lab.run_dirs(entry):
                if run_dir.name in seen:
                    continue
                seen.add(run_dir.name)
                path = METRICS / f"{run_dir.name}.json"
                if not path.exists():
                    continue
                rows.append({"plan": plan, "cell": entry["cell"], "seed": seed,
                             "run_id": run_dir.name,
                             "metrics": json.loads(path.read_text())})
    return rows


def run_window_row(run: dict, window_name: str) -> dict | None:
    metrics = run["metrics"]
    params = metrics["parameters"]
    window = metrics["windows"].get(window_name, {})
    avalanches = window.get("avalanches")
    if not avalanches:
        return None
    powerlaw = avalanches.get("powerlaw") or {}
    cutoff = avalanches.get("powerlaw_cutoff") or {}
    scan = avalanches.get("tail_scan") or {}
    lrt = avalanches.get("lrt_cutoff_vs_pure") or {}
    vuong = avalanches.get("vuong_pl_vs_ln") or {}
    boot = (metrics.get("bootstrap") or {}) if window_name == "burn0.25" else {}
    boot_alpha = boot.get("alpha_cutoff") or {}
    return {
        "plan": run["plan"], "cell": run["cell"], "seed": run["seed"],
        "run_id": run["run_id"],
        "gamma": params["gamma"], "A": params["A"], "lam": params["lam"],
        "K0": params["K0"], "delta": params["delta"],
        "T": params["T"], "window": window_name,
        "status": metrics["model_status"],
        "n_tail": avalanches.get("n_tail"),
        "identifiable": int(bool(avalanches.get("identifiable"))),
        "tau_hat": avalanches.get("tau_hat"),
        "tau_hat_source": avalanches.get("tau_hat_source"),
        "s_c_out_of_range": avalanches.get("s_c_out_of_range"),
        "alpha_trunc": cutoff.get("alpha"),
        "s_c": cutoff.get("cutoff"),
        "alpha_pure": powerlaw.get("alpha"),
        "alpha_pure_se": powerlaw.get("se"),
        "scan_s_min": scan.get("s_min"),
        "scan_alpha": scan.get("alpha"),
        "lrt_p": lrt.get("p_value"),
        "vuong_z": vuong.get("z"),
        "branching": avalanches.get("branching_ratio"),
        "susceptibility": avalanches.get("susceptibility"),
        "singleton_rate": avalanches.get("singleton_rate"),
        "size_max": avalanches.get("size_max"),
        "size_q99": avalanches.get("size_q99"),
        "depth_max": avalanches.get("depth_max"),
        "rate_per_step": avalanches.get("rate_per_step"),
        "volume_mean_j": avalanches.get("volume_mean_j"),
        "boot_tau_sd": boot_alpha.get("sd"),
        "boot_tau_q025": boot_alpha.get("q025"),
        "boot_tau_q975": boot_alpha.get("q975"),
    }


def observables_row(run: dict) -> dict:
    metrics = run["metrics"]
    params = metrics["parameters"]
    window = metrics["windows"].get("burn0.25", {})
    series = window.get("series", {})
    deaths = window.get("deaths", {})
    snapshot = metrics.get("final_snapshot", {})
    network = snapshot.get("network", {}) if snapshot.get("available") else {}
    intensive = series.get("intensive", {})
    ratios = series.get("ratios", {})
    market = series.get("market", {})
    causes = deaths.get("cause_shares", {})
    return {
        "plan": run["plan"], "cell": run["cell"], "seed": run["seed"],
        "run_id": run["run_id"],
        "gamma": params["gamma"], "A": params["A"], "lam": params["lam"],
        "T": params["T"],
        "N_over_lambda": metrics.get("N_over_lambda"),
        "K_per_capita": intensive.get("K_per_capita"),
        "loans_per_capita": intensive.get("loans_per_capita"),
        "deaths_rate": intensive.get("deaths_rate"),
        "age_mean": deaths.get("age_mean"),
        "cause_liquidity": causes.get("liquidity"),
        "cause_insolvency": causes.get("insolvency"),
        "cause_cascade": causes.get("cascade"),
        "debt_to_K": snapshot.get("debt_to_K"),
        "rate_median": network.get("rate_median"),
        "rate_q90": network.get("rate_q90"),
        "principal_gini": network.get("principal_gini"),
        "interest_to_prod": ratios.get("interest_to_prod"),
        "new_credit_to_K": ratios.get("new_credit_to_K"),
        "tx_success_rate": market.get("tx_success_rate"),
        "merge_share": market.get("merge_share"),
        "nw_negative_frac": snapshot.get("nw_negative_frac"),
    }


def aggregate_cells(rows: list[dict], keys: list[str]) -> list[dict]:
    """Moyenne ± écart-type inter-graines par cellule (fenêtre par défaut)."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        cells[(row["plan"], row["cell"])].append(row)
    out = []
    for (plan, cell), members in sorted(cells.items()):
        entry: dict = {"plan": plan, "cell": cell,
                       "gamma": members[0]["gamma"], "A": members[0]["A"],
                       "lam": members[0]["lam"], "T": members[0]["T"],
                       "K0": members[0].get("K0"),
                       "delta": members[0].get("delta"),
                       "n_seeds": len(members)}
        for key in keys:
            values = [m[key] for m in members
                      if isinstance(m.get(key), (int, float))]
            if values:
                entry[f"{key}_mean"] = float(np.mean(values))
                entry[f"{key}_sd"] = (float(np.std(values, ddof=1))
                                      if len(values) > 1 else None)
            else:
                entry[f"{key}_mean"] = None
                entry[f"{key}_sd"] = None
        out.append(entry)
    return out


def scaling_rows(cell_rows: list[dict]) -> list[dict]:
    """Pentes log-log en λ par γ (3 points — exploratoire)."""
    by_gamma: dict[float, list[dict]] = defaultdict(list)
    for row in cell_rows:
        if row["T"] in (4000, 8000) and row["A"] == 1.0:
            by_gamma[row["gamma"]].append(row)
    out = []
    for gamma, rows in sorted(by_gamma.items()):
        lams = sorted({row["lam"] for row in rows})
        if len(lams) < 3:
            continue
        entry = {"gamma": gamma, "lams": ",".join(str(int(l)) for l in lams)}
        for key in ("s_c", "size_max", "susceptibility"):
            points = []
            for lam in lams:
                values = [row[f"{key}_mean"] for row in rows
                          if row["lam"] == lam and row.get(f"{key}_mean")
                          # coupures dégénérées exclues du scaling de s_c
                          and not (key == "s_c" and row.get("s_c_out_n"))]
                if values:
                    points.append((lam, float(np.mean(values))))
            minimum = 2 if key == "s_c" else 3
            if len(points) >= minimum and all(v > 0 for _, v in points):
                x = np.log([p[0] for p in points])
                y = np.log([p[1] for p in points])
                slope = float(np.polyfit(x, y, 1)[0])
                entry[f"{key}_exponent"] = round(slope, 3)
                entry[f"{key}_n_points"] = len(points)
            else:
                entry[f"{key}_exponent"] = None
        out.append(entry)
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    TABLES.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    runs = load_runs()
    if not runs:
        raise SystemExit("aucun run — lancer les campagnes puis extract_metrics")

    window_rows = []
    for run in runs:
        for window_name in WINDOWS:
            row = run_window_row(run, window_name)
            if row:
                window_rows.append(row)
    write_csv(TABLES / "avalanches_runs.csv", window_rows)

    default_rows = [row for row in window_rows if row["window"] == "burn0.25"]
    cell_rows = aggregate_cells(default_rows, [
        "tau_hat", "alpha_trunc", "s_c", "alpha_pure", "scan_alpha",
        "scan_s_min", "branching", "susceptibility", "singleton_rate",
        "size_max", "depth_max", "rate_per_step", "n_tail",
    ])
    # Nombre de graines à coupure hors portée : une cellule où la coupure
    # dégénère est exclue des scalings de s_c (protocole §identifiabilité).
    for cell in cell_rows:
        members = [r for r in default_rows
                   if (r["plan"], r["cell"]) == (cell["plan"], cell["cell"])]
        cell["s_c_out_n"] = sum(1 for r in members if r.get("s_c_out_of_range"))
    write_csv(TABLES / "avalanches_cells.csv", cell_rows)

    observable_rows = [observables_row(run) for run in runs]
    write_csv(TABLES / "observables_runs.csv", observable_rows)
    observable_cells = aggregate_cells(observable_rows, [
        "N_over_lambda", "K_per_capita", "loans_per_capita", "deaths_rate",
        "age_mean", "cause_liquidity", "cause_insolvency", "cause_cascade",
        "debt_to_K", "rate_median", "interest_to_prod", "tx_success_rate",
        "merge_share", "nw_negative_frac",
    ])
    write_csv(TABLES / "observables_cells.csv", observable_cells)

    write_csv(TABLES / "scaling_lambda.csv", scaling_rows(cell_rows))

    print(f"{len(runs)} runs, {len(window_rows)} lignes run×fenêtre\n")
    print(f"{'plan':<15}{'cellule':<16}{'γ':>6}{'λ':>5}{'τ̂':>8}{'±sd':>7}"
          f"{'s_c':>8}{'hors':>5}{'b':>7}{'n≥2':>7}")
    for row in cell_rows:
        tau = row.get("tau_hat_mean")
        sd = row.get("tau_hat_sd")
        sc = row.get("s_c_mean")
        out_share = ""
        members = [r for r in default_rows
                   if (r["plan"], r["cell"]) == (row["plan"], row["cell"])]
        n_out = sum(1 for r in members if r.get("s_c_out_of_range"))
        if n_out:
            out_share = f"{n_out}/{len(members)}"
        print(f"{row['plan']:<15}{row['cell']:<16}{row['gamma']:>6.3f}"
              f"{row['lam']:>5.0f}"
              f"{tau if tau is not None else float('nan'):>8.3f}"
              f"{sd if sd is not None else float('nan'):>7.3f}"
              f"{sc if sc is not None else float('nan'):>8.1f}"
              f"{out_share:>5}"
              f"{row.get('branching_mean') or float('nan'):>7.3f}"
              f"{row.get('n_tail_mean') or 0:>7.0f}")


if __name__ == "__main__":
    main()
