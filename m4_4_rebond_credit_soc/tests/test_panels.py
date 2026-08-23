"""Test M4.4 §7 — les panneaux par entité se referment sur les agrégats.

C'est la SECONDE porte du lot A. La parité bit à bit ne la couvre pas : un
panneau n'entre pas dans `step()`, donc un instantané pris au mauvais
instant du pas laisserait la trajectoire intacte et fausserait toutes les
distributions du programme.

CE QUI SE REFERME EXACTEMENT, ET CE QUI NE PEUT PAS
---------------------------------------------------
Le panneau est pris à la FIN du pas, sur `population.living()` — les entités
mortes pendant le pas n'y sont plus (`model.py`, `_fail_one` appelle
`population.kill`). Or `series.csv` mélange deux instants :

- `pop`, `K_tot`, `nw_tot` sont mesurés sur les MÊMES vivantes que le
  panneau, dans le MÊME ordre : égalité BIT À BIT exigée ici ;
- `prod_tot` et `interest_paid` sont des FLUX du pas, cumulés AVANT les
  faillites : ils contiennent la production et les intérêts des entités
  mortes pendant le pas. Le panneau seul ne peut pas les reproduire, et à
  ≈ 30 morts par pas l'écart est massif.

D'où la mesure conservée dans le moteur (plan §4.1) : `dead_info` enregistre
`prod`, `int_in` et `int_out` de chaque morte. Panneau + mortes referment
alors les flux — à l'ordre de sommation près, qui n'est pas le même : la
tolérance relative de 1e-12 porte sur cela seul, pas sur une approximation.

    /home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/tests/test_panels.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_4.live import PANEL_STORED, read_panels, write_panels  # noqa: E402
from m4_4.model import Config, Simulation  # noqa: E402

BASE = dict(lam=30.0, sigma=0.01, delta=0.01, K0=25.0, A=1.0, gamma=0.5)


def relative_gap(value: float, expected: float) -> float:
    scale = max(1.0, abs(expected))
    return abs(value - expected) / scale


def test_panels_close_on_aggregates():
    config = Config(**BASE, seed=1, T=200, panel_every=1, record_deaths=True)
    simulation = Simulation(config)
    simulation.run()
    assert len(simulation.panels) == 200, len(simulation.panels)

    series = {row["t"]: row for row in simulation.series}
    deaths_by_t: dict[int, list[dict]] = {}
    for death in simulation.deaths:
        deaths_by_t.setdefault(death["t"], []).append(death)

    worst_flow = 0.0
    total_deaths = 0
    naive_worst = 0.0
    for panel in simulation.panels:
        row = series[panel["t"]]
        dead = deaths_by_t.get(panel["t"], [])
        total_deaths += len(dead)

        # (i) stocks : même instant, même ordre, donc BIT À BIT.
        assert len(panel["id"]) == row["pop"], (panel["t"], len(panel["id"]), row["pop"])
        assert sum(panel["K"].tolist()) == row["K_tot"], panel["t"]
        assert sum(panel["nw"].tolist()) == row["nw_tot"], panel["t"]

        # (ii) flux : panneau + mortes du pas.
        produced = sum(panel["prod"].tolist()) + sum(death["prod"] for death in dead)
        received = sum(panel["int_in"].tolist()) + sum(death["int_in"] for death in dead)
        paid = sum(panel["int_out"].tolist()) + sum(death["int_out"] for death in dead)
        worst_flow = max(
            worst_flow,
            relative_gap(produced, row["prod_tot"]),
            relative_gap(received, row["interest_paid"]),
            relative_gap(paid, row["interest_paid"]),
        )
        # (iii) le panneau SEUL ne referme pas les flux dès qu'il y a des
        # morts — on le mesure au lieu de le supposer.
        if dead:
            naive_worst = max(
                naive_worst, relative_gap(sum(panel["prod"].tolist()), row["prod_tot"])
            )

    assert worst_flow < 1e-12, worst_flow
    assert naive_worst > 1e-6, naive_worst
    print(
        f"  200 panneaux : effectif, K_tot et nw_tot bit à bit ; flux refermés à "
        f"{worst_flow:.1e} près avec les {total_deaths} mortes  OK"
    )
    print(
        f"  sans les mortes, l'écart sur prod_tot monte à {naive_worst:.2%} : "
        f"le panneau seul ne mesure pas un flux de pas  OK"
    )


def test_panels_do_not_touch_the_trajectory():
    """Prendre un panneau ne consomme aucun tirage et ne change aucun nombre."""
    columns = ("pop", "K_tot", "nw_tot", "prod_tot", "interest_paid", "deaths",
               "n_loans", "loan_volume", "n_avalanches")
    reference = Simulation(Config(**BASE, seed=2, T=150))
    reference.run()
    sampled = Simulation(Config(**BASE, seed=2, T=150, panel_every=1))
    sampled.run()
    for left, right in zip(reference.series, sampled.series):
        for column in columns:
            assert left[column] == right[column], (left["t"], column)
    assert not reference.panels and len(sampled.panels) == 150
    print(f"  panneaux à chaque pas : 150 pas × {len(columns)} colonnes inchangées  OK")


def test_sampling_step_is_honoured():
    config = Config(**BASE, seed=2, T=150, panel_every=25)
    simulation = Simulation(config)
    simulation.run()
    times = [panel["t"] for panel in simulation.panels]
    assert times == [25, 50, 75, 100, 125, 150], times
    print(f"  pas d'échantillonnage k = 25 : instantanés {times}  OK")


def test_round_trip_on_disk():
    """Ce qui est relu est ce qui a été mesuré, et les trois champs dérivés
    sont reconstruits exactement (ils ne sont pas stockés : ce sont des
    fonctions exactes des autres, plan §4.2)."""
    config = Config(**BASE, seed=4, T=60, panel_every=20)
    simulation = Simulation(config)
    simulation.run()
    with tempfile.TemporaryDirectory() as directory:
        path = write_panels(simulation, directory)
        assert path is not None and os.path.exists(path), path
        size = os.path.getsize(path)
        loaded = read_panels(path)
    expected_rows = sum(len(panel["id"]) for panel in simulation.panels)
    assert len(loaded["t"]) == expected_rows, (len(loaded["t"]), expected_rows)
    offset = 0
    for panel in simulation.panels:
        count = len(panel["id"])
        window = slice(offset, offset + count)
        assert set(loaded["t"][window].tolist()) == {panel["t"]}
        for field in PANEL_STORED:
            assert (loaded[field][window] == panel[field]).all(), field
        for field in ("nw", "income", "income_net"):
            assert (loaded[field][window] == panel[field]).all(), field
        offset += count
    print(
        f"  aller-retour disque : {expected_rows} lignes × "
        f"{len(PANEL_STORED)} champs stockés (+3 dérivés), {size / 1024:.0f} Kio  OK"
    )


def main() -> int:
    print("test_panels.py — fermeture des panneaux par entité (plan §4.2, §7)")
    test_panels_close_on_aggregates()
    test_panels_do_not_touch_the_trajectory()
    test_sampling_step_is_honoured()
    test_round_trip_on_disk()
    print("test_panels.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
