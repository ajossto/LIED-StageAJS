"""Validation complète d'un ou plusieurs runs M2 (protocole §6 du rapport,
opérationnalisé par la spec §7). Produit results/validation/<run_id>.json
et les figures standard du run.

Usage :
    python3 run_validation.py baseline_s0 baseline_s1 ...
    python3 run_validation.py --all          # tous les runs présents
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

from exp_common import RESULTS, ROOT  # noqa: F401  (sys.path via exp_common)
from m2.analysis import (age_diagnostics, body_increment_moments,
                         bootstrap_tail_alpha, cascade_size_distribution,
                         credit_concentration, fit_body, fit_tail_csn,
                         fit_tail_fixed_xmin, lr_powerlaw_vs_lognormal,
                         renewal_diagnostics)
from m2.metrics import load_series, load_snapshots
from m2 import plots

WINDOWS = ((500, 1000), (1000, 1500), (1500, 2000))
VARS = ("nw", "income", "w")
POOL_EVERY = 50  # ne pooler que les snapshots réguliers (pas les denses)


def _pool(snaps, lo, hi, var):
    vals = []
    for t, snap in snaps.items():
        if lo <= t < hi and t % POOL_EVERY == 0:
            vals.append(snap[var])
    return np.concatenate(vals) if vals else np.array([])


def _round(x, nd=4):
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, nd) for v in x]
    if isinstance(x, float):
        return round(x, nd) if math.isfinite(x) else None
    return x


def stationarity(series, t_min=800):
    """Pente relative par 1000 pas des séries clefs sur [t_min, fin]."""
    rows = [s for s in series if s["t"] >= t_min]
    if len(rows) < 100:
        return None
    t = np.array([s["t"] for s in rows], dtype=float)
    out = {}
    for key in ("pop", "w_tot", "n_loans", "loan_volume"):
        y = np.array([s[key] for s in rows], dtype=float)
        mean = float(np.mean(y))
        slope = float(np.polyfit(t, y, 1)[0])
        out[key] = dict(mean=mean,
                        rel_slope_per_1000=slope * 1000.0 / mean if mean else None)
    out["deaths_mean"] = float(np.mean([s["deaths"] for s in rows]))
    out["births_mean"] = float(np.mean([s["births"] for s in rows]))
    out["top_decile_deaths_per_500"] = float(
        np.sum([s["top_decile_deaths"] for s in rows]) / (len(rows) / 500.0))
    return out


def validate_run(run_id, make_figures=True):
    run_dir = RESULTS / run_id
    series = load_series(run_dir)
    snaps = load_snapshots(run_dir)
    report = {"run_id": run_id}
    report["stationarity"] = stationarity(series)
    report["cascades"] = cascade_size_distribution(series)

    # ---- corps et queue par fenêtre et par variable
    per_var = {}
    for var in VARS:
        wins = {}
        xmins = []
        for lo, hi in WINDOWS:
            pool = _pool(snaps, lo, hi, var)
            if len(pool) < 200:
                continue
            entry = {"n_pool": int(len(pool))}
            body = fit_body(pool)
            if body:
                entry["body"] = dict(
                    best=body["best"], delta_aic_expon=body["delta_aic_expon"],
                    med_over_mean=body["med_over_mean"], n_body=body["n_body"],
                    aic={k: v["aic"] for k, v in body["fits"].items()},
                    expon_scale=(body["fits"]["expon"]["params"][-1]
                                 if "expon" in body["fits"] else None))
            tail = fit_tail_csn(pool)
            if tail:
                entry["tail_csn"] = tail
                xmins.append(tail["x_min"])
                for name, trunc in (("lr_trunc", True), ("lr_naive", False)):
                    lr = lr_powerlaw_vs_lognormal(pool, tail["x_min"],
                                                  tail["alpha"], truncated=trunc)
                    if lr:
                        entry[name] = lr
            wins[f"[{lo},{hi})"] = entry
        # exposant à x_min commun (médiane des x_min de fenêtres) + bootstrap
        if xmins:
            xc = float(np.median(xmins))
            for (lo, hi), key in zip(WINDOWS, list(wins)):
                pool = _pool(snaps, lo, hi, var)
                if len(pool) < 200:
                    continue
                fx = fit_tail_fixed_xmin(pool, xc)
                if fx:
                    bt = bootstrap_tail_alpha(pool, xc, n_boot=200, seed=0)
                    fx["bootstrap"] = bt
                    wins[key]["tail_common_xmin"] = fx
        per_var[var] = wins
    report["distributions"] = per_var

    # ---- anti-cohorte : dernier snapshot régulier de chaque fenêtre
    anti = {}
    for lo, hi in WINDOWS:
        t_snap = hi - POOL_EVERY
        if t_snap in snaps:
            anti[f"t={t_snap}"] = {
                "nw": age_diagnostics(snaps[t_snap], var="nw"),
                "w": age_diagnostics(snaps[t_snap], var="w"),
            }
    report["anti_cohorte"] = anti

    # ---- renouvellement du top décile (t=1000 -> t=2000)
    if 1000 in snaps and 2000 in snaps:
        report["renewal"] = renewal_diagnostics(snaps[1000], snaps[2000],
                                                1000, 2000, var="nw")

    # ---- test mécanistique T ~ B0/A0 sur incréments 1 pas (snapshots denses)
    dense_ts = [t for t in range(1500, 1521) if t in snaps]
    if len(dense_ts) >= 2:
        nw_ref = snaps[dense_ts[0]]["nw"]
        hi_body = float(np.quantile(nw_ref, 0.7))
        moments = []
        for a, b in zip(dense_ts[:-1], dense_ts[1:]):
            if b - a == 1:
                m = body_increment_moments(snaps[a], snaps[b], 0.0, hi_body)
                if m:
                    moments.append(m)
        if moments:
            A0 = float(np.mean([m["A0"] for m in moments]))
            B0 = float(np.mean([m["B0"] for m in moments]))
            body_w3 = report["distributions"]["nw"].get("[1500,2000)", {}).get("body")
            T_meas = body_w3["expon_scale"] if body_w3 else None
            report["mechanistic"] = dict(
                A0=A0, B0=B0, T_pred=(B0 / A0 if A0 > 0 else None),
                T_measured_expon_scale=T_meas, nw_window=[0.0, hi_body],
                n_pairs=len(moments), note="A0>0 requis pour un corps borné")

    # ---- SOC : concentration du crédit vs faillites suivantes
    conc, subsequent_deaths = [], []
    reg_ts = sorted(t for t in snaps if t % POOL_EVERY == 0 and t >= 500)
    deaths_by_t = {s["t"]: s["deaths"] for s in series}
    for t in reg_ts:
        c = credit_concentration(snaps[t])
        if c is None:
            continue
        d = sum(deaths_by_t.get(u, 0) for u in range(t, t + POOL_EVERY))
        conc.append(c)
        subsequent_deaths.append(d)
    if len(conc) > 10 and np.std(conc) > 0 and np.std(subsequent_deaths) > 0:
        report["soc_concentration"] = dict(
            mean_concentration=float(np.mean(conc)),
            corr_conc_deaths=float(np.corrcoef(conc, subsequent_deaths)[0, 1]),
            n_points=len(conc))

    # ---- figures
    if make_figures and 2000 in snaps:
        plots.plot_timeseries(series, run_dir)
        plots.plot_distributions(snaps[2000], run_dir, label="_t2000")
        plots.plot_qq_exponential(snaps[2000], run_dir, var="nw", label="_t2000")
        plots.plot_qq_exponential(snaps[2000], run_dir, var="income", label="_t2000")
        plots.plot_age_wealth(snaps[2000], run_dir, var="nw", label="_t2000")
        plots.plot_age_distribution(snaps[2000], run_dir, label="_t2000")
        plots.plot_cascades(series, run_dir)

    out_dir = RESULTS / "validation"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / f"{run_id}.json", "w") as fh:
        json.dump(_round(report), fh, indent=1)
    return report


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--all" in args:
        run_ids = sorted(p.name for p in RESULTS.iterdir()
                         if (p / "summary.json").exists())
    else:
        run_ids = args
    for rid in run_ids:
        print(f"=== validation {rid} ===", flush=True)
        rep = validate_run(rid)
        st = rep.get("stationarity")
        if st:
            print(f"  pop={st['pop']['mean']:.0f} "
                  f"(pente {st['pop']['rel_slope_per_1000']:+.3f}/1000)")
        for var in VARS:
            for win, e in rep["distributions"].get(var, {}).items():
                b = e.get("body", {})
                t = e.get("tail_csn", {})
                lr = e.get("lr_trunc", {})
                print(f"  {var:7s} {win}: body={b.get('best')} "
                      f"dAICexp={b.get('delta_aic_expon')} "
                      f"med/mean={b.get('med_over_mean')} | "
                      f"tail a={t.get('alpha')} xmin={t.get('x_min')} "
                      f"LRtr={lr.get('R')} p={lr.get('p')}")
