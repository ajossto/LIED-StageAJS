"""Couplage theta x delta_endo. Flux d'extraction vs dépréciation du capital."""
from __future__ import annotations
import json, sys, math
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

OUT = HERE / "results" / "claude_coupling_theta_depr.json"
AGG = HERE / "results" / "claude_coupling_theta_depr_aggregate.json"
THETA_VALUES = [0.20, 0.28, 0.35, 0.42, 0.50]
DEPR_VALUES  = [0.02, 0.05, 0.10]
# Deux centres pour voir l'interaction
K_VALUES     = [3, 4]
SEEDS        = [42, 7, 123]
N_STEPS      = 1500
N_WORKERS    = 6

def _job(k, theta, depr, seed):
    r = run_and_collect({"n_candidats_pool": k, "theta": theta,
                         "taux_depreciation_endo": depr, "epsilon": 1e-3},
                        n_steps=N_STEPS, seed=seed)
    for f in ("ts_n_alive","ts_actif","ts_n_loans","ts_failures","ts_densite_fin","ts_gini","dist_values_regime"):
        r.pop(f, None)
    r["k"] = k; r["theta"] = theta; r["depr_endo"] = depr
    return r

def mean(xs): return sum(xs)/len(xs) if xs else float("nan")
def std(xs):
    if len(xs)<2: return 0.
    m=mean(xs); return math.sqrt(sum((x-m)**2 for x in xs)/len(xs))

def main():
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    done = {(e["k"], e["theta"], e["depr_endo"], e["seed"]) for e in existing}
    jobs = [(k, th, d, s) for k in K_VALUES for th in THETA_VALUES
            for d in DEPR_VALUES for s in SEEDS if (k, th, d, s) not in done]
    print(f"{len(jobs)} sims, {len(existing)} déjà présentes.")
    if not jobs:
        _aggregate(existing); return
    results = list(existing)
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futures = {ex.submit(_job, k, th, d, s): (k, th, d, s) for k, th, d, s in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            k, th, d, s = futures[fut]
            try:
                r = fut.result(); results.append(r)
                bt = r.get("regime_diagnostics", {}).get("bounded_tail", "?")
                df = r.get("measure_densite_fin_mean", 0)
                print(f"[{i}/{len(jobs)}] k={k} theta={th:.2f} depr={d:.3f} seed={s}: bounded={bt} df={df:.3f}")
            except Exception as e:
                print(f"ERREUR k={k} th={th} d={d} s={s}: {e}")
            OUT.write_text(json.dumps(results, indent=2))
    _aggregate(results)

def _aggregate(results):
    groups = defaultdict(list)
    for r in results:
        groups[(r["k"], r["theta"], r["depr_endo"])].append(r)
    agg = []
    for (k, th, d), runs in sorted(groups.items()):
        dfs  = [r.get("measure_densite_fin_mean", 0) for r in runs]
        bts  = [r.get("regime_diagnostics", {}).get("bounded_tail", False) for r in runs]
        alives=[r.get("measure_n_alive_mean", 0) for r in runs]
        agg.append({"k": k, "theta": th, "depr_endo": d, "n": len(runs),
                    "bounded_share": sum(bts)/len(bts),
                    "df_mean": mean(dfs), "df_std": std(dfs),
                    "alive_mean": mean(alives)})
    AGG.write_text(json.dumps(agg, indent=2))
    print(f"Agrégat theta x depr écrit: {AGG}")
    for k in K_VALUES:
        print(f"\nk={k} — bounded_share[theta x depr_endo]:")
        thetas = sorted(set(r["theta"] for r in agg if r["k"]==k))
        deprs  = sorted(set(r["depr_endo"] for r in agg if r["k"]==k))
        print(f"{'th\\d':>5} " + " ".join(f"{d:>5.2f}" for d in deprs))
        for th in thetas:
            row = f"{th:>5.2f} "
            for d in deprs:
                e = next((r for r in agg if r["k"]==k and r["theta"]==th and r["depr_endo"]==d), None)
                row += f"  {e['bounded_share']:.1f} " if e else "   ?  "
            print(row)

if __name__ == "__main__":
    main()
