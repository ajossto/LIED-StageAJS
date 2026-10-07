"""Caracterisation directe de l'exposant de queue (existence de la loi de
Pareto acquise par hypothese -- decision utilisateur du 2026-08-06, suite
a l'echec de calculabilite du critere 1 revise, voir JOURNAL.md §20).

Ne teste plus rien : agrege alpha0 (seuil KS) et son ecart-type bootstrap
(deja calcules par admissibility_rollout.py, KS re-scanne a chaque
tirage) en TROIS composantes de variance gardees SEPAREES (pas de SE
unique fusionnee -- elles repondent a des questions differentes) :

- within-snapshot  : ecart-type bootstrap de alpha sur UN instantane
  (precision de lecture d'une seule coupe transversale)
- between-snapshot : dispersion de alpha ENTRE les instantanes
  selectionnes d'un meme run (mouvement reel dans le temps) --
  indefinie pour les runs "severes" (1 seul instantane)
- between-seed      : dispersion de la moyenne de run ENTRE graines
  d'une meme cellule (reproductibilite)

Champ d'application : uniquement int_in (intérêts reçus), pas income_net
-- confirme explicitement par l'utilisateur (2026-08-06)."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ADM_CSV = ROOT / "results" / "admissibility_all_runs.csv"
OUT_RUN_CSV = ROOT / "results" / "alpha_characterization_runs.csv"
OUT_CELL_CSV = ROOT / "results" / "alpha_characterization_cells.csv"


def main():
    rows = [r for r in csv.DictReader(open(ADM_CSV)) if r.get("alpha0") not in (None, "", "None")]

    by_run = defaultdict(list)
    for r in rows:
        key = (r["campaign"], r["label"], int(r["seed"]))
        by_run[key].append(r)

    run_rows = []
    for (campaign, label, seed), rs in sorted(by_run.items()):
        alphas = np.array([float(r["alpha0"]) for r in rs])
        boot_sds = np.array([float(r["alpha_boot_sd"]) for r in rs if r.get("alpha_boot_sd") not in (None, "", "None")])
        classification = rs[0]["classification"]
        n_selected = len(rs)
        within_sd = float(np.mean(boot_sds)) if len(boot_sds) else None
        between_sd = float(np.std(alphas, ddof=1)) if n_selected >= 2 else None
        run_rows.append({
            "campaign": campaign, "label": label, "seed": seed,
            "classification": classification, "n_selected": n_selected,
            "alpha_mean": float(np.mean(alphas)),
            "within_snapshot_sd": within_sd,
            "between_snapshot_sd": between_sd,
        })

    with open(OUT_RUN_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(run_rows[0].keys()))
        w.writeheader()
        w.writerows(run_rows)

    by_cell = defaultdict(list)
    for r in run_rows:
        by_cell[(r["campaign"], r["label"])].append(r)

    cell_rows = []
    for (campaign, label), rs in sorted(by_cell.items()):
        alpha_means = np.array([r["alpha_mean"] for r in rs])
        within_sds = [r["within_snapshot_sd"] for r in rs if r["within_snapshot_sd"] is not None]
        between_sds = [r["between_snapshot_sd"] for r in rs if r["between_snapshot_sd"] is not None]
        n_seeds = len(rs)
        between_seed_sd = float(np.std(alpha_means, ddof=1)) if n_seeds >= 2 else None
        classification = rs[0]["classification"]
        cell_rows.append({
            "campaign": campaign, "label": label, "n_seeds": n_seeds,
            "classification": classification,
            "alpha_cell_mean": float(np.mean(alpha_means)),
            "between_seed_sd": between_seed_sd,
            "mean_within_snapshot_sd": float(np.mean(within_sds)) if within_sds else None,
            "mean_between_snapshot_sd": float(np.mean(between_sds)) if between_sds else None,
        })

    with open(OUT_CELL_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cell_rows[0].keys()))
        w.writeheader()
        w.writerows(cell_rows)

    print(f"{len(run_rows)} runs -> {OUT_RUN_CSV}")
    print(f"{len(cell_rows)} cellules -> {OUT_CELL_CSV}")

    # le ratio critique signale par la revue : within-snapshot vs between-seed
    all_within = [r["within_snapshot_sd"] for r in run_rows if r["within_snapshot_sd"] is not None]
    all_between_seed = [c["between_seed_sd"] for c in cell_rows if c["between_seed_sd"] is not None]
    all_between_snap = [r["between_snapshot_sd"] for r in run_rows if r["between_snapshot_sd"] is not None]
    print(f"\nwithin-snapshot SD  : mean={np.mean(all_within):.3f} median={np.median(all_within):.3f} "
          f"(n={len(all_within)})")
    print(f"between-snapshot SD : mean={np.mean(all_between_snap):.3f} median={np.median(all_between_snap):.3f} "
          f"(n={len(all_between_snap)})")
    print(f"between-seed SD (cellule) : mean={np.mean(all_between_seed):.3f} median={np.median(all_between_seed):.3f} "
          f"(n={len(all_between_seed)})")
    print(f"\nratio within-snapshot / between-seed (moyennes) : "
          f"{np.mean(all_within)/np.mean(all_between_seed):.2f}")


if __name__ == "__main__":
    main()
