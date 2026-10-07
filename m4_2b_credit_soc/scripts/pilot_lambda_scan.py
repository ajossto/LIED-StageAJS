"""Pilote λ ∈ {10, 100} (baseline sinon inchangée), demandé pour deux raisons
distinctes après le balayage sigma :

1. §14 (robustesse à la taille du système) : λ=10 teste si une population
   plus petite / un mélange plus lent laisse l'hétérogénéité de degré
   s'accumuler en une véritable queue (le mécanisme identifié — accumulation
   age/degré tronquée par le turnover — prédit l'effet inverse de sigma).
2. §15 (scaling de taille finie des avalanches) : λ=100 donne un second
   point de population pour distinguer un exposant asymptotique d'une
   coupure liée à la taille du système (le run baseline λ=30 a une coupure
   ~136-163, proche de sa population ~1100-1200 — signature de taille finie
   à confirmer/infirmer avec un second point d'échelle).

Réutilise _run_one de pilot_sigma_and_control.py (même diagnostics). T=1000,
burn-in=375 (fraction T/8 utilisée pour le balayage sigma ; PAS re-vérifiée
pour λ=10/100 spécifiquement — à noter comme hypothèse non confirmée si la
dynamique de population diffère qualitativement, cf. rapport)."""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pilot_sigma_and_control import RESULTS as _OLD_RESULTS, _run_one  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "pilot_lambda_scan"


def main() -> None:
    specs = []
    for lam in (10.0, 100.0):
        for seed in (0, 1):
            specs.append({
                "label": f"lam{int(lam)}_seed{seed}", "sigma": 0.01, "seed": seed,
                "target_rule": "arithmetic", "T": 1000, "lam": lam,
            })

    RESULTS.mkdir(parents=True, exist_ok=True)
    # _run_one écrit sous ROOT/results/pilot_sigma_control/<label> ; on
    # redirige temporairement le module pour écrire sous pilot_lambda_scan.
    import pilot_sigma_and_control as mod
    mod.RESULTS = RESULTS

    with mp.Pool(processes=min(6, len(specs))) as pool:
        results = pool.map(_run_one, specs)

    (RESULTS / "all_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(f"{'label':16s} {'elapsed':>8s} {'pop':>6s} {'K_gini':>7s} {'sh_deg':>7s} "
          f"{'alpha':>7s} {'alpha/2':>8s} {'tau_hat':>8s} {'size_max':>9s} {'branch':>7s}")
    for r in results:
        print(
            f"{r['label']:16s} {r['elapsed_s']:8.1f} {r.get('population_final', 0):6d} "
            f"{r.get('K_gini_final', float('nan')):7.3f} "
            f"{r.get('share_from_deg_out_mean') if r.get('share_from_deg_out_mean') is not None else float('nan'):7.3f} "
            f"{r.get('alpha_density_mean') if r.get('alpha_density_mean') is not None else float('nan'):7.3f} "
            f"{r.get('alpha_density_half_threshold_mean') if r.get('alpha_density_half_threshold_mean') is not None else float('nan'):8.3f} "
            f"{r.get('avalanche_tau_hat') if r.get('avalanche_tau_hat') is not None else float('nan'):8.3f} "
            f"{r.get('avalanche_size_max', 0):9d} "
            f"{r.get('branching_ratio') if r.get('branching_ratio') is not None else float('nan'):7.3f}"
        )


if __name__ == "__main__":
    main()
