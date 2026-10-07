"""Analyse des runs longs : dérive de l'exposant de queue par fenêtres de 500
pas sur [500, 6000). Compare nocredit (modèle nul) et cancel (crédit, carnet
stationnaire). Sort un JSON + un tableau texte."""
import json

import numpy as np

from exp_common import RESULTS
from m2.analysis import (bootstrap_tail_alpha, fit_body, fit_tail_csn,
                         fit_tail_fixed_xmin, lr_powerlaw_vs_lognormal)
from m2.metrics import load_snapshots

RUNS = ("long_nocredit_s0", "long_cancel_s0", "long_nocredit_s1", "long_cancel_s1")
WINDOWS = [(lo, lo + 500) for lo in range(500, 6000, 500)]
VAR = "nw"


def pool(snaps, lo, hi):
    vals = [s[VAR] for t, s in snaps.items() if lo <= t < hi and t % 50 == 0]
    return np.concatenate(vals) if vals else np.array([])


def analyze(run_id):
    snaps = load_snapshots(RESULTS / run_id)
    rows = []
    xmins = []
    pools = {}
    for lo, hi in WINDOWS:
        p = pool(snaps, lo, hi)
        if len(p) < 500:
            continue
        pools[(lo, hi)] = p
        fit = fit_tail_csn(p)
        if fit:
            xmins.append(fit["x_min"])
    xc = float(np.median(xmins)) if xmins else None
    for (lo, hi), p in pools.items():
        fit = fit_tail_csn(p)
        row = dict(window=f"[{lo},{hi})", n=len(p))
        if fit:
            row.update(alpha_csn=fit["alpha"], xmin=fit["x_min"], ntail=fit["n_tail"])
            lr = lr_powerlaw_vs_lognormal(p, fit["x_min"], fit["alpha"])
            if lr:
                row.update(lr_R=lr["R"], lr_p=lr["p"])
        if xc:
            fx = fit_tail_fixed_xmin(p, xc)
            if fx:
                bt = bootstrap_tail_alpha(p, xc, n_boot=200, seed=0)
                row.update(alpha_xc=fx["alpha"], xc=xc,
                           ci=[bt["alpha_lo"], bt["alpha_hi"]] if bt else None)
        body = fit_body(p)
        if body:
            row.update(body_best=body["best"], mm=body["med_over_mean"])
        rows.append(row)
    return rows


if __name__ == "__main__":
    out = {}
    for rid in RUNS:
        if not (RESULTS / rid / "summary.json").exists():
            print(f"[skip] {rid}")
            continue
        rows = analyze(rid)
        out[rid] = rows
        print(f"\n=== {rid} ===")
        for r in rows:
            ci = r.get("ci")
            ci_s = f"[{ci[0]:.2f},{ci[1]:.2f}]" if ci else "-"
            print(f"  {r['window']:13s} n={r['n']:6d} a_csn={r.get('alpha_csn', float('nan')):.3f} "
                  f"xmin={r.get('xmin', float('nan')):7.1f} a@xc={r.get('alpha_xc', float('nan')):.3f} "
                  f"CI={ci_s} LR={r.get('lr_R', float('nan')):8.1f} p={r.get('lr_p', float('nan')):.4f} "
                  f"body={r.get('body_best')} mm={r.get('mm', float('nan')):.3f}")
    with open(RESULTS / "validation" / "long_runs.json", "w") as fh:
        json.dump(out, fh, indent=1, default=float)
