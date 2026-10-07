"""Profilage du coût réel (s/pas, en fonction de λ au minimum), à exécuter
AVANT tout engagement de campagne à plusieurs cellules (PROMPT_M4_3_FINAL.md
§3, dernier point). Mesure directe sur le moteur `m4_3` (copie exacte de
`m4_2b`, §8) — pas d'extrapolation depuis les temps mesurés en M4.2B (autre
machine potentiellement, autre charge système).

Usage : lancer à un moment où la machine n'est pas déjà chargée par un
pool (le lanceur de pool vérifie `pool_lock`, ce script ne le fait pas —
c'est une mesure ponctuelle, pas un run de campagne).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from m4_3 import Config, Simulation  # noqa: E402

BASE_PARAMS = dict(sigma=0.01, delta=0.01, gamma=0.5, A=1.0, K0=25.0,
                    rho=1.0, eta_beta=1.0, eta_n_ref=1.0, target_rule="arithmetic")
LAMBDAS = (10.0, 30.0, 100.0)
PROFILE_STEPS = 300  # assez pour lisser le coût d'amorçage, assez court pour rester un profilage


def profile_one(lam: float, steps: int = PROFILE_STEPS, seed: int = 0) -> dict:
    sim = Simulation(Config(seed=seed, T=steps, lam=lam, **BASE_PARAMS))
    started = time.perf_counter()
    for _ in range(steps):
        sim.step()
    elapsed = time.perf_counter() - started
    return {
        "lam": lam,
        "steps": steps,
        "elapsed_s": elapsed,
        "s_per_step": elapsed / steps,
        "population_final": int(sum(sim.population.alive)),
        "n_loans_final": len(sim.book.loans),
    }


def main() -> None:
    rows = [profile_one(lam) for lam in LAMBDAS]
    print(f"{'lam':>8} {'s/pas':>10} {'pop_final':>10} {'n_loans':>10} {'s/1000 pas':>12}")
    for r in rows:
        print(f"{r['lam']:>8.0f} {r['s_per_step']:>10.4f} {r['population_final']:>10} "
              f"{r['n_loans_final']:>10} {r['s_per_step'] * 1000:>12.1f}")
    print()
    print("Extrapolation grossière (linéaire dans le nombre de pas). ATTENTION : "
          "mesuré sur une fenêtre courte qui inclut le transitoire de montée en "
          "charge (le carnet de prêts dépasse largement son niveau stationnaire "
          "avant de se contracter, observé directement — pas une hypothèse). Le "
          "coût par pas mesuré ici est donc probablement un MAJORANT du coût "
          "stationnaire, pas un minorant : cette extrapolation SURESTIME "
          "probablement un run long plutôt que de le sous-estimer.")
    for r in rows:
        for t_target in (3000, 10000):
            est_s = r["s_per_step"] * t_target
            print(f"  lam={r['lam']:.0f}, T={t_target} -> ~{est_s:.0f} s "
                  f"(~{est_s / 60:.1f} min) si le coût par pas restait constant")


if __name__ == "__main__":
    main()
