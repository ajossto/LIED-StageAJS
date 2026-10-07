"""Agrège les validation.json de plusieurs runs en une table comparative
(CSV + markdown) : une ligne par run, colonnes = signatures majeures du
critère d'acceptation (rapport 02 §9). Sert au verdict A vs B vs C...

Usage : aggregate_results.py <run_dir> [...] [--out table]
"""
import argparse
import csv
import json
from pathlib import Path

COLS = [
    "run", "pop_final", "growth_last_q", "deaths_over_births",
    "roots_liquidity", "roots_insolvency",
    "nw_body_best", "nw_dAIC_expon", "nw_tail_alpha", "nw_tail_ci",
    "nw_lr_R", "income_body_best", "income_full_best", "L_body_best",
    "K_body_best", "gini_nw", "gini_L", "top10_nw", "renewal_survival",
    "renewal_frac_recent", "corr_age_lognw", "interest_top1",
    "aval_mean", "aval_max", "aval_var_over_mean", "aval_frac_multi",
    "hhi_claims", "auc_debts", "corr_hhi_deaths",
]


def row_from_validation(path):
    with open(path) as fh:
        v = json.load(fh)
    ts = sorted(v.get("distributions", {}), key=int)
    last = v["distributions"][ts[-1]] if ts else {}
    nw = last.get("nw", {})
    inc = last.get("income", {})
    ld = last.get("L", {})
    kd = last.get("K", {})
    boot = nw.get("tail_boot") or {}
    age = (v.get("age") or {}).get("nw") or {}
    ren = v.get("renewal") or {}
    av = v.get("avalanches") or {}
    auc = v.get("network_auc") or {}
    ser = v.get("series") or {}
    fin = v.get("interest_share_income") or {}

    def g(d, *keys):
        for k in keys:
            d = d.get(k) if isinstance(d, dict) else None
            if d is None:
                return None
        return d

    return {
        "run": v.get("run"),
        "pop_final": ser.get("pop_final"),
        "growth_last_q": ser.get("growth_last_quarter"),
        "deaths_over_births": ser.get("deaths_over_births"),
        "roots_liquidity": ser.get("roots_liquidity"),
        "roots_insolvency": ser.get("roots_insolvency"),
        "nw_body_best": g(nw, "body", "best"),
        "nw_dAIC_expon": g(nw, "body", "delta_aic_expon"),
        "nw_tail_alpha": g(nw, "tail_csn", "alpha"),
        "nw_tail_ci": (f"[{boot.get('alpha_lo'):.2f},{boot.get('alpha_hi'):.2f}]"
                       if boot.get("alpha_lo") else None),
        "nw_lr_R": g(nw, "lr_pl_vs_ln", "R"),
        "income_body_best": g(inc, "body", "best"),
        "income_full_best": g(inc, "full_families", "best"),
        "L_body_best": g(ld, "body", "best"),
        "K_body_best": g(kd, "body", "best"),
        "gini_nw": nw.get("gini"),
        "gini_L": ld.get("gini"),
        "top10_nw": g(nw, "top_shares", "top10"),
        "renewal_survival": ren.get("survival"),
        "renewal_frac_recent": ren.get("frac_recent"),
        "corr_age_lognw": age.get("corr_age_log"),
        "interest_top1": fin.get("top1"),
        "aval_mean": av.get("mean"),
        "aval_max": av.get("max"),
        "aval_var_over_mean": av.get("var_over_mean"),
        "aval_frac_multi": av.get("frac_multi"),
        "hhi_claims": v.get("hhi_claims"),
        "auc_debts": auc.get("debts"),
        "corr_hhi_deaths": v.get("corr_hhi_future_deaths"),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--out", default="comparison")
    args = ap.parse_args()
    rows = []
    for rd in args.run_dirs:
        p = Path(rd) / "validation.json"
        if p.exists():
            rows.append(row_from_validation(p))
        else:
            print(f"[warn] {p} absent — lancer run_validation.py d'abord")
    out_csv = Path(args.out + ".csv")
    with open(out_csv, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=COLS)
        wr.writeheader()
        wr.writerows(rows)
    print(f"[done] {out_csv} ({len(rows)} runs)")
    fmt = {c: (lambda x: f"{x:.3g}" if isinstance(x, float) else str(x))
           for c in COLS}
    for r in rows:
        print("  " + " | ".join(f"{c}={fmt[c](r[c])}" for c in COLS
                                if r[c] is not None))
