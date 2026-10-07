"""Recalibrage des seuils chaud/tiède/froid SUR LA MACHINE CIBLE (§11).

Le rapport d'architecture donne ses chiffres (≈ 1800 usages pour amortir une
table, 3,49× de gain de la LUT cubique) sur un banc synthétique. Le prompt
demande de les recalculer ici. On mesure en plus, comme le seuil ne se juge
pas dans l'absolu, la PART DU COÛT D'UN PAS que représente le noyau : si
elle est marginale, le seuil d'amortissement l'est aussi, et c'est une
meilleure réponse à la question ouverte qu'un nombre recalibré.

Domaine de test = domaine réel de M4.3 (rapport §7) : C reconstruit à
partir de la baseline arithmétique, quantiles 0,1 % / 50 % / 99,9 % =
192,0 / 1589,6 / 2213,6.

    python3 scripts/bench_kernel.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from m4_3live.kernel import PrincipalKernel, TechRegistry  # noqa: E402
from m4_3live.live import load_snapshot  # noqa: E402
from m4_3live.model import Config, Intervention, Simulation  # noqa: E402

CALLS = 300_000
REPEATS = 5
OUT = ROOT / "results" / "analysis"


def sample_pairs(count: int) -> tuple[np.ndarray, np.ndarray]:
    """(x, y) tirés sur le domaine réel : C log-normal calé sur les quantiles
    de M4.3, x/C uniforme sur [0,05 ; 0,5] (l'emprunteuse est la plus pauvre)."""
    rng = np.random.default_rng(12345)
    log_median = np.log(1589.6)
    log_sigma = (np.log(2213.6) - np.log(192.0)) / (2 * 3.09)
    capital_sum = np.exp(rng.normal(log_median, log_sigma, size=count))
    fraction = rng.uniform(0.05, 0.5, size=count)
    return capital_sum * fraction, capital_sum * (1.0 - fraction)


def timed(function, x, y, repeats=REPEATS) -> float:
    best = float("inf")
    for _ in range(repeats):
        started = time.perf_counter()
        function(x, y)
        best = min(best, time.perf_counter() - started)
    return best


def bench_paths() -> dict:
    x, y = sample_pairs(CALLS)
    x_list, y_list = x.tolist(), y.tolist()
    results = {}

    def make(policy, threshold, points, same_gamma, warm_only=False):
        registry = TechRegistry()
        kernel = PrincipalKernel(registry, policy=policy, threshold=threshold, points=points)
        if same_gamma:
            tech_b = registry.intern(1.5, 0.5)
            tech_l = registry.intern(1.0, 0.5)
        else:
            tech_b = registry.intern(1.0, 0.5)
            tech_l = registry.intern(1.25, 0.6)
        kernel.sync_matrix()
        return kernel, tech_b, tech_l

    # chemin (a) : même technologie
    kernel, tech, _ = make("exact_lut", 10**9, 65, True)
    identity = timed(lambda a, b: [kernel.solve(tech, tech, u, v) for u, v in zip(a, b)],
                     x_list, y_list)
    results["identite"] = {"seconds": identity, "mreq_s": CALLS / identity / 1e6, "erreur": "exacte"}

    # chemin (b) : γ égaux, forme fermée
    kernel, tech_b, tech_l = make("exact_lut", 10**9, 65, True)
    same = timed(lambda a, b: [kernel.solve(tech_b, tech_l, u, v) for u, v in zip(a, b)],
                 x_list, y_list)
    results["gamma_egaux"] = {"seconds": same, "mreq_s": CALLS / same / 1e6, "erreur": "exacte"}

    # chemin froid : Newton exact, sans table
    kernel, tech_b, tech_l = make("exact_lut", 10**9, 65, False)
    cold = timed(lambda a, b: [kernel.solve(tech_b, tech_l, u, v) for u, v in zip(a, b)],
                 x_list, y_list)
    results["newton_exact"] = {"seconds": cold, "mreq_s": CALLS / cold / 1e6, "erreur": "référence"}

    # chemin tiède : une étape de Newton
    kernel, tech_b, tech_l = make("hybrid", 10**9, 65, False)
    for u, v in zip(x_list[:2], y_list[:2]):
        kernel.solve(tech_b, tech_l, u, v)
    warm = timed(lambda a, b: [kernel.solve(tech_b, tech_l, u, v) for u, v in zip(a, b)],
                 x_list, y_list)
    registry = TechRegistry()
    exact_kernel = PrincipalKernel(registry)
    eb = registry.intern(1.0, 0.5)
    el = registry.intern(1.25, 0.6)
    exact_kernel.sync_matrix()
    warm_error = max(
        abs(kernel.solve(tech_b, tech_l, u, v) - exact_kernel.solve_exact(eb, el, u, v))
        for u, v in zip(x_list[:20000], y_list[:20000])
    )
    results["tiede_newton_1"] = {"seconds": warm, "mreq_s": CALLS / warm / 1e6,
                                 "erreur_max_capital": warm_error}

    # chemin chaud : LUT cubique de Hermite
    for points in (33, 65):
        kernel, tech_b, tech_l = make("exact_lut", 3, points, False)
        for u, v in zip(x_list[:5000], y_list[:5000]):
            kernel.solve(tech_b, tech_l, u, v)
        lut = timed(lambda a, b: [kernel.solve(tech_b, tech_l, u, v) for u, v in zip(a, b)],
                    x_list, y_list)
        lut_error = max(
            abs(kernel.solve(tech_b, tech_l, u, v) - exact_kernel.solve_exact(eb, el, u, v))
            for u, v in zip(x_list[:20000], y_list[:20000])
        )
        results[f"lut_hermite_{points}"] = {
            "seconds": lut,
            "mreq_s": CALLS / lut / 1e6,
            "erreur_max_capital": lut_error,
            "lignes": len(kernel.matrix[tech_b][tech_l].rows),
        }
    return results


def bench_build(points: int = 65) -> dict:
    registry = TechRegistry()
    kernel = PrincipalKernel(registry, threshold=10**9, points=points)
    tech_b = registry.intern(1.0, 0.5)
    tech_l = registry.intern(1.25, 0.6)
    kernel.sync_matrix()
    entry = kernel.matrix[tech_b][tech_l] or kernel._entry(tech_b, tech_l)
    best = float("inf")
    for exponent in (8, 9, 10, 11, 12):
        started = time.perf_counter()
        entry.build_row(exponent)
        best = min(best, time.perf_counter() - started)
    return {"points": points, "seconds_par_ligne": best}


def bench_step_share() -> dict:
    """Part du coût d'un pas imputable au noyau, en régime (c) réel."""
    snapshot = ROOT / "results" / "campaign" / "burn" / "seed0" / f"snapshot_t2000.pkl"
    if not snapshot.exists():
        return {"disponible": False, "raison": f"{snapshot} absent (lancer campaign.py burn)"}
    config = Config(gamma=0.5, A=1.0, lam=30.0, delta=0.01, sigma=0.01, K0=25.0, seed=0, T=2120)
    simulation = load_snapshot(snapshot, config=config)
    simulation.submit(Intervention(param="gamma", value=0.6, scope="fraction", phi=0.2))
    for _ in range(20):  # laisse la table se compiler et le régime s'installer
        simulation.step()
    before = dict(simulation.kernel.path_counts)
    started = time.perf_counter()
    for _ in range(100):
        simulation.step()
    elapsed = time.perf_counter() - started
    after = dict(simulation.kernel.path_counts)
    calls = {key: after[key] - before[key] for key in after}
    return {
        "disponible": True,
        "pas": 100,
        "secondes": elapsed,
        "s_par_pas": elapsed / 100,
        "appels_noyau": calls,
        "appels_par_pas": sum(calls.values()) / 100,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = bench_paths()
    build = bench_build()
    share = bench_step_share()

    newton_cost = paths["newton_exact"]["seconds"] / CALLS
    lut_cost = paths["lut_hermite_65"]["seconds"] / CALLS
    threshold = build["seconds_par_ligne"] / max(newton_cost - lut_cost, 1e-15)

    result = {
        "machine": {"appels": CALLS, "repetitions": REPEATS},
        "chemins": paths,
        "construction": build,
        "seuil_amortissement_mesure": threshold,
        "part_du_pas": share,
    }
    if share.get("disponible"):
        kernel_seconds = share["appels_par_pas"] * lut_cost
        result["part_du_pas"]["fraction_du_pas_estimee"] = kernel_seconds / share["s_par_pas"]
    (OUT / "bench_kernel.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
