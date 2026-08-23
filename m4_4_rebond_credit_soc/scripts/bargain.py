"""Le taux comme variable de partage — analyse du balayage en p.

Le taux n'est plus une formule mais un partage `r·q = L + p·Δ` entre deux
bornes : `p = 0` la donneuse fait une opération blanche (altruisme), `p = 1`
c'est la receveuse (asservissement). Ce script lit le balayage
`results/campaign/bargain/` et répond, quantité par quantité, à « qu'est-ce
que le partage gouverne ? ».

Ce qui est regardé, et pourquoi
-------------------------------
- **population**, la prédiction de l'utilisateur : beaucoup plus grande côté
  altruiste. C'est le test le plus direct.
- **rapport de branchement**, les DEUX estimateurs (racines et descendance) :
  un service plus lourd doit rendre les faillites plus contagieuses.
- **tension** K_aut/K_eq, la grandeur d'échelle de la lignée.
- **coefficient de Gini** du capital, et de la valeur nette, qui ne répondent
  pas de la même façon (M4B : Gini NW 0,44 contre Gini K 0,07 au centre).
- **distributions** du capital, de la valeur nette et du revenu d'intérêt,
  par leurs quantiles et leurs parts de tête.
- **taux effectif du carnet**, `Σ int_out / Σ dettes`, qui mêle les contrats
  hérités de l'amorçage (au taux `marginal`, gelé) et les nouveaux : c'est
  lui qui dit à quelle vitesse l'institution nouvelle prend la main.
- **partage impliqué** `mkt_p_implied`, qui doit valoir exactement p sur les
  bras `bargain` — contrôle d'intégrité — et qui MESURE, sur le bras
  `marginal`, où se situe la règle de toute la lignée antérieure.

    python3 scripts/bargain.py [--t-min 3000] [--t-max 4000]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from m4_4.cascades import reconcile  # noqa: E402
from m4_4.live import read_edges, read_panels  # noqa: E402

T_CRITICAL = 2.201  # Student, 11 ddl

SERIES_COLUMNS = (
    "pop", "prod_tot", "K_tot", "nw_tot", "loan_volume", "n_loans",
    "interest_paid", "deaths", "n_creditors", "K_share_creditors",
    "corr_marg_net", "mkt_rounds", "mkt_reversed", "mkt_surplus",
    "mkt_loss", "mkt_rq", "mkt_p_implied", "n_avalanches", "max_avalanche",
)
TENSION_COLUMNS = ("n_prod", "K_eq", "K_mean", "tension", "jensen")


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def window_mean(rows, column, t_min, t_max) -> float:
    total, count = 0.0, 0
    for row in rows:
        t = float(row["t"])
        if t_min < t <= t_max:
            value = float(row[column])
            if value == value:
                total += value
                count += 1
    return total / count if count else float("nan")


def gini(values: np.ndarray) -> float:
    n = values.size
    if n == 0:
        return float("nan")
    ordered = np.sort(values)
    mean = ordered.mean()
    if mean == 0:
        return float("nan")
    index = np.arange(1, n + 1)
    return float(((2 * index - n - 1) * ordered).sum() / (n * n * mean))


def panel_measures(path: Path, t_min: float, t_max: float) -> dict:
    """Grandeurs de distribution, moyennées sur les instantanés de la fenêtre."""
    panels = read_panels(path)
    times = np.unique(panels["t"])
    times = times[(times > t_min) & (times <= t_max)]
    rows = []
    for t in times:
        mask = panels["t"] == t
        K = panels["K"][mask]
        nw = panels["nw"][mask]
        int_in = panels["int_in"][mask]
        int_out = panels["int_out"][mask]
        debts = panels["debts"][mask]
        claims = panels["claims"][mask]
        prod = panels["prod"][mask]
        total_debts = float(debts.sum())
        row = {
            "gini_K": gini(K),
            "gini_int_in": gini(int_in),
            "gini_prod": gini(prod),
            # Le Gini d'une grandeur signée n'est pas borné par 1 ; on le
            # rend quand même, en le nommant pour ce qu'il est.
            "gini_nw_signed": gini(nw),
            "mean_K": float(K.mean()),
            "median_K": float(np.median(K)),
            "q99_K": float(np.quantile(K, 0.99)),
            "mean_nw": float(nw.mean()),
            "median_nw": float(np.median(nw)),
            "q01_nw": float(np.quantile(nw, 0.01)),
            "q99_nw": float(np.quantile(nw, 0.99)),
            "mean_int_in": float(int_in.mean()),
            "q99_int_in": float(np.quantile(int_in, 0.99)),
            "share_int_in_top10": float(
                np.sort(int_in)[-max(1, int(0.1 * int_in.size)):].sum() / int_in.sum()
            ) if int_in.sum() > 0 else float("nan"),
            "interest_share_of_income": float(
                int_in.sum() / (prod.sum() + int_in.sum())
            ),
            # Taux EFFECTIF porté par le carnet : mêle contrats hérités et
            # nouveaux, donc il mesure la prise en main de l'institution.
            "book_rate": float(int_out.sum() / total_debts) if total_debts > 0 else float("nan"),
            "debt_over_K": float(total_debts / K.sum()) if K.sum() > 0 else float("nan"),
            "claims_over_K": float(claims.sum() / K.sum()) if K.sum() > 0 else float("nan"),
            "share_net_creditors": float((claims - debts > 0).mean()),
            "share_net_debtors": float((claims - debts < 0).mean()),
            "mean_age": float(panels["age"][mask].mean()),
        }
        rows.append(row)
    if not rows:
        return {}
    return {
        key: float(np.mean([row[key] for row in rows if row[key] == row[key]]))
        for key in rows[0]
    }


def student(values) -> dict:
    clean = [value for value in values if value == value and math.isfinite(value)]
    n = len(clean)
    if n == 0:
        return {"n": 0, "mean": float("nan"), "ci95": float("nan")}
    mean = sum(clean) / n
    if n < 2:
        return {"n": n, "mean": mean, "ci95": float("nan")}
    variance = sum((value - mean) ** 2 for value in clean) / (n - 1)
    se = math.sqrt(variance / n)
    return {"n": n, "mean": mean, "se": se, "ci95": T_CRITICAL * se}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path,
                        default=ROOT / "results" / "campaign" / "bargain")
    parser.add_argument("--t-min", type=float, default=3000)
    parser.add_argument("--t-max", type=float, default=4000)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    args = parser.parse_args(argv[1:])

    arms = sorted(path.name for path in args.dir.iterdir() if path.is_dir())
    # Ordre de lecture : la référence historique, puis le partage croissant.
    arms.sort(key=lambda name: (-1.0, name) if name == "marginal"
              else (float(name.split("=")[1]), name))
    args.out.mkdir(parents=True, exist_ok=True)

    per_run = []
    for arm in arms:
        for directory in sorted((args.dir / arm).iterdir()):
            if not (directory / "series.csv").exists():
                continue
            seed = int(directory.name[4:])
            series = read_csv(directory / "series.csv")
            tension = read_csv(directory / "tension_agg.csv")
            row = {"arm": arm, "seed": seed}
            for column in SERIES_COLUMNS:
                if column in series[0]:
                    row[column] = window_mean(series, column, args.t_min, args.t_max)
            for column in TENSION_COLUMNS:
                row[column] = window_mean(tension, column, args.t_min, args.t_max)
            row["rotation"] = row["loan_volume"] / row["K_tot"]
            row["mortality"] = row["deaths"] / row["pop"]
            row["prod_per_prod"] = row["prod_tot"] / row["n_prod"]

            edges_path = directory / "loss_edges.npz"
            if edges_path.exists():
                both = reconcile(series, read_edges(edges_path), args.t_min, args.t_max)
                row["b1"] = both["b1"]
                row["b2"] = both["b2"]
                row["multi_parent_share"] = both["multi_parent_share"]
                row["closes"] = both["closes"]
            panels_path = directory / "panels.npz"
            if panels_path.exists():
                row.update(panel_measures(panels_path, args.t_min, args.t_max))
            per_run.append(row)
    assert per_run, f"aucun run sous {args.dir}"

    fieldnames = ["arm", "seed"] + sorted({k for r in per_run for k in r} - {"arm", "seed"})
    with open(args.out / "bargain_runs.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(per_run)

    quantities = [k for k in fieldnames if k not in ("arm", "seed", "closes")]
    summary: dict[str, dict] = {}
    for arm in arms:
        values = [row for row in per_run if row["arm"] == arm]
        summary[arm] = {
            quantity: student([row.get(quantity, float("nan")) for row in values])
            for quantity in quantities
        }

    # Contrastes appariés contre la règle historique.
    contrasts: dict[str, dict] = {}
    reference = {row["seed"]: row for row in per_run if row["arm"] == "marginal"}
    for arm in arms:
        if arm == "marginal" or not reference:
            continue
        contrasts[arm] = {}
        for quantity in quantities:
            ratios = []
            for row in per_run:
                if row["arm"] != arm or row["seed"] not in reference:
                    continue
                a = row.get(quantity, float("nan"))
                b = reference[row["seed"]].get(quantity, float("nan"))
                if a == a and b == b and b != 0:
                    ratios.append(a / b)
            contrasts[arm][quantity] = student(ratios)

    (args.out / "bargain_summary.json").write_text(
        json.dumps({"window": [args.t_min, args.t_max], "arms": arms,
                    "summary": summary, "contrasts_vs_marginal": contrasts},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # DISCRIMINATION DES DEUX EXPLICATIONS de la non-linéarité observée au
    # pilote : le bras asservi (p = 1) est indiscernable du régime historique
    # `marginal`, alors que celui-ci partage à p ≈ 0,52. Ou bien
    #   (i) la réponse est intrinsèquement convexe en p, et alors pop(0,5) du
    #       balayage doit tomber près de pop(`marginal`) ;
    #   (ii) ou bien c'est la DISPERSION du partage impliqué par `marginal`
    #        qui gouverne, et alors pop(0,5) doit se situer nettement
    #        au-dessus de pop(`marginal`).
    # Les deux prédictions sont opposées et se lisent sur les mêmes runs.
    convexity = {}
    if "marginal" in summary and "p=0.5" in summary:
        reference_pop = summary["marginal"]["pop"]["mean"]
        half_pop = summary["p=0.5"]["pop"]["mean"]
        implied = summary["marginal"].get("mkt_p_implied", {}).get("mean", float("nan"))
        convexity = {
            "pop_marginal": reference_pop,
            "pop_p_half": half_pop,
            "ratio": half_pop / reference_pop if reference_pop else float("nan"),
            "p_implied_marginal": implied,
            "lecture": (
                "dispersion (ii) : p=0,5 nettement au-dessus de `marginal`"
                if half_pop > 1.05 * reference_pop
                else "convexité seule (i) : p=0,5 proche de `marginal`"
            ),
        }
        payload_extra = {"convexity_test": convexity}
    else:
        payload_extra = {}

    if payload_extra:
        data = json.loads((args.out / "bargain_summary.json").read_text(encoding="utf-8"))
        data.update(payload_extra)
        (args.out / "bargain_summary.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    headline = ("pop", "prod_tot", "K_tot", "mortality", "rotation", "b1", "b2",
                "tension", "gini_K", "gini_nw_signed", "gini_int_in",
                "book_rate", "interest_share_of_income", "mkt_p_implied")
    width = max(len(name) for name in headline) + 2
    print(f"# fenêtre ]{args.t_min:g}, {args.t_max:g}], "
          f"{len(per_run) // max(len(arms), 1)} graines par bras")
    print()
    print("grandeur".ljust(width) + "".join(f"{arm:>16}" for arm in arms))
    for quantity in headline:
        line = quantity.ljust(width)
        for arm in arms:
            entry = summary[arm].get(quantity, {})
            value = entry.get("mean", float("nan"))
            line += f"{value:>16.4g}" if value == value else f"{'—':>16}"
        print(line)
    if convexity:
        print()
        print(f"  pop(p=0,5)/pop(`marginal`) = {convexity['ratio']:.3f} ; "
              f"partage impliqué par `marginal` = {convexity['p_implied_marginal']:.4f}")
        print(f"  → {convexity['lecture']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
