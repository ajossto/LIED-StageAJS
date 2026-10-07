"""Sonde de calculabilité AVANT reconstruction complète : le critère 1
révisé (seuil x2 au lieu de seuil/2, cf. discussion utilisateur du
2026-08-06) est-il seulement calculable sur les instantanés qui seront
réellement utilisés (window_selection.csv, snapshots légers post-3.tau +
dernier instantané pour les sévères) ?

N'écrit ni verdict ni CSV agrégé -- juste la distribution de n_tail au
seuil x2 face aux deux planchers en jeu : 80 (utilisé par campaign.py
pour le scan KS primaire) et 20 (plancher precedent, trop permissif,
de _alpha_hill_at_threshold avant correctif). Decide si l'etape 2
(reconstruction complete) a un sens tel quel ou si le verdict honnete
est "non calculable" plutot que "passe/echoue"."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import interest_income  # noqa: E402
import tail_test  # noqa: E402

WINDOW_CSV = ROOT / "results" / "window_selection.csv"
MIN_N_PIPELINE = 80


def run_dir_for(campaign: str, label: str, seed: int) -> Path:
    base = ROOT / "results" / ("campaign" if campaign == "exploration" else "confirmation")
    return base / label / f"seed{seed}"


def main():
    rows = list(csv.DictReader(open(WINDOW_CSV)))
    n_tail_2x = []
    n_tail_at_seuil = []
    n_fits_attempted = 0
    n_fits_ok_seuil = 0
    n_fits_ok_2x_floor80 = 0
    n_fits_ok_2x_floor20 = 0
    per_run_summary = []

    for r in rows:
        campaign, label, seed = r["campaign"], r["label"], int(r["seed"])
        times = [int(float(t)) for t in r["selected_times"].split(";")]
        run_dir = run_dir_for(campaign, label, seed)
        snaps = dict(interest_income.load_all_entity_snapshots(run_dir, t_min=min(times), t_max=max(times)))

        run_n2x = []
        for t in times:
            if t not in snaps:
                continue
            values = snaps[t]["int_in"]
            p0, positive = interest_income.zero_mass_and_positive(values)
            n_fits_attempted += 1
            best = tail_test.fit_powerlaw_xmin(positive, min_tail=MIN_N_PIPELINE)
            if best is None:
                continue
            n_fits_ok_seuil += 1
            n_tail_at_seuil.append(best["n_tail"])
            x_min2 = best["x_min"] * 2.0
            tail2 = positive[positive >= x_min2]
            n2 = len(tail2)
            n_tail_2x.append(n2)
            run_n2x.append(n2)
            if n2 >= MIN_N_PIPELINE:
                n_fits_ok_2x_floor80 += 1
            if n2 >= 20:
                n_fits_ok_2x_floor20 += 1

        if run_n2x:
            per_run_summary.append((campaign, label, seed, r["classification"], run_n2x))

    n_tail_2x = np.array(n_tail_2x)
    n_tail_at_seuil = np.array(n_tail_at_seuil)
    print(f"instantanes tentes : {n_fits_attempted}")
    print(f"fits ok au seuil KS (n_tail>={MIN_N_PIPELINE}) : {n_fits_ok_seuil}")
    print(f"  n_tail au seuil KS : mean={n_tail_at_seuil.mean():.0f} "
          f"median={np.median(n_tail_at_seuil):.0f} min={n_tail_at_seuil.min()} max={n_tail_at_seuil.max()}")
    print(f"\nparmi ceux-la, au seuil x2 :")
    print(f"  n_tail x2 : mean={n_tail_2x.mean():.1f} median={np.median(n_tail_2x):.0f} "
          f"min={n_tail_2x.min()} max={n_tail_2x.max()}")
    print(f"  n_tail(x2) >= 80 (plancher pipeline) : {n_fits_ok_2x_floor80}/{n_fits_ok_seuil} "
          f"({100*n_fits_ok_2x_floor80/n_fits_ok_seuil:.0f}%)")
    print(f"  n_tail(x2) >= 20 (ancien plancher, trop permissif) : {n_fits_ok_2x_floor20}/{n_fits_ok_seuil} "
          f"({100*n_fits_ok_2x_floor20/n_fits_ok_seuil:.0f}%)")
    print(f"  n_tail(x2) < 20 (fit impossible meme avec l'ancien plancher) : "
          f"{n_fits_ok_seuil - n_fits_ok_2x_floor20}/{n_fits_ok_seuil}")

    print("\nquelques exemples (campaign, label, seed, classification, [n_tail x2 par instantane]):")
    for row in per_run_summary[:5]:
        print(" ", row)
    print("  ...")
    worst = sorted(per_run_summary, key=lambda r: min(r[4]))[:5]
    print("pires cas (n_tail x2 le plus faible) :")
    for row in worst:
        print(" ", row)


if __name__ == "__main__":
    main()
