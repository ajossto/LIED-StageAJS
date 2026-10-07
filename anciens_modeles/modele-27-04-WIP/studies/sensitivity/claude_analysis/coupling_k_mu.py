"""Couplage k x mu. Question : k=3,mu=0 atteint-il le même régime que k=4,mu=0.05 ?"""
from __future__ import annotations
import json, sys, math
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

OUT = HERE / "results" / "claude_coupling_k_mu.json"
AGG = HERE / "results" / "claude_coupling_k_mu_aggregate.json"
K_VALUES  = [2, 3, 4, 5]
MU_VALUES = [0.0, 0.01, 0.03, 0.05, 0.10]
SEEDS     = [42, 7, 123]
N_STEPS   = 1500
N_WORKERS = 6

def _job(k, mu, seed):
    r = run_and_collect({"n_candidats_pool": k, "mu": mu, "epsilon": 1e-3},
                        n_steps=N_STEPS, seed=seed)
    for f in ("ts_n_alive","ts_actif","ts_n_loans","ts_failures","ts_densite_fin","ts_gini","dist_values_regime"):
        r.pop(f, None)
    r["k"] = k; r["mu"] = mu
    return r

def mean(xs): return sum(xs)/len(xs) if xs else float("nan")
def std(xs):
    if len(xs)<2: return 0.
    m=mean(xs); return math.sqrt(sum((x-m)**2 for x in xs)/len(xs))

def main():
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    done = {(e["k"], e["mu"], e["seed"]) for e in existing}
    jobs = [(k, mu, s) for k in K_VALUES for mu in MU_VALUES for s in SEEDS
            if (k, mu, s) not in done]
    print(f"{len(jobs)} sims, {len(existing)} déjà présentes.")
    if not jobs:
        _aggregate(existing); return
    results = list(existing)
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futures = {ex.submit(_job, k, m, s): (k, m, s) for k, m, s in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            k, m, s = futures[fut]
            try:
                r = fut.result(); results.append(r)
                bt = r.get("regime_diagnostics", {}).get("bounded_tail", "?")
                df = r.get("measure_densite_fin_mean", 0)
                print(f"[{i}/{len(jobs)}] k={k} mu={m:.3f} seed={s}: bounded={bt} df={df:.3f}")
            except Exception as e:
                print(f"ERREUR k={k} mu={m} seed={s}: {e}")
            OUT.write_text(json.dumps(results, indent=2))
    _aggregate(results)

def _aggregate(results):
    groups = defaultdict(list)
    for r in results:
        groups[(r["k"], r["mu"])].append(r)
    agg = []
    for (k, mu), runs in sorted(groups.items()):
        dfs   = [r.get("measure_densite_fin_mean", 0) for r in runs]
        alives= [r.get("measure_n_alive_mean", 0) for r in runs]
        bts   = [r.get("regime_diagnostics", {}).get("bounded_tail", False) for r in runs]
        fails = [r.get("measure_failure_rate_mean", 0) for r in runs]
        cascade= [r.get("cascade_size_mean", 0) for r in runs]
        agg.append({"k": k, "mu": mu, "n": len(runs),
                    "bounded_share": sum(bts)/len(bts),
                    "df_mean": mean(dfs), "df_std": std(dfs),
                    "alive_mean": mean(alives), "failure_rate_mean": mean(fails),
                    "cascade_size_mean": mean(cascade)})
    AGG.write_text(json.dumps(agg, indent=2))
    print(f"\nCarte k x mu (bounded_share):")
    ks = sorted(set(r["k"] for r in agg))
    mus = sorted(set(r["mu"] for r in agg))
    print(f"{'k\\mu':>5} " + " ".join(f"{m:>6.3f}" for m in mus))
    for k in ks:
        row = f"{k:>5} "
        for m in mus:
            e = next((r for r in agg if r["k"]==k and r["mu"]==m), None)
            row += f"  {e['bounded_share']:.2f} " if e else "   ?   "
        print(row)

if __name__ == "__main__":
    main()
