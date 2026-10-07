"""Tableau de synthèse de la grille §6.5 + balayage k : statut démographique,
queue (alpha CSN, LR), corps (famille, med/mean), cascades. Sort un JSON et
un tableau texte pour le rapport de validation."""
import json

import numpy as np

from exp_common import RESULTS
from m2.analysis import (cascade_size_distribution, fit_body, fit_tail_csn,
                         lr_powerlaw_vs_lognormal)
from m2.metrics import load_series, load_snapshots


def pool_nw(snaps, lo=1500, hi=2000):
    vals = [s["nw"] for t, s in snaps.items() if lo <= t < hi and t % 50 == 0]
    return np.concatenate(vals) if vals else np.array([])


def summarize(run_id):
    run_dir = RESULTS / run_id
    with open(run_dir / "summary.json") as fh:
        summ = json.load(fh)
    row = dict(run=run_id, status=summ["status"], pop=summ["pop_final"],
               loans=summ["n_loans_final"])
    series = load_series(run_dir)
    if len(series) >= 1000:
        tail_rows = [s for s in series if s["t"] >= len(series) - 500]
        pop = np.array([s["pop"] for s in tail_rows], dtype=float)
        row["pop_slope_rel"] = float(np.polyfit(
            np.arange(len(pop)), pop, 1)[0]) * 1000.0 / max(np.mean(pop), 1)
        casc = cascade_size_distribution(series, t_min=500)
        if casc:
            row["deaths_mean"] = casc["mean"]
            row["deaths_max"] = casc["max"]
    snaps = load_snapshots(run_dir, t_min=1400)
    p = pool_nw(snaps)
    if len(p) > 500:
        body = fit_body(p)
        if body:
            row["body"] = body["best"]
            row["mm"] = body["med_over_mean"]
            row["dAIC_exp"] = body["delta_aic_expon"]
        fit = fit_tail_csn(p)
        if fit:
            row["alpha"] = fit["alpha"]
            row["xmin"] = fit["x_min"]
            lr = lr_powerlaw_vs_lognormal(p, fit["x_min"], fit["alpha"])
            if lr:
                row["lr_R"] = lr["R"]
                row["lr_p"] = lr["p"]
    return row


if __name__ == "__main__":
    run_ids = sorted(p.name for p in RESULTS.iterdir()
                     if p.is_dir() and (p / "summary.json").exists()
                     and (p.name.startswith("grid_") or p.name.startswith("ksweep_")))
    rows = [summarize(rid) for rid in run_ids]
    with open(RESULTS / "validation" / "grid_summary.json", "w") as fh:
        json.dump(rows, fh, indent=1, default=float)
    hdr = (f"{'run':32s} {'stat':10s} {'pop':>6s} {'slope':>7s} {'d/pas':>6s} "
           f"{'dmax':>4s} {'corps':>8s} {'m/m':>5s} {'alpha':>6s} {'LR':>7s} {'p':>7s}")
    print(hdr)
    for r in rows:
        print(f"{r['run']:32s} {r['status']:10s} {r['pop']:6d} "
              f"{r.get('pop_slope_rel', float('nan')):7.3f} "
              f"{r.get('deaths_mean', float('nan')):6.2f} "
              f"{r.get('deaths_max', 0):4d} "
              f"{r.get('body', '-'):>8s} {r.get('mm', float('nan')):5.2f} "
              f"{r.get('alpha', float('nan')):6.2f} {r.get('lr_R', float('nan')):7.1f} "
              f"{r.get('lr_p', float('nan')):7.4f}")
