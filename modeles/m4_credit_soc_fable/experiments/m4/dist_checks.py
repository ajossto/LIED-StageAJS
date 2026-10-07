"""Vérification des contraintes distributionnelles d'un run M4 (brief,
« Contraintes à préserver ») :
- familles du corps (NW, K) et de l'échantillon complet (revenu, dont dPlN),
  via m4.analysis (MLE tronqué, outillage corrigé de M2/M3) ;
- renouvellement du top décile entre fenêtres temporelles (PAS de mortalité
  instantanée — piège n°5) ;
- Gini et parts du top pour suivre l'effet distributif du crédit.

Usage : /home/anatole/jupyter/.venv/bin/python3 dist_checks.py <run_dir> ...
Écrit <run_dir>/figures/dist_checks.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))

from m4.analysis import (fit_body, fit_full_families, gini,  # noqa: E402
                         renewal_diagnostics, top_shares)
from m4.metrics import load_snapshots  # noqa: E402


def dist_checks(run_dir) -> dict:
    run_dir = Path(run_dir)
    snaps = load_snapshots(run_dir)
    if not snaps:
        return dict(run=run_dir.name, error="aucun snapshot")
    ts = sorted(snaps)
    t_last = ts[-1]
    snap = snaps[t_last]
    out = dict(run=run_dir.name, t_snap=t_last, n_alive=len(snap["id"]))

    for var in ("nw", "K", "income"):
        v = snap[var]
        v = v[v > 0]
        body = fit_body(v)
        out[f"{var}_body"] = (dict(best=body["best"],
                                   delta_aic_expon=body["delta_aic_expon"],
                                   n=body["n_body"])
                              if body else None)
        full = fit_full_families(v)
        out[f"{var}_full"] = (dict(best=full["best"], n=full["n"])
                              if full else None)
        g = gini(v)
        out[f"{var}_gini"] = g
        shares = top_shares(v)
        if shares:
            out[f"{var}_top"] = shares

    # renouvellement entre fenêtres : dernier snapshot vs snapshot à mi-course
    t_mid = min(ts, key=lambda t: abs(t - t_last // 2))
    if t_mid < t_last:
        ren = renewal_diagnostics(snaps[t_mid], snap, t_mid, t_last)
        if ren:
            out["renewal_mid_to_last"] = dict(
                survival=ren["survival"], persistence=ren["persistence"],
                frac_recent=ren["frac_recent"], window=[t_mid, t_last])
    return out


def _fmt(d: dict) -> str:
    def fam(key):
        b = d.get(key)
        return b["best"] if b else "n/a"
    ren = d.get("renewal_mid_to_last", {})
    return (f"{d['run']}: n={d.get('n_alive')} | corps NW={fam('nw_body')} "
            f"K={fam('K_body')} | revenu(full)={fam('income_full')} | "
            f"Gini NW={d.get('nw_gini'):.2f} | "
            f"persistence top={ren.get('persistence', float('nan')):.2f}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        d = dist_checks(arg)
        fig_dir = Path(arg) / "figures"
        fig_dir.mkdir(exist_ok=True)
        with open(fig_dir / "dist_checks.json", "w") as fh:
            json.dump(d, fh, indent=2)
        print(_fmt(d))
