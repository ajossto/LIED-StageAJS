"""Tests du carnet de contrats (LoanBook) et du marché du crédit (run_market).
Assertions Python simples — pas de pytest."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import math

import numpy as np

from m3.config import M3Config
from m3.contracts import LoanBook
from m3.entities import Population
from m3.market import run_market, lendable


def test_add_remove_incremental():
    """add/remove : claims, debts, due incrémentaux exacts ; consistency vide."""
    book = LoanBook()
    lid1 = book.add(0, 1, 10.0, 0.05)
    book.add(2, 1, 4.0, 0.1)
    assert book.claims[0] == 10.0 and book.claims[2] == 4.0
    assert book.debts[1] == 14.0
    assert book.due[1] == 10.0 * 0.05 + 4.0 * 0.1
    assert len(book) == 2
    book.remove(lid1)
    assert book.claims[0] == 0.0
    assert book.debts[1] == 4.0
    assert book.due[1] == 4.0 * 0.1
    assert len(book) == 1
    assert book.check_consistency([True, True, True]) == []


def test_merge_pairs_weighted_rate():
    """Deux add sur la même paire -> un contrat, q sommé, taux moyen pondéré,
    due == q_total*r_moyen, flux d'intérêts total préservé."""
    book = LoanBook(merge_pairs=True)
    lid1 = book.add(0, 1, 10.0, 0.04)
    lid2 = book.add(0, 1, 30.0, 0.08)
    assert lid1 == lid2
    assert len(book) == 1
    lender, borrower, q, r = book.loans[lid1]
    assert (lender, borrower) == (0, 1)
    assert q == 40.0
    r_expected = (10.0 * 0.04 + 30.0 * 0.08) / 40.0
    assert abs(r - r_expected) < 1e-15, r
    flux = 10.0 * 0.04 + 30.0 * 0.08  # q1*r1 + q2*r2
    assert abs(book.due[1] - q * r) < 1e-12
    assert abs(book.due[1] - flux) < 1e-12
    assert book.claims[0] == 40.0 and book.debts[1] == 40.0
    # la paire inverse reste un contrat distinct
    book.add(1, 0, 5.0, 0.02)
    assert len(book) == 2
    assert book.check_consistency([True, True]) == []


def test_I5_claims_equal_debts():
    """I5 : total des créances == total des dettes."""
    book = LoanBook()
    rng = np.random.default_rng(12)
    lids = []
    for _ in range(50):
        a, b = rng.integers(0, 20, size=2)
        if a == b:
            continue
        lids.append(book.add(int(a), int(b), float(rng.uniform(0.1, 5.0)),
                             float(rng.uniform(0.01, 0.2))))
    for lid in lids[::3]:
        if lid in book.loans:
            book.remove(lid)
    total_claims = sum(book.claims.values())
    total_debts = sum(book.debts.values())
    assert abs(total_claims - total_debts) < 1e-9 * max(1.0, total_claims)
    assert book.check_consistency([True] * 20) == []


def _two_agent_setup():
    """Une riche en L (id 0), une pauvre en K (id 1)."""
    pop = Population()
    pop.born(100.0, 50.0, 0)  # prêteuse : L=100, K=50
    pop.born(0.0, 1.0, 0)     # emprunteuse : L=0, K=1
    return pop


def test_market_productive():
    """Marché baseline : L_lender -= q, K_borrower += q, r = sqrt(r_l*r_b),
    q = min(prêtable, K*(rho) - K_b) avec rho = r+delta, K*(rho) = (alpha/2rho)^2."""
    cfg = M3Config(k=2)
    pop = _two_agent_setup()
    book = LoanBook()
    rng = np.random.default_rng(0)
    n_new, volume = run_market(pop, book, cfg, rng)
    assert n_new == 1
    # valeurs attendues (mêmes formules que la spec §3 phase 6)
    r_l = cfg.alpha / (2.0 * math.sqrt(50.0))
    r_b = cfg.alpha / (2.0 * math.sqrt(1.0))
    r_exp = math.sqrt(r_l * r_b)
    rho = r_exp + cfg.delta
    k_star = (cfg.alpha / (2.0 * rho)) ** 2
    q_exp = min(100.0, max(0.0, k_star - 1.0))
    assert abs(volume - q_exp) < 1e-12
    assert abs(pop.L[0] - (100.0 - q_exp)) < 1e-12    # L_lender diminue de q
    assert pop.K[0] == 50.0                            # K_lender intact
    assert abs(pop.K[1] - (1.0 + q_exp)) < 1e-12       # K_borrower += q
    assert pop.L[1] == 0.0                             # pas de liquidité créée
    assert len(book) == 1
    lender, borrower, q, r = next(iter(book.loans.values()))
    assert (lender, borrower) == (0, 1)
    assert abs(q - q_exp) < 1e-12
    assert abs(r - r_exp) < 1e-15
    assert book.check_consistency(pop.alive) == []


def test_loan_target_L():
    """Ablation C : q va dans L_borrower, K_borrower inchangé."""
    cfg = M3Config(k=2, loan_target="L")
    pop = _two_agent_setup()
    book = LoanBook()
    rng = np.random.default_rng(0)
    n_new, volume = run_market(pop, book, cfg, rng)
    assert n_new == 1
    q = next(iter(book.loans.values()))[2]
    assert pop.K[1] == 1.0                        # K inchangé
    assert abs(pop.L[1] - q) < 1e-12              # q versé en liquidité
    assert abs(pop.L[0] - (100.0 - q)) < 1e-12


def test_beta_L_buffer():
    """Tampon beta_L : L=10 et due=8, beta_L=1 -> prêtable = 2 max."""
    cfg = M3Config(k=2, beta_L=1.0)
    pop = Population()
    pop.born(10.0, 50.0, 0)   # future prêteuse, avec service dû
    pop.born(0.0, 1.0, 0)     # emprunteuse pauvre en K
    pop.born(200.0, 300.0, 0)  # créancière de l'entité 0 (hors pool : defaulted)
    pop.defaulted[2] = True    # exclue du pool pour garder un round à 2
    book = LoanBook()
    book.add(2, 0, 80.0, 0.1)  # due[0] = 8
    assert book.due[0] == 8.0
    assert lendable(pop, book, cfg, 0) == 2.0
    rng = np.random.default_rng(0)
    run_market(pop, book, cfg, rng)
    # le prêt éventuel de 0 vers 1 est plafonné par le prêtable 2
    new_loans = [rec for rec in book.loans.values() if rec[0] == 0]
    assert len(new_loans) == 1
    assert new_loans[0][2] <= 2.0 + 1e-12
    assert pop.L[0] >= 8.0 - 1e-12   # le tampon de service est préservé


def test_market_random_valid():
    """Ablation F (market_selection=random) : tourne sans erreur, contrats
    valides (pas d'auto-prêt, q > 0), transferts conservatifs."""
    cfg = M3Config(k=3, market_selection="random")
    pop = Population()
    rng_init = np.random.default_rng(21)
    for j in range(12):
        pop.born(float(rng_init.uniform(0.0, 120.0)), float(j + 1), 0)
    book = LoanBook()
    total_before = sum(pop.L) + sum(pop.K)
    rng = np.random.default_rng(10)
    n_new, volume = run_market(pop, book, cfg, rng)
    assert n_new >= 1, "seed choisi pour produire au moins un contrat"
    assert n_new == len(book)
    for lender, borrower, q, r in book.loans.values():
        assert lender != borrower
        assert q > 0.0 and r > 0.0
    assert abs(volume - sum(rec[2] for rec in book.loans.values())) < 1e-9
    total_after = sum(pop.L) + sum(pop.K)
    assert abs(total_after - total_before) < 1e-9
    assert book.check_consistency(pop.alive) == []


def test_credit_false_noop():
    """credit=False : run_market retourne (0, 0.0) et ne touche à rien."""
    cfg = M3Config(k=2, credit=False)
    pop = _two_agent_setup()
    book = LoanBook()
    rng = np.random.default_rng(0)
    out = run_market(pop, book, cfg, rng)
    assert out == (0, 0.0)
    assert len(book) == 0
    assert pop.L[0] == 100.0 and pop.K[0] == 50.0
    assert pop.L[1] == 0.0 and pop.K[1] == 1.0


def _main():
    mod = sys.modules[__name__]
    names = sorted(n for n in dir(mod) if n.startswith("test_"))
    for name in names:
        getattr(mod, name)()
        print(f"OK {name}")
    return len(names)


if __name__ == "__main__":
    _main()
