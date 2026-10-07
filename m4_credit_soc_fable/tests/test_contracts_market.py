"""Tests du carnet de contrats (LoanBook) et du marché du crédit (run_market)
— moteur fusionné. Assertions Python simples — pas de pytest."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import math

import numpy as np

from m4.config import M4Config
from m4.contracts import LoanBook
from m4.entities import Population
from m4.market import run_market, pair_terms


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
    """Une riche en K (id 0), une pauvre (id 1)."""
    pop = Population()
    pop.born(64.0, 0)   # prêteuse
    pop.born(1.0, 0)    # emprunteuse
    return pop


def test_market_income_objective():
    """Objectif « revenu » (baseline) : cible commune K*(r) = (alpha/2r)^2
    = sqrt(K_l * K_b) (taux géométrique) ; q = min(K_l - K*, K* - K_b) ;
    transfert conservatif K -> K + contrat nominal."""
    cfg = M4Config(k=2, rounds_div=2)  # un seul round : teste la formule par round
    assert cfg.objective == "income"
    pop = _two_agent_setup()
    book = LoanBook()
    rng = np.random.default_rng(0)
    n_new, volume = run_market(pop, book, cfg, rng)
    assert n_new == 1
    r_exp, k_star = pair_terms(cfg, 64.0, 1.0)
    # identité analytique : K*(r) == sqrt(K_l * K_b) = 8
    assert abs(k_star - 8.0) < 1e-9
    q_exp = min(64.0 - k_star, k_star - 1.0)   # min(56, 7) = 7
    assert abs(q_exp - 7.0) < 1e-9
    assert abs(volume - q_exp) < 1e-12
    assert abs(pop.K[0] - (64.0 - q_exp)) < 1e-12
    assert abs(pop.K[1] - (1.0 + q_exp)) < 1e-12
    assert abs(pop.K[0] + pop.K[1] - 65.0) < 1e-12   # conservatif
    assert len(book) == 1
    lender, borrower, q, r = next(iter(book.loans.values()))
    assert (lender, borrower) == (0, 1)
    assert abs(q - q_exp) < 1e-12
    assert abs(r - r_exp) < 1e-15
    assert book.check_consistency(pop.alive) == []


def test_market_wealth_objective():
    """Objectif « richesse » (contrôle) : rho = r + delta -> cible plus
    basse, prêt plus petit qu'en objectif revenu."""
    cfg_w = M4Config(k=2, objective="wealth")
    cfg_i = M4Config(k=2, objective="income")
    _, k_star_w = pair_terms(cfg_w, 64.0, 1.0)
    _, k_star_i = pair_terms(cfg_i, 64.0, 1.0)
    assert k_star_w < k_star_i


def test_market_lender_keeps_target():
    """L'offre est bornée par K_l - K* : la prêteuse ne descend jamais sous
    la cible commune (cas où la demande dépasse l'offre)."""
    cfg = M4Config(k=2, rounds_div=2)  # un seul round : teste la formule par round
    pop = Population()
    pop.born(9.0, 0)    # prêteuse à peine au-dessus de K* = sqrt(9*1) = 3
    pop.born(1.0, 0)
    book = LoanBook()
    rng = np.random.default_rng(0)
    n_new, volume = run_market(pop, book, cfg, rng)
    assert n_new == 1
    _, k_star = pair_terms(cfg, 9.0, 1.0)
    q_exp = min(9.0 - k_star, k_star - 1.0)     # min(6, 2) = 2
    assert abs(volume - q_exp) < 1e-12
    assert pop.K[0] >= k_star - 1e-12


def test_rounds_div_volume_lever():
    """rounds_div découple le volume du tri : moins de rounds (rounds_div
    plus grand) -> jamais plus de prêts créés, à tirages égaux par ailleurs."""
    def run_with(rounds_div):
        cfg = M4Config(k=3, rounds_div=rounds_div)
        pop = Population()
        rng_init = np.random.default_rng(7)
        for j in range(24):
            pop.born(float(rng_init.uniform(1.0, 200.0)), 0)
        book = LoanBook()
        rng = np.random.default_rng(10)
        n_new, _ = run_market(pop, book, cfg, rng)
        return n_new
    assert run_with(12) <= run_with(3)
    assert run_with(3) >= 1


def test_credit_false_noop():
    """credit=False : run_market retourne (0, 0.0) et ne touche à rien."""
    cfg = M4Config(k=2, credit=False)
    pop = _two_agent_setup()
    book = LoanBook()
    rng = np.random.default_rng(0)
    out = run_market(pop, book, cfg, rng)
    assert out == (0, 0.0)
    assert len(book) == 0
    assert pop.K[0] == 64.0 and pop.K[1] == 1.0


def test_defaulted_excluded_from_pool():
    """Les entités en défaut de service sont exclues du marché du pas."""
    cfg = M4Config(k=2, rounds_div=2)  # un seul round : teste la formule par round
    pop = _two_agent_setup()
    pop.defaulted[1] = True
    book = LoanBook()
    rng = np.random.default_rng(0)
    n_new, volume = run_market(pop, book, cfg, rng)
    assert (n_new, volume) == (0, 0.0)   # pool réduit à 1 : aucun round


def _main():
    mod = sys.modules[__name__]
    names = sorted(n for n in dir(mod) if n.startswith("test_"))
    for name in names:
        getattr(mod, name)()
        print(f"OK {name}")
    return len(names)


if __name__ == "__main__":
    _main()
