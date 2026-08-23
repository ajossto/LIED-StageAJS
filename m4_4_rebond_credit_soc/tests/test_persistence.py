"""Test M4.4 §4.1 — ce qui est mesuré est ÉCRIT.

Le manque bloquant du plan : v2 mesurait `deaths`, `avalanches`,
`avalanche_members` et `loan_events` en mémoire quand les drapeaux étaient
armés, et `write_series` ne les écrivait jamais. Aucune campagne v2 n'armait
d'ailleurs ces drapeaux — d'où l'absence totale de données d'avalanche dans
les 153 runs de la lignée, alors que le moteur savait les produire.

Ce test arme tous les drapeaux, écrit un run, et vérifie fichier par fichier
que le nombre de lignes sur disque vaut le nombre d'enregistrements en
mémoire. Il vérifie aussi le chemin qui compte vraiment : que les fichiers
relus se réconcilient (`scripts/branching.py` sur `series.csv` +
`loss_edges.csv`), parce qu'un fichier présent mais incohérent avec la série
serait pire qu'un fichier absent.

    /home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/tests/test_persistence.py
"""

from __future__ import annotations

import csv
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from m4_4.live import EDGE_COLUMNS, EVENT_TABLES, read_edges, write_series  # noqa: E402
from m4_4.model import Config, Simulation  # noqa: E402

import branching  # noqa: E402

ARMED = dict(
    record_deaths=True,
    record_avalanches=True,
    record_loss_edges=True,
    record_loan_events=True,
    record_market_stats=True,
    panel_every=10,
)


def rows_of(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_every_armed_record_lands_on_disk():
    simulation = Simulation(Config(seed=7, T=150, **ARMED))
    simulation.run()
    with tempfile.TemporaryDirectory() as directory:
        write_series(simulation, directory)
        directory = Path(directory)
        written = sorted(path.name for path in directory.iterdir())
        counts = {}
        for attribute, filename in EVENT_TABLES:
            expected = len(getattr(simulation, attribute))
            assert expected > 0, f"{attribute} vide : le test ne prouverait rien"
            path = directory / filename
            assert path.exists(), f"{filename} n'a pas été écrit"
            found = len(rows_of(path))
            assert found == expected, (filename, found, expected)
            counts[filename] = found
        assert (directory / "panels.npz").exists()

        # L'arbre causal va en colonnes compressées, pas en CSV (le CSV
        # pesait 53,9 Mio par run de campagne — voir le JOURNAL du lot A).
        edges = read_edges(directory / "loss_edges.npz")
        assert set(edges) == set(EDGE_COLUMNS), sorted(edges)
        assert len(edges["t"]) == len(simulation.loss_edges)
        for index in (0, len(simulation.loss_edges) // 2, -1):
            row = simulation.loss_edges[index]
            for name in EDGE_COLUMNS:
                assert edges[name][index] == row[name], (index, name)
        counts["loss_edges.npz"] = len(edges["t"])

        # Le contrôle qui compte : l'arbre causal relu depuis le CSV ferme
        # sur la série relue depuis le CSV.
        payload = branching.measure(directory, None, None)
    assert payload["closes"], payload
    assert payload["n_pairs"] >= payload["expected_non_roots"], payload
    print("  fichiers écrits : " + ", ".join(written) + "  OK")
    print(
        "  lignes sur disque = lignes en mémoire pour "
        + ", ".join(f"{name} ({count})" for name, count in counts.items())
        + "  OK"
    )
    print(
        f"  relecture : b₁ = {payload['b1']:.4f}, b₂ = {payload['b2']:.4f} sur "
        f"{payload['deaths']:.0f} morts — l'arbre ferme sur la série  OK"
    )


def test_nothing_is_written_when_nothing_is_armed():
    """Le défaut reste le défaut : un run non instrumenté produit exactement
    les cinq fichiers de v2, ni plus ni moins. C'est ce qui garantit qu'une
    comparaison avec un run v2 porte sur les mêmes fichiers."""
    simulation = Simulation(Config(seed=7, T=50))
    simulation.run()
    with tempfile.TemporaryDirectory() as directory:
        write_series(simulation, directory)
        written = sorted(path.name for path in Path(directory).iterdir())
    assert written == ["kernel.json", "series.csv", "tech_series.csv",
                       "tension.csv", "tension_agg.csv"], written
    print("  sans drapeau : " + ", ".join(written) + " — rien de plus  OK")


def main() -> int:
    print("test_persistence.py — les mesures atteignent le disque (plan §4.1)")
    test_every_armed_record_lands_on_disk()
    test_nothing_is_written_when_nothing_is_armed()
    print("test_persistence.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
