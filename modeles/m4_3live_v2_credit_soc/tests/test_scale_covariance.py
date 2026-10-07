"""Test §9 — covariance d'échelle du modèle, en non-régression (§6, §12.5).

ÉNONCÉ. Le modèle est covariant d'échelle en capital : si l'on remplace le
coefficient de production `A` par `A'` et le capital de naissance `K0` par
`c·K0` avec

    c = (A'/A)^{1/(1−γ)},

on obtient la MÊME simulation à l'échelle `c` près. Chaque phase du pas est
homogène de degré 1 en capital (production : A(cK)^γ = c·A K^γ dès que
A' c^γ = c A ; intérêts, dépréciation, transferts : linéaires), et le taux
marginal γA K^{γ−1} est SANS DIMENSION — il est invariant. La population, le
nombre de prêts et les morts sont donc rigoureusement identiques, pas
seulement proches, et tous les capitaux sont multipliés par c.

POURQUOI CE TEST-CI ET PAS LE RECALAGE TEMPOREL. v2 a deux groupes de
covariance (§6). Celui-ci est EXACT à la précision machine, il fait donc un
test de non-régression légitime. Le recalage de pas de temps, lui, laisse un
résidu mesuré de 6 à 17 % dont la source est la phase de marché — qui ne se
compose pas. Un seuil de non-régression y serait arbitraire : il reste une
vérification rapportée dans le rapport, pas un test. C'est la réponse à la
question ouverte §12.5 du prompt v2.

CE QUI EMPÊCHE L'EXACTITUDE ABSOLUE. Deux constantes du moteur sont
dimensionnées en capital et ne sont PAS rééchelonnées : `MIN_LOAN` (1e-9,
plancher de transfert) et `ZERO_TOL` (1e-12, seuil d'annulation du capital
après dépréciation). Elles sont conservées telles quelles — les rééchelonner
rendrait l'invariance exacte mais casserait la comparabilité avec toutes les
campagnes antérieures (question ouverte §12.4, tranchée par la négative). Au
régime observé (K ≈ 800), elles sont à 12 ordres de grandeur du capital
typique et n'ont jamais mordu.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_scale_covariance.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.model import Config, Simulation  # noqa: E402

STEPS = 600
BASE = dict(seed=0, lam=30.0, delta=0.01, sigma=0.01, K0=25.0, A=1.0)

#: Colonnes rigoureusement invariantes (comptages) et colonnes qui doivent
#: être multipliées par c (extensives en capital).
INVARIANT = ("births", "deaths", "pop", "n_loans", "new_loans", "defaults",
             "mkt_pool", "mkt_rounds", "mkt_new_edges", "mkt_merges",
             "mkt_blocked_dir", "mkt_reversed")
#: `n_creditors` est DÉLIBÉRÉMENT exclu des invariants. Il compte les entités
#: dont la position nette `créances − dettes` est strictement positive : c'est
#: un SEUIL sur une différence de deux flottants du même ordre de grandeur.
#: Une entité dont la position nette est à 1e-13 du capital typique bascule
#: d'un côté ou de l'autre selon l'arrondi, et le rééchelonnement change les
#: arrondis. L'écart mesuré est d'une unité sur ~450, soit 0,2 %, et il ne
#: dit rien sur la covariance — seulement sur l'ambiguïté du seuil.
AMBIGUOUS = ("n_creditors",)
EXTENSIVE = ("K_tot", "nw_tot", "prod_tot", "loan_volume", "interest_paid",
             "injected", "depreciated", "destroyed", "claim_losses",
             "mkt_volume_rev")


def _run(gamma: float, coefficient: float, K0: float) -> list[dict]:
    config = Config(**{**BASE, "A": coefficient, "K0": K0}, gamma=gamma, T=STEPS)
    simulation = Simulation(config)
    simulation.run()
    assert simulation.status == "ok", simulation.status
    return simulation.series


def test_covariance(gamma: float, ratio: float) -> None:
    scale = ratio ** (1.0 / (1.0 - gamma))
    reference = _run(gamma, BASE["A"], BASE["K0"])
    scaled = _run(gamma, BASE["A"] * ratio, BASE["K0"] * scale)
    assert len(reference) == len(scaled) == STEPS

    for index, (left, right) in enumerate(zip(reference, scaled)):
        for column in INVARIANT:
            assert left[column] == right[column], (
                f"γ={gamma} : colonne invariante {column} différente à t={index + 1} : "
                f"{left[column]!r} vs {right[column]!r}"
            )
    ambiguous = max(
        abs(left[column] - right[column])
        for left, right in zip(reference, scaled)
        for column in AMBIGUOUS
    )
    worst, worst_column, worst_t = 0.0, "", 0
    for index, (left, right) in enumerate(zip(reference, scaled)):
        for column in EXTENSIVE:
            expected = left[column] * scale
            if abs(expected) < 1e-9:
                continue
            gap = abs(right[column] - expected) / abs(expected)
            if gap > worst:
                worst, worst_column, worst_t = gap, column, index + 1
    assert worst < 1e-11, (worst, worst_column, worst_t)
    print(
        f"  γ = {gamma} : A×{ratio} et K0×{scale:.6g} sur {STEPS} pas — population, "
        f"prêts et morts RIGOUREUSEMENT identiques ; écart relatif maximal sur les "
        f"grandeurs extensives {worst:.2e} (colonne {worst_column}, t={worst_t}) ; "
        f"écart maximal sur le comptage à seuil `n_creditors` : {ambiguous:.0f} entité(s)  OK"
    )


def test_marginal_rate_is_dimensionless() -> None:
    """Le taux marginal γA K^{γ−1} ne bouge pas sous la transformation."""
    gamma, ratio = 0.5, 1.5
    scale = ratio ** (1.0 / (1.0 - gamma))
    capital = 800.0
    before = gamma * BASE["A"] * capital ** (gamma - 1.0)
    after = gamma * (BASE["A"] * ratio) * (capital * scale) ** (gamma - 1.0)
    assert abs(after / before - 1.0) < 1e-14, (before, after)
    print(
        f"  taux marginal : {before:.12g} avant, {after:.12g} après — invariant "
        f"(écart relatif {abs(after / before - 1):.1e})  OK"
    )


def main() -> int:
    print("test_scale_covariance.py — covariance d'échelle (prompt v2 §6, §9, §12.5)")
    test_marginal_rate_is_dimensionless()
    test_covariance(0.5, 1.5)
    test_covariance(0.4, 2.0)
    print("test_scale_covariance.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
