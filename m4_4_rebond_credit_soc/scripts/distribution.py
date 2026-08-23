"""Lot B — LA question du mandat : où va le surcroît de production ?

Les agrégats disent que la production totale monte de 0,747 % par pour-cent
d'A, parce que la production par entité monte de ×1,80 pendant que la
population se contracte de 25 %. Ce script demande où ce surcroît se dépose
dans la distribution, en lisant les panneaux par entité (§4.2) plutôt que
les seules colonnes agrégées.

Trois façons de répondre, et elles ne disent pas la même chose
---------------------------------------------------------------
1. **Les parts.** Quelle fraction de la production, du revenu, de la valeur
   nette chaque groupe (§4.5) détient-il, et cette fraction bouge-t-elle
   entre le contrôle et le bras traité ? Une part est sans échelle : elle
   compare deux populations d'effectifs différents sans être écrasée par
   l'effectif.
2. **Les rapports de quantiles.** Pour chaque niveau p, le rapport
   q_p(traité)/q_p(contrôle). S'il est PLAT à 1,80, la hausse est un pur
   changement d'échelle et la forme de la distribution ne bouge pas. S'il
   croît avec p, la queue capte plus que le corps.
3. **Le partage production / intérêt.** `income = prod + int_in` : la part
   du revenu qui vient de l'intérêt plutôt que de la production dit si le
   surcroît va aux producteurs ou aux rentiers. M4B avait montré que
   l'inégalité de ce modèle est dans les BILANS, pas dans le capital ; c'est
   ici qu'on le retrouve ou non.

Chaque grandeur est calculée PAR INSTANTANÉ, puis moyennée sur les
instantanés d'un run, puis appariée graine à graine. Les trois échelles
d'incertitude — intra-instantané, inter-instantanés, inter-graines — ne sont
jamais fusionnées (leçon de M4.2B, plan §2.2) : la dispersion
inter-instantanés est rendue à part.

    python3 scripts/distribution.py [--arms-dir …] [--t-min 3000] [--t-max 4000]
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

from m4_4.groups import NET_POSITIONS, partitions, shares  # noqa: E402
from m4_4.live import read_panels  # noqa: E402

T_CRITICAL = 2.201  # Student, 11 ddl
LOG_A = math.log(1.5)
#: Niveaux de quantile rendus. Serrés dans la queue, où la question se pose.
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999)
#: Grandeurs par entité dont on suit la distribution.
FIELDS = ("prod", "income", "income_net", "nw", "K", "int_in")


def gini(values: np.ndarray) -> float:
    """G = Σ(2i − n − 1)x_i / (n² x̄), sur les valeurs triées.

    Forme exacte du Gini discret ; elle admet les valeurs négatives (la
    valeur nette peut l'être), auquel cas elle n'est plus bornée par 1 — on
    la rend telle quelle plutôt que de tronquer, et on ne l'emploie que sur
    des grandeurs positives dans les conclusions.
    """
    n = values.size
    if n == 0:
        return float("nan")
    ordered = np.sort(values)
    mean = ordered.mean()
    if mean == 0:
        return float("nan")
    index = np.arange(1, n + 1)
    return float(((2 * index - n - 1) * ordered).sum() / (n * n * mean))


def top_share(values: np.ndarray, fraction: float) -> float:
    """Part du total détenue par la fraction supérieure (par la grandeur
    elle-même)."""
    n = values.size
    if n == 0:
        return float("nan")
    count = max(1, int(round(fraction * n)))
    total = values.sum()
    if total == 0:
        return float("nan")
    return float(np.sort(values)[-count:].sum() / total)


def snapshot_measures(panel: dict) -> dict:
    """Toutes les grandeurs d'UN instantané."""
    groups = partitions(panel)
    n = panel["id"].size
    measures: dict[str, float] = {"n": float(n)}

    for field in FIELDS:
        values = panel[field]
        measures[f"mean_{field}"] = float(values.mean()) if n else float("nan")
        measures[f"total_{field}"] = float(values.sum())
        if field != "nw":  # le Gini d'une grandeur signée n'est pas lisible
            measures[f"gini_{field}"] = gini(values)
            measures[f"top1_{field}"] = top_share(values, 0.01)
            measures[f"top10_{field}"] = top_share(values, 0.10)
        for level in QUANTILES:
            measures[f"q{level:g}_{field}"] = float(np.quantile(values, level))

    # Partage production / intérêt : la question « producteurs ou rentiers ».
    total_income = float(panel["income"].sum())
    measures["interest_share_of_income"] = (
        float(panel["int_in"].sum()) / total_income if total_income else float("nan")
    )
    measures["rentier_count_share"] = (
        float((panel["int_in"] > panel["prod"]).mean()) if n else float("nan")
    )

    # Position nette (§4.5) : part de population, de capital, de production et
    # de revenu net de chaque camp.
    labels = groups["net_position"]
    for index, name in enumerate(NET_POSITIONS):
        mask = labels == index
        measures[f"popshare_{name}"] = float(mask.mean()) if n else float("nan")
        for field in ("K", "prod", "income_net"):
            total = float(panel[field].sum())
            measures[f"{field}share_{name}"] = (
                float(panel[field][mask].sum()) / total if total else float("nan")
            )

    # Déciles de capital : part de la production et du revenu d'intérêt.
    for field in ("prod", "int_in", "K"):
        for level, value in shares(panel, groups["K_decile"], field,
                                   levels=range(10)).items():
            measures[f"Kdec{level}_{field}share"] = value

    # Déciles d'âge : part de la production, et âge moyen.
    for level, value in shares(panel, groups["age_decile"], "prod",
                               levels=range(10)).items():
        measures[f"agedec{level}_prodshare"] = value
    measures["mean_age"] = float(panel["age"].mean()) if n else float("nan")

    # Technologies : effectif et production par technologie présente.
    techs = np.unique(panel["tech"])
    measures["n_tech"] = float(techs.size)
    for rank, tech in enumerate(sorted(techs.tolist())):
        mask = panel["tech"] == tech
        measures[f"tech{rank}_id"] = float(tech)
        measures[f"tech{rank}_popshare"] = float(mask.mean())
        total = float(panel["prod"].sum())
        measures[f"tech{rank}_prodshare"] = (
            float(panel["prod"][mask].sum()) / total if total else float("nan")
        )
    return measures


def run_measures(path: Path, t_min: float, t_max: float) -> tuple[dict, dict, int]:
    """Moyenne et écart-type INTER-INSTANTANÉS d'un run, sur la fenêtre."""
    panels = read_panels(path)
    times = np.unique(panels["t"])
    times = times[(times > t_min) & (times <= t_max)]
    per_snapshot: list[dict] = []
    for t in times:
        mask = panels["t"] == t
        panel = {name: values[mask] for name, values in panels.items() if name != "t"}
        per_snapshot.append(snapshot_measures(panel))
    if not per_snapshot:
        return {}, {}, 0
    keys = sorted({key for row in per_snapshot for key in row})
    mean, sigma = {}, {}
    for key in keys:
        values = np.array([row.get(key, np.nan) for row in per_snapshot], dtype=float)
        finite = values[np.isfinite(values)]
        mean[key] = float(finite.mean()) if finite.size else float("nan")
        sigma[key] = float(finite.std(ddof=1)) if finite.size > 1 else float("nan")
    return mean, sigma, len(per_snapshot)


def student(values: list[float]) -> tuple[float, float, float, int]:
    clean = [value for value in values if value == value and math.isfinite(value)]
    n = len(clean)
    if n < 2:
        return (clean[0] if clean else float("nan")), float("nan"), float("nan"), n
    mean = sum(clean) / n
    variance = sum((value - mean) ** 2 for value in clean) / (n - 1)
    se = math.sqrt(variance / n)
    return mean, se, T_CRITICAL * se, n


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms-dir", type=Path,
                        default=ROOT / "results" / "campaign" / "arms" / "free")
    parser.add_argument("--t-min", type=float, default=3000)
    parser.add_argument("--t-max", type=float, default=4000)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    args = parser.parse_args(argv[1:])

    arms = sorted(path.name for path in args.arms_dir.iterdir() if path.is_dir())
    seeds = sorted(
        int(path.name[4:])
        for path in (args.arms_dir / "control").iterdir()
        if path.is_dir() and path.name.startswith("seed")
    )
    args.out.mkdir(parents=True, exist_ok=True)

    runs: dict[tuple[str, int], dict] = {}
    rows = []
    n_snapshots = 0
    for arm in arms:
        for seed in seeds:
            path = args.arms_dir / arm / f"seed{seed}" / "panels.npz"
            if not path.exists():
                continue
            mean, sigma, count = run_measures(path, args.t_min, args.t_max)
            if not mean:
                continue
            n_snapshots = count
            runs[(arm, seed)] = mean
            rows.append({"arm": arm, "seed": seed, "n_snapshots": count,
                         "statistic": "mean", **mean})
            rows.append({"arm": arm, "seed": seed, "n_snapshots": count,
                         "statistic": "sd_inter_snapshot", **sigma})
    assert runs, f"aucun panneau trouvé sous {args.arms_dir}"

    fieldnames = ["arm", "seed", "n_snapshots", "statistic"] + sorted(
        {key for row in rows for key in row}
        - {"arm", "seed", "n_snapshots", "statistic"}
    )
    with open(args.out / "lotB_distribution.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)

    # Contrastes appariés contre le contrôle : différence pour les parts,
    # rapport (et élasticité) pour les niveaux.
    contrasts = []
    summary: dict[str, dict] = {}
    keys = sorted({key for (arm, seed), mean in runs.items() for key in mean})
    for arm in arms:
        if arm == "control":
            continue
        summary[arm] = {}
        for key in keys:
            differences, elasticities = [], []
            for seed in seeds:
                treated = runs.get((arm, seed))
                control = runs.get(("control", seed))
                if treated is None or control is None:
                    continue
                a, b = treated.get(key, float("nan")), control.get(key, float("nan"))
                if not (isinstance(a, float) and isinstance(b, float)):
                    continue
                if math.isfinite(a) and math.isfinite(b):
                    differences.append(a - b)
                    if a > 0 and b > 0:
                        elasticities.append(math.log(a / b) / LOG_A)
            if not differences:
                continue
            d_mean, d_se, d_ci, n = student(differences)
            e_mean, e_se, e_ci, _ = student(elasticities)
            contrasts.append({
                "arm": arm, "quantity": key, "n_seeds": n,
                "diff_mean": d_mean, "diff_ci95": d_ci,
                "elasticity_mean": e_mean, "elasticity_ci95": e_ci,
                "significant_diff": abs(d_mean) > d_ci if d_ci == d_ci else False,
            })
            summary[arm][key] = {
                "diff": d_mean, "diff_ci95": d_ci,
                "elasticity": e_mean, "elasticity_ci95": e_ci,
            }
    with open(args.out / "lotB_contrasts.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(contrasts[0]))
        writer.writeheader()
        writer.writerows(contrasts)

    (args.out / "lotB_distribution.json").write_text(
        json.dumps({"n_snapshots_par_run": n_snapshots, "seeds": seeds,
                    "window": [args.t_min, args.t_max], "contrasts": summary},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Lecture à l'écran : le rapport de quantiles, qui est LA réponse.
    print(f"# {n_snapshots} instantanés par run, {len(seeds)} graines, "
          f"fenêtre ]{args.t_min:g}, {args.t_max:g}]")
    for arm in arms:
        if arm == "control" or arm not in summary:
            continue
        print(f"\n=== {arm} ===")
        print("  rapport de quantiles traité/contrôle (1,80 = pur changement d'échelle)")
        for field in ("prod", "income", "nw"):
            pieces = []
            for level in QUANTILES:
                key = f"q{level:g}_{field}"
                if key not in summary[arm]:
                    continue
                elasticity = summary[arm][key]["elasticity"]
                pieces.append(f"q{level:g} ×{math.exp(elasticity * LOG_A):.3f}")
            if pieces:
                print(f"    {field:<11} " + "  ".join(pieces))
        for key, label in (("interest_share_of_income", "part du revenu venant de l'intérêt"),
                           ("rentier_count_share", "part des entités rentières"),
                           ("gini_prod", "Gini de la production"),
                           ("gini_K", "Gini du capital"),
                           ("top10_prod", "part de production du décile supérieur"),
                           ("popshare_crediteur", "part créancière nette"),
                           ("prodshare_crediteur", "production des créancières nettes")):
            if key in summary[arm]:
                entry = summary[arm][key]
                flag = "*" if abs(entry["diff"]) > entry["diff_ci95"] else " "
                print(f"    {label:<40} {entry['diff']:+.4f} ± {entry['diff_ci95']:.4f} {flag}")
    print("\n  * = écart significatif à 5 % (Student apparié, 11 ddl)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
