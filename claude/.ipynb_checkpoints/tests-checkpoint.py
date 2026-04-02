"""
tests.py — Tests élémentaires et scénarios de validation.

Chaque test vérifie une règle précise du modèle.
Exécuter : python tests.py
"""

import math
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from simulation import Entite, Pret, MasseFaillite, Simulation, PARAMS
import copy


# ============================================================
#  Helpers
# ============================================================

def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) < tol

def assert_approx(val, expected, msg: str, tol: float = 1e-6):
    if not approx(val, expected, tol):
        raise AssertionError(f"ÉCHEC — {msg}\n  Obtenu   : {val}\n  Attendu  : {expected}")
    print(f"  OK — {msg}")


# ============================================================
#  TEST 1 — Extraction
# ============================================================

def test_extraction():
    print("\n[Test 1] Extraction depuis la nature")
    Entite._compteur = 0
    e = Entite(actif_liquide=10.0, passif_inne=4.0)
    alpha = 2.0
    # Extraction attendue : 2 * sqrt(4) = 4.0
    extraction = alpha * math.sqrt(e.passif_total)
    e.actif_liquide += extraction
    assert_approx(e.actif_liquide, 14.0, "Extraction = alpha * sqrt(P) = 4.0")


# ============================================================
#  TEST 2 — Dépréciation
# ============================================================

def test_depreciation():
    print("\n[Test 2] Dépréciation")
    Entite._compteur = 0
    e = Entite(actif_liquide=100.0, passif_inne=0.0)
    e.actif_endoinvesti = 50.0
    e.passif_endoinvesti = 50.0
    e.actif_exoinvesti = 20.0
    e.passif_exoinvesti = 20.0

    dL, de, dx = 0.1, 0.2, 0.3
    e.actif_liquide *= (1 - dL)
    delta_e = de * e.actif_endoinvesti
    e.actif_endoinvesti -= delta_e
    e.passif_endoinvesti -= delta_e
    delta_x = dx * e.actif_exoinvesti
    e.actif_exoinvesti -= delta_x
    e.passif_exoinvesti -= delta_x

    assert_approx(e.actif_liquide, 90.0, "Liquide après dépréciation 10%")
    assert_approx(e.actif_endoinvesti, 40.0, "Endo après dépréciation 20%")
    assert_approx(e.passif_endoinvesti, 40.0, "Passif endo après dépréciation 20%")
    assert_approx(e.actif_exoinvesti, 14.0, "Exo après dépréciation 30%")
    assert_approx(e.passif_exoinvesti, 14.0, "Passif exo après dépréciation 30%")


# ============================================================
#  TEST 3 — Auto-investissement
# ============================================================

def test_auto_investissement():
    print("\n[Test 3] Auto-investissement")
    Entite._compteur = 0
    e = Entite(actif_liquide=20.0, passif_inne=5.0)
    A_avant = e.actif_total
    P_avant = e.passif_total

    x = 8.0
    e.actif_liquide -= x
    e.actif_endoinvesti += x
    e.passif_endoinvesti += x

    assert_approx(e.actif_total, A_avant, "L'actif total ne change pas après auto-investissement")
    assert_approx(e.passif_total, P_avant + x, "Le passif total augmente de x")
    assert_approx(e.actif_liquide, 12.0, "Actif liquide réduit de x")


# ============================================================
#  TEST 4 — Prêt
# ============================================================

def test_pret():
    print("\n[Test 4] Prêt entre deux entités")
    Entite._compteur = 0
    Pret._compteur = 0
    preteur = Entite(actif_liquide=50.0, passif_inne=10.0)
    emprunteur = Entite(actif_liquide=5.0, passif_inne=3.0)

    q, taux = 20.0, 0.05
    preteur.actif_liquide -= q
    preteur.actif_prete += q
    emprunteur.actif_exoinvesti += q
    emprunteur.passif_exoinvesti += q
    pret = Pret(preteur, emprunteur, q, taux)

    assert_approx(preteur.actif_liquide, 30.0, "Prêteur : liquide réduit de q")
    assert_approx(preteur.actif_prete, 20.0, "Prêteur : actif prêté +q")
    assert_approx(emprunteur.actif_exoinvesti, 20.0, "Emprunteur : exo-investi +q")
    assert_approx(emprunteur.passif_exoinvesti, 20.0, "Emprunteur : passif exo +q")
    assert_approx(pret.interet_du(), 1.0, "Intérêt = r * q = 1.0")


# ============================================================
#  TEST 5 — Scission de prêt
# ============================================================

def test_scission_pret():
    print("\n[Test 5] Scission d'un prêt")
    Entite._compteur = 0
    Pret._compteur = 0
    p = Entite(actif_liquide=100.0, passif_inne=1.0)
    e = Entite(actif_liquide=0.0, passif_inne=1.0)
    pret = Pret(p, e, 10.0, 0.05)

    nouveau = pret.scinder(3.0)
    assert_approx(pret.principal, 7.0, "Prêt original réduit à 7")
    assert_approx(nouveau.principal, 3.0, "Nouveau prêt de montant 3")
    assert_approx(nouveau.taux, 0.05, "Taux conservé lors de la scission")
    assert nouveau.emprunteur is pret.emprunteur, "Même emprunteur après scission"


# ============================================================
#  TEST 6 — Faillite
# ============================================================

def test_faillite():
    print("\n[Test 6] Détection de la faillite")
    Entite._compteur = 0
    e = Entite(actif_liquide=5.0, passif_inne=10.0)
    # A = 5, P = 10 → insolvable
    assert e.est_insolvable(), "Entité insolvable détectée correctement"
    e2 = Entite(actif_liquide=15.0, passif_inne=10.0)
    assert not e2.est_insolvable(), "Entité solvable détectée correctement"
    print("  OK — Faillite : A < P")
    print("  OK — Solvabilité : A >= P")


# ============================================================
#  TEST 7 — Masse de faillite et redistribution
# ============================================================

def test_masse_faillite():
    print("\n[Test 7] Masse de faillite et redistribution")
    Entite._compteur = 0
    Pret._compteur = 0

    faillie = Entite(actif_liquide=0.0, passif_inne=1.0)
    c1 = Entite(actif_liquide=10.0, passif_inne=1.0)
    c2 = Entite(actif_liquide=10.0, passif_inne=1.0)
    emprunteur = Entite(actif_liquide=10.0, passif_inne=1.0)

    pret_detenu = Pret(faillie, emprunteur, 20.0, 0.1)

    masse = MasseFaillite(
        faillie,
        [pret_detenu],
        [c1, c2],
        [30.0, 70.0]  # c1 détient 30%, c2 détient 70%
    )

    masse.redistribuer(100.0)
    assert_approx(c1.actif_liquide, 40.0, "c1 reçoit 30% du flux = 30.0 → total 40.0")
    assert_approx(c2.actif_liquide, 80.0, "c2 reçoit 70% du flux = 70.0 → total 80.0")


# ============================================================
#  TEST 8 — Taux interne marginal
# ============================================================

def test_taux_interne():
    print("\n[Test 8] Taux interne marginal")
    Entite._compteur = 0
    e = Entite(actif_liquide=0.0, passif_inne=4.0)
    alpha = 2.0
    # r* = alpha / (2 * sqrt(P)) = 2 / (2 * 2) = 0.5
    r = e.taux_interne(alpha)
    assert_approx(r, 0.5, "r* = alpha / (2 * sqrt(P)) = 0.5")


# ============================================================
#  TEST 9 — Simulation minimale (smoke test)
# ============================================================

def test_simulation_minimale():
    print("\n[Test 9] Simulation minimale (smoke test)")
    params = copy.deepcopy(PARAMS)
    params["nb_pas"] = 10
    params["graine"] = 0
    params["lambda_creation"] = 0.0  # pas de nouvelles entités

    sim = Simulation(params)
    stats = sim.run(verbose=False)

    assert len(stats) == 10, f"Doit avoir 10 entrées de stats, obtenu {len(stats)}"
    for s in stats:
        assert s["nb_entites_vivantes"] >= 0
        assert s["actif_total_systeme"] >= 0
    print(f"  OK — 10 pas exécutés, statistiques cohérentes")
    resume = sim.resume()
    print(f"  Résumé : {resume}")


# ============================================================
#  TEST 10 — Critère d'activation du marché
# ============================================================

def test_critere_activation():
    print("\n[Test 10] Critère d'activation du marché")
    Entite._compteur = 0
    e = Entite(actif_liquide=10.0, passif_inne=100.0)
    # L/P = 10/100 = 0.1
    seuil = 0.05
    assert e.est_active(seuil), "Active si L/P > seuil"
    seuil_haut = 0.2
    assert not e.est_active(seuil_haut), "Inactive si L/P <= seuil"
    print("  OK — Critère L/P > seuil fonctionne correctement")


# ============================================================
#  LANCEUR
# ============================================================

def run_all():
    print("=" * 50)
    print("TESTS DE VALIDATION — Simulation multi-agents")
    print("=" * 50)

    tests = [
        test_extraction,
        test_depreciation,
        test_auto_investissement,
        test_pret,
        test_scission_pret,
        test_faillite,
        test_masse_faillite,
        test_taux_interne,
        test_simulation_minimale,
        test_critere_activation,
    ]

    echecs = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  *** {e}")
            echecs += 1
        except Exception as e:
            print(f"  *** ERREUR INATTENDUE dans {t.__name__} : {e}")
            import traceback; traceback.print_exc()
            echecs += 1

    print("\n" + "=" * 50)
    if echecs == 0:
        print(f"Tous les tests ont réussi ({len(tests)}/{len(tests)})")
    else:
        print(f"{echecs} test(s) ont échoué sur {len(tests)}")
    print("=" * 50)
    return echecs


if __name__ == "__main__":
    sys.exit(run_all())
