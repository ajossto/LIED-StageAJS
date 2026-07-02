import json
import multiprocessing as mp
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import load_stationary_runs, last_step_values, measurement_step_floor
import families as fam

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
os.makedirs(OUT_DIR, exist_ok=True)

VARIABLES = ["actif_total", "passif_total", "revenu_total"]


def process_run(run):
    rid = run["run_id"]
    out_path = os.path.join(OUT_DIR, f"{rid}.json")
    if os.path.exists(out_path):
        return rid, "skip"
    p = run["params"]
    s = run["summary"]
    mstep = measurement_step_floor(run)
    record = {
        "run_id": rid,
        "params": {k: p.get(k) for k in (
            "n_candidats_pool", "alpha_min", "alpha_max", "alpha_sigma_brownien",
            "theta", "mu", "lambda_creation", "fraction_taux_emprunteur",
            "seuil_ratio_endettement", "duree_simulation",
        )},
        "summary_flags": {k: s.get(k) for k in ("stationary", "bounded_tail", "flow_balanced")},
        "variables": {},
    }
    for var in VARIABLES:
        try:
            step, vals = last_step_values(run["csv_dir"], var, min_step=mstep)
        except Exception:
            continue
        if not vals:
            continue
        n_pos = sum(1 for v in vals if v > 0)
        entry = {"step": step, "n_total": len(vals), "n_pos": n_pos}
        try:
            fits = fam.fit_all(vals)
        except Exception:
            fits = None
            entry["error"] = traceback.format_exc()
        if fits:
            entry["fits"] = fits
            entry["best_per_k"] = {str(k): v["name"] for k, v in fam.best_per_k(fits).items()}
            overall_best = min(fits.values(), key=lambda r: r["aic"])
            entry["overall_best_aic"] = overall_best["name"]
            overall_best_bic = min(fits.values(), key=lambda r: r["bic"])
            entry["overall_best_bic"] = overall_best_bic["name"]
        record["variables"][var] = entry
    with open(out_path, "w") as fh:
        json.dump(record, fh, indent=1)
    return rid, "done"


def main():
    runs = load_stationary_runs()
    print(f"{len(runs)} stationary runs", flush=True)
    t0 = time.time()
    with mp.Pool(8) as pool:
        for i, (rid, status) in enumerate(pool.imap_unordered(process_run, runs)):
            print(f"[{i+1}/{len(runs)}] {rid} {status} ({time.time()-t0:.0f}s)", flush=True)
    print("ALL DONE", time.time() - t0)


if __name__ == "__main__":
    main()
