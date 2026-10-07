"""Parité M4.2B(target_rule="geometric", rho=1, eta_beta=1) contre M4.2 —
mêmes paramètres, mêmes graines (PROMPT_M4_2B.md §12 : « à paramètres
identiques »). Ce test isole strictement l'effet de la refonte de code
(séparation _pair_rate/_pair_principal, signature de _run_market, table
loan_events) de tout changement institutionnel : avec target_rule=geometric,
_pair_principal reproduit EXACTEMENT la formule de M4.2 (même target, même
min(...)), donc le discret (naissances, morts, contrats, avalanches,
compteurs entiers) et le flottant (tolérance relative 1e-9) doivent
coïncider pas à pas.

Le passage à target_rule="arithmetic" (baseline M4.2B réelle) est comparé à
"geometric" sur grille dans test_arithmetic_institution.py, pas ici."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M4_2_ROOT = ROOT.parent / "m4_2_credit_soc"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(M4_2_ROOT))

from m4_2 import Config as M42Config, Simulation as M42Simulation  # noqa: E402
from m4_2b import Config, Simulation  # noqa: E402

REL_TOL = 1e-9
INT_FIELDS = {
    "t", "births", "deaths", "pop", "n_loans", "new_loans", "defaults",
    "roots_liquidity", "roots_insolvency", "roots_both", "cascade_iters",
    "n_avalanches", "max_avalanche",
}


def _pair(seed: int, steps: int, lam: float, sigma: float, delta: float, gamma: float):
    reference = M42Simulation(
        M42Config(seed=seed, T=steps, lam=lam, sigma=sigma, delta=delta, gamma=gamma, A=1.0)
    )
    candidate = Simulation(
        Config(
            seed=seed, T=steps, lam=lam, sigma=sigma, delta=delta, gamma=gamma, A=1.0,
            target_rule="geometric", rho=1.0, eta_beta=1.0,
        )
    )
    return reference, candidate


def assert_parity(seed: int, steps: int, lam: float, sigma: float, delta: float, gamma: float) -> float:
    reference, candidate = _pair(seed, steps, lam, sigma, delta, gamma)
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

    assert len(candidate.deaths) == len(reference.deaths)
    for actual_death, expected_death in zip(candidate.deaths, reference.deaths):
        for field in ("t", "id", "age", "cause", "death_iter", "deg_out", "deg_in"):
            assert actual_death[field] == expected_death[field]

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


def test_parity_m4_2_default_regime() -> None:
    """Régime M4.2 par défaut (delta=0.05, sigma=0.25) : parité stricte."""
    first = assert_parity(seed=0, steps=120, lam=10.0, sigma=0.25, delta=0.05, gamma=0.5)
    second = assert_parity(seed=7, steps=90, lam=18.0, sigma=0.31, delta=0.05, gamma=1.0 / 3.0)
    print(f"  écart flottant max : régime 1 = {first:.3e}, régime 2 = {second:.3e}")


def test_parity_m4_2b_baseline_regime() -> None:
    """Régime baseline M4.2B (delta=0.01, sigma=0.01) : la refonte de code ne
    change rien à géométrie constante, même sous la nouvelle baseline lente."""
    result = assert_parity(seed=3, steps=200, lam=30.0, sigma=0.01, delta=0.01, gamma=0.5)
    print(f"  écart flottant max (baseline M4.2B, target_rule=geometric) : {result:.3e}")


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
