"""Tests du service des intérêts, des faillites (simples, cascades) et de la
séquence de pas complète."""
import conftest_path  # noqa: F401
import numpy as np

from m2.bankruptcy import net_worth, resolve_bankruptcies
from m2.config import M2Config
from m2.contracts import LoanBook
from m2.entities import Population
from m2.simulation import Simulation

CFG = M2Config(seed=0)


def make_world(*ws, cfg=CFG):
    pop = Population()
    for w in ws:
        i = pop.born(cfg.w0, 0)
        pop.w[i] = w
    return pop, LoanBook()


def test_full_interest_payment_conserves_w():
    """Service complet : transfert conservatif (I5) via un pas de Simulation
    sans hasard (sigma=0, lam=0)."""
    cfg = M2Config(seed=0, sigma=0.0, lam=0.0, credit=False, delta=0.05)
    sim = Simulation(cfg)
    a = sim.pop.born(cfg.w0, 0)
    b = sim.pop.born(cfg.w0, 0)
    sim.pop.w[a], sim.pop.w[b] = 100.0, 50.0
    sim.book.add(a, b, 10.0, 0.05)
    sim.step()
    # phase 3 ajoute sqrt, phase 4 transfère 0.5 de b vers a, phase 5 déprécie
    assert sim.pop.int_in[a] == 0.5 and sim.pop.int_out[b] == 0.5
    assert not sim.pop.defaulted[b]
    assert len(sim.book) == 1  # contrat non déprécié, principal intact (I6)
    assert next(iter(sim.book.loans.values()))[2] == 10.0


def test_partial_interest_payment_triggers_default_and_bankruptcy():
    cfg = M2Config(seed=0, sigma=0.0, lam=0.0, credit=False)
    sim = Simulation(cfg)
    a = sim.pop.born(cfg.w0, 0)
    b = sim.pop.born(cfg.w0, 0)
    sim.pop.w[a] = 100.0
    sim.pop.w[b] = 0.0
    sim.book.add(a, b, 40.0, 0.5)  # dû = 20 >> disponible (~1 après extraction)
    sim.step()
    assert not sim.pop.alive[b]          # défaut => faillite
    assert len(sim.book) == 0            # contrat annulé, perte sèche de a
    assert abs(sim.book.claims[a]) < 1e-12
    assert sim.pop.alive[a]
    # a a reçu le paiement partiel : tout le w disponible de b (=1 après
    # extraction sqrt(0)=0... w=0 => extraction 0 => paiement 0)
    assert sim.series[-1]["defaults"] == 1
    assert sim.series[-1]["deaths"] == 1


def test_simple_bankruptcy_residual_prorata_and_d0_extinction():
    """Faillite d'une entité endettée avec capital résiduel : les créanciers
    reçoivent le résiduel au prorata ; d0 disparaît."""
    cfg = M2Config(seed=0)
    pop, book = make_world(50.0, 40.0, 6.0, cfg=cfg)
    # l'entité 2 doit 30 à 0 et 10 à 1 => NW = 6 + 0 - 40 - 28 < 0
    book.add(0, 2, 30.0, 0.05)
    book.add(1, 2, 10.0, 0.05)
    assert net_worth(pop, book, cfg, 2) < 0
    dead, iters = resolve_bankruptcies(pop, book, cfg)
    assert dead == [2] and not pop.alive[2]
    # résiduel 6 réparti 3/4 - 1/4
    assert abs(pop.w[0] - (50.0 + 4.5)) < 1e-12
    assert abs(pop.w[1] - (40.0 + 1.5)) < 1e-12
    assert len(book) == 0
    assert book.check_consistency(pop.alive) == []


def test_bankruptcy_transfers_lender_loans_prorata():
    """M2 §2.2 phase 7 : les contrats où la faillie est prêteuse passent aux
    créanciers au prorata (convention C5)."""
    cfg = M2Config(seed=0)
    pop, book = make_world(0.0, 100.0, 100.0, 80.0, cfg=cfg)
    # 0 est endettée envers 1 (60) et 2 (20), et prête 40 à 3
    book.add(1, 0, 60.0, 0.05)
    book.add(2, 0, 20.0, 0.05)
    book.add(0, 3, 40.0, 0.07)
    assert net_worth(pop, book, cfg, 0) == 0 + 40 - 80 - cfg.d0
    dead, _ = resolve_bankruptcies(pop, book, cfg)
    assert 0 in dead
    # le prêt de 40 à l'entité 3 est scindé : 30 pour 1, 10 pour 2, taux 0.07
    loans = sorted((l, b, q, r) for l, b, q, r in book.loans.values())
    assert loans == [(1, 3, 30.0, 0.07), (2, 3, 10.0, 0.07)]
    assert abs(book.debts[3] - 40.0) < 1e-12  # la dette de 3 est inchangée
    assert book.check_consistency(pop.alive) == []


def test_bankruptcy_cancel_variant():
    cfg = M2Config(seed=0, fail_lender_loans="cancel")
    pop, book = make_world(0.0, 100.0, 80.0, cfg=cfg)
    book.add(1, 0, 60.0, 0.05)
    book.add(0, 2, 40.0, 0.07)
    resolve_bankruptcies(pop, book, cfg)
    assert len(book) == 0  # créance annulée : gain pour l'emprunteur 2
    assert abs(book.debts[2]) < 1e-12


def test_bankruptcy_share_to_borrower_is_cancelled():
    """Si un créancier de la faillie est aussi l'emprunteur du contrat
    transféré, sa part est une dette envers soi-même : annulée (C5)."""
    cfg = M2Config(seed=0)
    pop, book = make_world(0.0, 100.0, 100.0, cfg=cfg)
    # 0 doit 50 à 1 et 50 à 2 ; 0 prête 20 à 1
    book.add(1, 0, 50.0, 0.05)
    book.add(2, 0, 50.0, 0.05)
    book.add(0, 1, 20.0, 0.06)
    resolve_bankruptcies(pop, book, cfg)
    # part de 1 (10, envers soi-même) annulée ; part de 2 : contrat (2,1,10)
    loans = [(l, b, q) for l, b, q, _ in book.loans.values()]
    assert loans == [(2, 1, 10.0)]


def test_cascade_two_levels():
    """La perte sèche du prêteur le rend insolvable à son tour."""
    cfg = M2Config(seed=0)
    pop, book = make_world(0.0, 5.0, 200.0, cfg=cfg)
    # 1 a prêté 30 à 0 (insolvable) ; NW_1 = 5 + 30 - 0 - 28 = 7 > 0 avant,
    # = 5 - 28 < 0 après la perte sèche
    book.add(1, 0, 30.0, 0.05)
    dead, iters = resolve_bankruptcies(pop, book, cfg)
    assert set(dead) == {0, 1} and iters >= 2
    assert pop.alive[2]
    assert book.check_consistency(pop.alive) == []


def test_no_negative_capital_and_no_insolvent_after_resolution():
    """Invariants I1 et I8 sur un run court avec beaucoup de churn."""
    cfg = M2Config(seed=42, T=150, lam=10.0)
    sim = Simulation(cfg)
    sim.run()
    for i in sim.pop.alive_ids():
        assert sim.pop.w[i] >= 0.0
        assert net_worth(sim.pop, sim.book, cfg, i) >= -cfg.tol_nw
    assert sim.book.check_consistency(sim.pop.alive) == []


def test_dead_entities_have_no_contracts():
    cfg = M2Config(seed=7, T=100)
    sim = Simulation(cfg)
    sim.run()
    for lender, borrower, q, _ in sim.book.loans.values():
        assert sim.pop.alive[lender] and sim.pop.alive[borrower]
        assert q >= cfg.q_min


def test_reproducibility_same_seed():
    a = Simulation(M2Config(seed=123, T=80))
    b = Simulation(M2Config(seed=123, T=80))
    a.run()
    b.run()
    assert a.series == b.series
    assert a.pop.w == b.pop.w
    assert list(a.book.loans.items()) == list(b.book.loans.items())


def test_different_seeds_differ():
    a = Simulation(M2Config(seed=1, T=60))
    b = Simulation(M2Config(seed=2, T=60))
    a.run()
    b.run()
    assert a.series != b.series


def test_empty_world_runs():
    """N(0)=0 et lam=0 : le monde reste vide, extinction signalée proprement."""
    cfg = M2Config(seed=0, lam=0.0, T=10)
    sim = Simulation(cfg)
    sim.step()
    assert sim.pop.n_alive == 0 and sim.status == "extinction"


def test_snapshot_alignment():
    cfg = M2Config(seed=3, T=50)
    sim = Simulation(cfg)
    sim.run()
    snap = sim.snapshot()
    n = sim.pop.n_alive
    assert all(len(snap[k]) == n for k in snap)
    j = 0
    i = int(snap["id"][j])
    assert snap["w"][j] == sim.pop.w[i]
    assert snap["age"][j] == sim.t - sim.pop.birth[i]
