"""Chaîne causale γ → taux → exposition/réseau → propagation (volet 6).

Quantifie chaque maillon sur les runs « mecanisme » (instantanés denses,
graine 1) :
1. γ → production et rendements : production/K, taux contractuel médian du
   carnet (pondéré temps), à comparer à la prédiction γ·δ/(1-δ) ;
2. → service des intérêts : intérêts payés / production, part des morts par
   liquidité, charge relative des emprunteuses ;
3. → durée de vie, exposition, réseau : âge au décès, levier D/K, contrats
   par tête, concentration des principaux, taille des expositions
   unitaires (pertes par arête au décès) ;
4. → propagation : b, taux d'avalanches, taille moyenne des pertes
   unitaires vs capital des prêteuses.

Sortie : results/tables/mecanisme.csv (une ligne par γ, maillons colonnes)
+ résumé imprimé. Volet descriptif (une graine) : aucune conclusion
confirmatoire ici.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_lab
import lib_metrics

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "results" / "metrics"
TABLES = ROOT / "results" / "tables"


def snapshot_series(run_dir: Path, burn: int) -> dict:
    """Moyennes temporelles (post burn-in) sur les instantanés réseau/entités."""
    rates_median, rates_q90, leverage, loans_pc, gini_q = [], [], [], [], []
    for path in sorted((run_dir / "snapshots").glob("network_t*.npz")):
        step = int(path.stem.split("t")[-1])
        if step < burn:
            continue
        with np.load(path) as network:
            q = np.asarray(network["q"], dtype=float)
            r = np.asarray(network["r"], dtype=float)
        if len(q):
            rates_median.append(float(np.median(r)))
            rates_q90.append(float(np.quantile(r, 0.9)))
            gini_q.append(lib_metrics._gini(q))
    for path in sorted((run_dir / "snapshots").glob("entities_t*.npz")):
        step = int(path.stem.split("t")[-1])
        if step < burn:
            continue
        with np.load(path) as snap:
            K = np.asarray(snap["K"], dtype=float)
            debts = np.asarray(snap["debts"], dtype=float)
            deg = np.asarray(snap["deg_in"], dtype=float) + np.asarray(
                snap["deg_out"], dtype=float)
        if K.sum() > 0:
            leverage.append(float(debts.sum() / K.sum()))
            loans_pc.append(float(deg.mean() / 2.0))
    mean = lambda xs: float(np.mean(xs)) if xs else None
    return {"rate_median": mean(rates_median), "rate_q90": mean(rates_q90),
            "leverage": mean(leverage), "loans_per_capita": mean(loans_pc),
            "principal_gini": mean(gini_q)}


def loss_edges_stats(run_dir: Path, burn: int) -> dict:
    """Pertes unitaires au décès : dette de la morte (deaths.csv) comme proxy
    de l'exposition détruite, et volume par avalanche / taille."""
    deaths = lib_metrics.read_deaths(run_dir)
    debts = np.asarray([float(row["debts"]) for row in deaths
                        if int(row["t"]) >= burn], dtype=float)
    positive = debts[debts > 0]
    avalanches = lib_metrics.read_avalanches(run_dir)
    mask = avalanches["t"] >= burn
    sizes = avalanches["size"][mask]
    volumes = avalanches["volume_j"][mask]
    with_loss = volumes > 0
    return {
        "debt_at_death_mean": float(positive.mean()) if len(positive) else None,
        "debt_at_death_q90": float(np.quantile(positive, 0.9)) if len(positive) else None,
        "frac_deaths_indebted": float((debts > 0).mean()) if len(debts) else None,
        "loss_per_member": float((volumes[with_loss] / sizes[with_loss]).mean())
        if with_loss.any() else None,
    }


def main() -> None:
    manifest_name = "mecanisme"
    if not lib_lab.manifest_path(manifest_name).exists():
        raise SystemExit("volet mecanisme non exécuté")
    rows = []
    for entry in lib_lab.load_manifest(manifest_name)["cells"]:
        for seed, run_dir in lib_lab.run_dirs(entry):
            metrics = json.loads((METRICS / f"{run_dir.name}.json").read_text())
            params = metrics["parameters"]
            burn = params["T"] // 4
            window = metrics["windows"]["burn0.25"]
            series = window["series"]
            avalanches = window.get("avalanches", {})
            deaths = window.get("deaths", {})
            prediction = params["gamma"] * params["delta"] / (1 - params["delta"])
            row = {
                "cell": entry["cell"], "seed": seed, "run_id": run_dir.name,
                "gamma": params["gamma"],
                # Maillon 1 : production et rendements.
                "prod_over_K": series["prod_tot_mean"] / series["K_tot_mean"],
                "rate_predicted": prediction,
                # Maillon 2 : service.
                "interest_to_prod": series["ratios"]["interest_to_prod"],
                "cause_liquidity": (deaths.get("cause_shares") or {}).get("liquidity"),
                "defaults_per_step": series["defaults_mean"],
                # Maillon 3 : démographie/exposition/réseau.
                "age_mean": deaths.get("age_mean"),
                "N_over_lambda": metrics.get("N_over_lambda"),
                # Maillon 4 : propagation.
                "branching": avalanches.get("branching_ratio"),
                "tau_hat": avalanches.get("tau_hat"),
                "s_c": (avalanches.get("powerlaw_cutoff") or {}).get("cutoff"),
                "rate_per_step": avalanches.get("rate_per_step"),
                "susceptibility": avalanches.get("susceptibility"),
            }
            row.update(snapshot_series(run_dir, burn))
            row.update(loss_edges_stats(run_dir, burn))
            rows.append(row)

    TABLES.mkdir(parents=True, exist_ok=True)
    with (TABLES / "mecanisme.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    rows.sort(key=lambda row: row["gamma"])
    print(f"{'γ':>6}{'r médian':>10}{'γδ/(1-δ)':>10}{'int/prod':>10}"
          f"{'liq%':>7}{'âge':>7}{'D/K':>7}{'prêts/t':>9}{'b':>7}{'τ̂':>7}")
    for row in rows:
        fmt = lambda v, p=3: f"{v:.{p}f}" if isinstance(v, float) else "—"
        print(f"{row['gamma']:>6.3f}{fmt(row['rate_median']):>10}"
              f"{row['rate_predicted']:>10.4f}{fmt(row['interest_to_prod']):>10}"
              f"{fmt((row['cause_liquidity'] or 0)*100, 1):>7}"
              f"{fmt(row['age_mean'], 1):>7}{fmt(row['leverage'], 2):>7}"
              f"{fmt(row['loans_per_capita'], 2):>9}{fmt(row['branching']):>7}"
              f"{fmt(row['tau_hat'], 3):>7}")
    print(f"\ntable écrite : {TABLES / 'mecanisme.csv'}")


if __name__ == "__main__":
    main()
