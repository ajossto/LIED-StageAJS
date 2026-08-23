"""Test M4.4 §7 — les DEUX estimateurs du rapport de branchement.

Exigence du plan (§7, « Branchement ») : « sur une cascade construite à la
main dont on connaît l'arbre, les deux estimateurs rendent la valeur
attendue, et leur écart est celui qu'on calcule à la main ».

Deux parties :

(a) LA CASCADE À LA MAIN. Un arbre écrit en dur, dont b₁, b₂ et l'écart sont
    calculés au crayon dans le corps du test. C'est le seul endroit du
    programme où la valeur attendue ne vient pas du moteur.

(b) LE MOTEUR. Sur un run court, on vérifie l'énoncé structurel dont dépend
    tout le §3.2 du plan — « génération 1 ⟺ racine » — et la fermeture de
    l'arbre causal sur la série : le nombre de victimes mortelles vues dans
    `loss_edges` doit valoir `morts − racines` lu sur `series.csv`.

    /home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/tests/test_branching.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_4.live import read_edges, write_edges  # noqa: E402
from m4_4.cascades import (  # noqa: E402
    branching_from_counts,
    branching_from_edges,
    branching_from_series,
    reconcile,
)
from m4_4.model import Config, Simulation  # noqa: E402


def approx(value: float, expected: float, tol: float = 1e-12) -> bool:
    return abs(value - expected) <= tol


def test_hand_built_cascade():
    """Un pas, une cascade, un arbre connu.

        génération 1 (racines) : 1, 2
        génération 2           : 3, tué par 1 ET par 2 (sur-détermination)
        génération 3           : 5, tué par 3
        survivante             : 4, qui perd une créance sur 1 sans mourir

    Morts N = 4 (1, 2, 3, 5) ; racines R = 2.
        b₁ = 1 − 2/4 = 0,5
    Couples parent→enfant : (1→3), (2→3), (3→5) = 3.
        b₂ = 3/4 = 0,75
    Écart = 0,25, et il vient ENTIÈREMENT de la double parenté de 3 :
    l'entité 3 a deux parents, donc un couple de plus que le compte des
    morts non racines (N − R = 2).
    """
    series = [
        {"t": 7, "deaths": 4, "roots_insolvency": 2, "roots_liquidity": 0, "roots_both": 0}
    ]
    edges = [
        # (source, victime, gen_source, gen_victim) ; principal sans effet ici
        {"t": 7, "source": 1, "victim": 3, "principal": 10.0, "gen_source": 1, "gen_victim": 2},
        {"t": 7, "source": 2, "victim": 3, "principal": 20.0, "gen_source": 1, "gen_victim": 2},
        {"t": 7, "source": 1, "victim": 4, "principal": 5.0, "gen_source": 1, "gen_victim": 0},
        {"t": 7, "source": 3, "victim": 5, "principal": 30.0, "gen_source": 2, "gen_victim": 3},
    ]

    first = branching_from_series(series)
    assert first["deaths"] == 4 and first["roots"] == 2, first
    assert approx(first["b1"], 0.5), first

    second = branching_from_edges(edges, n_deaths=first["deaths"])
    assert second["n_edges"] == 4 and second["n_edges_lethal"] == 3, second
    assert second["n_pairs"] == 3, second
    assert approx(second["b2"], 0.75), second
    assert second["n_non_roots_seen"] == 2, second
    assert approx(second["mean_in_degree"], 1.5), second
    assert approx(second["multi_parent_share"], 0.5), second

    both = reconcile(series, edges)
    assert both["closes"], both
    assert approx(both["gap_b2_b1"], 0.25), both
    print(
        f"  cascade à la main : b₁ = {both['b1']:.3f}, b₂ = {both['b2']:.3f}, "
        f"écart = {both['gap_b2_b1']:.3f} (attendus 0,5 / 0,75 / 0,25)  OK"
    )

    # Le cas dégénéré doit rendre nan, pas lever : une fenêtre sans mort
    # existe (petites populations), et l'analyse doit pouvoir l'écarter.
    assert branching_from_counts(0, 0) != branching_from_counts(0, 0), "nan attendu"
    print("  fenêtre sans mort : b₁ = nan, aucune exception  OK")


def test_engine_generation_one_is_root():
    """Sur le moteur : génération 1 ⟺ racine, et l'arbre ferme sur la série.

    C'est l'énoncé du plan §3.2 dont dépend la validité de b₁ : les racines
    sont la file INITIALE du point fixe, donc exactement les morts de la
    première passe.
    """
    config = Config(seed=3, T=300, record_deaths=True, record_loss_edges=True)
    simulation = Simulation(config)
    simulation.run()

    roots = 0
    non_roots = 0
    for death in simulation.deaths:
        is_root = death["cause"] in ("insolvency", "liquidity", "both")
        if is_root:
            roots += 1
            assert death["death_iter"] == 1, death
        else:
            non_roots += 1
            assert death["cause"] == "cascade" and death["death_iter"] >= 2, death
    assert roots + non_roots == sum(row["deaths"] for row in simulation.series)
    print(
        f"  moteur : {roots} racines toutes en génération 1, "
        f"{non_roots} morts de cascade toutes en génération ≥ 2  OK"
    )

    both = reconcile(simulation.series, simulation.loss_edges)
    assert both["closes"], both
    assert both["b2"] >= both["b1"] - 1e-12, both
    assert both["n_pairs"] >= both["expected_non_roots"], both

    # Les DEUX formes d'entrée — lignes et colonnes — doivent rendre le même
    # résultat : le chemin vectorisé est le seul praticable sur un run de
    # campagne (1,4 million d'arêtes), donc c'est lui qui produira les
    # chiffres publiés, et il n'a pas le droit de dériver du chemin lisible.
    with tempfile.TemporaryDirectory() as directory:
        path = write_edges(simulation, directory)
        columns = reconcile(simulation.series, read_edges(path))
    for key, value in both.items():
        other = columns[key]
        if isinstance(value, float) and value != value:
            assert other != other, key
        else:
            assert abs(other - value) <= 1e-12 * max(1.0, abs(value)), (key, value, other)
    print("  chemins lignes et colonnes : résultats identiques champ par champ  OK")
    print(
        f"  arbre causal : {both['n_non_roots_seen']:.0f} victimes mortelles "
        f"= morts {both['deaths']:.0f} − racines {both['roots']:.0f}  OK"
    )
    print(
        f"  b₁ = {both['b1']:.4f}, b₂ = {both['b2']:.4f}, écart = {both['gap_b2_b1']:.4f}, "
        f"degré entrant moyen = {both['mean_in_degree']:.3f}, "
        f"part sur-déterminée = {both['multi_parent_share']:.3f}  OK"
    )


def test_edges_are_free_when_flag_is_off():
    """Le drapeau coupe l'enregistrement, pas le calcul : la trajectoire est
    la même avec et sans, bit à bit. C'est la garantie de parité locale du
    §4.4 — persister les arêtes ne doit RIEN changer."""
    columns = ("pop", "K_tot", "nw_tot", "prod_tot", "deaths", "n_loans", "loan_volume")
    reference = Simulation(Config(seed=5, T=200))
    reference.run()
    armed = Simulation(Config(seed=5, T=200, record_loss_edges=True, record_deaths=True))
    armed.run()
    assert len(reference.series) == len(armed.series)
    for left, right in zip(reference.series, armed.series):
        for column in columns:
            assert left[column] == right[column], (left["t"], column, left[column], right[column])
    assert not reference.loss_edges and armed.loss_edges
    print(
        f"  drapeau armé vs éteint : {len(reference.series)} pas × {len(columns)} colonnes "
        f"bit à bit identiques, {len(armed.loss_edges)} arêtes enregistrées  OK"
    )


def main() -> int:
    print("test_branching.py — les deux estimateurs du rapport de branchement (plan §3.2, §7)")
    test_hand_built_cascade()
    test_engine_generation_one_is_root()
    test_edges_are_free_when_flag_is_off()
    print("test_branching.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
