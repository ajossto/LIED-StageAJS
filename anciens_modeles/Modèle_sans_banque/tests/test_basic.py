"""
test_basic.py — Tests de validation unitaires pour claude_nouveau.

Couvre : extraction, dépréciation, auto-investissement (surplus), prêts,
         scission, faillite, masse de faillite, taux interne,
         simulation complète, marché du crédit.
"""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import SimulationConfig
from models import Entity, Loan
from simulation import Simulation


def make_config(**kwargs):
    cfg = SimulationConfig()
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg


# ------------------------------------------------------------------
#  1. Extraction depuis la nature
# ------------------------------------------------------------------
def test_extraction():
    cfg = make_config(alpha=2.0, lambda_creation=0, seed=0, duree_simulation=1)
    sim = Simulation(cfg)
    # Une seule entité, passif_inne = 5
    sim.entities = {}
    sim.next_entity_id = 1
    e = sim.create_entity(actif_liquide=0.0, passif_inne=4.0)
    liq_avant = e.actif_liquide
    sim.extract_from_nature()
    expected = e.alpha * math.sqrt(e.passif_total)
    assert abs(e.actif_liquide - (liq_avant + expected)) < 1e-9, \
        f"Extraction incorrecte : {e.actif_liquide} ≠ {liq_avant + expected}"
    print("  [OK] test_extraction")


# ------------------------------------------------------------------
#  2. Dépréciation
# ------------------------------------------------------------------
def test_depreciation():
    cfg = make_config(
        taux_depreciation_liquide=0.1,
        taux_depreciation_endo=0.2,
        taux_depreciation_exo=0.05,
        lambda_creation=0, seed=0,
    )
    sim = Simulation(cfg)
    sim.entities = {}
    sim.next_entity_id = 1
    e = sim.create_entity(actif_liquide=100.0, passif_inne=10.0)
    e.actif_endoinvesti = 50.0
    e.passif_endoinvesti = 50.0
    e.actif_exoinvesti = 20.0
    e.passif_exoinvesti = 20.0
    sim.apply_depreciation()
    assert abs(e.actif_liquide - 90.0) < 1e-9
    assert abs(e.actif_endoinvesti - 40.0) < 1e-9
    assert abs(e.passif_endoinvesti - 40.0) < 1e-9
    assert abs(e.actif_exoinvesti - 19.0) < 1e-9
    assert abs(e.passif_exoinvesti - 19.0) < 1e-9
    print("  [OK] test_depreciation")


# ------------------------------------------------------------------
#  3. Auto-investissement (sur surplus uniquement)
# ------------------------------------------------------------------
def test_auto_invest_on_surplus():
    cfg = make_config(
        fraction_auto_investissement=0.5,
        seuil_ratio_liquide_passif=0.1,
        lambda_creation=0, seed=0,
    )
    sim = Simulation(cfg)
    sim.entities = {}
    sim.next_entity_id = 1
    # L=20, P=10 → réserve = max(s·P, B_innée) = max(0.1*10, 10) = 10
    # surplus = 20 - 10 = 10 → x = 0.5 * 10 = 5
    e = sim.create_entity(actif_liquide=20.0, passif_inne=10.0)
    sim.auto_invest_end_of_turn()
    reserve = max(cfg.seuil_ratio_liquide_passif * e.passif_total, e.passif_inne)
    expected_surplus = max(0.0, 20.0 - reserve)
    expected_x = 0.5 * expected_surplus
    assert abs(e.actif_liquide - (20.0 - expected_x)) < 1e-9, \
        f"Liquide après auto-invest : {e.actif_liquide} ≠ {20.0 - expected_x}"
    assert abs(e.actif_endoinvesti - expected_x) < 1e-9
    assert abs(e.passif_endoinvesti - expected_x) < 1e-9
    print("  [OK] test_auto_invest_on_surplus")


# ------------------------------------------------------------------
#  4. Auto-invest nul si pas de surplus
# ------------------------------------------------------------------
def test_auto_invest_no_surplus():
    cfg = make_config(
        fraction_auto_investissement=0.5,
        seuil_ratio_liquide_passif=0.5,  # seuil élevé
        lambda_creation=0, seed=0,
    )
    sim = Simulation(cfg)
    sim.entities = {}
    sim.next_entity_id = 1
    # L=1, P=10 → L/P = 0.1 < seuil=0.5 → surplus négatif → clampé à 0
    e = sim.create_entity(actif_liquide=1.0, passif_inne=10.0)
    sim.auto_invest_end_of_turn()
    assert abs(e.actif_endoinvesti - 0.0) < 1e-9
    print("  [OK] test_auto_invest_no_surplus")


# ------------------------------------------------------------------
#  5. Exécution d'un prêt
# ------------------------------------------------------------------
def test_execute_loan():
    cfg = make_config(lambda_creation=0, seed=0)
    sim = Simulation(cfg)
    sim.entities = {}
    sim.next_entity_id = 1
    lender = sim.create_entity(actif_liquide=100.0, passif_inne=10.0)
    borrower = sim.create_entity(actif_liquide=10.0, passif_inne=5.0)
    sim.execute_loan(lender, borrower, principal=30.0, rate=0.05)
    assert abs(lender.actif_liquide - 70.0) < 1e-9
    assert abs(lender.actif_prete - 30.0) < 1e-9
    assert abs(borrower.actif_exoinvesti - 30.0) < 1e-9
    assert abs(borrower.passif_exoinvesti - 30.0) < 1e-9
    print("  [OK] test_execute_loan")


# ------------------------------------------------------------------
#  6. Scission d'un prêt
# ------------------------------------------------------------------
def test_loan_split():
    loan = Loan(loan_id=1, lender_id=10, borrower_id=20, principal=100.0, rate=0.03)
    transferred, remaining = loan.split(2, 3, 40.0, new_lender_id=99)
    assert not loan.active
    assert abs(transferred.principal - 40.0) < 1e-9
    assert transferred.lender_id == 99
    assert abs(remaining.principal - 60.0) < 1e-9
    assert remaining.lender_id == 10
    assert transferred.parent_loan_id == 1
    assert remaining.parent_loan_id == 1
    print("  [OK] test_loan_split")


# ------------------------------------------------------------------
#  7. Taux interne marginal
# ------------------------------------------------------------------
def test_internal_rate():
    cfg = make_config(alpha=2.0, lambda_creation=0, seed=0)
    sim = Simulation(cfg)
    sim.entities = {}
    sim.next_entity_id = 1
    e = sim.create_entity(passif_inne=4.0, actif_liquide=0.0)
    r = sim.compute_internal_rate(e)
    expected = e.alpha / (2.0 * math.sqrt(4.0))
    assert abs(r - expected) < 1e-9
    print("  [OK] test_internal_rate")


# ------------------------------------------------------------------
#  8. Faillite simple
# ------------------------------------------------------------------
def test_bankruptcy():
    cfg = make_config(lambda_creation=0, seed=0)
    sim = Simulation(cfg)
    sim.entities = {}
    sim.next_entity_id = 1
    lender = sim.create_entity(actif_liquide=50.0, passif_inne=5.0)
    borrower = sim.create_entity(actif_liquide=0.1, passif_inne=5.0)
    sim.execute_loan(lender, borrower, principal=20.0, rate=0.05)
    # Rendre borrower insolvable
    borrower.actif_liquide = 0.0
    borrower.actif_exoinvesti = 1.0  # actif_total = 1 < passif_total = 25
    assert sim.is_bankrupt(borrower)
    totals, cascade_ev = sim.resolve_cascades()
    assert not borrower.alive
    assert lender.actif_prete < 20.0  # créance annulée
    assert cascade_ev is not None
    assert cascade_ev.nb_entites_faillie == 1
    print("  [OK] test_bankruptcy")


# ------------------------------------------------------------------
#  9. Simulation complète (courte)
# ------------------------------------------------------------------
def test_full_simulation():
    cfg = make_config(
        duree_simulation=20,
        lambda_creation=0.3,
        seed=99,
    )
    sim = Simulation(cfg)
    stats = sim.run(verbose=False)
    assert len(stats) == 20
    assert all("step" in s for s in stats)
    assert sim.current_step == 20
    print("  [OK] test_full_simulation")


# ------------------------------------------------------------------
#  10. Collecteur statistique
# ------------------------------------------------------------------
def test_collector():
    cfg = make_config(duree_simulation=50, seed=7, freq_snapshot=5)
    sim = Simulation(cfg)
    sim.run(verbose=False)
    assert len(sim.collector.indicators) == 50
    # Un snapshot toutes les 5 étapes → ~10 * 6 grandeurs
    assert len(sim.collector.snapshots) > 0
    print("  [OK] test_collector")


# ------------------------------------------------------------------
#  LANCEMENT
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("Tests claude_nouveau\n")
    tests = [
        test_extraction,
        test_depreciation,
        test_auto_invest_on_surplus,
        test_auto_invest_no_surplus,
        test_execute_loan,
        test_loan_split,
        test_internal_rate,
        test_bankruptcy,
        test_full_simulation,
        test_collector,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{len(tests)} tests réussis", end="")
    if failed:
        print(f" ({failed} échec(s))")
        sys.exit(1)
    else:
        print(" ✓")
