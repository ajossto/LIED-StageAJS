"""Tests unitaires du noyau M2 : entités, contrats, NW, marché, intérêts."""
import math

import conftest_path  # noqa: F401
import numpy as np

from m2.bankruptcy import net_worth
from m2.config import M2Config
from m2.contracts import LoanBook
from m2.entities import Population
from m2.market import run_market


CFG = M2Config(seed=0)


def make_pop(*ws, cfg=CFG):
    pop = Population()
    for w in ws:
        i = pop.born(cfg.w0, 0)
        pop.w[i] = w
    return pop


def test_born_initial_state():
    pop = Population()
    i = pop.born(CFG.w0, 3)
    assert pop.w[i] == CFG.w0 and pop.alive[i] and pop.birth[i] == 3
    book = LoanBook()
    assert net_worth(pop, book, CFG, i) == CFG.eps0 == CFG.w0 - CFG.d0
    assert pop.n_alive == 1


def test_net_worth_with_contracts():
    pop = make_pop(50.0, 10.0)
    book = LoanBook()
    book.add(0, 1, 7.0, 0.05)
    assert net_worth(pop, book, CFG, 0) == 50.0 + 7.0 - CFG.d0
    assert net_worth(pop, book, CFG, 1) == 10.0 - 7.0 - CFG.d0


def test_loan_creation_conserves_principal_and_indexes():
    pop = make_pop(100.0, 5.0)
    book = LoanBook()
    total_before = pop.w[0] + pop.w[1]
    q = 12.0
    pop.w[0] -= q
    pop.w[1] += q
    lid = book.add(0, 1, q, 0.08)
    assert pop.w[0] + pop.w[1] == total_before  # I4
    assert book.claims[0] == q and book.debts[1] == q
    assert lid in book.by_lender[0] and lid in book.by_borrower[1]
    assert book.check_consistency(pop.alive) == []


def test_loan_removal_updates_aggregates():
    pop = make_pop(100.0, 5.0)
    book = LoanBook()
    lid = book.add(0, 1, 12.0, 0.08)
    book.remove(lid)
    assert abs(book.claims[0]) < 1e-12 and abs(book.debts[1]) < 1e-12
    assert len(book) == 0
    assert book.check_consistency(pop.alive) == []


def test_market_basic_trade():
    """Prêteur riche + emprunteur pauvre dans le même échantillon => contrat
    conforme à la règle w*(rho), principal conservé."""
    cfg = M2Config(seed=1, k=2)
    pop = make_pop(200.0, 2.0, cfg=cfg)
    book = LoanBook()
    rng = np.random.default_rng(0)
    total = pop.w[0] + pop.w[1]
    n_new, vol = run_market(pop, book, cfg, rng)
    assert n_new == 1
    lender, borrower, q, r = next(iter(book.loans.values()))
    assert (lender, borrower) == (0, 1)
    rl = cfg.alpha / (2 * math.sqrt(200.0))
    rb = cfg.alpha / (2 * math.sqrt(2.0))
    r_expected = math.sqrt(rl * rb)
    assert abs(r - r_expected) < 1e-12
    w_star = (cfg.alpha / (2 * (r_expected + cfg.delta))) ** 2
    q_expected = min(w_star - 2.0, 200.0 - w_star)
    assert abs(q - q_expected) < 1e-12 and abs(vol - q) < 1e-12
    assert abs(pop.w[0] + pop.w[1] - total) < 1e-12  # I4


def test_market_no_trade_if_equal_wealth():
    cfg = M2Config(seed=1, k=2)
    pop = make_pop(50.0, 50.0, cfg=cfg)
    book = LoanBook()
    n_new, _ = run_market(pop, book, cfg, np.random.default_rng(0))
    assert n_new == 0


def test_market_demand_limited():
    """Emprunteur déjà au-dessus de w* : demande nulle, pas de contrat."""
    cfg = M2Config(seed=1, k=2)
    pop = make_pop(500.0, 400.0, cfg=cfg)
    book = LoanBook()
    n_new, _ = run_market(pop, book, cfg, np.random.default_rng(0))
    # w* < 100 pour ces taux : w_b = 400 > w* => q_dem = 0
    assert n_new == 0


def test_market_small_population():
    cfg = M2Config(seed=1, k=6)
    for ws in ([], [10.0], [10.0, 20.0, 30.0]):  # N=0, N=1, N<k
        pop = make_pop(*ws, cfg=cfg)
        book = LoanBook()
        n_new, vol = run_market(pop, book, cfg, np.random.default_rng(0))
        assert n_new == 0 and vol == 0.0  # floor(N/k) = 0 round


def test_market_excludes_defaulted():
    cfg = M2Config(seed=1, k=2)
    pop = make_pop(200.0, 2.0, cfg=cfg)
    pop.defaulted[0] = True
    book = LoanBook()
    n_new, _ = run_market(pop, book, cfg, np.random.default_rng(0))
    assert n_new == 0  # pool = 1 seule entité => 0 round


def test_market_zero_wealth_borrower_guard():
    """w_b = 0 : r_b* énorme => w* minuscule => demande minuscule ; pas de
    crash, pas de w négatif."""
    cfg = M2Config(seed=1, k=2)
    pop = make_pop(200.0, 0.0, cfg=cfg)
    book = LoanBook()
    run_market(pop, book, cfg, np.random.default_rng(0))
    assert pop.w[0] >= 0 and pop.w[1] >= 0
