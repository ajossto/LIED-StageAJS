"""Parité M4.2(γ=1/2, A=1) contre M4B(k=2) — mêmes paramètres, mêmes graines.

Le discret (naissances, morts, contrats, avalanches, compteurs entiers) doit
être identique ; le flottant est comparé en tolérance relative 1e-9 : les
formes génériques A·γ·K^(γ-1) et (A·γ/r)^(1/(1-γ)) peuvent différer d'un ULP
des formes M4B 1/(2√K) et (1/(2r))², et le cahier des charges interdit une
branche de compatibilité fabriquant l'égalité bit à bit. La sonde longue
(non bloquante) mesure et affiche l'écart accumulé et l'éventuel premier pas
de divergence discrète ; son résultat est consigné dans report/spec_m4_2.tex.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M4B_ROOT = ROOT.parent / "m4b_credit_soc_mini"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(M4B_ROOT))

from m4b import Config as M4BConfig, Simulation as M4BSimulation  # noqa: E402
from m4_2 import Config, Simulation  # noqa: E402

REL_TOL = 1e-9
INT_FIELDS = {
    "t", "births", "deaths", "pop", "n_loans", "new_loans", "defaults",
    "roots_liquidity", "roots_insolvency", "roots_both", "cascade_iters",
    "n_avalanches", "max_avalanche",
}


def _close(actual: float, expected: float, tolerance: float = REL_TOL) -> bool:
    return abs(actual - expected) <= tolerance * max(1.0, abs(expected))


def _pair(seed: int, steps: int, lam: float, sigma: float):
    reference = M4BSimulation(
        M4BConfig(seed=seed, T=steps, lam=lam, sigma=sigma, k=2)
    )
    candidate = Simulation(
        Config(seed=seed, T=steps, lam=lam, sigma=sigma, gamma=0.5, A=1.0)
    )
    return reference, candidate


def assert_parity(seed: int, steps: int, lam: float, sigma: float) -> float:
    reference, candidate = _pair(seed, steps, lam, sigma)
    max_rel = 0.0

    for _ in range(steps):
        assert candidate.step() == reference.step()
        expected = reference.series[-1]
        actual = candidate.series[-1]
        for field, value in expected.items():
            if field in INT_FIELDS:
                assert actual[field] == value, (candidate.t, field, actual[field], value)
            else:
                deviation = abs(actual[field] - value) / max(1.0, abs(value))
                max_rel = max(max_rel, deviation)
                assert deviation <= REL_TOL, (candidate.t, field, actual[field], value)
        # M4.2 ajoute les compteurs de marché ; new_loans (commun) est déjà
        # comparé, et rounds = taille du pool par construction (η identité).
        assert actual["mkt_new_edges"] + actual["mkt_merges"] == actual["new_loans"]

        pop_new, pop_ref = candidate.population, reference.population
        assert pop_new.alive == pop_ref.alive
        assert pop_new.birth == pop_ref.birth
        assert pop_new.defaulted == pop_ref.defaulted
        for entity, expected_K in enumerate(pop_ref.K):
            deviation = abs(pop_new.K[entity] - expected_K) / max(1.0, abs(expected_K))
            max_rel = max(max_rel, deviation)
            assert deviation <= REL_TOL, (candidate.t, entity, pop_new.K[entity], expected_K)

        book_new, book_ref = candidate.book, reference.book
        assert set(book_new.loans) == set(book_ref.loans)
        assert set(book_new.by_pair) == set(book_ref.by_pair)
        for loan_id, record in book_ref.loans.items():
            candidate_record = book_new.loans[loan_id]
            assert int(candidate_record[0]) == int(record[0])
            assert int(candidate_record[1]) == int(record[1])
            for slot in (2, 3):
                deviation = abs(
                    float(candidate_record[slot]) - float(record[slot])
                ) / max(1.0, abs(float(record[slot])))
                max_rel = max(max_rel, deviation)
                assert deviation <= REL_TOL, (candidate.t, loan_id, slot)
        for aggregate in ("claims", "debts", "due"):
            current = getattr(book_new, aggregate)
            target = getattr(book_ref, aggregate)
            for entity in set(current) | set(target):
                deviation = abs(current[entity] - target[entity]) / max(
                    1.0, abs(target[entity])
                )
                max_rel = max(max_rel, deviation)
                assert deviation <= REL_TOL, (candidate.t, aggregate, entity)

    # Historique des morts : structure discrète identique.
    assert len(candidate.deaths) == len(reference.deaths)
    for actual_death, expected_death in zip(candidate.deaths, reference.deaths):
        for field in ("t", "id", "age", "cause", "death_iter", "deg_out", "deg_in"):
            assert actual_death[field] == expected_death[field]

    # Avalanches : structure discrète identique, volume en tolérance.
    assert len(candidate.avalanches) == len(reference.avalanches)
    for actual_row, expected_row in zip(candidate.avalanches, reference.avalanches):
        for field in ("avalanche_id", "t", "size", "depth", "n_roots", "causes"):
            assert actual_row[field] == expected_row[field]
        deviation = abs(actual_row["volume_j"] - expected_row["volume_j"]) / max(
            1.0, abs(expected_row["volume_j"])
        )
        max_rel = max(max_rel, deviation)
        assert deviation <= REL_TOL
    assert candidate.avalanche_members == reference.avalanche_members
    return max_rel


def test_parity_two_regimes() -> None:
    first = assert_parity(seed=0, steps=120, lam=10.0, sigma=0.25)
    second = assert_parity(seed=7, steps=90, lam=18.0, sigma=0.31)
    print(f"  écart flottant max : régime 1 = {first:.3e}, régime 2 = {second:.3e}")


def test_divergence_probe_long_run() -> None:
    """Sonde non bloquante : premier pas de divergence discrète (s'il existe)
    et écart flottant accumulé sur un run long λ=30. Documentée dans la spec."""
    steps = 1000
    reference, candidate = _pair(seed=1, steps=steps, lam=30.0, sigma=0.25)
    first_discrete_divergence = None
    max_rel = 0.0
    for _ in range(steps):
        status_new = candidate.step()
        status_ref = reference.step()
        expected = reference.series[-1]
        actual = candidate.series[-1]
        discrete_equal = status_new == status_ref and all(
            actual[field] == expected[field] for field in INT_FIELDS
        )
        if not discrete_equal:
            first_discrete_divergence = candidate.t
            break
        for field in expected:
            if field not in INT_FIELDS:
                max_rel = max(
                    max_rel,
                    abs(actual[field] - expected[field]) / max(1.0, abs(expected[field])),
                )
    if first_discrete_divergence is None:
        print(
            f"  sonde λ=30, T={steps} : aucune divergence discrète, "
            f"écart flottant max (séries) = {max_rel:.3e}"
        )
    else:
        print(
            f"  sonde λ=30 : première divergence discrète à t={first_discrete_divergence}, "
            f"écart flottant max avant divergence = {max_rel:.3e}"
        )


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
