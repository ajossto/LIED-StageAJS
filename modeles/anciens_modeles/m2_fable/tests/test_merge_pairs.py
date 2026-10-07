"""Tests de la variante merge_pairs : fusion des contrats d'une même paire au
taux moyen pondéré — équivalence des flux, unicité des paires, carnet borné."""
import conftest_path  # noqa: F401
import numpy as np

from m2.bankruptcy import resolve_bankruptcies
from m2.config import M2Config
from m2.contracts import LoanBook
from m2.entities import Population
from m2.simulation import Simulation


def test_merge_aggregates_principal_and_weighted_rate():
    book = LoanBook(merge_pairs=True)
    lid1 = book.add(0, 1, 10.0, 0.05)
    lid2 = book.add(0, 1, 20.0, 0.08)
    assert lid1 == lid2 and len(book) == 1
    _, _, q, r = book.loans[lid1]
    assert q == 30.0
    assert abs(r - (10 * 0.05 + 20 * 0.08) / 30) < 1e-15
    # flux d'intérêts identique à la somme des deux contrats séparés
    assert abs(q * r - (10 * 0.05 + 20 * 0.08)) < 1e-12
    assert book.claims[0] == 30.0 and book.debts[1] == 30.0


def test_merge_distinct_pairs_stay_separate():
    book = LoanBook(merge_pairs=True)
    book.add(0, 1, 10.0, 0.05)
    book.add(1, 0, 5.0, 0.06)   # sens inverse : autre paire
    book.add(0, 2, 7.0, 0.04)
    assert len(book) == 3


def test_merge_remove_clears_pair_index():
    book = LoanBook(merge_pairs=True)
    lid = book.add(0, 1, 10.0, 0.05)
    book.remove(lid)
    lid2 = book.add(0, 1, 4.0, 0.09)
    assert lid2 != lid and book.loans[lid2][2] == 4.0


def test_merge_interest_flow_equivalent_one_step():
    """Un pas de Simulation sans hasard : le prêteur reçoit le même montant
    avec deux contrats séparés ou un contrat fusionné."""
    results = []
    for merge in (False, True):
        cfg = M2Config(seed=0, sigma=0.0, lam=0.0, credit=False,
                       merge_pairs=merge)
        sim = Simulation(cfg)
        a = sim.pop.born(cfg.w0, 0)
        b = sim.pop.born(cfg.w0, 0)
        sim.pop.w[a], sim.pop.w[b] = 100.0, 50.0
        sim.book.add(a, b, 10.0, 0.05)
        sim.book.add(a, b, 20.0, 0.08)
        sim.step()
        results.append((sim.pop.w[a], sim.pop.w[b], sim.pop.int_in[a]))
    assert results[0] == results[1]


def test_merge_bankruptcy_prorata_equivalent():
    """Le prorata de faillite ne dépend que des principaux agrégés par
    créancier : mêmes transferts avec ou sans fusion."""
    outcomes = []
    for merge in (False, True):
        cfg = M2Config(seed=0, merge_pairs=merge)
        pop = Population()
        for w in (6.0, 40.0, 50.0):
            pop.born(cfg.w0, 0)
        pop.w[0], pop.w[1], pop.w[2] = 6.0, 40.0, 50.0
        book = LoanBook(merge_pairs=merge)
        # l'entité 0 doit 30 à 2 (en deux contrats) et 10 à 1
        book.add(2, 0, 20.0, 0.05)
        book.add(2, 0, 10.0, 0.07)
        book.add(1, 0, 10.0, 0.05)
        resolve_bankruptcies(pop, book, cfg)
        outcomes.append((pop.w[1], pop.w[2], pop.alive[0]))
    assert outcomes[0] == outcomes[1]


def test_merge_book_stays_bounded_with_transfer_rule():
    """Run court avec la règle M2 (transfer) : le nombre de contrats reste
    borné par le nombre de paires vivantes (pas de prolifération)."""
    cfg = M2Config(seed=5, T=300, merge_pairs=True)
    sim = Simulation(cfg)
    sim.run()
    assert sim.book.check_consistency(sim.pop.alive) == []
    pairs = {(rec[0], rec[1]) for rec in sim.book.loans.values()}
    assert len(sim.book) == len(pairs)
