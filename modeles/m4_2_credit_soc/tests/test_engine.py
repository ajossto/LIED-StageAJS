"""Tests du moteur M4.2 : points 1 à 13 du cahier des charges, bilan global
et point fixe autarcique discret. (Le point 14 — estimateurs statistiques —
est couvert par test_stats.py ; la parité M4B par test_parity_m4b.py.)"""

from __future__ import annotations

import copy
import csv
import gzip
import json
import math
import sys
import tempfile
from dataclasses import fields
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from m4_2 import Config, Simulation, run_and_save  # noqa: E402
from m4_2.io import FIXED_RULES  # noqa: E402
from m4_2.model import (  # noqa: E402
    INSOLVENCY_TOL,
    K_FLOOR,
    POOL_SIZE,
    _pair_terms,
    _resolve_bankruptcies,
    _run_market,
    eta,
    net_worth,
)

GAMMAS = (0.2, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.9)
CAPITALS = (0.01, 1.0, 25.0, 361.0, 1.0e4)


def _rel(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(1.0, abs(expected))


def test_marginal_return_matches_derivative() -> None:
    """Point 1 : m_γ(K) = A·γ·K^(γ-1) est bien la dérivée de F_γ(K) = A·K^γ."""
    for A in (1.0, 0.375, 2.668):
        for gamma in GAMMAS:
            for K in CAPITALS:
                h = K * 1e-5
                numerical = (A * (K + h) ** gamma - A * (K - h) ** gamma) / (2 * h)
                analytical = A * gamma * K ** (gamma - 1.0)
                assert abs(numerical - analytical) <= 1e-6 * abs(analytical), (
                    gamma, K, numerical, analytical,
                )


def test_target_capital_is_geometric_mean() -> None:
    """Point 2 : K*(r) = sqrt(K_ℓ·K_b) pour tout γ et tout A."""
    pairs = ((10.0, 1.0), (100.0, 25.0), (361.0, 25.0), (1.0e4, 1.0e-3), (2.0, 1.9))
    for A in (1.0, 0.375, 2.668):
        for gamma in (0.05, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.95):
            for lender_K, borrower_K in pairs:
                _, target = _pair_terms(lender_K, borrower_K, gamma, A)
                expected = math.sqrt(lender_K * borrower_K)
                assert abs(target - expected) <= 1e-12 * expected, (
                    gamma, A, lender_K, borrower_K, target, expected,
                )


def test_rate_bracketed_by_marginal_returns() -> None:
    """Point 3 : m_ℓ < r < m_b strictement quand K_ℓ > K_b."""
    for A in (1.0, 0.375):
        for gamma in GAMMAS:
            for lender_K, borrower_K in ((10.0, 1.0), (361.0, 25.0), (2.0, 1.9)):
                rate, _ = _pair_terms(lender_K, borrower_K, gamma, A)
                lender_rate = A * gamma * lender_K ** (gamma - 1.0)
                borrower_rate = A * gamma * borrower_K ** (gamma - 1.0)
                assert lender_rate < rate < borrower_rate, (
                    gamma, A, lender_rate, rate, borrower_rate,
                )


def test_k_floor_is_applied_and_finite() -> None:
    """La tolérance K_FLOOR (documentée dans la spec) borne le taux à K = 0."""
    for gamma in GAMMAS:
        rate, target = _pair_terms(100.0, 0.0, gamma, 1.0)
        rate_floor, target_floor = _pair_terms(100.0, K_FLOOR, gamma, 1.0)
        assert math.isfinite(rate) and math.isfinite(target)
        assert rate == rate_floor and target == target_floor


def _fresh_simulation(gamma: float = 0.55, **overrides) -> Simulation:
    parameters = dict(gamma=gamma, lam=0.0, sigma=0.0, T=1)
    parameters.update(overrides)
    return Simulation(Config(**parameters))


def test_loan_conserves_real_capital() -> None:
    """Point 4 : le transfert de principal conserve le capital réel total."""
    simulation = _fresh_simulation()
    simulation.population.born(100.0, 0)
    simulation.population.born(4.0, 0)
    before = sum(simulation.population.K)
    market = _run_market(
        simulation.population, simulation.book, simulation.config, simulation.rng
    )
    assert market["new_loans"] >= 1
    after = sum(simulation.population.K)
    assert abs(after - before) <= 1e-9 * max(1.0, before)


def test_loan_conserves_individual_net_worth() -> None:
    """Point 5 : la valeur nette de chaque partie est inchangée au prêt."""
    simulation = _fresh_simulation()
    lender = simulation.population.born(100.0, 0)
    borrower = simulation.population.born(4.0, 0)
    nw_before = {
        entity: net_worth(simulation.population, simulation.book, entity)
        for entity in (lender, borrower)
    }
    market = _run_market(
        simulation.population, simulation.book, simulation.config, simulation.rng
    )
    assert market["new_loans"] >= 1
    for entity in (lender, borrower):
        nw_after = net_worth(simulation.population, simulation.book, entity)
        assert abs(nw_after - nw_before[entity]) <= 1e-9 * max(1.0, abs(nw_before[entity]))


def test_merge_preserves_interest_flow() -> None:
    """Point 6 : la fusion garde due = Σ qᵢ·rᵢ et le taux moyen pondéré."""
    simulation = _fresh_simulation()
    lender = simulation.population.born(100.0, 0)
    borrower = simulation.population.born(4.0, 0)
    book = simulation.book
    book.add(lender, borrower, 10.0, 0.04)
    book.add(lender, borrower, 30.0, 0.08)
    assert len(book.loans) == 1
    loan = next(iter(book.loans.values()))
    expected_flow = 10.0 * 0.04 + 30.0 * 0.08
    expected_rate = expected_flow / 40.0
    assert abs(book.due[borrower] - expected_flow) <= 1e-12 * expected_flow
    assert abs(float(loan[2]) - 40.0) <= 1e-12 * 40.0
    assert abs(float(loan[3]) - expected_rate) <= 1e-12 * expected_rate


def test_pool_fixed_at_two_and_absent_from_config() -> None:
    """Point 7 : k ≡ 2 est constitutif, absent de la configuration scientifique."""
    names = {field.name for field in fields(Config)}
    assert "k" not in names
    assert "gamma" in names and "A" in names
    assert "k" not in Config().to_dict()
    assert POOL_SIZE == 2
    assert FIXED_RULES["pool_size"] == 2


def test_eta_identity_including_empty_and_singleton() -> None:
    """Point 8 : η est l'identité ; à N ∈ {0, 1} aucun round, aucun tirage RNG."""
    assert eta(0) == 0.0
    assert eta(1) == 1.0
    assert eta(7) == 7.0

    for population_size in (0, 1):
        simulation = _fresh_simulation()
        for _ in range(population_size):
            simulation.population.born(50.0, 0)
        state_before = copy.deepcopy(simulation.rng.bit_generator.state)
        market = _run_market(
            simulation.population, simulation.book, simulation.config, simulation.rng
        )
        assert market["pool"] == population_size
        assert market["rounds"] == 0
        assert market["new_loans"] == 0
        assert simulation.rng.bit_generator.state == state_before


def test_market_counters_distinguish_outcomes() -> None:
    """Point 9 : rounds, transactions, nouvelles arêtes et fusions distincts."""
    # Deux entités inégales : round 1 crée l'arête, round 2 fusionne.
    simulation = _fresh_simulation()
    simulation.population.born(100.0, 0)
    simulation.population.born(25.0, 0)
    market = _run_market(
        simulation.population, simulation.book, simulation.config, simulation.rng
    )
    assert market["pool"] == 2
    assert market["rounds"] == 2
    assert market["new_loans"] == 2
    assert market["new_edges"] == 1
    assert market["merges"] == 1
    assert market["new_loans"] == market["new_edges"] + market["merges"]
    total_principal = sum(float(loan[2]) for loan in simulation.book.loans.values())
    assert abs(market["volume"] - total_principal) <= 1e-12 * max(1.0, total_principal)

    # Deux entités égales : les rounds sont stériles mais comptés.
    sterile = _fresh_simulation()
    sterile.population.born(50.0, 0)
    sterile.population.born(50.0, 0)
    market = _run_market(sterile.population, sterile.book, sterile.config, sterile.rng)
    assert market["rounds"] == 2
    assert market["new_loans"] == 0
    assert len(sterile.book.loans) == 0


def test_book_invariants_no_orphans() -> None:
    """Point 10 : créances = dettes, agrégats exacts, aucun contrat orphelin."""
    simulation = Simulation(Config(gamma=0.55, lam=20.0, seed=4, T=150))
    while simulation.t < simulation.config.T and simulation.status == "ok":
        simulation.step()
    book = simulation.book
    assert book.consistency_errors(simulation.population.alive) == []
    assert set(book.by_pair.values()) == set(book.loans.keys())
    referenced = set()
    for loans in book.by_lender.values():
        referenced |= loans
    for loans in book.by_borrower.values():
        referenced |= loans
    assert referenced == set(book.loans.keys())


def test_cascade_reaches_fixed_point() -> None:
    """Point 11 : résolution itérative complète d'une chaîne d'expositions."""
    simulation = _fresh_simulation()
    entity_a = simulation.population.born(1.0, 0)
    entity_b = simulation.population.born(0.0, 0)
    entity_d = simulation.population.born(2.0, 0)
    book = simulation.book
    book.add(entity_a, entity_b, 10.0, 0.05)   # A prête 10 à B.
    book.add(entity_d, entity_a, 8.0, 0.05)    # D prête 8 à A.
    # B : nw = 0 - 10 < 0 (racine d'insolvabilité) ; sa mort coûte 10 à A,
    # dont nw passe de 3 à -7 (génération 2) ; D perd 8 mais survit (nw = 2).
    dead, ledger = _resolve_bankruptcies(simulation.population, book)

    assert dead == [entity_b, entity_a]
    assert ledger["iterations"] == 2
    assert ledger["death_iteration"] == {entity_b: 1, entity_a: 2}
    assert ledger["roots"] == {entity_b: "insolvency"}
    assert abs(ledger["claim_losses"] - 18.0) <= 1e-12
    assert abs(ledger["destroyed"] - 1.0) <= 1e-12

    assert len(ledger["avalanches"]) == 1
    avalanche = ledger["avalanches"][0]
    assert avalanche["size"] == 2
    assert avalanche["depth"] == 2
    assert avalanche["n_roots"] == 1
    assert avalanche["members"] == sorted([entity_a, entity_b])
    assert abs(avalanche["volume_j"] - 18.0) <= 1e-12

    # Point fixe : plus aucune vivante insolvable ni défaillante.
    for entity in simulation.population.living():
        assert net_worth(simulation.population, book, entity) >= -INSOLVENCY_TOL
        assert not simulation.population.defaulted[entity]
    assert book.consistency_errors(simulation.population.alive) == []


def test_seed_reproducibility() -> None:
    """Point 12 : même graine, mêmes trajectoires — en mémoire et sur disque."""
    config = Config(gamma=0.6, lam=15.0, seed=11, T=80)
    first = Simulation(config)
    second = Simulation(config)
    first.run()
    second.run()
    assert first.series == second.series
    assert first.avalanches == second.avalanches
    assert first.deaths == second.deaths

    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        run_and_save(config, base / "a", snapshot_every=0, individual_every=0)
        run_and_save(config, base / "b", snapshot_every=0, individual_every=0)
        for name in ("series.csv", "avalanches.csv", "deaths.csv"):
            assert (base / "a" / name).read_bytes() == (base / "b" / name).read_bytes()


def test_recording_options_are_neutral() -> None:
    """Point 13 : instantanés et mesures individuelles sans effet dynamique."""
    config = Config(gamma=0.45, seed=9, lam=10.0, T=100)
    plain = Simulation(config)
    recorded = Simulation(config)
    plain.run()
    recorded.run(
        snapshot_times=(25, 50, 75, 100),
        on_snapshot=lambda _t, _entities, _network: None,
        on_step=lambda simulation: simulation.individual_records(),
    )
    assert recorded.series == plain.series
    assert recorded.avalanches == plain.avalanches

    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        run_and_save(config, base / "full", snapshot_every=25, individual_every=1)
        run_and_save(config, base / "light", snapshot_every=0, individual_every=0)
        series_full = (base / "full" / "series.csv").read_bytes()
        series_light = (base / "light" / "series.csv").read_bytes()
        assert series_full == series_light


def test_individual_frequency_can_be_reduced() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        simulation, summary = run_and_save(
            Config(gamma=0.5, lam=10.0, seed=1, T=11),
            temporary,
            snapshot_every=0,
            individual_every=3,
        )
        with gzip.open(
            Path(temporary) / "individual_series.csv.gz", "rt", encoding="utf-8"
        ) as stream:
            rows = list(csv.DictReader(stream))
        living_times = {int(row["t"]) for row in rows if row["alive"] == "1"}
        assert living_times <= {3, 6, 9, 11}
        expected = sum(row["deaths"] for row in simulation.series)
        expected += sum(
            row["pop"]
            for row in simulation.series
            if row["t"] % 3 == 0 or row["t"] == simulation.t
        )
        assert len(rows) == expected == summary["individual_rows"]


def test_nonzero_partial_interest_payment_is_proportional() -> None:
    """Un défaut distribue tout le K disponible, proportionnellement (γ = 1/2)."""
    simulation = Simulation(Config(gamma=0.5, lam=0.0, sigma=0.0, delta=0.0, T=1))
    lender_a = simulation.population.born(100.0, 0)
    lender_b = simulation.population.born(100.0, 0)
    borrower = simulation.population.born(4.0, 0)
    simulation.book.add(lender_a, borrower, principal=10.0, rate=0.4)
    simulation.book.add(lender_b, borrower, principal=20.0, rate=0.4)

    # Après production, l'emprunteuse a K = 4 + sqrt(4) = 6 et doit 12 :
    # ratio 1/2, donc paiements respectifs 2 et 4.
    simulation.step()
    assert simulation.population.int_in[lender_a] == 2.0
    assert simulation.population.int_in[lender_b] == 4.0
    assert simulation.population.int_out[borrower] == 6.0
    assert not simulation.population.alive[borrower]


def test_global_balance_and_book() -> None:
    """Identité ΔK = injecté + choc + production − dépréciation − destruction,
    vérifiée hors du cas M4B (γ = 0,4 puis γ = 0,65)."""
    for gamma in (0.4, 0.65):
        simulation = Simulation(Config(gamma=gamma, lam=10.0, seed=3, T=120))
        previous_capital = 0.0
        while simulation.t < simulation.config.T and simulation.status == "ok":
            simulation.step()
            row = simulation.series[-1]
            change = row["K_tot"] - previous_capital
            flows = (
                row["injected"]
                + row["shock_gain"]
                + row["prod_tot"]
                - row["depreciated"]
                - row["destroyed"]
            )
            assert abs(change - flows) <= 1e-6 * max(1.0, abs(row["K_tot"])), (
                gamma, simulation.t, change, flows,
            )
            assert simulation.book.consistency_errors(simulation.population.alive) == []
            previous_capital = row["K_tot"]


def test_autarkic_fixed_point() -> None:
    """Sans choc ni crédit, K converge vers ((1-δ)A/δ)^(1/(1-γ)) — relation
    discrète exacte (production avant dépréciation), pas son approximation
    continue."""
    for gamma in (1.0 / 3.0, 0.5, 2.0 / 3.0):
        config = Config(gamma=gamma, lam=0.0, sigma=0.0, T=2500)
        simulation = Simulation(config)
        entity = simulation.population.born(config.K0, 0)
        while simulation.t < config.T and simulation.status == "ok":
            simulation.step()
        capital = simulation.population.K[entity]
        expected = ((1.0 - config.delta) * config.A / config.delta) ** (
            1.0 / (1.0 - gamma)
        )
        assert _rel(capital, expected) <= 1e-9, (gamma, capital, expected)
        # La relation de point fixe discrète est satisfaite par l'état atteint.
        image = (1.0 - config.delta) * (capital + config.A * capital**gamma)
        assert _rel(image, capital) <= 1e-9


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
