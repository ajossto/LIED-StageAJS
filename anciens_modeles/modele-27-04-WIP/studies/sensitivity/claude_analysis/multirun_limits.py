"""
Multi-seeds pour les cas limites (1/3 ou 2/3 bornés dans les campagnes précédentes).
10 seeds supplémentaires pour estimer la probabilité de convergence.
"""
from __future__ import annotations
import json, sys, math
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

OUT = HERE / "results" / "claude_multirun_limits.json"
AGG = HERE / "results" / "claude_multirun_limits_aggregate.json"
N_STEPS   = 1500
N_WORKERS = 6
EXTRA_SEEDS = list(range(200, 213))  # 13 seeds supplémentaires

LIMIT_CASES = [
    # (nom, override)
    ("k4_theta05",    {"n_candidats_pool": 4, "theta": 0.5,  "epsilon": 1e-3}),
    ("k4_depr002",    {"n_candidats_pool": 4, "taux_depreciation_endo": 0.02, "epsilon": 1e-3}),
    ("k3_sigma005",   {"n_candidats_pool": 3, "alpha_sigma_brownien": 0.005, "epsilon": 1e-3}),
    ("k3_sigma020",   {"n_candidats_pool": 3, "alpha_sigma_brownien": 0.020, "epsilon": 1e-3}),
    ("k4_lam120",     {"n_candidats_pool": 4, "lambda_creation": 1.2, "epsilon": 1e-3}),
    ("k4_lam100",     {"n_candidats_pool": 4, "lambda_creation": 1.0, "epsilon": 1e-3}),
    ("k3_actif100",   {"n_candidats_pool": 3, "actif_liquide_initial": 100.0, "epsilon": 1e-3}),
]

def _job(name, override, seed):
    r = run_and_collect(override, n_steps=N_STEPS, seed=seed)
    for f in ("ts_n_alive","ts_actif","ts_n_loans","ts_failures","ts_densite_fin","ts_gini","dist_values_regime"):
        r.pop(f, None)
    r["case_name"] = name
    return r

def mean(xs): return sum(xs)/len(xs) if xs else float("nan")
def std(xs):
    if len(xs)<2: return 0.
    m=mean(xs); return math.sqrt(sum((x-m)**2 for x in xs)/len(xs))

def main():
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    done = {(e["case_name"], e["seed"]) for e in existing}
    jobs = [(name, ov, s) for name, ov in LIMIT_CASES
            for s in EXTRA_SEEDS if (name, s) not in done]
    print(f"{len(jobs)} sims, {len(existing)} déjà présentes.")
    if not jobs:
        _aggregate(existing); return
    results = list(existing)
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futures = {ex.submit(_job, n, ov, s): (n, s) for n, ov, s in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            n, s = futures[fut]
            try:
                r = fut.result(); results.append(r)
                bt = r.get("regime_diagnostics", {}).get("bounded_tail", "?")
                df = r.get("measure_densite_fin_mean", 0)
                print(f"[{i}/{len(jobs)}] {n} seed={s}: bounded={bt} df={df:.3f}")
            except Exception as e:
                print(f"ERREUR {n} seed={s}: {e}")
            OUT.write_text(json.dumps(results, indent=2))
    _aggregate(results)

def _aggregate(results):
    # Combiner avec seeds 42,7,123 existants depuis les campagnes précédentes
    prev_data = {}
    for fname in ("claude_oat_robustness_seeds.json", "codex_oat_screen_steps1500_seeds42.json",
                  "alpha_sigma_sweep_steps1500_eps0.001.json", "claude_lambda_fine_sweep.json"):
        f = HERE / "results" / fname
        if not f.exists(): continue
        try:
            for r in json.loads(f.read_text()):
                pass  # just check parseable
        except: continue

    groups = defaultdict(list)
    for r in results:
        groups[r["case_name"]].append(r)

    agg = []
    for name, runs in sorted(groups.items()):
        bts  = [r.get("regime_diagnostics", {}).get("bounded_tail", False) for r in runs]
        dfs  = [r.get("measure_densite_fin_mean", 0) for r in runs]
        p = sum(bts)/len(bts)
        agg.append({"case": name, "n_seeds": len(runs),
                    "p_bounded": p, "ci_95_half": 1.96*math.sqrt(p*(1-p)/len(runs)) if len(runs)>1 else float("nan"),
                    "df_mean": mean(dfs), "df_std": std(dfs)})
        print(f"  {name:20s}: {sum(bts)}/{len(bts)} bornés ({p:.2f}) df={mean(dfs):.3f}±{std(dfs):.3f}")
    AGG.write_text(json.dumps(agg, indent=2))
    print(f"Agrégat: {AGG}")

if __name__ == "__main__":
    main()
