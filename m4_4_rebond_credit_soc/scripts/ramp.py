"""Le partage qui ÉVOLUE — hystérésis entre la rampe montante et la descendante.

Les bras statiques du lot T sont déjà des expériences de changement brusque :
ils passent de la règle historique à un p fixe, à t₀. Ce que la rampe ajoute,
et qu'eux ne peuvent pas donner, c'est la MÉMOIRE : le partage monte par
paliers dans un bras, descend par les mêmes paliers dans l'autre, et l'on
compare l'état aux MÊMES valeurs de p.

Une différence est attendue, puisque les contrats déjà signés gardent leur
taux : à p = 0,5 en montant, le carnet porte encore des contrats conclus à
p = 0,25 ; en descendant, il en porte à p = 0,75. Ce que la mesure donne,
c'est l'AMPLEUR de cette mémoire, et le temps qu'il faut pour l'effacer.

Chaque palier dure `RAMP_STEP` pas ; on ne lit que sa SECONDE MOITIÉ, pour
laisser au carnet le temps de tourner.

    python3 scripts/ramp.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

T_CRITICAL = 2.201
T0 = 2000
RAMP_STEP = 400
LEVELS_UP = (0.0, 0.25, 0.5, 0.75, 1.0)
COLUMNS = ("pop", "prod_tot", "K_tot", "loan_volume", "n_loans", "interest_paid",
           "deaths", "mkt_p_implied")


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def plateau_mean(rows, column, index: int) -> float:
    """Moyenne sur la SECONDE MOITIÉ du palier `index`."""
    start = T0 + index * RAMP_STEP + RAMP_STEP // 2
    stop = T0 + (index + 1) * RAMP_STEP
    total, count = 0.0, 0
    for row in rows:
        t = float(row["t"])
        if start < t <= stop and row.get(column) not in (None, "", "nan"):
            total += float(row[column])
            count += 1
    return total / count if count else float("nan")


def student(values) -> dict:
    clean = [v for v in values if v == v and math.isfinite(v)]
    n = len(clean)
    if n < 2:
        return {"n": n, "mean": clean[0] if clean else float("nan"), "ci95": float("nan")}
    mean = sum(clean) / n
    variance = sum((v - mean) ** 2 for v in clean) / (n - 1)
    return {"n": n, "mean": mean, "ci95": T_CRITICAL * math.sqrt(variance / n)}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path,
                        default=ROOT / "results" / "campaign" / "bargain")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    args = parser.parse_args(argv[1:])

    # p -> direction -> {graine: {colonne: valeur}}
    data: dict[float, dict[str, dict[int, dict]]] = {}
    rows = []
    for direction in ("up", "down"):
        arm = args.dir / f"ramp_{direction}"
        if not arm.exists():
            continue
        levels = LEVELS_UP if direction == "up" else tuple(reversed(LEVELS_UP))
        for run in sorted(arm.iterdir()):
            if not (run / "series.csv").exists():
                continue
            seed = int(run.name[4:])
            series = read_csv(run / "series.csv")
            for index, level in enumerate(levels):
                measures = {c: plateau_mean(series, c, index) for c in COLUMNS}
                data.setdefault(level, {}).setdefault(direction, {})[seed] = measures
                rows.append({"direction": direction, "p": level, "palier": index,
                             "seed": seed, **measures})
    assert rows, f"aucune rampe sous {args.dir}"

    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "lotT_ramp.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    payload = {}
    print("# hystérésis : état au MÊME partage, atteint en montant ou en descendant")
    print(f"# seconde moitié de chaque palier de {RAMP_STEP} pas, 12 graines appariées")
    print()
    print(f"{'p':>6}{'pop montant':>14}{'pop descendant':>16}{'rapport':>11}{'IC 95 %':>10}"
          f"{'p impliqué ↑':>14}{'p impliqué ↓':>14}")
    for level in sorted(data):
        if set(data[level]) != {"up", "down"}:
            continue
        seeds = sorted(set(data[level]["up"]) & set(data[level]["down"]))
        ratios = [data[level]["up"][s]["pop"] / data[level]["down"][s]["pop"]
                  for s in seeds]
        statistics = student(ratios)
        up_pop = student([data[level]["up"][s]["pop"] for s in seeds])
        down_pop = student([data[level]["down"][s]["pop"] for s in seeds])
        up_p = student([data[level]["up"][s]["mkt_p_implied"] for s in seeds])
        down_p = student([data[level]["down"][s]["mkt_p_implied"] for s in seeds])
        payload[f"p={level:g}"] = {
            "pop_up": up_pop, "pop_down": down_pop, "ratio": statistics,
            "p_implied_up": up_p, "p_implied_down": down_p,
            "significant": abs(statistics["mean"] - 1.0) > statistics["ci95"],
        }
        flag = "*" if payload[f"p={level:g}"]["significant"] else " "
        print(f"{level:>6.2f}{up_pop['mean']:>14.1f}{down_pop['mean']:>16.1f}"
              f"{statistics['mean']:>11.4f}{statistics['ci95']:>10.4f}{flag}"
              f"{up_p['mean']:>14.4f}{down_p['mean']:>14.4f}")
    (args.out / "lotT_ramp.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print("  * = rapport significativement différent de 1 (Student apparié, 11 ddl)")
    print("  Le partage IMPLIQUÉ doit valoir p dans les deux sens : c'est le")
    print("  contrôle d'intégrité. Toute différence d'état à p égal est donc")
    print("  portée par le CARNET hérité, pas par le taux courant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
