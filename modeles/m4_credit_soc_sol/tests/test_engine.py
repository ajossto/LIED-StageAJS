import math
import random

from m4.bankruptcy import net_worth, resolve_bankruptcies
from m4.config import M4Config
from m4.contracts import LoanBook
from m4.entities import Population
from m4.market import run_market
from m4.rng import ModelRNG
from m4.simulation import Simulation


def test_no_abstract_birth_debt():
    cfg = M4Config()
    pop, book = Population(), LoanBook()
    i = pop.born(cfg.L0, cfg.K0, 0)
    assert net_worth(pop, book, cfg, i) == cfg.L0 + cfg.K0
    assert "d0" not in cfg.to_dict()


def test_rng_is_local_random_random():
    state = random.getstate()
    a, b = ModelRNG(7), ModelRNG(7)
    draws_a = [a.poisson(10), a.normal(0, 1), a.randrange(5)]
    draws_b = [b.poisson(10), b.normal(0, 1), b.randrange(5)]
    assert draws_a == draws_b
    assert random.getstate() == state


def test_market_and_book_consistency():
    cfg = M4Config(k=2, shock_rho_sector=0.0)
    pop, book = Population(), LoanBook()
    pop.born(100.0, 50.0, 0)
    pop.born(0.0, 1.0, 0)
    before = sum(pop.L) + sum(pop.K)
    n, volume = run_market(pop, book, cfg, ModelRNG(0))
    assert n == 1 and volume > 0
    assert abs(sum(pop.L) + sum(pop.K) - before) < 1e-12
    assert book.check_consistency(pop.alive) == []


def test_concentrated_market_respects_portfolio_limit():
    cfg = M4Config(k=3, portfolio_limit=2, shock_rho_sector=0.0)
    pop, book = Population(), LoanBook()
    for j in range(30):
        pop.born(20.0 + j, 1.0 + j, 0)
    rng = ModelRNG(12)
    for _ in range(30):
        run_market(pop, book, cfg, rng)
    assert max((len(v) for v in book.by_lender.values()), default=0) <= 2
    assert book.check_consistency(pop.alive) == []


def test_cascade_two_levels_and_components():
    cfg = M4Config(lam=0, sigma=0, credit=False, s=1, c=0,
                   shock_rho_sector=0)
    pop, book = Population(), LoanBook()
    root = pop.born(0.0, 0.0, 0)
    middle = pop.born(10.0, 0.0, 0)
    survivor = pop.born(100.0, 0.0, 0)
    book.add(middle, root, 50.0, 0.05)
    book.add(survivor, middle, 40.0, 0.05)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [root, middle]
    assert ledger["death_iter"] == {root: 1, middle: 2}
    assert len(ledger["avalanches"]) == 1
    assert ledger["avalanches"][0]["size"] == 2
    assert book.check_consistency(pop.alive) == []


def test_positive_nw_can_fail_capital_buffer():
    cfg = M4Config(lam=0, sigma=0, credit=False, capital_ratio=0.10,
                   shock_rho_sector=0)
    pop, book = Population(), LoanBook()
    lender = pop.born(100.0, 0.0, 0)
    borrower = pop.born(11.0, 100.0, 0)
    book.add(lender, borrower, 100.0, 0.05)
    assert net_worth(pop, book, cfg, borrower) == 11.0
    # NW=11 > 0 et coussin requis=10 : encore solvable.
    assert resolve_bankruptcies(pop, book, cfg)[0] == []
    pop.L[borrower] = 9.0
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [borrower]
    assert ledger["roots"][borrower] == "capital"


def test_simulation_reproducible_snapshot_pure_and_balanced():
    cfg = M4Config(seed=9, T=120)
    plain, observed = Simulation(cfg), Simulation(cfg)
    plain.run()
    observed.run(snapshot_times=(40, 80, 120), on_snapshot=lambda *_: None)
    assert plain.series == observed.series
    prev = 0.0
    for row in plain.series:
        total = row["L_tot"] + row["K_tot"]
        expected = (row["births"] * cfg.w0 + row["shock_gain"] + row["prod_tot"]
                    - row["depreciated"] - row["consumed"] - row["destroyed"]
                    + row["injected"])
        assert math.isclose(total - prev, expected, rel_tol=1e-6, abs_tol=1e-6)
        prev = total
    assert plain.book.check_consistency(plain.pop.alive) == []
