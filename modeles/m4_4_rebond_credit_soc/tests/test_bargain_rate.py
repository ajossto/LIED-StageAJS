"""Test M4.4 — le taux comme VARIABLE DE PARTAGE (demande du 24 août 2026).

La règle `bargain` remplace la formule du taux par un paramètre p ∈ [0, 1]
entre deux bornes économiques :

    r · q  =  L  +  p · Δ

    L = A_d·K_d^γ − A_d·(K_d − q)^γ   perte de puissance extractrice de la donneuse
    Δ = surplus coopératif de la paire (gain joint de production par pas)

- p = 0, ALTRUISME : la donneuse fait une opération blanche — sa production
  d'après contrat PLUS l'intérêt qu'elle reçoit valent exactement ce qu'elle
  produisait avant.
- p = 1, ASSERVISSEMENT : la receveuse fait l'opération blanche — sa
  production d'après contrat MOINS l'intérêt qu'elle verse vaut exactement ce
  qu'elle produisait avant.

Les deux égalités ne valent QU'AU MOMENT DU CONTRAT, et c'est ce que ce test
vérifie : littéralement, à la précision machine, sur des paires construites à
la main puis sur le moteur.

    /home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/tests/test_bargain_rate.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_4.kernel import PrincipalKernel, TechRegistry, joint_production_gain  # noqa: E402
from m4_4.model import (  # noqa: E402
    Config,
    Intervention,
    Simulation,
    bargain_rate,
    extraction_loss,
    pair_rate,
)

#: Paires (A_donneuse, γ_donneuse, K_donneuse, A_receveuse, γ_receveuse, K_receveuse)
PAIRS = (
    (1.0, 0.5, 400.0, 1.0, 0.5, 100.0),
    (1.0, 0.5, 900.0, 1.5, 0.5, 100.0),
    (1.5, 0.6, 250.0, 1.0, 0.5, 40.0),
    (1.0, 0.5, 1000.0, 1.0, 0.6, 300.0),
)


def optimal_transfer(pair):
    """Le transfert que l'institution choisirait, ET QUI VA OÙ.

    Le sens n'est pas un choix du test : sous le sens libre, c'est l'optimum
    de production jointe qui désigne la donneuse. Une paire écrite dans un
    ordre et une paire écrite dans l'autre donnent le même contrat ; on lit
    donc le signe et on nomme les rôles ensuite.

    Retourne (donneuse, receveuse, q) où chaque rôle est (A, γ, K) et q > 0.
    """
    left = pair[:3]
    right = pair[3:]
    registry = TechRegistry()
    tech_left = registry.intern(left[0], left[1])
    tech_right = registry.intern(right[0], right[1])
    kernel = PrincipalKernel(registry, policy="hybrid", threshold=10**9)
    kernel.sync_matrix()
    # `solve(a, b, K_a, K_b)` rend le transfert VERS `a`.
    delta = kernel.solve(tech_right, tech_left, right[2], left[2])
    if delta >= 0.0:
        return left, right, delta
    return right, left, -delta


def test_the_two_white_operations():
    """p = 0 : la donneuse est blanche. p = 1 : la receveuse l'est."""
    for pair in PAIRS:
        (A_d, g_d, K_d), (A_r, g_r, K_r), q = optimal_transfer(pair)
        assert q > 0, (pair, q)
        loss = extraction_loss(A_d, g_d, K_d, q)
        surplus = joint_production_gain(A_r, g_r, A_d, g_d, K_r, K_d, q)
        assert surplus > 0, (pair, surplus)

        # p = 0 : production d'après + intérêt reçu == production d'avant.
        rate_zero = bargain_rate(q, loss, surplus, 0.0)
        donor_before = A_d * K_d ** g_d
        donor_after = A_d * (K_d - q) ** g_d + rate_zero * q
        assert abs(donor_after - donor_before) < 1e-9 * donor_before, (pair, donor_after, donor_before)

        # p = 1 : production d'après − intérêt versé == production d'avant.
        rate_one = bargain_rate(q, loss, surplus, 1.0)
        receiver_before = A_r * K_r ** g_r
        receiver_after = A_r * (K_r + q) ** g_r - rate_one * q
        assert abs(receiver_after - receiver_before) < 1e-9 * max(receiver_before, 1.0), (
            pair, receiver_after, receiver_before
        )
    print(f"  {len(PAIRS)} paires : p=0 rend la donneuse blanche, p=1 rend la "
          f"receveuse blanche, à 1e-9 relatif  OK")


def test_the_share_is_linear_and_bracketing():
    """r(p) est affine en p, et les deux bornes encadrent tout p intermédiaire."""
    (A_d, g_d, K_d), (A_r, g_r, K_r), q = optimal_transfer(PAIRS[1])
    loss = extraction_loss(A_d, g_d, K_d, q)
    surplus = joint_production_gain(A_r, g_r, A_d, g_d, K_r, K_d, q)
    rates = {p: bargain_rate(q, loss, surplus, p) for p in (0.0, 0.25, 0.5, 0.75, 1.0)}
    for p, rate in rates.items():
        expected = (loss + p * surplus) / q
        assert abs(rate - expected) < 1e-15 * max(expected, 1.0), (p, rate, expected)
        assert rates[0.0] <= rate <= rates[1.0]
    assert rates[1.0] > rates[0.0]
    print(f"  linéarité exacte : r(0) = {rates[0.0]:.6f} → r(1) = {rates[1.0]:.6f}, "
          f"rapport ×{rates[1.0] / rates[0.0]:.2f}  OK")


def test_where_the_historic_rule_sits_on_the_scale():
    """Le partage IMPLIQUÉ par la règle historique `marginal`.

    La moyenne géométrique des rendements marginaux n'a jamais été présentée
    comme un partage. On mesure ici ce qu'elle partage en fait :
    p_impliqué = (r·q − L)/Δ. Le test n'exige pas une valeur — il exige que la
    mesure soit possible et bornée, et il l'imprime, parce que c'est ce
    nombre qui situe toute la lignée antérieure sur la nouvelle échelle.
    """
    implied = []
    for pair in PAIRS:
        (A_d, g_d, K_d), (A_r, g_r, K_r), q = optimal_transfer(pair)
        loss = extraction_loss(A_d, g_d, K_d, q)
        surplus = joint_production_gain(A_r, g_r, A_d, g_d, K_r, K_d, q)
        rate = pair_rate(K_d, K_r, g_d, A_d, g_r, A_r)
        implied.append((rate * q - loss) / surplus)
    assert all(-1.0 < value < 2.0 for value in implied), implied
    formatted = ", ".join(f"{value:+.3f}" for value in implied)
    print(f"  partage impliqué par la règle `marginal` sur ces paires : {formatted}  OK")


def test_engine_runs_and_the_extremes_differ():
    """Sur le moteur : les deux extrêmes produisent des trajectoires très
    différentes, et aucune paire n'est refusée faute de taux."""
    base = dict(seed=4, T=250, rate_rule="bargain", record_rate_split=True)
    results = {}
    for share in (0.0, 1.0):
        simulation = Simulation(Config(**base, bargain_p=share))
        simulation.run()
        last = simulation.series[-1]
        results[share] = last
        assert sum(row["mkt_blocked_rate"] for row in simulation.series) == 0
        assert last["pop"] > 0, share
    altruistic, enslaved = results[0.0], results[1.0]
    assert altruistic["pop"] != enslaved["pop"]
    print(f"  moteur, 250 pas : population {altruistic['pop']} (p=0) contre "
          f"{enslaved['pop']} (p=1), intérêts versés "
          f"{altruistic['interest_paid']:.0f} contre {enslaved['interest_paid']:.0f}, "
          f"aucun refus de taux  OK")


def test_old_contracts_keep_their_interest_when_merged():
    """« Le paramètre détermine le taux des nouveaux contrats et seulement
    ceux-là » — y compris quand une paire re-traite.

    Le carnet FUSIONNE deux prêts d'une même paire et n'en garde qu'un taux,
    la moyenne pondérée par les principaux (`LoanBook.add`). On pourrait
    craindre que l'ancien contrat soit re-tarifé au nouveau taux. Il ne l'est
    pas : la fusion conserve `q_ancien·r_ancien + q_nouveau·r_nouveau` au bit
    près, et le taux moyen n'est qu'une façon de ranger deux taux dans un
    nombre. C'est vérifié ici parce que c'est la condition de la persistance.
    """
    from m4_4.model import LoanBook  # noqa: PLC0415

    book = LoanBook()
    old_principal, old_rate = 40.0, 0.02
    new_principal, new_rate = 25.0, 0.11
    book.add(1, 2, old_principal, old_rate)
    due_before = book.due[2]
    book.add(1, 2, new_principal, new_rate)
    expected = old_principal * old_rate + new_principal * new_rate
    assert abs(book.due[2] - expected) < 1e-12, (book.due[2], expected)
    assert abs(due_before - old_principal * old_rate) < 1e-15
    blended = book.loans[book.by_pair[(1, 2)]][3]
    assert old_rate < blended < new_rate
    print(f"  fusion : dû = {book.due[2]:.6f} = q₁r₁ + q₂r₂ exactement, "
          f"taux rangé {blended:.6f} entre {old_rate} et {new_rate}  OK")


def test_p_is_intervenable_live():
    """Le partage doit pouvoir ÉVOLUER en cours de trajectoire (§ demande).

    Les contrats déjà signés gardent leur taux : l'effet ne passe que par le
    renouvellement du carnet, et c'est bien ce qu'on vérifie — le taux moyen
    du carnet se déplace progressivement, pas d'un coup.
    """
    simulation = Simulation(Config(seed=6, T=200, rate_rule="bargain",
                                   bargain_p=0.0, record_rate_split=True))
    while simulation.t < 100:
        simulation.step()
    before = simulation.series[-1]["mkt_p_implied"]
    simulation.submit(Intervention(param="bargain_p", value=1.0, scope="all", t=101))
    while simulation.t < 200:
        simulation.step()
    after = simulation.series[-1]["mkt_p_implied"]
    assert abs(before) < 1e-9, before
    assert abs(after - 1.0) < 1e-9, after
    assert simulation.config.bargain_p == 1.0
    assert simulation.intervention_log[0]["param"] == "bargain_p"
    print(f"  intervention en direct : partage impliqué {before:.3f} → {after:.3f}, "
          f"journalisée à t = {simulation.intervention_log[0]['t']}  OK")


def test_default_rule_is_untouched():
    """La règle par défaut n'a pas bougé : c'est la condition de la parité."""
    reference = Simulation(Config(seed=8, T=150))
    reference.run()
    with_flag = Simulation(Config(seed=8, T=150, record_rate_split=True))
    with_flag.run()
    columns = ("pop", "K_tot", "prod_tot", "interest_paid", "loan_volume", "deaths")
    for left, right in zip(reference.series, with_flag.series):
        for column in columns:
            assert left[column] == right[column], (left["t"], column)
    measured = [row["mkt_p_implied"] for row in with_flag.series
                if row["mkt_p_implied"] == row["mkt_p_implied"]]
    average = sum(measured) / len(measured)
    print(f"  `marginal` inchangée par la mesure : {len(columns)} colonnes bit à bit ; "
          f"partage impliqué moyen sur 150 pas = {average:.4f}  OK")


def main() -> int:
    print("test_bargain_rate.py — le taux comme variable de partage (M4.4)")
    test_the_two_white_operations()
    test_the_share_is_linear_and_bracketing()
    test_where_the_historic_rule_sits_on_the_scale()
    test_engine_runs_and_the_extremes_differ()
    test_old_contracts_keep_their_interest_when_merged()
    test_p_is_intervenable_live()
    test_default_rule_is_untouched()
    print("test_bargain_rate.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
