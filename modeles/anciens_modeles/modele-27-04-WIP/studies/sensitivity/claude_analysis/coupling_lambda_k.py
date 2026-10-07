"""Couplage lambda x k. 6 workers, eps=1e-3, 1500 pas, 3 seeds."""
from __future__ import annotations
import json, sys, math
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

OUT = HERE / "results" / "claude_coupling_lambda_k.json"
AGG = HERE / "results" / "claude_coupling_lambda_k_aggregate.json"
K_VALUES    = [2, 3, 4, 5, 6]
LAM_VALUES  = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
SEEDS       = [42, 7, 123]
N_STEPS     = 1500
N_WORKERS   = 6

def _job(k, lam, seed):
    r = run_and_collect({"n_candidats_pool": k, "lambda_creation": lam, "epsilon": 1e-3},
                        n_steps=N_STEPS, seed=seed)
    for f in ("ts_n_alive","ts_actif","ts_n_loans","ts_failures","ts_densite_fin","ts_gini","dist_values_regime"):
        r.pop(f, None)
    r["k"] = k; r["lambda_creation"] = lam
    return r

def mean(xs): return sum(xs)/len(xs) if xs else float("nan")
def std(xs):
    if len(xs)<2: return 0.
    m=mean(xs); return math.sqrt(sum((x-m)**2 for x in xs)/len(xs))

def main():
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    done = {(e["k"], e["lambda_creation"], e["seed"]) for e in existing}
    jobs = [(k, lam, s) for k in K_VALUES for lam in LAM_VALUES for s in SEEDS
            if (k, lam, s) not in done]
    print(f"{len(jobs)} sims à lancer, {len(existing)} déjà présentes.")
    if not jobs:
        _aggregate(existing); return
    results = list(existing)
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futures = {ex.submit(_job, k, l, s): (k, l, s) for k, l, s in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            k, l, s = futures[fut]
            try:
                r = fut.result(); results.append(r)
                bt = r.get("regime_diagnostics", {}).get("bounded_tail", "?")
                df = r.get("measure_densite_fin_mean", 0)
                print(f"[{i}/{len(jobs)}] k={k} lam={l:.1f} seed={s}: bounded={bt} df={df:.3f}")
            except Exception as e:
                print(f"ERREUR k={k} lam={l} seed={s}: {e}")
            OUT.write_text(json.dumps(results, indent=2))
    _aggregate(results)

def _aggregate(results):
    groups = defaultdict(list)
    for r in results:
        groups[(r["k"], r["lambda_creation"])].append(r)
    agg = []
    for (k, lam), runs in sorted(groups.items()):
        dfs   = [r.get("measure_densite_fin_mean", 0) for r in runs]
        alives= [r.get("measure_n_alive_mean", 0) for r in runs]
        bts   = [r.get("regime_diagnostics", {}).get("bounded_tail", False) for r in runs]
        fails = [r.get("measure_failure_rate_mean", 0) for r in runs]
        ginis = [r.get("measure_gini_actif_mean", 0) for r in runs]
        agg.append({"k": k, "lambda": lam, "n": len(runs),
                    "bounded_share": sum(bts)/len(bts),
                    "df_mean": mean(dfs), "df_std": std(dfs),
                    "alive_mean": mean(alives), "alive_std": std(alives),
                    "failure_rate_mean": mean(fails),
                    "gini_mean": mean(ginis)})
    AGG.write_text(json.dumps(agg, indent=2))
    print(f"Agrégat: {AGG}")
    print("\nCarte de phase lambda x k:")
    ks = sorted(set(r["k"] for r in agg))
    lams = sorted(set(r["lambda"] for r in agg))
    header = f"{'k\\lam':>6} " + " ".join(f"{l:>5.1f}" for l in lams)
    print(header)
    for k in ks:
        row = f"{k:>6} "
        for l in lams:
            entry = next((r for r in agg if r["k"]==k and r["lambda"]==l), None)
            if entry:
                b = entry["bounded_share"]
                row += f"  {b:.1f} " if b < 0.5 else f" [{b:.1f}]"
            else:
                row += "   ?  "
        print(row)
    print("Légende: [0.X] = borné, 0.X = non borné")

if __name__ == "__main__":
    main()
