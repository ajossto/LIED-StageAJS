"""Applique à TOUS les runs (exploration + confirmation) la régression
"réponse exponentielle délayée" (FOPDT) validée sur un exemple unique
(baseline seed0, voir scripts/renewal_worked_example.py et JOURNAL.md) :
extrait tau (temps caractéristique), t_delay, floor et R² pour les
courbes de persistance du décile supérieur (net worth, capital, revenu),
sur TOUTE la plage temporelle disponible de chaque run (pas seulement la
fenêtre de confirmation ]T/4, T]).

But : classer les runs selon que leur temps de convergence estimé
(t_delay + 3*tau) tombe avant ou après le burn-in du pipeline (T/4), ce
qui indique si la fenêtre d'analyse utilisée partout ailleurs
(exploration_summary.csv, confirmation_runs.csv) risque de mélanger
régime transitoire et régime stationnaire.

Ne modifie AUCUN run ni AUCUNE analyse existante : lecture seule des
snapshots bruts déjà sur disque, écrit uniquement
results/renewal_relaxation_all_runs.csv.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import interest_income  # noqa: E402

BURN_FRACTION = 0.25  # scripts/campaign.py:54
FIELDS = (("nw", "net_worth"), ("K", "capital"), ("income", "income"))
OUT_CSV = ROOT / "results" / "renewal_relaxation_all_runs.csv"

FIELDNAMES = [
    "campaign", "label", "seed", "T", "burn_in", "field",
    "n_snapshots", "t0", "t_last",
    "fit_ok", "floor", "tau", "t_delay", "r2", "t_converge",
    "transient_covers_burnin",
]


def persistence_curve(snaps, field: str) -> tuple[np.ndarray, np.ndarray]:
    t0, snap0 = snaps[0]
    key0 = snap0[field]
    threshold0 = np.quantile(key0, 0.90)
    base_ids = set(snap0["id"][key0 >= threshold0].tolist())
    n0 = len(base_ids)
    ts, ys = [], []
    for t, snap in snaps:
        current_key = snap[field]
        current_threshold = np.quantile(current_key, 0.90)
        current_top = set(snap["id"][current_key >= current_threshold].tolist())
        persistence = len(base_ids & current_top) / max(1, n0)
        ts.append(t)
        ys.append(persistence)
    return np.array(ts, dtype=float), np.array(ys, dtype=float)


def fopdt(t, floor, tau, t_delay, t0):
    dt = t - t0
    return np.where(dt <= t_delay, 1.0, floor + (1.0 - floor) * np.exp(-(dt - t_delay) / tau))


def fit_fopdt(t: np.ndarray, y: np.ndarray, t0: float) -> dict:
    def model(tt, floor, tau, t_delay):
        return fopdt(tt, floor, tau, t_delay, t0)

    span = max(t.max() - t0, 1.0)
    p0 = [max(float(y[-1]), 1e-3), span / 5, span / 20]
    bounds = ([0.0, 1.0, 0.0], [1.0, span * 5, span])
    try:
        popt, _ = curve_fit(model, t, y, p0=p0, bounds=bounds, maxfev=20000)
    except (RuntimeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    floor, tau, t_delay = (float(v) for v in popt)
    y_pred = model(t, *popt)
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"ok": True, "floor": floor, "tau": tau, "t_delay": t_delay, "r2": r2}


def find_runs():
    for campaign_dir, campaign_name in ((ROOT / "results" / "campaign", "exploration"),
                                          (ROOT / "results" / "confirmation", "confirmation")):
        if not campaign_dir.exists():
            continue
        for label_dir in sorted(campaign_dir.iterdir()):
            if not label_dir.is_dir():
                continue
            for seed_dir in sorted(label_dir.iterdir()):
                if not seed_dir.is_dir() or not (seed_dir / "snapshots").exists():
                    continue
                yield campaign_name, label_dir.name, seed_dir


def main():
    rows = []
    for i, (campaign_name, label, seed_dir) in enumerate(find_runs()):
        seed = int(seed_dir.name.replace("seed", ""))
        snaps = interest_income.load_all_entity_snapshots(seed_dir)
        if len(snaps) < 5:
            continue
        t_all = [t for t, _ in snaps]
        t0, t_last = t_all[0], t_all[-1]
        T = t_last  # approximation : dernier snapshot enregistre (config.json a T exact si besoin)
        burn_in = BURN_FRACTION * T

        for field, field_name in FIELDS:
            t, y = persistence_curve(snaps, field)
            fit = fit_fopdt(t, y, t0)
            row = {
                "campaign": campaign_name, "label": label, "seed": seed, "T": T, "burn_in": burn_in,
                "field": field_name, "n_snapshots": len(snaps), "t0": t0, "t_last": t_last,
                "fit_ok": fit["ok"],
            }
            if fit["ok"]:
                t_converge = t0 + fit["t_delay"] + 3 * fit["tau"]
                row.update({
                    "floor": fit["floor"], "tau": fit["tau"], "t_delay": fit["t_delay"],
                    "r2": fit["r2"], "t_converge": t_converge,
                    "transient_covers_burnin": t_converge > burn_in,
                })
            else:
                row.update({"floor": None, "tau": None, "t_delay": None, "r2": None,
                             "t_converge": None, "transient_covers_burnin": None})
            rows.append(row)
        if (i + 1) % 20 == 0:
            print(f"[{i+1}] {campaign_name}/{label}/seed{seed} traite", flush=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} lignes ecrites dans {OUT_CSV}")


if __name__ == "__main__":
    main()
