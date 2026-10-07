"""Parité M4.3 / M4.2B : `m4_3/model.py` et `m4_3/io.py` sont des copies
octet pour octet de `m4_2b_credit_soc/m4_2b/{model,io}.py` (§8,
`diff` vide, vérifié à la copie). Ce test n'existe donc pas pour détecter
un écart de comportement aujourd'hui (impossible, même code source) mais
comme garde-fou de RÉGRESSION : si `m4_3/model.py` est un jour modifié
(ablation §4) sans que ce test soit mis à jour en conséquence, il doit
échouer bruyamment plutôt que de laisser une dérive silencieuse.

Contrairement à `test_parity_m4_2.py` de M4.2B (tolérance 1e-9, une seule
institution géométrique — les deux moteurs comparés avaient un code
différent), on teste ici l'ÉGALITÉ EXACTE sur les deux `target_rule`, même
RNG (`random.Random`/`numpy.random.Generator` déterministes par graine)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M4_2B_ROOT = ROOT.parent / "m4_2b_credit_soc"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(M4_2B_ROOT))

from m4_2b import Config as RefConfig, Simulation as RefSimulation  # noqa: E402
from m4_3 import Config, Simulation  # noqa: E402

INT_FIELDS = {
    "t", "births", "deaths", "pop", "n_loans", "new_loans", "defaults",
    "roots_liquidity", "roots_insolvency", "roots_both", "cascade_iters",
    "n_avalanches", "max_avalanche",
}


def assert_exact_parity(seed: int, steps: int, target_rule: str) -> None:
    kwargs = dict(seed=seed, T=steps, lam=30.0, sigma=0.01, delta=0.01, gamma=0.5, A=1.0,
                  target_rule=target_rule, rho=1.0, eta_beta=1.0)
    reference = RefSimulation(RefConfig(**kwargs))
    candidate = Simulation(Config(**kwargs))

    for _ in range(steps):
        assert candidate.step() == reference.step()
        expected = reference.series[-1]
        actual = candidate.series[-1]
        assert actual == expected, (candidate.t, "series mismatch")

        pop_new, pop_ref = candidate.population, reference.population
        assert pop_new.alive == pop_ref.alive
        assert list(pop_new.K) == list(pop_ref.K)

        book_new, book_ref = candidate.book, reference.book
        assert book_new.loans == book_ref.loans
        assert book_new.claims == book_ref.claims
        assert book_new.debts == book_ref.debts

    assert candidate.deaths == reference.deaths
    assert candidate.avalanches == reference.avalanches
    print(f"assert_exact_parity(seed={seed}, T={steps}, target_rule={target_rule}) OK")


def test_parity_arithmetic():
    for seed in (0, 1, 7):
        assert_exact_parity(seed, steps=200, target_rule="arithmetic")


def test_parity_geometric():
    for seed in (0, 1, 7):
        assert_exact_parity(seed, steps=200, target_rule="geometric")


if __name__ == "__main__":
    test_parity_arithmetic()
    test_parity_geometric()
    print("ALL TESTS PASSED")
