"""Lot E — TENTATIVE DE CONTRÔLE de l'exposant de queue et du branchement.

Le plan §3.3 définit « contrôler » de façon restrictive, et c'est tout
l'intérêt : un levier contrôle une grandeur si, et seulement si

1. la réponse appariée a un **signe constant** sur toutes les graines ;
2. elle est **monotone** sur une étendue mesurée d'au moins **×3** du levier ;
3. son exposant intra-famille **survit au contrôle §14.2** — c'est-à-dire
   qu'il ne coïncide pas avec la droite qui joint les lignes de base.

Tout ce qui est plus faible est une corrélation, et doit être appelé ainsi.

Le troisième point, traduit en procédure
-----------------------------------------
Le piège que v2 a documenté : un balayage à un levier autour d'un point
unique produit un R² groupé qui n'est que la droite joignant les lignes de
base des cellules. La parade employée ici est de **fabriquer l'exposant
graine par graine** : pour chaque graine, on ajuste ln(y) contre ln(ρ) sur
les cinq niveaux de CETTE graine, ce qui donne douze exposants indépendants
appariés. Si la relation n'était qu'un artefact d'agrégation, ces douze
exposants seraient dispersés autour de zéro ; s'ils s'accordent, la relation
existe à l'intérieur de chaque trajectoire.

Ce qui est suivi : α̂ du revenu d'intérêt et de la valeur nette (queue), les
deux estimateurs du branchement, et les grandeurs d'accompagnement qui
disent PAR QUEL CANAL le levier agirait (rotation, mortalité, Gini).

    python3 scripts/control.py [--dir results/campaign/control_rho] [--ref 1]
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
from m4_4.tails import fit_tail  # noqa: E402

T_CRITICAL = 2.201
TAIL_QUANTITIES = ("int_in", "nw")


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def window_mean(rows, column, t_min, t_max) -> float:
    total, count = 0.0, 0
    for row in rows:
        t = float(row["t"])
        if t_min < t <= t_max and row.get(column) not in (None, "", "nan"):
            total += float(row[column])
            count += 1
    return total / count if count else float("nan")


def student(values) -> dict:
    clean = [v for v in values if v == v and math.isfinite(v)]
    n = len(clean)
    if n == 0:
        return {"n": 0, "mean": float("nan"), "ci95": float("nan"), "sd": float("nan")}
    mean = sum(clean) / n
    if n < 2:
        return {"n": n, "mean": mean, "ci95": float("nan"), "sd": float("nan")}
    variance = sum((v - mean) ** 2 for v in clean) / (n - 1)
    sd = math.sqrt(variance)
    return {"n": n, "mean": mean, "sd": sd, "ci95": T_CRITICAL * sd / math.sqrt(n)}


def run_measures(directory: Path, t_min: float, t_max: float) -> dict:
    series = read_csv(directory / "series.csv")
    tension = read_csv(directory / "tension_agg.csv")
    market_path = directory / "market_stats.csv"
    row = {
        "pop": window_mean(series, "pop", t_min, t_max),
        "prod_tot": window_mean(series, "prod_tot", t_min, t_max),
        "K_tot": window_mean(series, "K_tot", t_min, t_max),
        "loan_volume": window_mean(series, "loan_volume", t_min, t_max),
        "deaths": window_mean(series, "deaths", t_min, t_max),
        "n_loans": window_mean(series, "n_loans", t_min, t_max),
        "interest_paid": window_mean(series, "interest_paid", t_min, t_max),
        "tension": window_mean(tension, "tension", t_min, t_max),
        "K_eq": window_mean(tension, "K_eq", t_min, t_max),
    }
    row["rotation"] = row["loan_volume"] / row["K_tot"]
    row["mortality"] = row["deaths"] / row["pop"]
    if market_path.exists():
        row["gini"] = window_mean(read_csv(market_path), "gini_before", t_min, t_max)
    edges = directory / "loss_edges.npz"
    if edges.exists():
        both = reconcile(series, read_edges(edges), t_min, t_max)
        row["b1"], row["b2"] = both["b1"], both["b2"]
    panels = directory / "panels.npz"
    if panels.exists():
        data = read_panels(panels)
        times = np.unique(data["t"])
        times = times[(times > t_min) & (times <= t_max)]
        for quantity in TAIL_QUANTITIES:
            alphas, tails = [], []
            for t in times:
                mask = data["t"] == t
                values = data[quantity][mask]
                fit = fit_tail(values[values > 0])
                if fit["alpha"] == fit["alpha"]:
                    alphas.append(fit["alpha"])
                    tails.append(fit["n_tail"])
            row[f"alpha_{quantity}"] = float(np.mean(alphas)) if alphas else float("nan")
            row[f"alpha_{quantity}_sd_snap"] = (
                float(np.std(alphas, ddof=1)) if len(alphas) > 1 else float("nan"))
            row[f"ntail_{quantity}"] = float(np.median(tails)) if tails else float("nan")
    return row


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path,
                        default=ROOT / "results" / "campaign" / "control_rho")
    parser.add_argument("--lever", default="rho")
    parser.add_argument("--ref", type=float, default=1.0)
    parser.add_argument("--t-min", type=float, default=3000)
    parser.add_argument("--t-max", type=float, default=4000)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    args = parser.parse_args(argv[1:])

    levels: dict[float, dict[int, dict]] = {}
    for arm_dir in sorted(p for p in args.dir.iterdir() if p.is_dir()):
        level = float(arm_dir.name.split("=")[1])
        for run_dir in sorted(p for p in arm_dir.iterdir() if p.is_dir()):
            if not (run_dir / "series.csv").exists():
                continue
            seed = int(run_dir.name[4:])
            levels.setdefault(level, {})[seed] = run_measures(
                run_dir, args.t_min, args.t_max)
    assert levels, f"aucun run sous {args.dir}"
    ordered = sorted(levels)
    span = max(ordered) / min(ordered)
    seeds = sorted(set.intersection(*(set(levels[l]) for l in ordered)))

    quantities = sorted({k for l in ordered for s in levels[l] for k in levels[l][s]})
    rows = []
    for level in ordered:
        for seed, measures in sorted(levels[level].items()):
            rows.append({args.lever: level, "seed": seed, **measures})
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / f"lotE_{args.lever}_runs.csv", "w", newline="",
              encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[args.lever, "seed"] + quantities,
                                restval="")
        writer.writeheader()
        writer.writerows(rows)

    verdicts: dict[str, dict] = {}
    log_levels = np.log(np.array(ordered, dtype=float))
    for quantity in quantities:
        # (1) SIGNE : réponse appariée entre l'extrême haut et la référence.
        responses = []
        for seed in seeds:
            high = levels[max(ordered)][seed].get(quantity, float("nan"))
            base = levels[args.ref][seed].get(quantity, float("nan"))
            if high == high and base == base:
                responses.append(high - base)
        if not responses:
            continue
        constant_sign = all(r > 0 for r in responses) or all(r < 0 for r in responses)

        # (2) MONOTONIE des moyennes de niveau.
        means = [student([levels[l][s].get(quantity, float("nan"))
                          for s in seeds])["mean"] for l in ordered]
        monotone = (all(b >= a for a, b in zip(means, means[1:]))
                    or all(b <= a for a, b in zip(means, means[1:])))

        # (3) CONTRÔLE §14.2 : un exposant PAR GRAINE, sur les niveaux de
        #     cette graine seulement — jamais une régression groupée.
        exponents = []
        for seed in seeds:
            values = np.array([levels[l][seed].get(quantity, float("nan"))
                               for l in ordered], dtype=float)
            if np.all(np.isfinite(values)) and np.all(values > 0):
                slope = np.polyfit(log_levels, np.log(values), 1)[0]
                exponents.append(float(slope))
        exponent = student(exponents)
        # Un exposant est « survivant » s'il est significativement non nul ET
        # de signe constant d'une graine à l'autre.
        survives = (
            exponent["n"] >= 2
            and abs(exponent["mean"]) > exponent["ci95"]
            and (all(e > 0 for e in exponents) or all(e < 0 for e in exponents))
        )
        verdicts[quantity] = {
            "levels": ordered,
            "means": means,
            "span": span,
            "constant_sign": bool(constant_sign),
            "monotone": bool(monotone),
            "exponent": exponent,
            "exponent_survives": bool(survives),
            "controlled": bool(constant_sign and monotone and survives and span >= 3.0),
        }

    (args.out / f"lotE_{args.lever}_verdicts.json").write_text(
        json.dumps({"lever": args.lever, "span": span, "seeds": seeds,
                    "window": [args.t_min, args.t_max], "verdicts": verdicts},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")

    headline = ("alpha_int_in", "alpha_nw", "b1", "b2", "pop", "rotation",
                "mortality", "gini", "tension", "ntail_int_in")
    print(f"# levier {args.lever}, niveaux {ordered} (étendue ×{span:g}), "
          f"{len(seeds)} graines, fenêtre ]{args.t_min:g}, {args.t_max:g}]")
    print(f"# « contrôlé » exige : signe constant ET monotonie ET exposant par "
          f"graine non nul ET étendue ≥ ×3")
    print()
    header = f"{'grandeur':<16}" + "".join(f"{l:>10g}" for l in ordered)
    print(header + f"{'exposant':>16}{'contrôlé':>10}")
    for quantity in headline:
        if quantity not in verdicts:
            continue
        entry = verdicts[quantity]
        line = f"{quantity:<16}"
        for value in entry["means"]:
            line += f"{value:>10.4g}" if value == value else f"{'—':>10}"
        line += f"{entry['exponent']['mean']:>+10.4f}±{entry['exponent']['ci95']:<5.4f}"
        line += f"{'OUI' if entry['controlled'] else 'non':>10}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
