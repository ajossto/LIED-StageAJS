"""Tests §8 — chantier taux/p (prompt §3.4) : positivité et solvabilité.

HYPOTHÈSE DE CONVERSION retenue, et c'est elle la vraie question ouverte du
§3.4 : dans ce modèle la production A·K^γ est un FLUX PAR PAS, donc le
surplus coopératif Δ créé par la réallocation est lui aussi un flux par pas,
qui persiste tant que l'allocation persiste. On le gèle au moment du contrat
— exactement comme `pair_rate` gèle déjà le rendement marginal — et on
impose que le service perpétuel r·q verse à la prêteuse sa part p du surplus
par pas :

    r · q = p · Δ        d'où      r = p Δ / q.

Le prompt décrit Δ comme « une quantité ponctuelle » ; sur les termes du
modèle c'est un flux, et c'est précisément ce qui rend la conversion bien
posée sans horizon ni actualisation implicites. Cette lecture est signalée
ici plutôt que laissée implicite.

Ce fichier vérifie les deux exigences du prompt : r > 0, et absence de pic
de défauts MÉCANIQUE au pas suivant.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_surplus_rate.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.kernel import PrincipalKernel, TechRegistry, joint_production_gain  # noqa: E402
from m4_3live_v2.model import Config, Simulation, pair_rate, surplus_rate  # noqa: E402

PAIRS = [(x, 3.0 * x) for x in (5.0, 50.0, 200.0, 795.0, 2000.0)] + [
    (400.0, 1200.0),
    (700.0, 900.0),
    (1.0, 2000.0),
]
TECHS = (((1.0, 0.5), (1.0, 0.5)), ((1.5, 0.5), (1.0, 0.5)), ((1.0, 0.5), (1.25, 0.6)))


def test_rate_is_strictly_positive_and_below_the_marginal_rate():
    registry = TechRegistry()
    kernel = PrincipalKernel(registry)
    worst_ratio = 0.0
    checked = 0
    for (a_b, g_b), (a_l, g_l) in TECHS:
        tech_b = registry.intern(a_b, g_b)
        tech_l = registry.intern(a_l, g_l)
        kernel.sync_matrix()
        for x, y in PAIRS:
            delta = kernel.solve(tech_b, tech_l, x, y)
            if delta <= 0.0:
                continue
            surplus = joint_production_gain(a_b, g_b, a_l, g_l, x, y, delta)
            assert surplus > 0.0, (a_b, g_b, a_l, g_l, x, y, surplus)
            rate = surplus_rate(delta, surplus, 0.5)
            assert rate > 0.0, (x, y, rate)
            marginal = pair_rate(y, x, g_l, a_l, g_b, a_b)
            worst_ratio = max(worst_ratio, rate / marginal)
            checked += 1
    assert checked >= 15
    assert worst_ratio < 1.0, (
        f"le taux au surplus dépasse le taux marginal (rapport {worst_ratio:.3f}) : "
        "risque de service mécaniquement plus lourd"
    )
    print(
        f"  r = pΔ/q > 0 sur {checked} paires ; rapport maximal au taux marginal "
        f"{worst_ratio:.3f} < 1 (service PLUS LÉGER, pas plus lourd)  OK"
    )


def test_surplus_rate_does_not_create_a_default_spike():
    """Aucun pic de défauts mécanique au pas qui suit la bascule de règle.

    `due` est prélevé AVANT la dépréciation (model.py, phase d'intérêts) :
    un taux dérivé du surplus qui serait très supérieur au rendement
    marginal provoquerait une vague de défauts de LIQUIDITÉ n'ayant rien à
    voir avec la question du rebond. On compare donc, sur la même graine et
    la même fenêtre, la règle candidate à la règle par défaut.
    """
    window = 120
    results = {}
    for rule in ("marginal", "surplus_share"):
        simulation = Simulation(
            Config(seed=17, lam=25.0, T=window, rate_rule=rule, surplus_share_p=0.5)
        )
        simulation.run()
        rows = simulation.series
        results[rule] = {
            "defaults": sum(row["defaults"] for row in rows),
            "deaths": sum(row["deaths"] for row in rows),
            "max_defaults": max(row["defaults"] for row in rows),
            "interest": sum(row["interest_paid"] for row in rows),
            "prod": rows[-1]["prod_tot"],
            "pop": rows[-1]["pop"],
            "blocked_rate": sum(row["mkt_blocked_rate"] for row in rows),
        }
        assert not simulation.book.consistency_errors(simulation.population.alive)
    reference = results["marginal"]
    candidate = results["surplus_share"]
    assert candidate["defaults"] <= max(5, 2 * reference["defaults"]), (reference, candidate)
    assert candidate["max_defaults"] <= max(5, 2 * reference["max_defaults"]), (reference, candidate)
    assert candidate["pop"] > 0
    print(
        f"  sur {window} pas : défauts {reference['defaults']} (marginal) → "
        f"{candidate['defaults']} (surplus), intérêts versés "
        f"{reference['interest']:.0f} → {candidate['interest']:.0f}, "
        f"{candidate['blocked_rate']} paires refusées faute de surplus  OK"
    )
    return results


def test_share_scales_the_rate_linearly():
    """p pilote bien le partage : r est proportionnel à p."""
    registry = TechRegistry()
    kernel = PrincipalKernel(registry)
    # Emprunteuse mieux dotée que la prêteuse : δ* > 0, donc la paire traite.
    # (Le couple inverse donne δ* < 0 — l'optimum jointe voudrait envoyer le
    # capital du pauvre vers le riche — et le marché refuse : c'est le canal
    # compté par `mkt_blocked_dir`, cf. test_institution.py.)
    tech_b = registry.intern(1.25, 0.6)
    tech_l = registry.intern(1.0, 0.5)
    kernel.sync_matrix()
    x, y = 400.0, 1200.0
    delta = kernel.solve(tech_b, tech_l, x, y)
    assert delta > 0.0, delta
    surplus = joint_production_gain(1.25, 0.6, 1.0, 0.5, x, y, delta)
    base = surplus_rate(delta, surplus, 1.0)
    assert base > 0.0
    for share in (0.1, 0.25, 0.5, 0.9):
        # (p·Δ)/q et p·(Δ/q) ne diffèrent que par l'associativité flottante
        assert abs(surplus_rate(delta, surplus, share) - share * base) < 1e-14 * base
    print(f"  partage p linéaire : r(p=1) = {base:.6f}, r(p) = p·r(1) exactement  OK")


def test_null_surplus_blocks_the_loan():
    """Δ ≤ 0 ⇒ pas de contrat : un taux nul serait rejeté par le carnet."""
    assert surplus_rate(10.0, 0.0, 0.5) == 0.0
    assert surplus_rate(10.0, -1.0, 0.5) == 0.0
    assert surplus_rate(0.0, 5.0, 0.5) == 0.0
    simulation = Simulation(Config(seed=2, lam=10.0, T=40, rate_rule="surplus_share"))
    simulation.run()
    errors = simulation.book.consistency_errors(simulation.population.alive)
    assert not errors, errors[:5]
    for _, _, principal, rate in simulation.book.loans.values():
        assert rate > 0.0 and principal > 0.0
    print("  Δ ≤ 0 ⇒ aucun contrat ; tous les contrats du carnet ont r > 0  OK")


def main():
    print("test_surplus_rate.py — chantier taux/p (prompt §3.4, §8)")
    test_rate_is_strictly_positive_and_below_the_marginal_rate()
    test_share_scales_the_rate_linearly()
    test_null_surplus_blocks_the_loan()
    test_surplus_rate_does_not_create_a_default_spike()
    print("test_surplus_rate.py : tout est passé.")


if __name__ == "__main__":
    main()
