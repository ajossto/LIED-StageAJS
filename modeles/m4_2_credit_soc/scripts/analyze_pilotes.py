"""Diagnostics go/no-go des pilotes M4.2 (volet 1 du protocole).

Lit results/metrics/<run_id>.json (produits par extract_metrics.py) pour le
plan pilotes et produit :
- results/tables/pilotes_diagnostics.csv — une ligne par run : statut,
  stationnarité (dérive relative, demi-fenêtres pop et K), N/λ, échelle de
  capital (K/tête vs K*_aut), comptages d'avalanches s≥2 par fenêtre,
  activité du marché, durée ;
- results/tables/pilotes_avalanches.csv — fits exploratoires par run
  (α tronqué, s_c, α pur, scan s_min, b, susceptibilité, taux de
  singletons) ;
- un verdict imprimé par cellule contre les critères pré-enregistrés
  (stationnarité §7 du protocole, identifiabilité ≥100 tailles ≥2).

Les fits de ce script sont EXPLORATOIRES (graines 1-3) : aucun verdict
scientifique n'est rendu ici, seulement la décision de grille du
§ « stratégie adaptative » du protocole.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_lab

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "results" / "metrics"
TABLES = ROOT / "results" / "tables"

DRIFT_MAX = 0.04          # |dérive relative| max par fenêtre (protocole §7)
HALF_POP_MAX = 0.05       # |Δpop/pop| max entre demi-fenêtres
HALF_POP_SD_MAX = 2.0     # |Δpop| max en écarts-types poolés
HALF_K_MAX = 0.10         # |ΔK/K| max entre demi-fenêtres
N_MIN_AVALANCHES = 100    # identifiabilité (tailles >= 2)


def load_runs(plan: str) -> list[dict]:
    manifest = lib_lab.load_manifest(plan)
    rows = []
    for entry in manifest["cells"]:
        for seed, run_dir in lib_lab.run_dirs(entry):
            metrics = json.loads((METRICS / f"{run_dir.name}.json").read_text())
            rows.append({"cell": entry["cell"], "seed": seed,
                         "run_id": run_dir.name, "metrics": metrics})
    return rows


def autarkic_K(gamma: float, A: float, delta: float) -> float:
    return ((1.0 - delta) * A / delta) ** (1.0 / (1.0 - gamma))


def diagnostics_row(run: dict) -> dict:
    metrics = run["metrics"]
    params = metrics["parameters"]
    window = metrics["windows"].get("burn0.25", {})
    series = window.get("series", {})
    avalanches = window.get("avalanches", {})
    stationarity = metrics.get("stationarity", {})
    pop = series.get("pop", {})
    intensive = series.get("intensive", {})
    market = series.get("market", {})
    ratios = series.get("ratios", {})

    n_tail = avalanches.get("n_tail", 0)
    drift = pop.get("rel_drift_window")
    half_pop = stationarity.get("rel_diff")
    half_pop_sd = stationarity.get("diff_in_sd")
    half_K = stationarity.get("K_rel_diff")

    stationary = all((
        drift is not None and abs(drift) <= DRIFT_MAX,
        half_pop is not None and abs(half_pop) <= HALF_POP_MAX,
        half_pop_sd is not None and abs(half_pop_sd) <= HALF_POP_SD_MAX,
        half_K is not None and abs(half_K) <= HALF_K_MAX,
    ))
    return {
        "cell": run["cell"],
        "seed": run["seed"],
        "run_id": run["run_id"],
        "gamma": params["gamma"],
        "A": params["A"],
        "lam": params["lam"],
        "T": params["T"],
        "status": metrics["model_status"],
        "stationary": int(stationary),
        "pop_drift_rel": drift,
        "half_pop_rel": half_pop,
        "half_pop_sd": half_pop_sd,
        "half_K_rel": half_K,
        "N_over_lambda": metrics.get("N_over_lambda"),
        "K_per_capita": intensive.get("K_per_capita"),
        "K_autarkic": autarkic_K(params["gamma"], params["A"], params["delta"]),
        "n_avalanches_ge2": n_tail,
        "identifiable": int(n_tail >= N_MIN_AVALANCHES),
        "avalanches_per_step": avalanches.get("rate_per_step"),
        "tx_success_rate": market.get("tx_success_rate"),
        "merge_share": market.get("merge_share"),
        "new_credit_to_K": ratios.get("new_credit_to_K"),
        "interest_to_prod": ratios.get("interest_to_prod"),
        "balance_residual": metrics["integrity"]["balance_max_rel_residual"],
        "book_errors": len(metrics["integrity"]["book_errors"]),
    }


def avalanche_row(run: dict, window_name: str) -> dict | None:
    metrics = run["metrics"]
    window = metrics["windows"].get(window_name, {})
    avalanches = window.get("avalanches")
    if not avalanches:
        return None
    powerlaw = avalanches.get("powerlaw") or {}
    cutoff = avalanches.get("powerlaw_cutoff") or {}
    scan = avalanches.get("tail_scan") or {}
    lrt = avalanches.get("lrt_cutoff_vs_pure") or {}
    vuong = avalanches.get("vuong_pl_vs_ln") or {}
    return {
        "cell": run["cell"],
        "seed": run["seed"],
        "run_id": run["run_id"],
        "gamma": metrics["parameters"]["gamma"],
        "lam": metrics["parameters"]["lam"],
        "window": window_name,
        "n_tail": avalanches.get("n_tail"),
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
        "depth_max": avalanches.get("depth_max"),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    runs = load_runs("pilotes")
    if not runs:
        raise SystemExit("aucun run pilote — lancer run_campaign --plan pilotes")

    diagnostics = [diagnostics_row(run) for run in runs]
    write_csv(TABLES / "pilotes_diagnostics.csv", diagnostics)

    avalanche_rows = []
    for run in runs:
        for window_name in ("burn0.125", "burn0.25", "burn0.5"):
            row = avalanche_row(run, window_name)
            if row:
                avalanche_rows.append(row)
    write_csv(TABLES / "pilotes_avalanches.csv", avalanche_rows)

    print(f"{len(runs)} runs pilotes analysés\n")
    cells: dict[str, list[dict]] = {}
    for row in diagnostics:
        cells.setdefault(row["cell"], []).append(row)
    print(f"{'cellule':<14}{'γ':>6}{'statuts':>10}{'stat.':>7}{'N/λ':>8}"
          f"{'K/tête':>9}{'K*aut':>9}{'aval≥2':>8}{'ident.':>7}")
    for name in sorted(cells):
        rows = cells[name]
        statuses = ",".join(sorted({row["status"] for row in rows}))
        stationary = sum(row["stationary"] for row in rows)
        n_over = sum(row["N_over_lambda"] or 0 for row in rows) / len(rows)
        k_pc = sum(row["K_per_capita"] or 0 for row in rows) / len(rows)
        n_av = sum(row["n_avalanches_ge2"] for row in rows) / len(rows)
        identifiable = sum(row["identifiable"] for row in rows)
        print(f"{name:<14}{rows[0]['gamma']:>6.3f}{statuses:>10}"
              f"{stationary}/{len(rows):>4}{n_over:>8.2f}{k_pc:>9.1f}"
              f"{rows[0]['K_autarkic']:>9.0f}{n_av:>8.0f}"
              f"{identifiable}/{len(rows):>4}")
    print("\nVerdict go/no-go par cellule (critères pré-enregistrés) :")
    for name in sorted(cells):
        rows = cells[name]
        ok_status = all(row["status"] == "ok" for row in rows)
        ok_stationary = all(row["stationary"] for row in rows)
        ok_ident = all(row["identifiable"] for row in rows)
        if ok_status and ok_stationary and ok_ident:
            verdict = "GO"
        elif not ok_status:
            verdict = "NO-GO (statut) — documenter comme résultat négatif"
        elif not ok_stationary:
            verdict = "T=8000 requis (clause adaptative : stationnarité)"
        else:
            verdict = "T=8000 requis (clause adaptative : identifiabilité)"
        print(f"  {name}: {verdict}")


if __name__ == "__main__":
    main()
