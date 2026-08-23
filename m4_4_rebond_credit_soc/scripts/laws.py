"""Lots C0 et C — couverture de queue, puis classes de lois coordonnées.

C0 : LA COUVERTURE, avant tout le reste
----------------------------------------
Ce qui a bloqué M4.2B n'est pas la finesse du critère mais le NOMBRE DE
POINTS dans la queue extrême : `n_tail` médian 113 au seuil optimal, 17 au
seuil doublé, 2 % des instantanés restant admissibles. Reconduire le même
protocole, c'est reproduire l'impasse avec un moteur plus récent.

Le mode `--pilot` mesure donc `n_tail` par instantané AVANT d'engager quoi
que ce soit, et le confronte à une cible dérivée — non choisie — de la
précision voulue sur α̂ :

    SE(α̂) ≈ (α̂ − 1)/√n_tail      (erreur-type asymptotique de Hill)

À α̂ ≈ 3 et pour une erreur-type de 0,10, il faut n_tail ≈ 400. Le bootstrap
à seuil re-balayé élargit ce chiffre d'un facteur ≈ 1,6 mesuré
(`tests/test_tails.py`), donc l'erreur-type honnête est plutôt 0,16.

C : LES CLASSES DE LOIS, COORDONNÉES
-------------------------------------
Revenu d'intérêt et valeur nette, par groupe (§4.5) et par instantané, avec
les trois échelles d'incertitude JAMAIS FUSIONNÉES :

- intra-instantané : bootstrap à seuil re-balayé, sur un instantané ;
- inter-instantanés : écart-type des α̂ sur les instantanés d'un run ;
- inter-graines : écart-type des moyennes de run.

M4.2B mesure la première ≈ 3,7 fois la troisième. Les confondre ferait
passer un α̂ d'instantané pour une mesure de cellule.

RIEN ICI NE VALIDE L'EXISTENCE D'UNE QUEUE. M4.2B a montré que la question
n'est pas décidable à ce volume ; ce programme la pose en hypothèse et
caractérise α̂. Le test `tests/test_tails.py` ajoute une raison de plus : la
log-normale tronquée CONTIENT la loi de puissance à la limite σ → ∞, donc le
test de Vuong sur ce couple n'a structurellement pas de pouvoir.

    python3 scripts/laws.py --pilot            # C0, une cellule
    python3 scripts/laws.py                    # C, toute la campagne
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

from m4_4.groups import NET_POSITIONS, partitions  # noqa: E402
from m4_4.live import read_panels  # noqa: E402
from m4_4.tails import (  # noqa: E402
    N_MIN_TAIL,
    bootstrap_tail,
    compare_tail_families,
    fit_composite,
    fit_tail,
)

T_CRITICAL = 2.201
#: Cible de couverture, DÉRIVÉE : erreur-type asymptotique de Hill ≤ 0,10 à
#: α̂ ≈ 3, soit √n ≥ (α̂−1)/0,10 = 20.
TARGET_N_TAIL = 400
TARGET_SE = 0.10
#: Grandeurs dont on suit la queue. `nw` est signée : on n'ajuste que sa
#: partie positive, et on le dit.
QUANTITIES = ("int_in", "nw", "K", "prod")


def groups_of(panel: dict) -> dict[str, np.ndarray]:
    """Masques de groupe, calculés sur le MÊME instantané (§4.5)."""
    parts = partitions(panel)
    masks = {"tous": np.ones(panel["id"].size, dtype=bool)}
    for index, name in enumerate(NET_POSITIONS):
        masks[f"net:{name}"] = parts["net_position"] == index
    for tech in np.unique(panel["tech"]):
        masks[f"tech:{int(tech)}"] = panel["tech"] == tech
    for decile in (0, 4, 9):
        masks[f"Kdec:{decile}"] = parts["K_decile"] == decile
    for decile in (0, 9):
        masks[f"age:{decile}"] = parts["age_decile"] == decile
    return masks


def snapshot_fits(panel: dict, quantities=QUANTITIES) -> list[dict]:
    rows = []
    for group, mask in groups_of(panel).items():
        for quantity in quantities:
            values = panel[quantity][mask]
            positive = values[values > 0]
            fit = fit_tail(positive)
            rows.append({
                "group": group,
                "quantity": quantity,
                "n_group": int(mask.sum()),
                "n_positive": int(positive.size),
                "alpha": fit["alpha"],
                "xmin": fit["xmin"],
                "n_tail": fit["n_tail"],
                "ks": fit["ks"],
                "se_hill": fit["se"],
            })
    return rows


def student(values) -> dict:
    clean = [v for v in values if v == v and math.isfinite(v)]
    n = len(clean)
    if n == 0:
        return {"n": 0, "mean": float("nan"), "sd": float("nan"), "ci95": float("nan")}
    mean = sum(clean) / n
    if n < 2:
        return {"n": n, "mean": mean, "sd": float("nan"), "ci95": float("nan")}
    variance = sum((v - mean) ** 2 for v in clean) / (n - 1)
    sd = math.sqrt(variance)
    return {"n": n, "mean": mean, "sd": sd, "ci95": T_CRITICAL * sd / math.sqrt(n)}


def load_snapshots(path: Path, t_min: float, t_max: float):
    panels = read_panels(path)
    times = np.unique(panels["t"])
    times = times[(times > t_min) & (times <= t_max)]
    for t in times:
        mask = panels["t"] == t
        yield int(t), {name: values[mask] for name, values in panels.items()
                       if name != "t"}


def pilot(path: Path, t_min: float, t_max: float, out: Path) -> int:
    """C0 — la couverture, mesurée sur une cellule."""
    rows = []
    for t, panel in load_snapshots(path, t_min, t_max):
        for row in snapshot_fits(panel):
            rows.append({"t": t, **row})
    assert rows, f"aucun panneau dans ]{t_min}, {t_max}] pour {path}"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "lotC0_coverage.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    payload = {"run": str(path), "window": [t_min, t_max],
               "n_snapshots": len({row["t"] for row in rows}),
               "target_n_tail": TARGET_N_TAIL, "target_se": TARGET_SE,
               "groups": {}}
    print(f"# C0 — couverture de queue sur {path.parent.name}, "
          f"{payload['n_snapshots']} instantanés")
    print(f"# cible dérivée : n_tail ≥ {TARGET_N_TAIL} pour SE(α̂) ≤ {TARGET_SE:.2f} à α̂ ≈ 3")
    print()
    header = f"{'groupe':<16}{'grandeur':<9}{'n_pos':>7}{'n_tail méd.':>13}{'α̂ méd.':>9}{'SE':>8}{'atteint':>9}"
    print(header)
    for group in sorted({row["group"] for row in rows}):
        for quantity in QUANTITIES:
            selected = [row for row in rows
                        if row["group"] == group and row["quantity"] == quantity]
            tails = [row["n_tail"] for row in selected if row["n_tail"] > 0]
            alphas = [row["alpha"] for row in selected if row["alpha"] == row["alpha"]]
            if not tails:
                continue
            median_tail = float(np.median(tails))
            median_alpha = float(np.median(alphas)) if alphas else float("nan")
            se = (median_alpha - 1.0) / math.sqrt(median_tail) if median_tail > 0 else float("nan")
            reached = median_tail >= TARGET_N_TAIL
            payload["groups"][f"{group}/{quantity}"] = {
                "n_positive_median": float(np.median([r["n_positive"] for r in selected])),
                "n_tail_median": median_tail,
                "n_tail_q10": float(np.quantile(tails, 0.1)),
                "alpha_median": median_alpha,
                "se_hill_at_median": se,
                "reaches_target": bool(reached),
            }
            print(f"{group:<16}{quantity:<9}"
                  f"{np.median([r['n_positive'] for r in selected]):>7.0f}"
                  f"{median_tail:>13.0f}{median_alpha:>9.3f}{se:>8.3f}"
                  f"{'oui' if reached else 'non':>9}")
    (out / "lotC0_coverage.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Le facteur d'échelle qu'il faudrait sur λ pour atteindre la cible.
    key = "tous/int_in"
    if key in payload["groups"]:
        current = payload["groups"][key]["n_tail_median"]
        factor = TARGET_N_TAIL / current if current > 0 else float("inf")
        print()
        print(f"  revenu d'intérêt, tous : n_tail médian {current:.0f} → "
              f"facteur {factor:.2f} sur l'effectif pour atteindre {TARGET_N_TAIL}")
        print(f"  soit λ ≈ {30 * factor:.0f} au lieu de 30, "
              f"pour un coût par run d'environ ×{factor:.1f}")
    return 0


def full(arms_dirs, t_min: float, t_max: float, out: Path, draws: int) -> int:
    """C — les classes de lois sur toute la campagne."""
    per_run_rows = []
    family_rows = []
    for root in arms_dirs:
        if not root.exists():
            continue
        for arm_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for run_dir in sorted(p for p in arm_dir.iterdir() if p.is_dir()):
                path = run_dir / "panels.npz"
                if not path.exists():
                    continue
                arm = f"{root.name}/{arm_dir.name}"
                seed = int(run_dir.name[4:])
                by_key: dict[tuple[str, str], list[dict]] = {}
                last_panel = None
                for _, panel in load_snapshots(path, t_min, t_max):
                    last_panel = panel
                    for row in snapshot_fits(panel):
                        by_key.setdefault((row["group"], row["quantity"]), []).append(row)
                for (group, quantity), fits in by_key.items():
                    alphas = [f["alpha"] for f in fits]
                    tails = [f["n_tail"] for f in fits]
                    statistics = student(alphas)
                    per_run_rows.append({
                        "arm": arm, "seed": seed, "group": group, "quantity": quantity,
                        "n_snapshots": len(fits),
                        "alpha_mean": statistics["mean"],
                        # ÉCHELLE 2 : inter-instantanés, à ne pas confondre
                        # avec l'incertitude d'un instantané.
                        "alpha_sd_inter_snapshot": statistics["sd"],
                        "n_tail_median": float(np.median(tails)),
                        "xmin_median": float(np.median([f["xmin"] for f in fits])),
                        "ks_median": float(np.median([f["ks"] for f in fits])),
                    })
                # ÉCHELLE 1 : intra-instantané, sur le DERNIER instantané du
                # run, avec le seuil re-balayé à chaque tirage. Et les
                # familles concurrentes, au même seuil.
                if last_panel is not None and draws:
                    for quantity in QUANTITIES:
                        values = last_panel[quantity]
                        positive = values[values > 0]
                        if positive.size < N_MIN_TAIL * 2:
                            continue
                        comparison = compare_tail_families(positive, draws=draws,
                                                           seed=seed)
                        if not comparison.get("identifiable"):
                            continue
                        composite = fit_composite(positive)
                        family_rows.append({
                            "arm": arm, "seed": seed, "quantity": quantity,
                            "alpha": comparison["powerlaw"]["alpha"],
                            "xmin": comparison["powerlaw"]["xmin"],
                            "n_tail": comparison["powerlaw"]["n_tail"],
                            "alpha_sd_intra_snapshot": comparison["bootstrap"]["alpha_sd"],
                            "lognormal_sigma": comparison["lognormal"]["sigma"],
                            "lognormal_degenerate": comparison["lognormal_degenerate"],
                            "vuong_pl_vs_ln": comparison["vuong_pl_vs_ln"]["z"],
                            "vuong_pl_vs_exp": comparison["vuong_pl_vs_exp"]["z"],
                            "aic_powerlaw": comparison["aic"]["powerlaw"],
                            "aic_lognormal": comparison["aic"]["lognormal"],
                            "aic_exponential": comparison["aic"]["exponential"],
                            "composite_T": composite.get("T", float("nan")),
                            "composite_x_b": composite.get("x_b", float("nan")),
                            "composite_alpha": composite.get("alpha", float("nan")),
                            "composite_aic": composite.get("aic", float("nan")),
                        })
    assert per_run_rows, "aucun panneau trouvé"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "lotC_alpha.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_run_rows[0]))
        writer.writeheader()
        writer.writerows(per_run_rows)
    if family_rows:
        with open(out / "lotC_families.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(family_rows[0]))
            writer.writeheader()
            writer.writerows(family_rows)

    # Résumé par bras/groupe/grandeur, avec les TROIS échelles côte à côte.
    summary: dict[str, dict] = {}
    keys = sorted({(r["arm"], r["group"], r["quantity"]) for r in per_run_rows})
    for arm, group, quantity in keys:
        selected = [r for r in per_run_rows if r["arm"] == arm
                    and r["group"] == group and r["quantity"] == quantity]
        across_seeds = student([r["alpha_mean"] for r in selected])
        intra = [r["alpha_sd_intra_snapshot"] for r in family_rows
                 if r["arm"] == arm and r["quantity"] == quantity]
        summary[f"{arm}|{group}|{quantity}"] = {
            "alpha_mean": across_seeds["mean"],
            # ÉCHELLE 3 : inter-graines.
            "alpha_sd_inter_seed": across_seeds["sd"],
            "alpha_ci95_inter_seed": across_seeds["ci95"],
            "alpha_sd_inter_snapshot_median": float(np.median(
                [r["alpha_sd_inter_snapshot"] for r in selected])),
            "alpha_sd_intra_snapshot_median": float(np.median(intra)) if intra else float("nan"),
            "n_tail_median": float(np.median([r["n_tail_median"] for r in selected])),
            "n_seeds": across_seeds["n"],
        }
    (out / "lotC_summary.json").write_text(
        json.dumps({"window": [t_min, t_max], "summary": summary},
                   indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"# C — {len(per_run_rows)} (bras, graine, groupe, grandeur), "
          f"{len(family_rows)} comparaisons de familles")
    print()
    print(f"{'bras|groupe|grandeur':<44}{'α̂':>8}{'σ graines':>11}"
          f"{'σ instant.':>12}{'σ intra':>10}{'n_tail':>9}")
    for key in sorted(summary):
        entry = summary[key]
        if entry["n_seeds"] < 2:
            continue
        print(f"{key[:43]:<44}{entry['alpha_mean']:>8.3f}"
              f"{entry['alpha_sd_inter_seed']:>11.3f}"
              f"{entry['alpha_sd_inter_snapshot_median']:>12.3f}"
              f"{entry['alpha_sd_intra_snapshot_median']:>10.3f}"
              f"{entry['n_tail_median']:>9.0f}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", action="store_true", help="mode C0")
    parser.add_argument("--run", type=Path, default=None,
                        help="cellule du pilote (défaut : control/seed0)")
    parser.add_argument("--dirs", nargs="*", type=Path, default=[
        ROOT / "results" / "campaign" / "arms" / "free",
        ROOT / "results" / "campaign" / "bargain",
    ])
    parser.add_argument("--t-min", type=float, default=3000)
    parser.add_argument("--t-max", type=float, default=4000)
    parser.add_argument("--draws", type=int, default=200)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analysis")
    args = parser.parse_args(argv[1:])

    if args.pilot:
        path = args.run or (ROOT / "results" / "campaign" / "arms" / "free"
                            / "control" / "seed0" / "panels.npz")
        return pilot(path, args.t_min, args.t_max, args.out)
    return full(args.dirs, args.t_min, args.t_max, args.out, args.draws)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
