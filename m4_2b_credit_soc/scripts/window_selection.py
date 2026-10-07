"""Redéfinit la fenêtre d'analyse "régime stationnaire" par run, à partir
des tau/t_delay du renouvellement (fig8/fig9, results/renewal_relaxation_
all_runs.csv, champ 'income' -- la quantité pertinente pour la régression
alpha), au lieu du burn-in fixe T/4 utilisé partout jusqu'ici.

Règle (validée par l'utilisateur, 2026-08-06) :
- cellule "légère" (t_conv = t0+t_delay+3·tau < T, marge disponible) :
  fenêtre = [t_conv, T], instantanés gardés espacés d'au moins ~tau (pour
  limiter l'autocorrélation entre points -- la composition du réseau/de
  l'élite ne s'est pas renouvelée entre deux instantanés plus proches que
  tau) ;
- cellule "sévère" (t_conv >= T, pas de marge -- ex. K0_2000) : on ne
  garde QUE le dernier instantané disponible, avec un signal explicite
  que ce n'est pas un régime stationnaire établi (voir aussi la question
  sur la reprise de simulation, JOURNAL.md).

N'effectue aucun ajustement statistique lui-même : produit uniquement la
liste des instantanés à utiliser par run, pour que campaign.py (ou un
script d'analyse dédié) les consomme ensuite.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELAX_CSV = ROOT / "results" / "renewal_relaxation_all_runs.csv"
OUT_CSV = ROOT / "results" / "window_selection.csv"
SNAPSHOT_CADENCE = 25  # scripts/campaign.py : snapshot_every par defaut


def load_income_relaxation():
    rows = {}
    for r in csv.DictReader(open(RELAX_CSV)):
        if r["field"] != "income" or r["fit_ok"] != "True":
            continue
        key = (r["campaign"], r["label"], int(r["seed"]))
        rows[key] = r
    return rows


def select_snapshots(t0: float, t_delay: float, tau: float, t_last: float,
                      cadence: int = SNAPSHOT_CADENCE):
    """Renvoie (classification, t_window_start, instantanés retenus)."""
    t_conv = t0 + t_delay + 3 * tau
    if t_conv >= t_last:
        return "severe", None, [t_last]

    spacing_native = max(1, round(tau / cadence))
    spacing_steps = spacing_native * cadence
    all_times = list(range(int(t0), int(t_last) + 1, cadence))
    window_times = [t for t in all_times if t >= t_conv]
    if not window_times:
        return "severe", None, [t_last]

    selected = [window_times[0]]
    for t in window_times[1:]:
        if t - selected[-1] >= spacing_steps:
            selected.append(t)
    return "mild", t_conv, selected


def main():
    relax = load_income_relaxation()
    out_rows = []
    for (campaign, label, seed), r in sorted(relax.items()):
        t0, t_delay, tau = float(r["t0"]), float(r["t_delay"]), float(r["tau"])
        t_last = float(r["t_last"])
        span = t_last - t0
        degenerate = tau > span
        classification, t_start, selected = select_snapshots(t0, t_delay, tau, t_last)
        out_rows.append({
            "campaign": campaign, "label": label, "seed": seed,
            "t0": t0, "t_delay": t_delay, "tau": tau, "t_last": t_last,
            "degenerate_fit": degenerate,
            "classification": "severe" if degenerate else classification,
            "window_start": t_start if not degenerate else None,
            "n_selected": len(selected) if not degenerate else 1,
            "selected_times": ";".join(str(t) for t in (selected if not degenerate else [int(t_last)])),
        })

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    n_mild = sum(1 for r in out_rows if r["classification"] == "mild")
    n_severe = sum(1 for r in out_rows if r["classification"] == "severe")
    print(f"{len(out_rows)} runs : {n_mild} legers (fenetre post-convergence), "
          f"{n_severe} severes (dernier instantane seul)")
    print(f"ecrit : {OUT_CSV}")

    print("\nExemples :")
    for camp, label, seed in [("exploration", "baseline", 0), ("exploration", "K0_2000", 0),
                                ("confirmation", "gamma_comp_0.6667", 10)]:
        row = next((r for r in out_rows if r["campaign"] == camp and r["label"] == label
                     and r["seed"] == seed), None)
        if row:
            print(f"  {camp}/{label}/seed{seed} : {row['classification']}, "
                  f"n_selected={row['n_selected']}, temps={row['selected_times']}")


if __name__ == "__main__":
    main()
