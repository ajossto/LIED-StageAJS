"""Agrège les analysis.json de la campagne d'exploration M4.2B en une table
plate (un run = une ligne), triable par cellule/branche.

Ne sélectionne rien, ne conclut rien : c'est un outil de lecture, l'analyse
et la sélection des cellules de confirmation restent §"Ordre d'exécution"
du protocole (report/protocole.md), après exploration complète.

Métriques des critères pré-enregistrés (report/protocole.md) calculées ICI,
pas dans campaign.py :
- critère 1 (stabilité de seuil) : |alpha_density(seuil KS) -
  alpha_density(seuil/2)| / alpha_density(seuil KS), PAR SNAPSHOT, agrégé en
  moyenne et en fraction de snapshots < 20 %. Ne pas confondre avec l'étalement
  temporel alpha_density_max/min sur les snapshots (colonne
  alpha_snapshot_spread_ratio, diagnostic différent : dérive dans le temps,
  pas stabilité au seuil).
- critère 2 (effectif de queue) : n_tail moyen par snapshot (table des
  intérêts, PAS n_tail des avalanches qui est un diagnostic séparé).
- critère 4 (Vuong) : fraction des snapshots où la loi de puissance est
  favorisée (z>0) face à l'exponentielle et à la lognormale séparément.
"""

import csv
import json
from pathlib import Path

CAMPAIGN_DIR = Path(__file__).resolve().parent.parent / "results" / "campaign"

PARAM_KEYS = [
    "gamma", "delta", "sigma", "K0", "lam", "rho", "eta_beta",
    "eta_n_ref", "target_rule",
]

# Runs dont elapsed_s a été mesuré AVANT le correctif de streaming de
# loan_events (JOURNAL.md §10) : valeurs jusqu'à ~49x plus lentes que la
# vitesse réelle post-correctif (swap/GC sur une liste de plusieurs millions
# d'éléments jamais vidée). Jamais recalculées depuis (reprise automatique
# sur status="ok"). Ne pas utiliser pour un tableau de coût de calcul.
PRE_FIX_STALE_ELAPSED = {
    ("baseline", 0), ("baseline", 1), ("baseline", 2),
    ("K0_1", 0), ("K0_1", 1), ("K0_1", 2),
    ("K0_5", 0), ("K0_5", 1), ("K0_5", 2),
    ("K0_100", 0), ("K0_100", 1), ("K0_100", 2),
    ("t10000_baseline", 0), ("t10000_baseline", 1),
}

FIELDS = [
    "label", "seed", "T", *PARAM_KEYS,
    "population_final", "pop_cv_window",
    "alpha_density_mean", "alpha_density_std",
    "alpha_density_min", "alpha_density_max", "alpha_snapshot_spread_ratio",
    "threshold_reldiff_mean", "threshold_reldiff_frac_under_20pct",
    "n_snapshots", "n_identifiable",
    "interest_n_tail_mean",
    "frac_snapshots_favor_powerlaw_vs_exp", "frac_snapshots_favor_powerlaw_vs_lognormal",
    "tau_hat", "tau_hat_source", "s_c_out_of_range", "branching_ratio",
    "avalanche_n_tail", "avalanche_size_max",
    "share_from_deg_out_mean", "share_from_mean_rq_mean",
    "share_from_covariance_mean",
    "gini_K_mean", "gini_K_std",
    "renewal_networth_half_life", "renewal_networth_floor",
    "renewal_income_half_life", "renewal_income_floor",
    "elapsed_s", "elapsed_pre_fix_stale",
]


def _threshold_stability(per_snapshot: list[dict]) -> tuple[float | None, float | None]:
    diffs = []
    for row in per_snapshot:
        a = row.get("alpha_density")
        b = row.get("alpha_density_half_threshold")
        if a is None or b is None or a == 0:
            continue
        diffs.append(abs(a - b) / abs(a))
    if not diffs:
        return None, None
    mean_diff = sum(diffs) / len(diffs)
    frac_under_20 = sum(1 for d in diffs if d < 0.20) / len(diffs)
    return mean_diff, frac_under_20


def _vuong_fraction_favor_powerlaw(per_snapshot: list[dict], key: str) -> float | None:
    zs = [row.get(key) for row in per_snapshot if row.get(key) is not None]
    if not zs:
        return None
    return sum(1 for z in zs if z > 0) / len(zs)


def load_run(path: Path) -> dict:
    with open(path) as f:
        d = json.load(f)
    if d.get("status") != "ok":
        return None
    label, seed = d["label"], d["seed"]
    row = {"label": label, "seed": seed, "T": d["T"]}
    for k in PARAM_KEYS:
        row[k] = d["params"].get(k)
    row["population_final"] = d.get("population_final")
    row["pop_cv_window"] = d.get("pop_cv_window")
    isum = d.get("interest_summary", {})
    row["alpha_density_mean"] = isum.get("alpha_density_mean")
    row["alpha_density_std"] = isum.get("alpha_density_std")
    amin, amax = isum.get("alpha_density_min"), isum.get("alpha_density_max")
    row["alpha_density_min"] = amin
    row["alpha_density_max"] = amax
    row["alpha_snapshot_spread_ratio"] = (amax / amin) if amin else None
    row["n_snapshots"] = isum.get("n_snapshots")
    row["n_identifiable"] = isum.get("n_identifiable")

    per_snapshot = d.get("interest_per_snapshot", [])
    mean_diff, frac_under_20 = _threshold_stability(per_snapshot)
    row["threshold_reldiff_mean"] = mean_diff
    row["threshold_reldiff_frac_under_20pct"] = frac_under_20
    n_tails = [r.get("n_tail") for r in per_snapshot if r.get("n_tail") is not None]
    row["interest_n_tail_mean"] = (sum(n_tails) / len(n_tails)) if n_tails else None
    row["frac_snapshots_favor_powerlaw_vs_exp"] = _vuong_fraction_favor_powerlaw(
        per_snapshot, "tail_vs_exponential_z"
    )
    row["frac_snapshots_favor_powerlaw_vs_lognormal"] = _vuong_fraction_favor_powerlaw(
        per_snapshot, "tail_vs_lognormal_z"
    )

    av = d.get("avalanches", {})
    row["tau_hat"] = av.get("tau_hat")
    row["tau_hat_source"] = av.get("tau_hat_source")
    row["s_c_out_of_range"] = av.get("s_c_out_of_range")
    row["branching_ratio"] = av.get("branching_ratio")
    row["avalanche_n_tail"] = av.get("n_tail")
    row["avalanche_size_max"] = av.get("size_max")
    dec = d.get("decomposition", {})
    row["share_from_deg_out_mean"] = dec.get("share_from_deg_out_mean")
    row["share_from_mean_rq_mean"] = dec.get("share_from_mean_rq_mean")
    row["share_from_covariance_mean"] = dec.get("share_from_covariance_mean")
    gini = d.get("gini_K_window", {})
    row["gini_K_mean"] = gini.get("mean")
    row["gini_K_std"] = gini.get("std")
    ren = d.get("renewal", {})
    row["renewal_networth_half_life"] = ren.get("net_worth", {}).get("half_life_steps")
    row["renewal_networth_floor"] = ren.get("net_worth", {}).get("floor_last5_mean")
    row["renewal_income_half_life"] = ren.get("income", {}).get("half_life_steps")
    row["renewal_income_floor"] = ren.get("income", {}).get("floor_last5_mean")
    row["elapsed_s"] = d.get("elapsed_s")
    row["elapsed_pre_fix_stale"] = (label, seed) in PRE_FIX_STALE_ELAPSED
    return row


def main():
    rows = []
    for p in sorted(CAMPAIGN_DIR.glob("*/seed*/analysis.json")):
        row = load_run(p)
        if row is not None:
            rows.append(row)
    out_path = CAMPAIGN_DIR / "exploration_summary.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"{len(rows)} runs agrégés -> {out_path}")
    return rows


if __name__ == "__main__":
    main()
