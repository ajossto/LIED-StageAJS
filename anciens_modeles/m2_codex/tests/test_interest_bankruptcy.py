import unittest

from m2 import M2Config, M2Simulation
from m2.bankruptcy import resolve_cascades


class InterestAndBankruptcyTests(unittest.TestCase):
    def make_sim(self, **overrides):
        params = dict(birth_rate=0, w0=0, d0=0, steps=0, check_invariants=True)
        params.update(overrides)
        return M2Simulation(M2Config(**params), seed=4)

    def test_full_interest_payment_is_conservative(self):
        sim = self.make_sim()
        lender = sim.create_entity(w=2, d0=0)
        borrower = sim.create_entity(w=50, d0=0)
        sim.book.add(lender.entity_id, borrower.entity_id, 100, 0.1, 0)
        before = lender.w + borrower.w
        due, paid = sim.service_interests()
        self.assertAlmostEqual(due, 10)
        self.assertAlmostEqual(paid, 10)
        self.assertAlmostEqual(lender.w, 12)
        self.assertAlmostEqual(borrower.w, 40)
        self.assertAlmostEqual(lender.w + borrower.w, before)
        self.assertFalse(borrower.defaulted)

    def test_partial_interest_is_pro_rata_and_causes_default(self):
        sim = self.make_sim()
        lender_a = sim.create_entity(w=0, d0=0)
        lender_b = sim.create_entity(w=0, d0=0)
        borrower = sim.create_entity(w=6, d0=0)
        sim.book.add(lender_a.entity_id, borrower.entity_id, 50, 0.1, 0)
        sim.book.add(lender_b.entity_id, borrower.entity_id, 25, 0.2, 0)
        due, paid = sim.service_interests()
        self.assertAlmostEqual(due, 10)
        self.assertAlmostEqual(paid, 6)
        self.assertAlmostEqual(lender_a.w, 3)
        self.assertAlmostEqual(lender_b.w, 3)
        self.assertAlmostEqual(borrower.w, 0)
        self.assertTrue(borrower.defaulted)

    def test_simple_bankruptcy_returns_residual_to_creditor(self):
        sim = self.make_sim()
        creditor = sim.create_entity(w=10, d0=0)
        failed = sim.create_entity(w=4, d0=0)
        sim.book.add(creditor.entity_id, failed.entity_id, 8, 0.1, 0)
        failed.defaulted = True
        result = resolve_cascades(sim.entities, sim.book, sim.config, 1)
        self.assertEqual(result.failures, 1)
        self.assertAlmostEqual(creditor.w, 14)
        self.assertFalse(failed.alive)
        self.assertEqual(len(sim.book), 0)
        sim.validate_invariants(require_stable=True)

    def test_claims_are_transferred_pro_rata(self):
        sim = self.make_sim()
        creditor = sim.create_entity(w=100, d0=0)
        intermediary = sim.create_entity(w=20, d0=0)
        borrower = sim.create_entity(w=5, d0=0)
        sim.create_loan(creditor.entity_id, intermediary.entity_id, 10, 0.1)
        original = sim.create_loan(intermediary.entity_id, borrower.entity_id, 15, 0.2)
        intermediary.defaulted = True
        result = resolve_cascades(sim.entities, sim.book, sim.config, 1)
        self.assertEqual(result.failures, 1)
        inherited = sim.book.borrowed_contracts(borrower.entity_id)
        self.assertEqual(len(inherited), 1)
        self.assertEqual(inherited[0].lender_id, creditor.entity_id)
        self.assertEqual(inherited[0].parent_id, original.contract_id)
        self.assertAlmostEqual(inherited[0].principal, 15)
        sim.validate_invariants(require_stable=True)

    def test_bankruptcy_cascade_reaches_stability(self):
        sim = self.make_sim()
        lender = sim.create_entity(w=10, d0=5)
        borrower = sim.create_entity(w=0, d0=0)
        sim.create_loan(lender.entity_id, borrower.entity_id, 8, 0.1)
        borrower.w = 0
        result = resolve_cascades(sim.entities, sim.book, sim.config, 1)
        self.assertEqual(result.failures, 2)
        self.assertEqual(len(sim.alive_ids()), 0)
        self.assertEqual(len(sim.book), 0)

    def test_failure_without_creditor_destroys_residual(self):
        sim = self.make_sim()
        entity = sim.create_entity(w=3, d0=4)
        result = resolve_cascades(sim.entities, sim.book, sim.config, 1)
        self.assertEqual(result.failures, 1)
        self.assertAlmostEqual(result.destroyed_capital, 3)
        self.assertEqual(entity.d0, 0)

    def test_no_orphan_contract_after_failure(self):
        sim = self.make_sim()
        a = sim.create_entity(w=20, d0=0)
        b = sim.create_entity(w=10, d0=0)
        c = sim.create_entity(w=5, d0=0)
        sim.create_loan(a.entity_id, b.entity_id, 4, 0.1)
        sim.create_loan(b.entity_id, c.entity_id, 3, 0.1)
        b.defaulted = True
        resolve_cascades(sim.entities, sim.book, sim.config, 1)
        sim.book.validate(sim.alive_ids())
        for contract in sim.book.contracts.values():
            self.assertTrue(sim.entities[contract.lender_id].alive)
            self.assertTrue(sim.entities[contract.borrower_id].alive)


if __name__ == "__main__":
    unittest.main()
