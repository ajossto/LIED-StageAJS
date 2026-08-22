"""Porte de sortie du lot A : le coût par pas est-il redevenu linéaire en T ?

Ce que mesure ce script
-----------------------
Le moteur v1 (`m4_3live_credit_soc/m4_3live/model.py`, LU et non modifié)
laisse dans `LoanBook.by_borrower` une clef à ensemble vide par entité morte,
et la phase de service des intérêts itère sur TOUTES les clefs. Le nombre de
clefs croît donc comme le nombre d'entités jamais créées, soit environ λ·t :
le coût *par pas* croît linéairement en t et le coût *total* d'un run croît
comme λT²/2.

Le moteur v2 purge la clef au moment de la mort (`LoanBook.forget`,
`m4_3live_v2/model.py`). On compare donc, à configuration et graine
identiques :

- le temps de mur de chaque pas (`seconds`) ;
- le nombre de clefs du carnet (`book_keys`), qui est le mécanisme lui-même.

Les deux moteurs tournent dans deux processus séparés, en parallèle, pour que
la mesure de l'un ne soit pas polluée par la charge de l'autre — chacun a son
cœur. Sorties : `results/analysis/cost_profile.csv` (une ligne par pas et par
moteur) et `report/figures/cost_profile.png`.

    python3 scripts/cost_profile.py [--steps 4000] [--seed 0]
"""

from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUPYTER = ROOT.parent
V1_ROOT = JUPYTER / "m4_3live_credit_soc"

ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "report" / "figures"

#: Régime de référence des deux lignées (`scripts/campaign.py`, BASE).
BASE = dict(gamma=0.5, A=1.0, lam=30.0, delta=0.01, sigma=0.01, K0=25.0,
            pop_max=30_000, rate_rule="marginal", kernel_policy="exact_lut")


def _profile(engine: str, steps: int, seed: int) -> list[dict]:
    """Exécute `steps` pas et retourne le temps et la taille du carnet par pas."""
    if engine == "v1":
        sys.path.insert(0, str(V1_ROOT))
        from m4_3live.model import Config, Simulation  # type: ignore
    else:
        sys.path.insert(0, str(ROOT))
        from m4_3live_v2.model import Config, Simulation  # type: ignore

    known = set(Config.__dataclass_fields__)
    config = Config(**{k: v for k, v in BASE.items() if k in known}, seed=seed, T=steps)
    simulation = Simulation(config)
    rows = []
    while simulation.t < steps and simulation.status == "ok":
        started = time.perf_counter()
        simulation.step()
        elapsed = time.perf_counter() - started
        rows.append(
            {
                "engine": engine,
                "t": simulation.t,
                "seconds": elapsed,
                "book_keys": len(simulation.book.by_borrower),
                "n_loans": len(simulation.book),
                "pop": simulation.series[-1]["pop"],
            }
        )
    return rows


def _worker(args) -> list[dict]:
    return _profile(*args)


def median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return float("nan")
    middle = n // 2
    return ordered[middle] if n % 2 else 0.5 * (ordered[middle - 1] + ordered[middle])


def summarise(rows: list[dict], steps: int) -> dict:
    """Coût médian par pas sur la première et la dernière tranche de 200 pas.

    On prend la MÉDIANE et non la moyenne : un pas isolé peut être ralenti par
    l'ordonnanceur du système, et une moyenne sur 200 pas en garde la trace.
    """
    early = [row["seconds"] for row in rows if 10 < row["t"] <= 210]
    late = [row["seconds"] for row in rows if steps - 200 < row["t"] <= steps]
    m_early, m_late = median(early), median(late)
    return {
        "engine": rows[0]["engine"],
        "median_s_t10_210": m_early,
        "median_s_last200": m_late,
        "growth": m_late / m_early if m_early > 0 else float("nan"),
        "book_keys_final": rows[-1]["book_keys"],
        "pop_final": rows[-1]["pop"],
        "n_loans_final": rows[-1]["n_loans"],
        "total_seconds": sum(row["seconds"] for row in rows),
    }


def figure(rows: list[dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        sys.path.insert(0, str(JUPYTER))
        from simulation_lab.plot_utils import apply_style

        apply_style()
    except Exception:
        pass

    colours = {"v1": "#c1440e", "v2": "#294c60"}
    labels = {"v1": "v1 (clefs mortes conservées)", "v2": "v2 (purge à la mort)"}
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))

    for engine in ("v1", "v2"):
        subset = [row for row in rows if row["engine"] == engine]
        if not subset:
            continue
        steps = [row["t"] for row in subset]
        seconds = [row["seconds"] for row in subset]
        window = 101
        smooth = [
            median(seconds[max(0, i - window // 2): i + window // 2 + 1])
            for i in range(len(seconds))
        ]
        axes[0].plot(steps, smooth, color=colours[engine], lw=1.2, label=labels[engine])
        axes[1].plot(steps, [row["book_keys"] for row in subset],
                     color=colours[engine], lw=1.2, label=labels[engine])

    axes[0].set_title("coût d'un pas (médiane glissante sur 101 pas)", fontsize=9)
    axes[0].set_xlabel("t (pas)")
    axes[0].set_ylabel("secondes par pas")
    axes[1].set_title("clefs du carnet parcourues à la phase d'intérêts", fontsize=9)
    axes[1].set_xlabel("t (pas)")
    axes[1].set_ylabel("len(by_borrower)")
    for axis in axes:
        axis.grid(True, alpha=0.2)
        axis.legend(fontsize=7)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(figure)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    ANALYSIS.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with mp.Pool(processes=2) as pool:
        results = pool.map(_worker, [("v1", args.steps, args.seed), ("v2", args.steps, args.seed)])
    rows = [row for chunk in results for row in chunk]

    with open(ANALYSIS / "cost_profile.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = [summarise(chunk, args.steps) for chunk in results]
    with open(ANALYSIS / "cost_profile_summary.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    figure(rows, FIGURES / "cost_profile.png")

    for row in summary:
        print(
            f"{row['engine']} : {row['median_s_t10_210']*1000:.1f} ms/pas au début, "
            f"{row['median_s_last200']*1000:.1f} ms/pas à la fin "
            f"(×{row['growth']:.3f}) ; {row['book_keys_final']} clefs pour "
            f"{row['pop_final']} vivantes ; {row['total_seconds']:.0f} s au total",
            flush=True,
        )
    print(f"# {args.steps} pas × 2 moteurs en {time.time() - started:.0f} s de mur")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
