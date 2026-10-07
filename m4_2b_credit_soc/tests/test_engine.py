"""Tests du moteur M4.2B : mécanique héritée de M4.2 + institution arithmétique
(PROMPT_M4_2B.md §2-3). La parité stricte avec M4.2 (target_rule="geometric",
rho=1, eta_beta=1) est couverte par test_parity_m4_2.py ; la comparaison
grille arithmétique/géométrique par test_arithmetic_institution.py."""

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

from m4_2b import Config, Simulation, run_and_save  # noqa: E402
from m4_2b.io import FIXED_RULES  # noqa: E402
from m4_2b.model import (  # noqa: E402
    INSOLVENCY_TOL,
    K_FLOOR,
    POOL_SIZE,
    _pair_principal,
    _pair_rate,
    _resolve_bankruptcies,
    _run_market,
    eta,
    net_worth,
)

GAMMAS = (0.2, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.9)
CAPITALS = (0.01, 1.0, 25.0, 9801.0, 1.0e4)


def _rel(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(1.0, abs(expected))


def test_marginal_return_matches_derivative() -> None:
    """m_γ(K) = A·γ·K^(γ-1) est la dérivée de F_γ(K) = A·K^γ (inchangé de M4.2)."""
    for A in (1.0, 0.375, 2.668):
        for gamma in GAMMAS:
            for K in CAPITALS:
                h = K * 1e-5
                numerical = (A * (K + h) ** gamma - A * (K - h) ** gamma) / (2 * h)
                analytical = A * gamma * K ** (gamma - 1.0)
                assert abs(numerical - analytical) <= 1e-6 * abs(analytical), (
                    gamma, K, numerical, analytical,
                )


def test_rate_is_geometric_mean_bracketed() -> None:
    """Le taux (INCHANGÉ, §3) reste √(m_ℓ·m_b), strictement entre m_ℓ et m_b."""
    for A in (1.0, 0.375):
        for gamma in GAMMAS:
            for lender_K, borrower_K in ((10.0, 1.0), (9801.0, 25.0), (2.0, 1.9)):
                rate = _pair_rate(lender_K, borrower_K, gamma, A)
                lender_rate = A * gamma * lender_K ** (gamma - 1.0)
                borrower_rate = A * gamma * borrower_K ** (gamma - 1.0)
                assert lender_rate < rate < borrower_rate, (
                    gamma, A, lender_rate, rate, borrower_rate,
                )
                expected = math.sqrt(lender_rate * borrower_rate)
                assert abs(rate - expected) <= 1e-12 * expected


def test_k_floor_is_applied_and_finite() -> None:
    for gamma in GAMMAS:
        rate = _pair_rate(100.0, 0.0, gamma, 1.0)
        rate_floor = _pair_rate(100.0, K_FLOOR, gamma, 1.0)
        assert math.isfinite(rate)
        assert rate == rate_floor


def test_geometric_rule_reproduces_m4_2_target() -> None:
    """target_rule="geometric" : K*(r) = √(K_ℓ·K_b) pour tout γ (formule M4.2)."""
    pairs = ((10.0, 1.0), (100.0, 25.0), (9801.0, 25.0), (1.0e4, 1.0e-3), (2.0, 1.9))
    for A in (1.0, 0.375, 2.668):
        for gamma in (0.05, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.95):
            for lender_K, borrower_K in pairs:
                rate = _pair_rate(lender_K, borrower_K, gamma, A)
                q = _pair_principal(lender_K, borrower_K, rate, gamma, A, "geometric")
                target = lender_K - q
                expected_target = math.sqrt(lender_K * borrower_K)
                assert abs(target - expected_target) <= 1e-9 * expected_target or abs(
                    borrower_K + q - expected_target
                ) <= 1e-9 * expected_target, (
                    gamma, A, lender_K, borrower_K, q, expected_target,
                )


def test_arithmetic_rule_equalizes_capitals_exactly() -> None:
    """§2 : q_A=(K_ℓ-K_b)/2, K_ℓ'=K_b' après transfert, sans passer par K*(r)."""
    pairs = ((100.0, 10.0), (9801.0, 25.0), (50.0, 49.0), (1000.0, 1.0), (200.0, 150.0))
    for gamma in GAMMAS:
        for lender_K, borrower_K in pairs:
            rate = _pair_rate(lender_K, borrower_K, gamma, 1.0)
            q = _pair_principal(lender_K, borrower_K, rate, gamma, 1.0, "arithmetic")
            expected_q = 0.5 * (lender_K - borrower_K)
            assert abs(q - expected_q) <= 1e-12 * max(1.0, expected_q)
            lender_after = lender_K - q
            borrower_after = borrower_K + q
            assert abs(lender_after - borrower_after) <= 1e-9 * max(1.0, lender_after)
            assert abs((lender_after + borrower_after) - (lender_K + borrower_K)) <= 1e-9 * max(
                1.0, lender_K + borrower_K
            )


def _fresh_simulation(gamma: float = 0.55, **overrides) -> Simulation:
    parameters = dict(gamma=gamma, lam=0.0, sigma=0.0, delta=0.01, T=1)
    parameters.update(overrides)
    return Simulation(Config(**parameters))


def test_loan_conserves_real_capital_both_rules() -> None:
    """Le transfert de principal conserve le capital réel total, quel que soit
    target_rule (arithmétique ou géométrique)."""
    for rule in ("arithmetic", "geometric"):
        simulation = _fresh_simulation(target_rule=rule)
        simulation.population.born(100.0, 0)
        simulation.population.born(4.0, 0)
        before = sum(simulation.population.K)
        market, events = _run_market(
            simulation.population, simulation.book, simulation.config, simulation.rng, 1
        )
        assert market["new_loans"] >= 1
        assert len(events) == market["new_loans"]
        after = sum(simulation.population.K)
        assert abs(after - before) <= 1e-9 * max(1.0, before)


def test_loan_conserves_individual_net_worth_both_rules() -> None:
    for rule in ("arithmetic", "geometric"):
        simulation = _fresh_simulation(target_rule=rule)
        lender = simulation.population.born(100.0, 0)
        borrower = simulation.population.born(4.0, 0)
        nw_before = {
            entity: net_worth(simulation.population, simulation.book, entity)
            for entity in (lender, borrower)
        }
        market, _events = _run_market(
            simulation.population, simulation.book, simulation.config, simulation.rng, 1
        )
        assert market["new_loans"] >= 1
        for entity in (lender, borrower):
            nw_after = net_worth(simulation.population, simulation.book, entity)
            assert abs(nw_after - nw_before[entity]) <= 1e-9 * max(1.0, abs(nw_before[entity]))


def test_merge_preserves_interest_flow() -> None:
    simulation = _fresh_simulation()
    lender = simulation.population.born(100.0, 0)
    borrower = simulation.population.born(4.0, 0)
    book = simulation.book
    loan_id_1, merged_1 = book.add(lender, borrower, 10.0, 0.04)
    loan_id_2, merged_2 = book.add(lender, borrower, 30.0, 0.08)
    assert not merged_1 and merged_2
    assert loan_id_1 == loan_id_2
    assert len(book.loans) == 1
    loan = next(iter(book.loans.values()))
    expected_flow = 10.0 * 0.04 + 30.0 * 0.08
    expected_rate = expected_flow / 40.0
    assert abs(book.due[borrower] - expected_flow) <= 1e-12 * expected_flow
    assert abs(float(loan[2]) - 40.0) <= 1e-12 * 40.0
    assert abs(float(loan[3]) - expected_rate) <= 1e-12 * expected_rate


def test_config_carries_new_institution_fields() -> None:
    names = {field.name for field in fields(Config)}
    assert "k" not in names
    assert {"target_rule", "rho", "eta_beta", "eta_n_ref"} <= names
    assert Config().target_rule == "arithmetic"
    assert Config().delta == 0.01 and Config().sigma == 0.01
    assert POOL_SIZE == 2
    assert FIXED_RULES["pool_size"] == 2
    try:
        Config(target_rule="bogus")
    except ValueError:
        pass
    else:
        raise AssertionError("target_rule invalide aurait dû lever ValueError")


def test_eta_family_reproduces_identity_and_scales() -> None:
    """ρ=1,β=1 : η_{ρ,β}(N)=N bit-identique à M4.2. Sinon ρ et β agissent
    comme attendu (échelle linéaire, puis élasticité non linéaire)."""
    assert eta(0) == 0.0
    assert eta(1, rho=1.0, beta=1.0) == 1.0
    assert eta(7, rho=1.0, beta=1.0) == 7.0
    assert eta(7, rho=2.0, beta=1.0) == 14.0
    assert eta(7, rho=0.5, beta=1.0) == 3.5
    # non linéaire : eta_{rho,beta}(N) = rho * n_ref * (N/n_ref)^beta
    value = eta(100, rho=2.0, beta=0.5, n_ref=25.0)
    expected = 2.0 * 25.0 * (100.0 / 25.0) ** 0.5
    assert abs(value - expected) <= 1e-12

    for population_size in (0, 1):
        simulation = _fresh_simulation()
        for _ in range(population_size):
            simulation.population.born(50.0, 0)
        state_before = copy.deepcopy(simulation.rng.bit_generator.state)
        market, events = _run_market(
            simulation.population, simulation.book, simulation.config, simulation.rng, 1
        )
        assert market["pool"] == population_size
        assert market["rounds"] == 0
        assert market["new_loans"] == 0
        assert events == []
        assert simulation.rng.bit_generator.state == state_before


def test_market_counters_distinguish_outcomes() -> None:
    """target_rule="geometric" reproduit exactement le comportement M4.2 (round
    1 crée l'arête, round 2 fusionne, car seul le bras de l'emprunteuse
    atteint la cible)."""
    simulation = _fresh_simulation(target_rule="geometric")
    simulation.population.born(100.0, 0)
    simulation.population.born(25.0, 0)
    market, events = _run_market(
        simulation.population, simulation.book, simulation.config, simulation.rng, 1
    )
    assert market["pool"] == 2
    assert market["rounds"] == 2
    assert market["new_loans"] == 2
    assert market["new_edges"] == 1
    assert market["merges"] == 1
    assert market["new_loans"] == market["new_edges"] + market["merges"]
    total_principal = sum(float(loan[2]) for loan in simulation.book.loans.values())
    assert abs(market["volume"] - total_principal) <= 1e-12 * max(1.0, total_principal)
    assert len(events) == 2

    sterile = _fresh_simulation(target_rule="geometric")
    sterile.population.born(50.0, 0)
    sterile.population.born(50.0, 0)
    market, events = _run_market(
        sterile.population, sterile.book, sterile.config, sterile.rng, 1
    )
    assert market["rounds"] == 2
    assert market["new_loans"] == 0
    assert events == []
    assert len(sterile.book.loans) == 0


def test_arithmetic_rule_self_terminates_after_one_round() -> None:
    """Différence structurelle avec le géométrique (§2) : l'arithmétique
    égalise EXACTEMENT les deux capitaux en un round, donc le round suivant
    entre la même paire devient stérile (K_ℓ<=K_b déclenche le "continue")
    au lieu de fusionner un second petit prêt."""
    simulation = _fresh_simulation(target_rule="arithmetic")
    simulation.population.born(100.0, 0)
    simulation.population.born(25.0, 0)
    market, events = _run_market(
        simulation.population, simulation.book, simulation.config, simulation.rng, 1
    )
    assert market["pool"] == 2
    assert market["rounds"] == 2
    assert market["new_loans"] == 1
    assert market["new_edges"] == 1
    assert market["merges"] == 0
    assert len(events) == 1
    lender, borrower = simulation.population.living()[:2]
    assert abs(simulation.population.K[lender] - simulation.population.K[borrower]) <= 1e-9

    sterile = _fresh_simulation(target_rule="arithmetic")
    sterile.population.born(50.0, 0)
    sterile.population.born(50.0, 0)
    market, events = _run_market(
        sterile.population, sterile.book, sterile.config, sterile.rng, 1
    )
    assert market["rounds"] == 2
    assert market["new_loans"] == 0
    assert events == []
    assert len(sterile.book.loans) == 0


def test_loan_events_diagnostics_are_self_consistent() -> None:
    """§3 : rq_over_Kb et rq_over_F recalculables depuis q, r, Kb_after."""
    simulation = _fresh_simulation(gamma=0.5, target_rule="arithmetic")
    simulation.population.born(9801.0, 0)
    simulation.population.born(25.0, 0)
    market, events = _run_market(
        simulation.population, simulation.book, simulation.config, simulation.rng, 1
    )
    assert len(events) == 1
    event = events[0]
    rq = event["r"] * event["q"]
    assert abs(rq - event["rq"]) <= 1e-9 * max(1.0, rq)
    assert abs(event["rq_over_Kb"] - rq / event["Kb_after"]) <= 1e-9
    production_after = 1.0 * event["Kb_after"] ** 0.5
    assert abs(event["rq_over_F"] - rq / production_after) <= 1e-6 * max(1.0, event["rq_over_F"])
    # Pathologie attendue (rapport final) : service > production de l'emprunteuse
    # sur ce pas pour un newborn K0=25 face à une prêteuse proche de K*_aut.
    assert event["rq_over_F"] > 1.0


def test_book_invariants_no_orphans() -> None:
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
    simulation = _fresh_simulation()
    entity_a = simulation.population.born(1.0, 0)
    entity_b = simulation.population.born(0.0, 0)
    entity_d = simulation.population.born(2.0, 0)
    book = simulation.book
    book.add(entity_a, entity_b, 10.0, 0.05)
    book.add(entity_d, entity_a, 8.0, 0.05)
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

    for entity in simulation.population.living():
        assert net_worth(simulation.population, book, entity) >= -INSOLVENCY_TOL
        assert not simulation.population.defaulted[entity]
    assert book.consistency_errors(simulation.population.alive) == []


def test_seed_reproducibility() -> None:
    config = Config(gamma=0.6, lam=15.0, seed=11, T=80)
    first = Simulation(config)
    second = Simulation(config)
    first.run()
    second.run()
    assert first.series == second.series
    assert first.avalanches == second.avalanches
    assert first.deaths == second.deaths
    assert first.loan_events == second.loan_events

    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        run_and_save(config, base / "a", snapshot_every=0, individual_every=0)
        run_and_save(config, base / "b", snapshot_every=0, individual_every=0)
        for name in ("series.csv", "avalanches.csv", "deaths.csv"):
            assert (base / "a" / name).read_bytes() == (base / "b" / name).read_bytes()


def test_recording_options_are_neutral() -> None:
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


def test_loan_events_written_and_readable() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        simulation, summary = run_and_save(
            Config(gamma=0.5, lam=15.0, seed=2, T=60),
            temporary,
            snapshot_every=0,
            individual_every=0,
        )
        with gzip.open(
            Path(temporary) / "loan_events.csv.gz", "rt", encoding="utf-8"
        ) as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == summary["loan_events_total"]
        # streamé pas par pas puis vidé pour borner la mémoire (JOURNAL.md,
        # garde-fous mémoire) : la liste en mémoire est vide en fin de run.
        assert simulation.loan_events == []
        if rows:
            row = rows[0]
            assert {"t", "lender", "borrower", "q", "r", "rq", "Kb_after",
                     "rq_over_Kb", "rq_over_F"} <= set(row)


def test_nonzero_partial_interest_payment_is_proportional() -> None:
    simulation = Simulation(Config(gamma=0.5, lam=0.0, sigma=0.0, delta=0.0, T=1))
    lender_a = simulation.population.born(100.0, 0)
    lender_b = simulation.population.born(100.0, 0)
    borrower = simulation.population.born(4.0, 0)
    simulation.book.add(lender_a, borrower, principal=10.0, rate=0.4)
    simulation.book.add(lender_b, borrower, principal=20.0, rate=0.4)

    simulation.step()
    assert simulation.population.int_in[lender_a] == 2.0
    assert simulation.population.int_in[lender_b] == 4.0
    assert simulation.population.int_out[borrower] == 6.0
    assert not simulation.population.alive[borrower]


def test_global_balance_and_book() -> None:
    for gamma in (0.4, 0.65):
        for rule in ("arithmetic", "geometric"):
            simulation = Simulation(
                Config(gamma=gamma, lam=10.0, seed=3, T=120, target_rule=rule)
            )
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
                    gamma, rule, simulation.t, change, flows,
                )
                assert simulation.book.consistency_errors(simulation.population.alive) == []
                previous_capital = row["K_tot"]


def test_autarkic_fixed_point() -> None:
    """Sans choc ni crédit, K converge vers ((1-δ)A/δ)^(1/(1-γ)) — inchangé par
    l'institution de principal (aucun crédit dans ce scénario). Vérifié à la
    baseline δ=0.01 : la relaxation y est ~5x plus lente qu'à δ=0.05 (M4.2) —
    T=10000 est nécessaire pour retomber sous 1e-9 relatif (vérifié
    numériquement, voir report/ pour la discussion complète du temps de
    relaxation autarcique à cette baseline)."""
    for gamma in (1.0 / 3.0, 0.5, 2.0 / 3.0):
        config = Config(gamma=gamma, lam=0.0, sigma=0.0, delta=0.01, T=10000)
        simulation = Simulation(config)
        entity = simulation.population.born(config.K0, 0)
        while simulation.t < config.T and simulation.status == "ok":
            simulation.step()
        capital = simulation.population.K[entity]
        expected = ((1.0 - config.delta) * config.A / config.delta) ** (
            1.0 / (1.0 - gamma)
        )
        assert _rel(capital, expected) <= 1e-9, (gamma, capital, expected)
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
