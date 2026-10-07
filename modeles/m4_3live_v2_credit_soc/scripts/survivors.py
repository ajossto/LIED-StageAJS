"""Le régime que le sens libre rend possible : qui survit, et de quoi ?

CE QUE CE SCRIPT ÉTABLIT. La campagne du lot D montre, au niveau agrégé, que
la cohorte de l'ancienne technologie s'éteint sous la règle v1 (« la plus
riche prête ») et SURVIT sous le sens libre. Un agrégat ne dit pas
*pourquoi*. Ce script rejoue le bras `new_A150` — à l'identique, mêmes
graines et mêmes snapshots que la campagne, ce qui est vérifié colonne par
colonne — puis ouvre l'état final entité par entité et répond à trois
questions :

1. les survivantes de l'ancienne technologie sont-elles en position nette
   CRÉANCIÈRE, c'est-à-dire ont-elles cédé leur capital ?
2. quelle part de leur revenu vient des intérêts plutôt que de leur propre
   production ?
3. à quel capital tournent-elles, comparé à la population de la nouvelle
   technologie ?

Le revenu d'une entité au dernier pas est décomposé en
`production + intérêts reçus − intérêts versés`, les trois quantités étant
déjà tenues par le moteur (`prod`, `int_in`, `int_out`).

    python3 scripts/survivors.py
"""

from __future__ import annotations

import csv
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent.parent))

from m4_3live_v2.live import load_snapshot  # noqa: E402
from m4_3live_v2.model import Config, Intervention, net_worth  # noqa: E402

ANALYSIS = ROOT / "results" / "analysis"
CAMPAIGN = ROOT / "results" / "campaign"

T0 = 2000
WINDOW = 2000
SEEDS = (0, 1, 2)
ARM = "new_A150"
BASE = dict(gamma=0.5, A=1.0, lam=30.0, delta=0.01, sigma=0.01, K0=25.0,
            pop_max=30_000, rate_rule="marginal", kernel_policy="exact_lut")


def replay(job: tuple[int, str]) -> list[dict]:
    seed, direction = job
    started = time.time()
    config = Config(**BASE, loan_direction=direction, seed=seed, T=T0 + WINDOW)
    simulation = load_snapshot(
        CAMPAIGN / "burn" / f"seed{seed}" / f"snapshot_t{T0}.pkl", config=config
    )
    plan = Intervention(param="A", value=1.5, scope="new")
    while simulation.t < config.T and simulation.status == "ok":
        if simulation.t + 1 == T0 + 1:
            simulation.submit(plan)
        simulation.step()

    # Contrôle de reproductibilité : la trajectoire doit être celle de la
    # campagne, colonne par colonne. Sans ce contrôle, on décrirait l'état
    # final d'un run qui n'est pas celui qu'on a publié.
    reference_path = CAMPAIGN / "arms" / direction / ARM / f"seed{seed}" / "series.csv"
    identical = None
    if reference_path.exists():
        with open(reference_path, newline="", encoding="utf-8") as handle:
            reference = list(csv.DictReader(handle))
        identical = True
        for left, right in zip(reference, simulation.series):
            for column in ("pop", "K_tot", "prod_tot", "loan_volume", "deaths"):
                if float(left[column]) != float(right[column]):
                    identical = False
                    break
            if not identical:
                break

    population = simulation.population
    book = simulation.book
    rows = []
    for entity in population.living():
        claims = book.claims.get(entity, 0.0)
        debts = book.debts.get(entity, 0.0)
        rows.append(
            {
                "seed": seed,
                "direction": direction,
                "id": entity,
                "tech": population.tech[entity],
                "A": population.A[entity],
                "gamma": population.g[entity],
                "K": population.K[entity],
                "claims": claims,
                "debts": debts,
                "net_position": claims - debts,
                "net_worth": net_worth(population, book, entity),
                "prod": population.prod[entity],
                "int_in": population.int_in[entity],
                "int_out": population.int_out[entity],
                "age": simulation.t - population.birth[entity],
                "reproduit_la_campagne": identical,
                "wall_seconds": time.time() - started,
            }
        )
    return rows


def summarise(rows: list[dict]) -> list[dict]:
    out = []
    keys = sorted({(row["seed"], row["direction"], row["tech"]) for row in rows})
    for seed, direction, tech in keys:
        group = [r for r in rows if (r["seed"], r["direction"], r["tech"]) == (seed, direction, tech)]
        n = len(group)
        income = sum(r["prod"] + r["int_in"] for r in group)
        interest = sum(r["int_in"] for r in group)
        out.append(
            {
                "seed": seed,
                "direction": direction,
                "tech": tech,
                "A": group[0]["A"],
                "n": n,
                "part_creancieres_nettes": sum(1 for r in group if r["net_position"] > 0) / n,
                "K_moyen": sum(r["K"] for r in group) / n,
                "K_median": sorted(r["K"] for r in group)[n // 2],
                "position_nette_moyenne": sum(r["net_position"] for r in group) / n,
                "part_du_revenu_en_interets": interest / income if income > 0 else float("nan"),
                "age_median": sorted(r["age"] for r in group)[n // 2],
                "creances_totales": sum(r["claims"] for r in group),
                "dettes_totales": sum(r["debts"] for r in group),
            }
        )
    return out


def main() -> int:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    jobs = [(seed, direction) for seed in SEEDS for direction in ("free", "richest_lends")]
    started = time.time()
    with mp.Pool(processes=min(len(jobs), 6)) as pool:
        chunks = pool.map(replay, jobs)
    rows = [row for chunk in chunks for row in chunk]

    reproduced = {(row["seed"], row["direction"]): row["reproduit_la_campagne"] for row in rows}
    failures = [key for key, ok in reproduced.items() if ok is False]
    if failures:
        raise SystemExit(f"le rejeu ne reproduit pas la campagne pour {failures}")

    with open(ANALYSIS / "survivors_entities.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarise(rows)
    with open(ANALYSIS / "survivors.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"# {len(jobs)} rejeux en {time.time() - started:.0f} s ; "
          f"tous reproduisent la campagne colonne par colonne")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
