"""Parité avec M4 et invariants propres au moteur minimal."""

from __future__ import annotations

import csv
import gzip
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
M4_SRC = ROOT.parent / "m4_credit_soc_fable" / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(M4_SRC))

from m4 import M4Config, Simulation as M4Simulation  # noqa: E402
from m4b import Config, Simulation, run_and_save  # noqa: E402


def assert_same_baseline(seed: int, steps: int, lam: float, sigma: float, k: int) -> None:
    reference = M4Simulation(M4Config(seed=seed, T=steps, lam=lam, sigma=sigma, k=k))
    mini = Simulation(Config(seed=seed, T=steps, lam=lam, sigma=sigma, k=k))

    for _ in range(steps):
        assert mini.step() == reference.step()
        expected = reference.series[-1]
        actual = mini.series[-1]
        assert actual.keys() <= expected.keys()
        for field, value in actual.items():
            assert value == expected[field], (mini.t, field, value, expected[field])

        assert mini.population.K == reference.pop.K
        assert mini.population.alive == reference.pop.alive
        assert mini.population.birth == reference.pop.birth
        assert mini.population.defaulted == reference.pop.defaulted
        assert mini.book.loans == reference.book.loans
        assert dict(mini.book.claims) == dict(reference.book.claims)
        assert dict(mini.book.debts) == dict(reference.book.debts)
        assert dict(mini.book.due) == dict(reference.book.due)

    actual_avalanches = [
        {
            key: value
            for key, value in row.items()
            if key not in {"avalanche_id", "volume_j"}
        }
        for row in mini.avalanches
    ]
    assert actual_avalanches == reference.avalanche_log


def test_exact_parity_two_regimes() -> None:
    assert_same_baseline(seed=0, steps=120, lam=10.0, sigma=0.25, k=3)
    assert_same_baseline(seed=7, steps=90, lam=18.0, sigma=0.31, k=2)


def test_global_balance_and_book() -> None:
    simulation = Simulation(Config(seed=3, T=180))
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
        assert abs(change - flows) <= 1e-6 * max(1.0, abs(row["K_tot"]))
        assert simulation.book.consistency_errors(simulation.population.alive) == []
        previous_capital = row["K_tot"]


def test_nonzero_partial_interest_payment_is_proportional() -> None:
    """Un défaut distribue tout le K disponible, sans paiement nul artificiel."""
    simulation = Simulation(Config(lam=0.0, sigma=0.0, delta=0.0, T=1, k=3))
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


def test_snapshots_do_not_change_dynamics() -> None:
    config = Config(seed=9, T=100)
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


def test_disk_output_is_reusable() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary) / "run"
        simulation, summary = run_and_save(Config(seed=2, T=40), directory, snapshot_every=20)
        expected = {
            "config.json",
            "summary.json",
            "series.csv",
            "avalanches.csv",
            "avalanche_members.csv",
            "deaths.csv",
            "entities.csv",
            "final_loans.csv",
            "individual_series.csv.gz",
        }
        assert expected <= {path.name for path in directory.iterdir()}
        assert (directory / "snapshots" / "entities_t00040.npz").exists()
        assert (directory / "snapshots" / "network_t00040.npz").exists()

        with (directory / "config.json").open(encoding="utf-8") as stream:
            saved_config = json.load(stream)
        assert saved_config["parameters"] == simulation.config.to_dict()
        assert saved_config["fixed_rules"]["bankruptcy"] == "cancel_and_destroy"
        assert summary["book_errors"] == []

        with (directory / "series.csv").open(encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == simulation.t
        assert int(rows[-1]["pop"]) == simulation.population.n_alive

        with (directory / "avalanches.csv").open(encoding="utf-8") as stream:
            avalanche_rows = list(csv.DictReader(stream))
        assert "volume_j" in avalanche_rows[0] if avalanche_rows else True
        assert all(float(row["volume_j"]) >= 0 for row in avalanche_rows)

        with gzip.open(
            directory / "individual_series.csv.gz", "rt", encoding="utf-8"
        ) as stream:
            individual_rows = list(csv.DictReader(stream))
        expected_rows = sum(row["pop"] + row["deaths"] for row in simulation.series)
        assert len(individual_rows) == expected_rows
        assert summary["individual_rows"] == expected_rows
        assert {int(row["id"]) for row in individual_rows} == set(
            range(len(simulation.population))
        )
        terminal_rows = [row for row in individual_rows if row["alive"] == "0"]
        assert len(terminal_rows) == len(simulation.deaths)
        assert all(row["death_cause"] for row in terminal_rows)

        last_rows = [
            row
            for row in individual_rows
            if int(row["t"]) == simulation.t and row["alive"] == "1"
        ]
        assert len(last_rows) == simulation.population.n_alive
        saved_capital = sum(float(row["K"]) for row in last_rows)
        assert abs(saved_capital - simulation.series[-1]["K_tot"]) < 1e-9

        with np.load(directory / "snapshots" / "entities_t00040.npz") as snapshot:
            assert set(snapshot.files) == {
                "id", "K", "claims", "debts", "nw", "prod", "int_in",
                "int_out", "income", "income_net", "age", "deg_out", "deg_in",
            }


def test_individual_frequency_can_be_reduced() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        simulation, summary = run_and_save(
            Config(seed=1, T=11), temporary, snapshot_every=0, individual_every=3
        )
        with gzip.open(
            Path(temporary) / "individual_series.csv.gz", "rt", encoding="utf-8"
        ) as stream:
            rows = list(csv.DictReader(stream))
        living_times = {int(row["t"]) for row in rows if row["alive"] == "1"}
        assert living_times == {3, 6, 9, 11}
        expected = sum(row["deaths"] for row in simulation.series)
        expected += sum(
            row["pop"]
            for row in simulation.series
            if row["t"] % 3 == 0 or row["t"] == simulation.t
        )
        assert len(rows) == expected == summary["individual_rows"]


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
