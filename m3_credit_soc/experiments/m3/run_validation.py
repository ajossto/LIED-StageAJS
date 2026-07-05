"""Analyse statistique d'un run M3 -> <run_dir>/validation.json.

Protocole du rapport 02 §5/§9 : par variable (L, K, NW, revenu brut/net),
corps en MLE tronqué, queue CSN + x_min commun + bootstrap + LR corrigé,
familles complètes (dont dPlN) pour le revenu ; anti-cohorte ; renouvellement ;
avalanches causales ; concentration ; prédiction réseau -> défauts ;
financiarisation du top. Aucun pooling inter-seed : ce script traite UN run.

Usage : run_validation.py <run_dir> [<run_dir> ...]
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))

from m3 import analysis as an                      # noqa: E402
from m3.metrics import load_series, load_snapshots, load_avalanches  # noqa: E402

VARS = ("L", "K", "nw", "income", "income_net")


def _windows(ts):
    """Trois fenêtres d'analyse : mi-parcours, avant-dernière, dernière."""
    ts = sorted(ts)
    if len(ts) < 3:
        return ts
    return [ts[len(ts) // 2], ts[3 * len(ts) // 4], ts[-1]]


def analyze_run(run_dir):
    run_dir = Path(run_dir)
    snaps = load_snapshots(run_dir)
    series = load_series(run_dir)
    avalanches = load_avalanches(run_dir)
    out = dict(run=run_dir.name)
    if not snaps:
        out["error"] = "aucun snapshot"
        return out
    ts = sorted(snaps)
    wins = _windows(ts)
    t_last = ts[-1]

    # --- distributions par variable et par fenêtre -------------------------
    dist = {}
    for t in wins:
        snap = snaps[t]
        per_var = {}
        for var in VARS:
            v = snap[var]
            d = {}
            body = an.fit_body(v)
            if body:
                d["body"] = dict(best=body["best"],
                                 delta_aic_expon=body["delta_aic_expon"],
                                 med_over_mean=body["med_over_mean"],
                                 n_body=body["n_body"])
            tail = an.fit_tail_csn(v)
            if tail:
                d["tail_csn"] = tail
                boot = an.bootstrap_tail_alpha(v, tail["x_min"], seed=1)
                if boot:
                    d["tail_boot"] = boot
                lr = an.lr_powerlaw_vs_lognormal(v, tail["x_min"], tail["alpha"])
                if lr:
                    d["lr_pl_vs_ln"] = lr
            g = an.gini(v)
            if g is not None:
                d["gini"] = g
            shares = an.top_shares(v)
            if shares:
                d["top_shares"] = shares
            per_var[var] = d
        # familles complètes pour le revenu (dPlN vs lognormale vs Fisk)
        ff = an.fit_full_families(snap["income"])
        if ff:
            per_var["income"]["full_families"] = dict(
                best=ff["best"],
                aic={k: round(f["aic"], 1) for k, f in ff["fits"].items()})
        ff = an.fit_full_families(snap["nw"])
        if ff:
            per_var["nw"]["full_families"] = dict(
                best=ff["best"],
                aic={k: round(f["aic"], 1) for k, f in ff["fits"].items()})
        dist[str(t)] = per_var
    out["distributions"] = dist

    # --- x_min commun : stabilité de l'exposant de NW inter-fenêtres -------
    tails = [an.fit_tail_csn(snaps[t]["nw"]) for t in wins]
    tails = [t for t in tails if t]
    if tails:
        x_common = float(np.median([t["x_min"] for t in tails]))
        out["nw_tail_common_xmin"] = {
            str(t): an.fit_tail_fixed_xmin(snaps[t]["nw"], x_common)
            for t in wins}
        out["nw_tail_common_xmin"]["x_min"] = x_common

    # --- anti-cohorte et renouvellement -------------------------------------
    out["age"] = {var: an.age_diagnostics(snaps[t_last], var=var)
                  for var in ("nw", "income", "K")}
    if len(ts) >= 2:
        t_mid = ts[len(ts) // 2]
        out["renewal"] = an.renewal_diagnostics(
            snaps[t_mid], snaps[t_last], t_mid, t_last)
        out["transition_nw"] = np.round(
            an.transition_matrix(snaps[t_mid], snaps[t_last]), 3).tolist()

    # --- financiarisation : part des intérêts dans le revenu du top --------
    snap = snaps[t_last]
    inc = snap["income"]
    fin = {}
    for f, name in ((0.01, "top1"), (0.10, "top10")):
        thr = np.quantile(inc, 1 - f)
        mask = inc >= thr
        tot = inc[mask].sum()
        fin[name] = float(snap["int_in"][mask].sum() / tot) if tot > 0 else None
    fin["all"] = float(snap["int_in"].sum() / inc.sum()) if inc.sum() > 0 else None
    out["interest_share_income"] = fin

    # --- avalanches causales -------------------------------------------------
    out["avalanches"] = an.avalanche_size_distribution(avalanches)

    # --- réseau : concentration et pouvoir prédictif ------------------------
    out["credit_concentration"] = an.credit_concentration(snap)
    out["hhi_claims"] = an.hhi(snap["claims"])
    # AUC : exposition à t_mid -> morts dans ]t_mid, t_last]
    if len(ts) >= 2:
        t_mid = ts[len(ts) // 2]
        ids_mid = set(int(i) for i in snaps[t_mid]["id"])
        ids_last = set(int(i) for i in snaps[t_last]["id"])
        deaths_after = ids_mid - ids_last
        out["network_auc"] = an.network_default_auc(
            None, snaps[t_mid], deaths_after)

    # --- série : régime, défauts par cause ----------------------------------
    last_q = [s for s in series if s["t"] > series[-1]["t"] * 3 // 4]
    births = sum(s["births"] for s in last_q)
    out["series"] = dict(
        pop_final=series[-1]["pop"],
        growth_last_quarter=(last_q[-1]["pop"] - last_q[0]["pop"])
        / max(last_q[0]["pop"], 1),
        deaths_over_births=sum(s["deaths"] for s in last_q) / births
        if births else None,
        roots_liquidity=sum(s["roots_liquidity"] for s in series),
        roots_insolvency=sum(s["roots_insolvency"] for s in series),
        roots_both=sum(s["roots_both"] for s in series),
        interest_paid_last=float(np.mean([s["interest_paid"] for s in last_q])),
        loans_final=series[-1]["n_loans"],
    )
    # corrélation concentration -> faillites (retard 1..20 pas)
    if len(series) > 200:
        hhi_ts, deaths_ts = [], []
        for t in ts[:-1]:
            h = an.hhi(snaps[t]["claims"])
            if h is None:
                continue
            idx = t
            future = [s["deaths"] for s in series if idx < s["t"] <= idx + 50]
            if future:
                hhi_ts.append(h)
                deaths_ts.append(sum(future))
        if len(hhi_ts) >= 8 and np.std(hhi_ts) > 0 and np.std(deaths_ts) > 0:
            out["corr_hhi_future_deaths"] = float(
                np.corrcoef(hhi_ts, deaths_ts)[0, 1])
    return out


if __name__ == "__main__":
    for run_dir in sys.argv[1:]:
        res = analyze_run(run_dir)
        path = Path(run_dir) / "validation.json"
        with open(path, "w") as fh:
            json.dump(res, fh, indent=2, default=float)
        print(f"[done] {path}")
