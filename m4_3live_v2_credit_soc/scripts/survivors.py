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
sys.path.insert(0, str(ROOT.parent))

from m4_3live_v2.live import load_snapshot  # noqa: E402
from m4_3live_v2.model import Config, Intervention, net_worth  # noqa: E402

ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "report" / "figures"
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


def figure(rows: list[dict], summary: list[dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        from simulation_lab.plot_utils import apply_style

        apply_style()
    except Exception:
        pass

    figure, axes = plt.subplots(1, 3, figsize=(13, 4))
    colours = {("free", 0): "#c1440e", ("free", 1): "#294c60",
               ("richest_lends", 0): "#e8a87c", ("richest_lends", 1): "#7a9e9f"}
    names = {0: "ancienne technologie (A = 1,0)", 1: "nouvelle technologie (A = 1,5)"}

    # (a) effectif survivant de l'ancienne technologie, par graine et par règle
    seeds = sorted({row["seed"] for row in summary})
    width = 0.35
    for index, direction in enumerate(("free", "richest_lends")):
        counts = []
        for seed in seeds:
            match = [s for s in summary if s["seed"] == seed
                     and s["direction"] == direction and s["tech"] == 0]
            counts.append(match[0]["n"] if match else 0)
        axes[0].bar([s + (index - 0.5) * width for s in seeds], counts, width=width,
                    color=colours[(direction, 0)],
                    label="sens libre" if direction == "free" else "règle v1")
    axes[0].set_xticks(seeds)
    axes[0].set_xlabel("graine")
    axes[0].set_ylabel("entités de l'ancienne technologie encore vivantes")
    axes[0].set_title(r"(a) à $t_0 + 2000$, la cohorte d'origine", fontsize=9)
    axes[0].legend(fontsize=7)

    # (b) position nette contre capital, état final, sens libre
    subset = [r for r in rows if r["direction"] == "free" and r["seed"] == seeds[0]]
    for tech in (1, 0):
        group = [r for r in subset if r["tech"] == tech]
        if not group:
            continue
        axes[1].scatter([r["K"] for r in group], [r["net_position"] for r in group],
                        s=18 if tech == 0 else 5, alpha=0.85 if tech == 0 else 0.25,
                        color=colours[("free", tech)], label=names[tech],
                        zorder=3 if tech == 0 else 1)
    axes[1].axhline(0.0, color="black", lw=0.8)
    axes[1].set_xscale("symlog")
    axes[1].set_xlabel("capital $K$")
    axes[1].set_ylabel("position nette (créances $-$ dettes)")
    axes[1].set_title("(b) qui détient les créances, sens libre", fontsize=9)
    axes[1].legend(fontsize=7)

    # (c) part du revenu venant des intérêts
    labels, values, colour_list = [], [], []
    for direction in ("free", "richest_lends"):
        for tech in (0, 1):
            match = [s for s in summary if s["direction"] == direction and s["tech"] == tech]
            if not match:
                continue
            labels.append(("libre" if direction == "free" else "v1") + f"\ntech {tech}")
            values.append(100.0 * sum(m["part_du_revenu_en_interets"] for m in match) / len(match))
            colour_list.append(colours[(direction, tech)])
    axes[2].bar(range(len(labels)), values, color=colour_list)
    axes[2].set_xticks(range(len(labels)))
    axes[2].set_xticklabels(labels, fontsize=7)
    axes[2].set_ylabel("part du revenu venant des intérêts (%)")
    axes[2].set_title("(c) vivre de sa production, ou de l'intérêt", fontsize=9)

    for axis in axes:
        axis.grid(True, alpha=0.2)
    figure.suptitle(
        "Le régime que le sens libre rend possible — bras new_A150, état à $t_0+2000$"
    )
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(figure)


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
    figure(rows, summary, FIGURES / "survivors.png")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"# {len(jobs)} rejeux en {time.time() - started:.0f} s ; "
          f"tous reproduisent la campagne colonne par colonne")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
