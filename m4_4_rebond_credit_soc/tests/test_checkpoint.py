"""Test M4.4 §7 — le checkpoint de fin de run (plan §4.3, dette héritée de M4.2B).

M4.2B a inscrit une décision d'ingénierie « pour tous les modèles
postérieurs » : sauvegarder le `Simulation` complet à la fin de chaque run.
v2 ne le faisait que pour ses amorçages ; aucun bras ne laissait de
checkpoint, et étendre une cellule sévère demandait de tout rejouer.

Deux exigences, et une nuance qu'il faut mesurer plutôt que promettre :

1. LA TRAJECTOIRE. Un run coupé en deux par un checkpoint doit reproduire
   le run mené d'un trait. \\fait{} La reproduction n'est PAS bit à bit sur
   `interest_paid` : le carnet range ses prêts dans des `set`, dont l'ordre
   d'itération change après un aller-retour `pickle` (mesuré et documenté
   par `tests/test_replay.py:57-65`, qui tolère la même colonne). Ce test
   MESURE l'écart au lieu de le supposer, et exige l'identité stricte
   partout ailleurs.

2. L'INSTRUMENTATION. C'est ce que le §4.3 ajoute : un checkpoint qui
   emporterait la trajectoire mais perdrait les décès, les arêtes de perte
   et les panneaux passerait le point 1 sans qu'on le voie.

    /home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/tests/test_checkpoint.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_4.live import load_snapshot, save_snapshot  # noqa: E402
from m4_4.model import Config, Simulation  # noqa: E402

BASE = dict(
    lam=30.0, sigma=0.01, delta=0.01, K0=25.0, A=1.0, gamma=0.5,
    record_deaths=True, record_avalanches=True, record_loss_edges=True,
    panel_every=20,
)
HALF = 120
FULL = 240

#: Colonnes dont la valeur est un ENTIER de comptage : aucune tolérance
#: n'y a de sens, un écart d'un demi ne peut pas exister.
INTEGER_COLUMNS = (
    "births", "deaths", "pop", "n_loans", "new_loans", "defaults",
    "roots_insolvency", "roots_liquidity", "roots_both", "cascade_iters",
    "n_avalanches", "max_avalanche", "n_creditors", "book_keys",
)
#: Colonnes flottantes. Plusieurs sont des SOMMES accumulées en parcourant
#: un `set` du carnet — `interest_paid` prêt par prêt, `claim_losses` créance
#: par créance. L'ordre de ces parcours change après un aller-retour
#: `pickle`, donc l'ordre d'addition change, donc les derniers bits changent.
#: Ce test ne devine pas lesquelles : il les MESURE toutes et exige que
#: l'écart reste au niveau de l'arrondi.
FLOAT_COLUMNS = (
    "K_tot", "nw_tot", "prod_tot", "loan_volume", "claim_losses",
    "destroyed", "injected", "depreciated", "shock_gain", "interest_paid",
)
#: Plafond de l'écart relatif toléré sur une colonne flottante. 1e-12, soit
#: ≈ 4500 fois l'epsilon machine : assez lâche pour un ordre de sommation,
#: bien trop serré pour une divergence de trajectoire — laquelle se voit de
#: toute façon sur les colonnes ENTIÈRES, qu'aucun arrondi ne peut bouger.
FLOAT_TOLERANCE = 1e-12


def relative_gap(value: float, expected: float) -> float:
    return abs(value - expected) / max(1.0, abs(expected))


def test_checkpoint_reproduces_the_trajectory():
    straight = Simulation(Config(**BASE, seed=11, T=FULL))
    straight.run()

    cut = Simulation(Config(**BASE, seed=11, T=HALF))
    cut.run()
    with tempfile.TemporaryDirectory() as directory:
        path = save_snapshot(cut, os.path.join(directory, "snapshot_final.pkl"))
        resumed = load_snapshot(path, config=Config(**BASE, seed=11, T=FULL))
        size = os.path.getsize(path)
    resumed.run()

    assert len(resumed.series) == len(straight.series) == FULL
    worst: dict[str, float] = {}
    for left, right in zip(straight.series, resumed.series):
        assert left["t"] == right["t"]
        for column in INTEGER_COLUMNS:
            assert left[column] == right[column], (left["t"], column, left[column], right[column])
        for column in FLOAT_COLUMNS:
            gap = relative_gap(right[column], left[column])
            if gap > worst.get(column, 0.0):
                worst[column] = gap
    moved = {column: gap for column, gap in worst.items() if gap > 0.0}
    for column, gap in moved.items():
        assert gap < FLOAT_TOLERANCE, (column, gap)
    exact = [column for column in FLOAT_COLUMNS if column not in moved]
    print(
        f"  {FULL} pas coupés à t={HALF} : les {len(INTEGER_COLUMNS)} colonnes entières et "
        f"{len(exact)} des {len(FLOAT_COLUMNS)} colonnes flottantes sont bit à bit  OK"
    )
    print(
        "  colonnes déplacées par l'ordre des `set` : "
        + ", ".join(f"{column} {gap:.1e}" for column, gap in sorted(moved.items()))
        + "  OK"
    )
    print(f"  checkpoint : {size / 1024 / 1024:.2f} Mio pour une population de "
          f"{straight.series[-1]['pop']} entités  OK")
    return straight, resumed


def test_checkpoint_carries_the_instrumentation(straight: Simulation, resumed: Simulation):
    """§4.3 : ce qui a été mesuré avant le checkpoint est encore là après."""
    assert len(resumed.deaths) == len(straight.deaths), (
        len(resumed.deaths), len(straight.deaths)
    )
    assert len(resumed.avalanches) == len(straight.avalanches)
    assert len(resumed.loss_edges) == len(straight.loss_edges)
    assert [panel["t"] for panel in resumed.panels] == [
        panel["t"] for panel in straight.panels
    ], "les panneaux d'avant le checkpoint ont disparu"
    # Les panneaux d'AVANT la coupure doivent être identiques champ par
    # champ : ils ont été mesurés avant l'aller-retour, donc rien ne peut
    # les avoir bougés.
    for left, right in zip(straight.panels, resumed.panels):
        if left["t"] > HALF:
            continue
        for field, values in left.items():
            if field == "t":
                continue
            assert (values == right[field]).all(), (left["t"], field)
    before = sum(1 for panel in straight.panels if panel["t"] <= HALF)
    print(
        f"  instrumentation reprise : {len(resumed.deaths)} décès, "
        f"{len(resumed.avalanches)} avalanches, {len(resumed.loss_edges)} arêtes de perte, "
        f"{len(resumed.panels)} panneaux dont {before} d'avant la coupure, identiques  OK"
    )


def test_v2_snapshots_stay_readable():
    """Un snapshot écrit SANS les champs M4.4 doit rester lisible : les
    amorçages de v2 existent sur disque et rien ne justifie de les rejouer."""
    simulation = Simulation(Config(**BASE, seed=12, T=30))
    simulation.run()
    with tempfile.TemporaryDirectory() as directory:
        path = save_snapshot(simulation, os.path.join(directory, "vieux.pkl"))
        import pickle  # noqa: PLC0415

        with open(path, "rb") as handle:
            payload = pickle.load(handle)
        for key in ("loss_edges", "panels", "loan_events", "market_stats", "amplitude_log"):
            payload.pop(key)
        with open(path, "wb") as handle:
            pickle.dump(payload, handle)
        restored = load_snapshot(path)
    assert restored.t == 30 and restored.loss_edges == [] and restored.panels == []
    print("  snapshot au format v2 (sans les champs M4.4) relu sans erreur  OK")


def main() -> int:
    print("test_checkpoint.py — checkpoint de fin de run (plan §4.3, §7)")
    straight, resumed = test_checkpoint_reproduces_the_trajectory()
    test_checkpoint_carries_the_instrumentation(straight, resumed)
    test_v2_snapshots_stay_readable()
    print("test_checkpoint.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
