"""Tests §8 — institution de principal : les trois régimes du prompt §3.1.

Convention du dépôt (CLAUDE.md) : assertions Python simples, pas de pytest.
Lancer :
    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_institution.py

Le solveur de RÉFÉRENCE de ce fichier est indépendant de la machinerie
(t, u, z) du noyau : c'est une bissection sur la condition du premier ordre

    a α (x+δ)^{α-1} - b β (y-δ)^{β-1} = 0,

strictement décroissante en δ sur ]-x, y[. Vérifier le noyau contre sa
propre reformulation ne prouverait rien.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.kernel import (  # noqa: E402
    PrincipalKernel,
    TechRegistry,
    joint_production_gain,
    lambda_star,
    newton_z,
)
from m4_3live_v2.model import (  # noqa: E402
    Config,
    Intervention,
    Simulation,
    net_worth,
)

# Tolérances DOCUMENTÉES (prompt §8). L'unité pertinente est le CAPITAL :
# les écarts sont normalisés par C = x + y (l'échelle du problème), pas par
# δ lui-même — δ peut être arbitrairement petit près d'un partage neutre,
# et une erreur relative à δ y exploserait sans qu'aucune quantité physique
# ne soit dégradée.
TOL_IDENTITY = 0.0  # régime (a) : égalité bit à bit exigée
TOL_CLOSED_FORM = 1e-14  # régime (b) : forme fermée vs bissection, en unités de C
TOL_NEWTON = 1e-12  # régime (c) : Newton exact vs bissection, en unités de C
TOL_LUT = 1e-8  # régime (c) : LUT cubique vs Newton exact (absolu, unités de capital)


def bisect_delta(a, alpha, b, beta, x, y, iterations=400):
    """Référence indépendante : δ* par bissection sur la dérivée."""

    def derivative(delta):
        return a * alpha * (x + delta) ** (alpha - 1.0) - b * beta * (y - delta) ** (beta - 1.0)

    lo, hi = -x * (1.0 - 1e-15), y * (1.0 - 1e-15)
    assert derivative(lo) > 0.0 and derivative(hi) < 0.0, "l'optimum doit être intérieur"
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if derivative(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def relative(value, reference, scale=1.0):
    """Écart normalisé par l'échelle de capital du problème (voir TOL_*)."""
    return abs(value - reference) / max(1.0, abs(scale))


CASES_XY = [
    (100.0, 900.0),
    (1.0, 3.0),
    (0.5, 2213.6),
    (192.0, 1589.6),
    (795.0, 795.5),
    (1e-3, 1e3),
    (12345.0, 98765.0),
]


def test_regime_a_identity():
    """(a) Même technologie : (K_ℓ - K_b)/2, littéral et bit à bit."""
    registry = TechRegistry()
    kernel = PrincipalKernel(registry)
    tech = registry.intern(1.0, 0.5)
    kernel.sync_matrix()
    for x, y in CASES_XY:
        if y <= x:
            continue
        delta = kernel.solve(tech, tech, x, y)
        expected = 0.5 * (y - x)
        assert delta == expected, f"régime (a) non bit-exact : {delta!r} != {expected!r}"
        # et c'est bien l'optimum de production jointe
        reference = bisect_delta(1.0, 0.5, 1.0, 0.5, x, y)
        assert relative(delta, reference, x + y) < 1e-12, (delta, reference)
    print("  (a) identité technologique : δ = (K_ℓ-K_b)/2 bit à bit, et = optimum jointe  OK")


def test_regime_b_closed_form():
    """(b) γ égaux, A différents : forme fermée éq.14, et λ* ≠ 1/2."""
    registry = TechRegistry()
    kernel = PrincipalKernel(registry)
    checked = 0
    for gamma in (0.3, 0.5, 0.6666666666666666, 0.9):
        for a_b, a_l in ((1.0, 1.25), (1.5, 1.0), (1.0, 1.0), (2.0, 0.4)):
            tech_b = registry.intern(a_b, gamma)
            tech_l = registry.intern(a_l, gamma)
            kernel.sync_matrix()
            if tech_b == tech_l:
                continue
            for x, y in CASES_XY:
                delta = kernel.solve(tech_b, tech_l, x, y)
                reference = bisect_delta(a_b, gamma, a_l, gamma, x, y)
                assert relative(delta, reference, x + y) < TOL_CLOSED_FORM, (
                    gamma, a_b, a_l, x, y, delta, reference,
                )
                checked += 1
            # λ* = 1/2 si et seulement si A_b == A_l
            lam = lambda_star(a_b, gamma, a_l, gamma, 1000.0)
            if a_b == a_l:
                assert lam == 0.5
            else:
                assert abs(lam - 0.5) > 1e-3, (gamma, a_b, a_l, lam)
    print(f"  (b) γ égaux : forme fermée exacte sur {checked} cas, λ* ≠ 1/2 dès que A_b ≠ A_ℓ  OK")


def test_regime_b_is_not_the_historical_rule():
    """Le régime (b) n'est PAS (K_ℓ-K_b)/2 : une intervention sur A seul
    déplace déjà le partage (piège signalé au §3.1 du prompt)."""
    registry = TechRegistry()
    kernel = PrincipalKernel(registry)
    tech_b = registry.intern(1.5, 0.5)
    tech_l = registry.intern(1.0, 0.5)
    kernel.sync_matrix()
    x, y = 400.0, 1200.0
    delta = kernel.solve(tech_b, tech_l, x, y)
    arithmetic = 0.5 * (y - x)
    assert delta > arithmetic * 1.2, (delta, arithmetic)
    # λ* = 1.5² / (1.5² + 1²) = 0.6923...
    expected_lambda = 1.5**2 / (1.5**2 + 1.0**2)
    assert relative(delta, expected_lambda * (x + y) - x, x + y) < 1e-14
    print(f"  (b) A_b=1.5 vs A_ℓ=1.0 : δ={delta:.3f} contre {arithmetic:.3f} (arithmétique)  OK")


def test_regime_c_newton():
    """(c) γ différents : Newton exact vs bissection indépendante."""
    registry = TechRegistry()
    kernel = PrincipalKernel(registry)
    checked = 0
    worst = 0.0
    for (a_b, g_b), (a_l, g_l) in (
        ((1.0, 0.5), (1.25, 0.6)),
        ((1.25, 0.6), (1.0, 0.5)),
        ((1.0, 0.2), (1.0, 0.9)),
        ((3.0, 0.9), (0.2, 0.15)),
        ((1.0, 0.5), (1.0, 0.5000001)),
    ):
        tech_b = registry.intern(a_b, g_b)
        tech_l = registry.intern(a_l, g_l)
        kernel.sync_matrix()
        for x, y in CASES_XY:
            delta = kernel.solve_exact(tech_b, tech_l, x, y)
            reference = bisect_delta(a_b, g_b, a_l, g_l, x, y)
            error = relative(delta, reference, x + y)
            worst = max(worst, error)
            assert error < TOL_NEWTON, (a_b, g_b, a_l, g_l, x, y, delta, reference, error)
            checked += 1
    print(f"  (c) Newton exact : {checked} cas, erreur relative max {worst:.2e} < {TOL_NEWTON:.0e}  OK")


def test_regime_c_lut_and_warm():
    """(c) Chemins chaud (LUT) et tiède (une étape de Newton) vs exact."""
    for policy, threshold in (("exact_lut", 5), ("hybrid", 5)):
        registry = TechRegistry()
        kernel = PrincipalKernel(registry, policy=policy, threshold=threshold, points=65)
        tech_b = registry.intern(1.0, 0.5)
        tech_l = registry.intern(1.25, 0.6)
        kernel.sync_matrix()
        # Chauffe la ligne d'exposant de C ≈ 1590 puis mesure la LUT.
        base = [(200.0 + 3.0 * i, 1400.0 - 1.0 * i) for i in range(60)]
        for x, y in base:
            kernel.solve(tech_b, tech_l, x, y)
        worst_lut = 0.0
        for x, y in base:
            delta = kernel.solve(tech_b, tech_l, x, y)
            exact = kernel.solve_exact(tech_b, tech_l, x, y)
            worst_lut = max(worst_lut, abs(delta - exact))
        counts = kernel.path_counts
        assert counts["lut"] > 0, "la table n'a jamais été utilisée"
        assert counts["build"] > 0, "la table n'a jamais été compilée"
        assert worst_lut < TOL_LUT, (policy, worst_lut)
        if policy == "hybrid":
            assert counts["warm"] > 0, "le chemin tiède n'a jamais servi"
        print(
            f"  (c) politique {policy!r} : LUT vs Newton exact, écart max "
            f"{worst_lut:.2e} unité de capital ; chemins {dict(counts)}  OK"
        )


def test_lut_convergence_order():
    """La LUT est bien une cubique de Hermite alimentée par h'(C) = q h / S
    (rapport éq. 12) : l'erreur doit décroître en O(pas⁴). Une dérivée
    fausse donnerait O(pas²) — ce test distingue les deux."""
    errors = []
    for points in (17, 33, 65):
        registry = TechRegistry()
        kernel = PrincipalKernel(registry, threshold=5, points=points)
        tech_b = registry.intern(1.0, 0.5)
        tech_l = registry.intern(1.25, 0.6)
        kernel.sync_matrix()
        base = [(200.0 + 3.0 * i, 1400.0 - 1.0 * i) for i in range(60)]
        for x, y in base:
            kernel.solve(tech_b, tech_l, x, y)
        errors.append(
            max(abs(kernel.solve(tech_b, tech_l, x, y) - kernel.solve_exact(tech_b, tech_l, x, y))
                for x, y in base)
        )
    ratios = [errors[i] / errors[i + 1] for i in range(len(errors) - 1)]
    for ratio in ratios:
        assert 10.0 < ratio < 24.0, f"ordre de convergence inattendu : {ratios}"
    print(
        f"  LUT : erreurs {['%.2e' % e for e in errors]} pour 17/33/65 nœuds, "
        f"rapports {['%.1f' % r for r in ratios]} ≈ 16 (ordre 4)  OK"
    )


def test_warm_path_error_is_real():
    """Le chemin tiède du rapport n'est PAS exact : on mesure son erreur sur
    le domaine réel de M4.3 (quantiles de C : 192 / 1590 / 2214)."""
    registry = TechRegistry()
    kernel = PrincipalKernel(registry, policy="hybrid", threshold=10**9)
    tech_b = registry.intern(1.0, 0.5)
    tech_l = registry.intern(1.25, 0.6)
    kernel.sync_matrix()
    worst = 0.0
    for capital_sum in (192.0, 800.0, 1589.6, 2213.6):
        for fraction in (0.1, 0.3, 0.5, 0.7):
            x = fraction * capital_sum
            y = capital_sum - x
            kernel.solve(tech_b, tech_l, x, y)  # 1er appel : Newton exact
            warm = kernel.solve(tech_b, tech_l, x, y)  # 2e appel : chemin tiède
            exact = kernel.solve_exact(tech_b, tech_l, x, y)
            worst = max(worst, abs(warm - exact))
    assert worst > 1e-6, "le chemin tiède devrait être approché, pas exact"
    print(
        f"  chemin tiède : erreur max {worst:.3e} unité de capital sur le domaine réel "
        f"(≫ LUT {TOL_LUT:.0e}) — motive le défaut 'exact_lut'  OK"
    )


def test_delta_is_a_maximiser():
    """δ* maximise bien la production jointe : perturbations des deux côtés."""
    for (a_b, g_b), (a_l, g_l) in (((1.0, 0.5), (1.25, 0.6)), ((2.0, 0.4), (0.5, 0.8))):
        for x, y in ((300.0, 1200.0), (10.0, 40.0)):
            reference = bisect_delta(a_b, g_b, a_l, g_l, x, y)
            best = joint_production_gain(a_b, g_b, a_l, g_l, x, y, reference)
            for perturbation in (-1e-2, -1e-4, 1e-4, 1e-2):
                other = joint_production_gain(
                    a_b, g_b, a_l, g_l, x, y, reference + perturbation
                )
                assert other <= best + 1e-12, (a_b, g_b, a_l, g_l, x, y, perturbation)
            assert best > 0.0
    print("  δ* est bien un maximum de la production jointe (perturbations bilatérales)  OK")


def test_newton_z_identity():
    """z résout exactement t = -z/2 + u L(z), et z = -2t quand u = 0."""
    worst = 0.0
    for t in (-30.0, -3.0, -0.1, 0.0, 0.7, 5.0, 40.0):
        assert newton_z(t, 0.0) == -2.0 * t
        for u in (-0.9, -0.4, -0.05, 0.05, 0.4, 0.9):
            z = newton_z(t, u)
            residual = -0.5 * z + u * (0.5 * abs(z) + math.log1p(math.exp(-abs(z)))) - t
            worst = max(worst, abs(residual))
    assert worst < 1e-12, worst
    print(f"  résidu max de l'équation d'optimalité : {worst:.2e}  OK")


def test_transfer_preserves_net_worth():
    """Le transfert ne peut pas créer d'insolvabilité DANS le pas : K baisse
    de q, les créances montent de q, la valeur nette est inchangée."""
    config = Config(seed=3, T=0, lam=20.0)
    sim = Simulation(config)
    for _ in range(40):
        sim.step()
    worst = 0.0
    for entity in sim.population.living():
        value = net_worth(sim.population, sim.book, entity)
        worst = max(worst, 0.0 if value >= -1e-9 else abs(value))
    assert worst == 0.0, worst
    errors = sim.book.consistency_errors(sim.population.alive)
    assert not errors, errors[:5]
    print("  valeur nette préservée par le transfert, carnet cohérent  OK")


def test_direction_block_is_counted():
    """Quand la technologie de la RICHE est meilleure, l'optimum jointe veut
    faire circuler le capital du pauvre vers le riche : le marché refuse, et
    ce refus est compté séparément (compteur `mkt_blocked_dir`)."""
    config = Config(seed=5, T=0, lam=25.0)
    sim = Simulation(config)
    for _ in range(30):
        sim.step()
    before = sum(row["mkt_blocked_dir"] for row in sim.series)
    assert before == 0, "aucune paire ne devrait être bloquée en régime homogène"
    # On dote la moitié la plus RICHE d'un A supérieur.
    living = sorted(sim.population.living(), key=lambda e: -sim.population.K[e])
    rich = living[: len(living) // 2]
    sim.submit(Intervention(param="A", value=3.0, scope="fraction", ids=rich))
    for _ in range(5):
        sim.step()
    after = sum(row["mkt_blocked_dir"] for row in sim.series[-5:])
    assert after > 0, "des paires devraient être bloquées par le sens du prêt"
    print(f"  paires bloquées par le sens du prêt après dotation des riches : {after}  OK")


def main():
    print("test_institution.py — institution de principal (prompt §3, §8)")
    test_regime_a_identity()
    test_regime_b_closed_form()
    test_regime_b_is_not_the_historical_rule()
    test_regime_c_newton()
    test_regime_c_lut_and_warm()
    test_lut_convergence_order()
    test_warm_path_error_is_real()
    test_delta_is_a_maximiser()
    test_newton_z_identity()
    test_transfer_preserves_net_worth()
    test_direction_block_is_counted()
    print("test_institution.py : tout est passé.")


if __name__ == "__main__":
    main()
