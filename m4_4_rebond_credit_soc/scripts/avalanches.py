"""Lot D — avalanches et branchement, et la réconciliation inter-lignées.

Ce que le lot D doit trancher (plan §5, §3.2) : l'écart entre le rapport de
branchement de cette lignée, b₁ ≈ 0,79, et celui de M4B, 0,297 — « expliqué,
ou déclaré ouvert avec ce qui a été essayé ».

Ce script mesure, sur chaque run et chaque fenêtre :

- les DEUX estimateurs de b (racines et descendance), déjà réconciliés au
  lot A, ici sur les 12 graines de la campagne ;
- la susceptibilité ⟨s²⟩/⟨s⟩ et la profondeur, dans les définitions EXACTES
  de M4B (`lib_metrics.window_avalanche_metrics`), pour que la comparaison
  porte sur les mêmes quantités ;
- la distribution des tailles, ajustée par une LOI DE PUISSANCE SEULE.
  Consigne héritée et toujours en vigueur (plan §2.3) : sur les tailles
  d'avalanches, aucune analyse de coupure. M4B a montré que la loi est
  tronquée PARTOUT ; ajuster une coupure ici ne ferait que remesurer la
  taille finie du système.
- les diagnostics de séparabilité que M4 fable impose : racines/taille et
  profondeur, sans lesquels des grappes synchronisées passent pour des
  cascades.

    python3 scripts/avalanches.py [--dirs …] [--t-min 3000] [--t-max 4000]
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
from m4_4.live import read_edges  # noqa: E402
from m4_4.tails import fit_powerlaw_discrete  # noqa: E402

T_CRITICAL = 2.201


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def avalanche_metrics(rows: list[dict], t_min: float, t_max: float,
                      pop_mean: float) -> dict:
    """Métriques d'avalanche dans les définitions de M4B."""
    sizes, depth, roots, volume = [], [], [], []
    for row in rows:
        t = float(row["t"])
        if not (t_min < t <= t_max):
            continue
        sizes.append(int(row["size"]))
        depth.append(int(row["depth"]))
        roots.append(int(row["n_roots"]))
        volume.append(float(row["volume_j"]))
    if not sizes:
        return {"n_events": 0, "identifiable": False}
    sizes = np.array(sizes, dtype=float)
    roots = np.array(roots, dtype=float)
    total = float(sizes.sum())
    payload = {
        "n_events": int(sizes.size),
        "rate_per_step": float(sizes.size / max(1.0, t_max - t_min)),
        "size_mean": float(sizes.mean()),
        "size_q50": float(np.quantile(sizes, 0.5)),
        "size_q90": float(np.quantile(sizes, 0.9)),
        "size_q99": float(np.quantile(sizes, 0.99)),
        "size_max": float(sizes.max()),
        "size_max_over_pop": float(sizes.max() / pop_mean) if pop_mean > 0 else float("nan"),
        "susceptibility": float((sizes**2).mean() / sizes.mean()),
        "branching_ratio_m4b": float(1.0 - roots.sum() / total) if total else float("nan"),
        "roots_per_avalanche": float(roots.mean()),
        "roots_over_size": float(roots.sum() / total) if total else float("nan"),
        "depth_mean": float(np.mean(depth)),
        "depth_max": float(np.max(depth)),
        "frac_size_ge2": float((sizes >= 2).mean()),
        "volume_mean_j": float(np.mean(volume)),
        "volume_max_j": float(np.max(volume)),
    }
    fit = fit_powerlaw_discrete(sizes)
    payload["identifiable"] = fit is not None
    if fit:
        payload.update({
            "alpha_size": fit["alpha"],
            "alpha_size_se": fit["se"],
            "alpha_n_tail": fit["n_tail"],
        })
    return payload


def student(values) -> dict:
    clean = [v for v in values if v == v and math.isfinite(v)]
    n = len(clean)
    if n == 0:
        return {"n": 0, "mean": float("nan"), "ci95": float("nan")}
    mean = sum(clean) / n
    if n < 2:
        return {"n": n, "mean": mean, "ci95": float("nan")}
    variance = sum((v - mean) ** 2 for v in clean) / (n - 1)
    return {"n": n, "mean": mean, "se": math.sqrt(variance / n),
            "ci95": T_CRITICAL * math.sqrt(variance / n)}


def collect(directory: Path, label: str, t_min: float, t_max: float) -> dict | None:
    series_path = directory / "series.csv"
    avalanche_path = directory / "avalanches.csv"
    if not series_path.exists() or not avalanche_path.exists():
        return None
    series = read_csv(series_path)
    window = [row for row in series if t_min < float(row["t"]) <= t_max]
    pop_mean = sum(float(row["pop"]) for row in window) / len(window)
    row = {"arm": label, "seed": int(directory.name[4:]), "pop_mean": pop_mean}
    row.update(avalanche_metrics(read_csv(avalanche_path), t_min, t_max, pop_mean))
    edges = directory / "loss_edges.npz"
    if edges.exists():
        both = reconcile(series, read_edges(edges), t_min, t_max)
        row["b1"] = both["b1"]
        row["b2"] = both["b2"]
        row["gap_b2_b1"] = both["gap_b2_b1"]
        row["multi_parent_share"] = both["multi_parent_share"]
        row["mean_in_degree"] = both["mean_in_degree"]
        row["closes"] = both["closes"]
    return row


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dirs", nargs="*", type=Path, default=[
        ROOT / "results" / "campaign" / "arms" / "free",
        ROOT / "results" / "campaign" / "bargain",
    ])
    parser.add_argument("--t-min", type=float, default=3000)
    parser.add_argument("--t-max", type=float, default=4000)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    args = parser.parse_args(argv[1:])

    rows = []
    for root in args.dirs:
        if not root.exists():
            continue
        family = root.name
        for arm_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            for run_dir in sorted(path for path in arm_dir.iterdir() if path.is_dir()):
                row = collect(run_dir, f"{family}/{arm_dir.name}", args.t_min, args.t_max)
                if row:
                    rows.append(row)
    assert rows, "aucune avalanche trouvée — les runs sont-ils instrumentés ?"

    args.out.mkdir(parents=True, exist_ok=True)
    fieldnames = ["arm", "seed"] + sorted({k for r in rows for k in r} - {"arm", "seed"})
    with open(args.out / "lotD_avalanches.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)

    arms = sorted({row["arm"] for row in rows})
    quantities = [k for k in fieldnames
                  if k not in ("arm", "seed", "closes", "identifiable")]
    summary = {
        arm: {q: student([r.get(q, float("nan")) for r in rows if r["arm"] == arm])
              for q in quantities}
        for arm in arms
    }
    (args.out / "lotD_avalanches.json").write_text(
        json.dumps({"window": [args.t_min, args.t_max], "summary": summary},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    headline = ("b1", "b2", "gap_b2_b1", "multi_parent_share", "susceptibility",
                "size_mean", "size_max", "depth_mean", "alpha_size",
                "roots_over_size", "frac_size_ge2", "rate_per_step")
    print(f"# fenêtre ]{args.t_min:g}, {args.t_max:g}]")
    width = max(len(a) for a in arms) + 2
    print("bras".ljust(width) + "".join(f"{q[:11]:>13}" for q in headline))
    for arm in arms:
        line = arm.ljust(width)
        for quantity in headline:
            value = summary[arm][quantity]["mean"]
            line += f"{value:>13.4g}" if value == value else f"{'—':>13}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
