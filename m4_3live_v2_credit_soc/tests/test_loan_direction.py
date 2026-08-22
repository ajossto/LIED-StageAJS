"""Test §9 — le sens du prêt n'est plus imposé (§3.1 du prompt v2).

Quatre vérifications, toutes sur des paires CONSTRUITES À LA MAIN dont on
connaît la réponse analytiquement :

1. la règle de taux est symétrique BIT À BIT (question ouverte §12.2) ;
2. sur une paire où l'optimum de production jointe exige que la MOINS RICHE
   cède, le prêt part bien dans ce sens, le carnet enregistre la bonne
   débitrice, et la valeur nette de chacune est préservée par le transfert ;
3. le compteur `blocked_dir` devient contrefactuel : sous `free` il compte ce
   que la règle v1 aurait refusé, sans rien refuser ;
4. sous `loan_direction="richest_lends"`, la paire est effectivement refusée
   et aucun contrat n'est créé — la v1 est rejouable dans le même moteur.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_loan_direction.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.model import (  # noqa: E402
    Config,
    LoanBook,
    Population,
    Simulation,
    _run_market,
    net_worth,
    pair_rate,
)

#: Paire de référence, choisie pour que l'optimum aille à CONTRE-SENS de la
#: règle « la plus riche prête », et pour que la réponse soit une fraction
#: exacte plutôt qu'une racine.
#:
#: Les deux entités ont le même exposant γ = 1/2, donc λ* a une forme fermée
#: (kernel.py, régime (b)) : avec 1/(1−γ) = 2,
#:
#:     λ* = A_a² / (A_a² + A_b²) = 1 / (1 + 9) = 0,1.
#:
#: Le capital joint est C = 100 + 200 = 300, donc le capital optimal de `a`
#: est λ*·C = 30, et le transfert optimal vaut δ* = 30 − 100 = −70 : `a`, qui
#: est la MOINS riche, doit céder 70 à `b`. La règle v1 l'interdisait.
K_A, K_B = 100.0, 200.0
A_A, A_B = 1.0, 3.0
GAMMA = 0.5
DELTA_STAR = -70.0


def _pair(direction: str):
    """Construit la paire de référence et fait tourner UNE ronde de marché."""
    config = Config(
        seed=0, T=0, lam=0.0, sigma=0.0, delta=0.0, rho=0.5,
        A=A_A, gamma=GAMMA, loan_direction=direction,
    )
    simulation = Simulation(config)
    population = simulation.population
    tech_a = simulation.registry.intern(A_A, GAMMA)
    tech_b = simulation.registry.intern(A_B, GAMMA)
    simulation.kernel.sync_matrix()
    entity_a = population.born(K_A, 0, A_A, GAMMA, tech_a)
    entity_b = population.born(K_B, 0, A_B, GAMMA, tech_b)
    book = LoanBook()
    # rho = 0.5 et deux entités dans le pool : floor(0.5 × 2) = 1 ronde, et
    # le pool ne contient que cette paire.
    market, _ = _run_market(
        population, book, config, simulation.kernel, np.random.default_rng(0), 1
    )
    assert market["rounds"] == 1, market["rounds"]
    return population, book, market, entity_a, entity_b


def test_rate_is_symmetric():
    """√(m₁·m₂) ne distingue pas les deux côtés — au dernier bit près."""
    cases = [
        (100.0, 200.0, 0.5, 1.0, 0.5, 3.0),
        (1.0, 5000.0, 0.4, 2.0, 0.65, 0.3),
        (25.0, 25.0, 0.5, 1.0, 0.5, 1.0),
    ]
    for k1, k2, g1, a1, g2, a2 in cases:
        direct = pair_rate(k1, k2, g1, a1, g2, a2)
        swapped = pair_rate(k2, k1, g2, a2, g1, a1)
        assert direct == swapped, (direct, swapped)
    print(
        f"  règle de taux symétrique bit à bit sur {len(cases)} paires "
        "(question ouverte §12.2 : rien à changer)  OK"
    )


def test_kernel_says_the_poor_must_give():
    """L'institution demande bien un transfert négatif sur la paire choisie."""
    simulation = Simulation(Config(seed=0, T=0, A=A_A, gamma=GAMMA))
    tech_a = simulation.registry.intern(A_A, GAMMA)
    tech_b = simulation.registry.intern(A_B, GAMMA)
    simulation.kernel.sync_matrix()
    delta = simulation.kernel.solve_exact(tech_a, tech_b, K_A, K_B)
    assert abs(delta - DELTA_STAR) < 1e-9, delta
    print(
        f"  δ* = {delta:.12f} sur la paire de référence "
        f"(attendu {DELTA_STAR:+.0f} : la moins riche doit céder)  OK"
    )


def test_free_direction_lets_the_poor_lend():
    population, book, market, entity_a, entity_b = _pair("free")
    assert market["new_loans"] == 1, market
    assert market["reversed"] == 1, market
    assert abs(market["volume_rev"] - 70.0) < 1e-9, market["volume_rev"]
    # Le carnet : la MOINS riche détient la créance, la plus riche la dette.
    (loan_id, record), = book.loans.items()
    lender, borrower, principal, rate = record
    assert lender == entity_a and borrower == entity_b, (lender, borrower)
    assert abs(principal - 70.0) < 1e-9, principal
    assert loan_id in book.by_lender[entity_a]
    assert loan_id in book.by_borrower[entity_b]
    assert abs(book.claims[entity_a] - 70.0) < 1e-9
    assert abs(book.debts[entity_b] - 70.0) < 1e-9
    # Capitaux après transfert : 30 et 270, soit exactement l'allocation
    # optimale λ*C = 30 pour `a`.
    assert abs(population.K[entity_a] - 30.0) < 1e-9, population.K[entity_a]
    assert abs(population.K[entity_b] - 270.0) < 1e-9, population.K[entity_b]
    # La valeur nette de chacune est inchangée par le transfert lui-même.
    assert abs(net_worth(population, book, entity_a) - K_A) < 1e-9
    assert abs(net_worth(population, book, entity_b) - K_B) < 1e-9
    # Le taux ne dépend pas du sens : c'est √(m_a·m_b) aux capitaux d'avant.
    expected = pair_rate(K_A, K_B, GAMMA, A_A, GAMMA, A_B)
    assert rate == expected, (rate, expected)
    print(
        f"  sens libre : la moins riche (K={K_A:.0f}) prête {principal:.0f} à la plus "
        f"riche (K={K_B:.0f}) au taux {rate:.6g} ; carnet et valeurs nettes cohérents  OK"
    )


def test_counterfactual_counter():
    _, book_free, market_free, _, _ = _pair("free")
    _, book_v1, market_v1, _, _ = _pair("richest_lends")
    # Sous `free` : rien n'est refusé, mais le compteur dit que la règle v1
    # l'aurait été.
    assert market_free["blocked_dir"] == 1, market_free
    assert market_free["new_loans"] == 1, market_free
    # Sous `richest_lends` : la paire est réellement refusée.
    assert market_v1["blocked_dir"] == 1, market_v1
    assert market_v1["new_loans"] == 0, market_v1
    assert len(book_v1) == 0 and len(book_free) == 1
    print(
        "  compteur contrefactuel : 1 refus compté sous `free` (pour 1 prêt conclu), "
        "1 refus RÉEL sous `richest_lends` (0 prêt)  OK"
    )


def test_homogeneous_pair_is_unchanged():
    """En régime homogène, le sens libre redonne littéralement (K_b − K_a)/2."""
    config = Config(seed=0, T=0, lam=0.0, sigma=0.0, delta=0.0, rho=0.5, A=1.0, gamma=0.5)
    simulation = Simulation(config)
    population = simulation.population
    tech = simulation.default_tech
    a = population.born(100.0, 0, 1.0, 0.5, tech)
    b = population.born(200.0, 0, 1.0, 0.5, tech)
    book = LoanBook()
    market, _ = _run_market(
        population, book, config, simulation.kernel, np.random.default_rng(0), 1
    )
    assert market["reversed"] == 0 and market["blocked_dir"] == 0, market
    assert population.K[a] == 150.0 and population.K[b] == 150.0
    assert market["volume"] == 50.0, market["volume"]
    print("  régime homogène : δ = (K_b − K_a)/2 = 50, aucun prêt inversé  OK")


def main() -> int:
    print("test_loan_direction.py — sens du prêt libre (prompt v2 §3.1, §9)")
    test_rate_is_symmetric()
    test_kernel_says_the_poor_must_give()
    test_free_direction_lets_the_poor_lend()
    test_counterfactual_counter()
    test_homogeneous_pair_is_unchanged()
    print("test_loan_direction.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
