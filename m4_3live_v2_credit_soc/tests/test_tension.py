"""Test §9 — la tension est une colonne native et EXACTE (§4.1 du prompt v2).

En v1, l'effectif producteur était reconstitué a posteriori (`n_alive +
deaths`), donc approché dès que plusieurs technologies vivaient ensemble. En
v2 il est enregistré à l'instant de la production. Ce test vérifie sur des
états SYNTHÉTIQUES, dont on connaît la réponse en forme fermée, que :

1. `K_aut` vaut littéralement [A(1−δ)/δ]^{1/(1−γ)} ;
2. `K_eq` vaut littéralement (prod/(n_prod·A))^{1/γ} ;
3. sur une population dont toutes les entités ont le MÊME capital, K_eq = ce
   capital et l'écart de Jensen vaut exactement 1 ;
4. l'effectif producteur enregistré est bien celui d'AVANT les morts du pas,
   et non celui de fin de pas — c'est précisément l'erreur que v1 ne pouvait
   pas éviter ;
5. l'agrégat multi-technologies est la moyenne pondérée par la production.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_tension.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.model import Config, Simulation  # noqa: E402
from m4_3live_v2.tension import (  # noqa: E402
    aggregate_rows,
    autarkic_scale,
    equivalent_capital,
    tension_row,
)


def test_closed_forms():
    """Les deux échelles, contre leur définition écrite à la main."""
    A, gamma, delta = 1.0, 0.5, 0.01
    expected = (A * (1.0 - delta) / delta) ** (1.0 / (1.0 - gamma))
    assert autarkic_scale(A, gamma, delta) == expected
    # (99)² = 9801 : l'échelle autarcique du régime de référence.
    assert abs(expected - 9801.0) < 1e-9, expected

    n, capital = 40, 625.0
    prod = n * A * capital**gamma
    assert abs(equivalent_capital(prod, n, A, gamma) - capital) < 1e-9

    # δ = 0 : pas de point fixe fini, la fonction doit rendre NaN et non lever.
    value = autarkic_scale(A, gamma, 0.0)
    assert value != value, value
    print(
        f"  formes fermées : K_aut(A=1, γ=0,5, δ=0,01) = {expected:.1f} = 99², "
        f"K_eq inversé exactement sur {n} entités à K = {capital:.0f}  OK"
    )


def test_row_on_equal_capitals():
    """Capitaux égaux ⇒ K_eq = K_moyen, donc Jensen = 1 exactement."""
    A, gamma, delta = 1.5, 0.6, 0.02
    n, capital = 250, 1234.5
    prod = n * A * capital**gamma
    row = tension_row(
        t=7, tech=0, A=A, gamma=gamma, delta=delta,
        n_alive=n, n_prod=n, capital=n * capital, capital_prod=n * capital, prod=prod,
    )
    assert abs(row["K_eq"] - capital) < 1e-9, row["K_eq"]
    assert abs(row["K_mean"] - capital) < 1e-12, row["K_mean"]
    assert abs(row["jensen"] - 1.0) < 1e-12, row["jensen"]
    assert abs(row["tension"] - autarkic_scale(A, gamma, delta) / capital) < 1e-9
    print(f"  capitaux égaux : Jensen = {row['jensen']:.15f} (exactement 1)  OK")


def test_jensen_below_one_when_unequal():
    """K^γ concave ⇒ K_eq < K_moyen dès que les capitaux diffèrent."""
    A, gamma = 1.0, 0.5
    capitals = [100.0, 400.0, 900.0]
    prod = sum(A * k**gamma for k in capitals)
    row = tension_row(
        t=1, tech=0, A=A, gamma=gamma, delta=0.01,
        n_alive=3, n_prod=3, capital=sum(capitals),
        capital_prod=sum(capitals), prod=prod,
    )
    assert row["jensen"] < 1.0, row["jensen"]
    # (10+20+30)/3 = 20 ⇒ K_eq = 400 ; moyenne des capitaux = 1400/3 ≈ 466,7.
    assert abs(row["K_eq"] - 400.0) < 1e-9, row["K_eq"]
    print(
        f"  capitaux inégaux : K_eq = {row['K_eq']:.1f} < K_moyen = "
        f"{row['K_mean']:.1f}, Jensen = {row['jensen']:.4f} < 1  OK"
    )


def test_engine_records_the_producing_headcount():
    """`n_prod` est l'effectif d'AVANT les morts, `n_alive` celui d'après."""
    config = Config(seed=3, T=400, lam=30.0, sigma=0.01, delta=0.01, K0=25.0)
    simulation = Simulation(config)
    simulation.run()
    rows = {row["t"]: row for row in simulation.tension_series}
    series = {row["t"]: row for row in simulation.series}
    checked = 0
    for step, row in rows.items():
        # une seule technologie : n_prod doit valoir n_alive + morts du pas
        assert row["n_prod"] == row["n_alive"] + series[step]["deaths"], (
            step, row["n_prod"], row["n_alive"], series[step]["deaths"]
        )
        # et K_eq doit être exactement l'inversion de la production du pas
        expected = equivalent_capital(row["prod"], row["n_prod"], row["A"], row["gamma"])
        assert abs(row["K_eq"] - expected) <= 1e-12 * expected, (step, row["K_eq"], expected)
        checked += 1
    deaths = sum(series[step]["deaths"] for step in rows)
    assert deaths > 0, "aucune mort : le test ne prouverait rien"
    print(
        f"  moteur : sur {checked} pas, n_prod = n_alive + morts ({deaths} morts au "
        "total), et K_eq inverse exactement la production du pas  OK"
    )


def test_aggregate_is_production_weighted():
    A1, A2, gamma, delta = 1.0, 4.0, 0.5, 0.01
    rows = [
        tension_row(1, 0, A1, gamma, delta, 10, 10, 1000.0, 1000.0, 10 * A1 * 100.0**gamma),
        tension_row(1, 1, A2, gamma, delta, 5, 5, 2000.0, 2000.0, 5 * A2 * 400.0**gamma),
    ]
    aggregate = aggregate_rows(rows)[0]
    weight = sum(row["prod"] for row in rows)
    expected = sum(row["prod"] * row["tension"] for row in rows) / weight
    assert abs(aggregate["tension"] - expected) < 1e-12
    assert aggregate["pop"] == 15 and aggregate["n_prod"] == 15
    assert abs(aggregate["K_tot"] - 3000.0) < 1e-9
    print(
        f"  agrégat : tension pondérée par la production = {aggregate['tension']:.6f} "
        f"sur deux technologies (T = {rows[0]['tension']:.3f} et {rows[1]['tension']:.3f})  OK"
    )


def main() -> int:
    print("test_tension.py — tension native et exacte (prompt v2 §4.1, §9)")
    test_closed_forms()
    test_row_on_equal_capitals()
    test_jensen_below_one_when_unequal()
    test_engine_records_the_producing_headcount()
    test_aggregate_is_production_weighted()
    print("test_tension.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
