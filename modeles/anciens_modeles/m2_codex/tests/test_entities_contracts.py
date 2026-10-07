import math
import unittest

from m2 import M2Config, M2Simulation
from m2.contracts import ContractBook


class EntityAndContractTests(unittest.TestCase):
    def setUp(self):
        self.sim = M2Simulation(M2Config(birth_rate=0, w0=30, d0=28, steps=0), seed=1)

    def test_entity_creation_and_net_worth(self):
        entity = self.sim.create_entity()
        self.assertEqual(entity.entity_id, 0)
        self.assertEqual(entity.w, 30)
        self.assertEqual(self.sim.net_worth(entity.entity_id), 2)

    def test_loan_conserves_principal_and_individual_net_worth(self):
        lender = self.sim.create_entity(w=50, d0=5)
        borrower = self.sim.create_entity(w=10, d0=2)
        total_before = lender.w + borrower.w
        lender_nw = self.sim.net_worth(lender.entity_id)
        borrower_nw = self.sim.net_worth(borrower.entity_id)
        contract = self.sim.create_loan(lender.entity_id, borrower.entity_id, 12, 0.1)
        self.assertEqual(contract.principal, 12)
        self.assertAlmostEqual(lender.w + borrower.w, total_before)
        self.assertAlmostEqual(self.sim.net_worth(lender.entity_id), lender_nw)
        self.assertAlmostEqual(self.sim.net_worth(borrower.entity_id), borrower_nw)

    def test_book_rejects_zero_principal_and_self_contract(self):
        book = ContractBook()
        with self.assertRaises(ValueError):
            book.add(0, 1, 0, 0.1, 0)
        with self.assertRaises(ValueError):
            book.add(0, 0, 1, 0.1, 0)

    def test_book_indexes_remove_cleanly(self):
        book = ContractBook()
        contract = book.add(1, 2, 3.0, 0.1, 0)
        self.assertEqual(book.claims(1), 3)
        self.assertEqual(book.debts(2), 3)
        book.remove(contract.contract_id)
        self.assertEqual(len(book), 0)
        self.assertNotIn(1, book.by_lender)
        self.assertNotIn(2, book.by_borrower)

    def test_same_pair_is_coalesced_without_changing_interest(self):
        book = ContractBook()
        first = book.add(1, 2, 3.0, 0.1, 0)
        second = book.add(1, 2, 2.0, 0.2, 1)
        self.assertEqual(first.contract_id, second.contract_id)
        self.assertEqual(len(book), 1)
        self.assertAlmostEqual(second.principal, 5.0)
        self.assertAlmostEqual(second.rate * second.principal, 0.7)
        self.assertEqual(second.component_count, 2)
        book.validate({1, 2})

    def test_config_rejects_invalid_birth_balance(self):
        with self.assertRaises(ValueError):
            M2Config(w0=10, d0=11)

    def test_zero_capital_is_valid(self):
        entity = self.sim.create_entity(w=0, d0=0)
        self.assertTrue(math.isfinite(entity.w))
        self.assertEqual(self.sim.net_worth(entity.entity_id), 0)


if __name__ == "__main__":
    unittest.main()
