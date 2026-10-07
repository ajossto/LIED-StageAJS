"""
Robustesse OAT : seeds 7 et 123 pour les 8 parametres les plus impactants.

Parametres choisis par amplitude |delta_densite_fin| sur le screening seed=42 :
  alpha_sigma_brownien, mu, taux_depreciation_endo, epsilon,
  fraction_taux_emprunteur, actif_liquide_initial, theta, n_candidats_pool

Centres : subcritical_k3 et regime_k4.
seeds : 7 et 123 (seed 42 deja fait par Codex).
steps : 1500.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict
import math

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from run_simulation import BASELINE, run_and_collect

RESULTS_FILE = HERE / "results" / "claude_oat_robustness_seeds.json"
N_STEPS = 1500
N_WORKERS = 6
SEEDS = [7, 123]

CENTERS = {
    "subcritical_k3": {"n_candidats_pool": 3, "alpha_sigma_brownien": 0.0, "epsilon": 1e-3},
    "regime_k4": {"n_candidats_pool": 4, "alpha_sigma_brownien": 0.0, "epsilon": 1e-3},
}

# Valeurs OAT reprises de oat_sweep.py (bas et haut uniquement, sans la valeur centrale)
OAT_TOP = {
    "alpha_sigma_brownien": [0.005, 0.02],
    "mu": [0.00, 0.10],
    "taux_depreciation_endo": [0.02, 0.10],
    "epsilon": [1e-6, 1e-2],
    "fraction_taux_emprunteur": [0.0, 0.5],
    "actif_liquide_initial": [100.0, 400.0],
    "theta": [0.20, 0.50],
}
OAT_K = {
    "subcritical_k3": {"n_candidats_pool": [2, 4]},
    "regime_k4": {"n_candidats_pool": [3, 5]},
}


def _build_jobs():
    jobs = []
    for center, base_override in CENTERS.items():
        for param, values in OAT_TOP.items():
            for val in values:
                override = {**base_override, param: val}
                if param == "actif_liquide_initial":
                    override["passif_inne_initial"] = val - 10.0
                for seed in SEEDS:
                    jobs.append((center, param, val, override, seed))
        for param, center_vals in OAT_K.items():
            for val in center_vals.get(center, []):
                override = {**base_override, "n_candidats_pool": val}
                for seed in SEEDS:
                    jobs.append((center, "n_candidats_pool", val, override, seed))
    return jobs


def _job(center, param, val, override, seed):
    r = run_and_collect(override, n_steps=N_STEPS, seed=seed)
    for k in ("ts_n_alive", "ts_actif", "ts_n_loans", "ts_failures", "ts_densite_fin", "ts_gini", "dist_values_regime"):
        r.pop(k, None)
    r["center"] = center
    r["oat_parameter"] = param
    r["oat_value"] = val
    return r


def mean(xs): return sum(xs)/len(xs) if xs else float("nan")
def std(xs):
    if len(xs) < 2: return 0.0
    m = mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs)/len(xs))


def main():
    existing = []
    if RESULTS_FILE.exists():
        existing = json.loads(RESULTS_FILE.read_text())
    done_keys = {(e["center"], e["oat_parameter"], e["oat_value"], e["seed"]) for e in existing}

    jobs = [j for j in _build_jobs() if (j[0], j[1], j[2], j[4]) not in done_keys]
    print(f"{len(jobs)} simulations a lancer, {len(existing)} deja presentes.")
    if not jobs:
        print("Rien a faire.")
        _aggregate(existing)
        return

    results = list(existing)
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futures = {ex.submit(_job, *j): j for j in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            j = futures[fut]
            try:
                r = fut.result()
                results.append(r)
                bounded = r.get("regime_diagnostics", {}).get("bounded_tail", "?")
                df = r.get("measure_densite_fin_mean", 0)
                print(f"[{i}/{len(jobs)}] {j[0][:8]} {j[1]:30s}={j[2]} seed={j[4]}: bounded={bounded} df={df:.3f}")
            except Exception as e:
                print(f"[{i}/{len(jobs)}] ERREUR {j}: {e}")
            RESULTS_FILE.write_text(json.dumps(results, indent=2))

    _aggregate(results)


def _aggregate(results):
    # Charger effets Codex seed=42
    codex_effects_file = HERE / "results" / "codex_oat_screen_steps1500_seeds42_effects.json"
    codex_agg_file = HERE / "results" / "codex_oat_screen_steps1500_seeds42_aggregate.json"
    codex_effects = json.loads(codex_effects_file.read_text()) if codex_effects_file.exists() else []
    codex_agg = json.loads(codex_agg_file.read_text()) if codex_agg_file.exists() else []

    # Regrouper les resultats robustesse par (center, param, value)
    groups = defaultdict(list)
    for r in results:
        groups[(r["center"], r["oat_parameter"], r["oat_value"])].append(r)

    # Fusionner avec les resultats seed=42 de Codex
    # On cherche dans codex_agg l'entree correspondante
    codex_by_key = {}
    for entry in codex_agg:
        if entry.get("direction") in ("high", "low", "center"):
            codex_by_key[(entry["center"], entry["parameter"], entry.get("value"))] = entry

    combined = []
    for (center, param, val), runs in sorted(groups.items()):
        dfs = [r.get("measure_densite_fin_mean", 0) for r in runs]
        alives = [r.get("measure_n_alive_mean", 0) for r in runs]
        bounded = [r.get("regime_diagnostics", {}).get("bounded_tail", False) for r in runs]
        seeds_here = [r["seed"] for r in runs]

        # Ajouter seed=42 depuis Codex si disponible
        c42 = codex_by_key.get((center, param, val))
        if c42:
            df42 = c42.get("measure_densite_fin_mean_mean", float("nan"))
            alive42 = c42.get("measure_n_alive_mean_mean", float("nan"))
            bt42 = bool(c42.get("bounded_tail_share", 0) >= 0.5)
            all_dfs = [df42] + dfs
            all_alives = [alive42] + alives
            all_bounded = [bt42] + bounded
            all_seeds = [42] + seeds_here
        else:
            all_dfs = dfs
            all_alives = alives
            all_bounded = bounded
            all_seeds = seeds_here

        combined.append({
            "center": center,
            "parameter": param,
            "value": val,
            "n": len(all_dfs),
            "seeds": all_seeds,
            "bounded_tail_share": sum(1 for b in all_bounded if b) / len(all_bounded),
            "densite_fin_mean": mean(all_dfs),
            "densite_fin_std": std(all_dfs),
            "n_alive_mean": mean(all_alives),
            "n_alive_std": std(all_alives),
        })

    out = HERE / "results" / "claude_oat_robustness_aggregate.json"
    out.write_text(json.dumps(combined, indent=2))
    print(f"\nAgregat robustesse: {out}")

    # Afficher resume
    print("\nResume robustesse OAT (3 seeds):")
    for row in combined:
        print(f"  {row['center'][:8]} {row['parameter']:30s}={row['value']}: "
              f"bounded={row['bounded_tail_share']:.2f} df={row['densite_fin_mean']:.3f}±{row['densite_fin_std']:.3f}")


if __name__ == "__main__":
    main()
