import unittest

import numpy as np

from m2 import M2Config, M2Simulation
from m2.market import compute_credit_terms, run_credit_market


class MarketAndSimulationTests(unittest.TestCase):
    def test_credit_terms_are_well_defined(self):
        terms = compute_credit_terms(100, 10, alpha=1, delta=0.05)
        self.assertIsNotNone(terms)
        self.assertGreater(terms.volume, 0)
        self.assertLessEqual(terms.volume, terms.demand)
        self.assertLessEqual(terms.volume, terms.supply)

    def test_zero_capital_produces_no_loan(self):
        self.assertIsNone(compute_credit_terms(100, 0, alpha=1, delta=0.05))

    def test_market_does_nothing_when_population_below_k(self):
        config = M2Config(birth_rate=0, w0=0, d0=0, k=3, steps=0)
        sim = M2Simulation(config, seed=0)
        sim.create_entity(w=100, d0=0)
        sim.create_entity(w=10, d0=0)
        result = run_credit_market(
            sim.entities, sim.book, np.random.default_rng(0), config, 1
        )
        self.assertEqual(result.rounds, 0)
        self.assertEqual(len(sim.book), 0)

    def test_market_conserves_capital(self):
        config = M2Config(birth_rate=0, w0=0, d0=0, k=2, steps=0)
        sim = M2Simulation(config, seed=0)
        sim.create_entity(w=100, d0=0)
        sim.create_entity(w=10, d0=0)
        before = sum(entity.w for entity in sim.entities.values())
        result = run_credit_market(
            sim.entities, sim.book, np.random.default_rng(0), config, 1
        )
        self.assertEqual(result.contracts_created, 1)
        self.assertAlmostEqual(
            sum(entity.w for entity in sim.entities.values()), before
        )
        sim.validate_invariants()

    def test_empty_population_is_supported(self):
        config = M2Config(birth_rate=0, steps=3, snapshot_interval=1)
        sim = M2Simulation(config, seed=0)
        run = sim.run()
        self.assertEqual(len(run.timeseries), 3)
        self.assertTrue(all(row.population == 0 for row in run.timeseries))
        self.assertEqual(run.snapshots[3], [])

    def test_reproducibility_by_seed(self):
        config = M2Config(
            birth_rate=3,
            steps=15,
            snapshot_interval=5,
            k=3,
            w0=30,
            d0=28,
        )
        first = M2Simulation(config, seed=42).run()
        second = M2Simulation(config, seed=42).run()
        other = M2Simulation(config, seed=43).run()
        self.assertEqual(
            [row.to_dict() for row in first.timeseries],
            [row.to_dict() for row in second.timeseries],
        )
        self.assertEqual(first.snapshots, second.snapshots)
        self.assertNotEqual(
            [row.births for row in first.timeseries],
            [row.births for row in other.timeseries],
        )

    def test_snapshot_interval_does_not_change_dynamics(self):
        common = dict(birth_rate=2, steps=10, k=2, w0=30, d0=28)
        fast = M2Simulation(M2Config(snapshot_interval=1, **common), seed=8).run()
        sparse = M2Simulation(M2Config(snapshot_interval=5, **common), seed=8).run()
        self.assertEqual(
            [row.to_dict() for row in fast.timeseries],
            [row.to_dict() for row in sparse.timeseries],
        )

    def test_no_negative_capital_in_smoke_run(self):
        config = M2Config(birth_rate=4, steps=40, snapshot_interval=10, k=3)
        sim = M2Simulation(config, seed=12)
        sim.run()
        sim.validate_invariants(require_stable=True)
        self.assertTrue(all(e.w >= 0 for e in sim.entities.values() if e.alive))


if __name__ == "__main__":
    unittest.main()
