"""Tests §8 — sémantique exacte des trois portées (prompt §2).

Convention du dépôt : assertions Python simples, pas de pytest.
    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_scopes.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.model import Config, Intervention, Simulation  # noqa: E402

BASE = dict(seed=7, T=0, lam=20.0, delta=0.01, sigma=0.01, K0=25.0, gamma=0.5, A=1.0)


def build(**overrides):
    simulation = Simulation(Config(**{**BASE, **overrides}))
    for _ in range(25):
        simulation.step()
    return simulation


def test_new_leaves_living_untouched():
    """`new` : aucune entité déjà née n'est modifiée, jamais."""
    simulation = build()
    before = {entity: simulation.population.A[entity] for entity in simulation.population.living()}
    t0 = simulation.t
    simulation.submit(Intervention(param="A", value=2.5, scope="new"))
    for _ in range(12):
        simulation.step()
    unchanged = 0
    for entity, value in before.items():
        if not simulation.population.alive[entity]:
            continue
        assert simulation.population.A[entity] == value, entity
        unchanged += 1
    newborns = [
        entity
        for entity in simulation.population.living()
        if simulation.population.birth[entity] > t0
    ]
    assert newborns, "il faut des naissances pour que le test ait un sens"
    for entity in newborns:
        assert simulation.population.A[entity] == 2.5, entity
    assert simulation.intervention_log[0]["t"] == t0 + 1
    print(
        f"  new : {unchanged} vivantes inchangées, {len(newborns)} nées après à A=2.5, "
        f"t effectif = {t0 + 1}  OK"
    )


def test_all_changes_every_living_entity():
    """`all` : rétroactif ET prospectif."""
    simulation = build()
    t0 = simulation.t
    simulation.submit(Intervention(param="A", value=1.75, scope="all"))
    simulation.step()
    for entity in simulation.population.living():
        assert simulation.population.A[entity] == 1.75, entity
    for _ in range(6):
        simulation.step()
    newborns = [
        entity
        for entity in simulation.population.living()
        if simulation.population.birth[entity] > t0 + 1
    ]
    assert newborns
    for entity in newborns:
        assert simulation.population.A[entity] == 1.75
    assert simulation.population.tech_alive[simulation.default_tech] == simulation.population.n_alive
    print(f"  all : toutes les vivantes ET les {len(newborns)} nées après à A=1.75  OK")


def test_fraction_touches_only_the_drawn_entities():
    """`fraction` : k entités tirées, et le DÉFAUT DE NAISSANCE INCHANGÉ.

    C'est le point que le prompt (§2) demande de vérifier explicitement :
    une entité née APRÈS t₀ doit recevoir l'ANCIEN défaut, pas la valeur
    de l'intervention — sans quoi l'intensité de traitement dériverait et
    l'élasticité mesurée au §7 n'aurait plus de dénominateur fixe.
    """
    simulation = build()
    t0 = simulation.t
    living_before = set(simulation.population.living())
    expected = int(round(0.2 * len(living_before)))
    simulation.submit(Intervention(param="A", value=3.0, scope="fraction", phi=0.2))
    simulation.step()
    record = simulation.intervention_log[0]
    assert record["scope"] == "fraction"
    assert record["n_selected"] == expected, (record["n_selected"], expected)
    selected = set(record["selected_ids"])
    assert selected <= living_before, "des entités hors du vivant ont été tirées"
    treated = [
        entity for entity in simulation.population.living() if simulation.population.A[entity] == 3.0
    ]
    assert set(treated) <= selected
    # Le défaut de naissance n'a pas bougé.
    assert simulation.default_A == 1.0
    for _ in range(10):
        simulation.step()
    newborns = [
        entity
        for entity in simulation.population.living()
        if simulation.population.birth[entity] > t0 + 1
    ]
    assert newborns
    for entity in newborns:
        assert simulation.population.A[entity] == 1.0, (
            f"l'entité {entity}, née après t₀, a reçu la valeur d'intervention : "
            "la portée fraction a contaminé le défaut de naissance"
        )
    print(
        f"  fraction φ=0.2 : {len(selected)} tirées sur {len(living_before)} vivantes, "
        f"défaut de naissance intact ({len(newborns)} nées après à A=1.0)  OK"
    )


def test_fraction_is_deterministic_and_uses_simulation_rng():
    """Deux simulations de même graine tirent EXACTEMENT la même fraction."""
    first = build()
    second = build()
    for simulation in (first, second):
        simulation.submit(Intervention(param="A", value=3.0, scope="fraction", phi=0.3))
        simulation.step()
    assert first.intervention_log[0]["selected_ids"] == second.intervention_log[0]["selected_ids"]
    # ... et le tirage a bien consommé le générateur commun : la suite diverge
    # d'un contrôle sans intervention (c'est attendu, et c'est pourquoi la
    # campagne §7 mesure un plancher de bruit avec un bras « null ».)
    control = build()
    for _ in range(5):
        control.step()
        first.step()
    assert control.series[-1]["prod_tot"] != first.series[-1]["prod_tot"]
    print("  fraction : tirage déterministe par la graine, et consomme bien le RNG commun  OK")


def test_fraction_accepts_explicit_ids_without_rng():
    """Une liste d'identifiants explicite (débogage, §2) ne consomme aucun tirage."""
    with_ids = build()
    without = build()
    targets = sorted(with_ids.population.living())[:5]
    with_ids.submit(Intervention(param="gamma", value=0.6, scope="fraction", ids=targets))
    with_ids.step()
    without.step()
    assert with_ids.intervention_log[0]["selected_ids"] == targets
    for entity in targets:
        if with_ids.population.alive[entity]:
            assert with_ids.population.g[entity] == 0.6
    # aucun tirage consommé : les naissances du pas suivant sont identiques
    assert with_ids.series[-1]["births"] == without.series[-1]["births"]
    print(f"  fraction avec ids explicites : {len(targets)} entités, aucun tirage consommé  OK")


def test_k0_all_and_new_are_identical():
    """K0 n'existe qu'à la naissance : `all` et `new` sont le même objet."""
    trajectories = []
    for scope in ("all", "new"):
        simulation = build()
        simulation.submit(Intervention(param="K0", value=80.0, scope=scope))
        for _ in range(15):
            simulation.step()
        trajectories.append([row["K_tot"] for row in simulation.series])
    assert trajectories[0] == trajectories[1], "all et new devraient coïncider pour K0"
    print("  K0 : `all` et `new` produisent des trajectoires bit-identiques  OK")


def test_population_parameter_new_is_an_alias_of_all():
    """lam/delta/sigma/rho/... : `new` est un alias explicite de `all`."""
    trajectories = []
    for scope in ("all", "new"):
        simulation = build()
        simulation.submit(Intervention(param="delta", value=0.03, scope=scope))
        for _ in range(15):
            simulation.step()
        trajectories.append([row["K_tot"] for row in simulation.series])
        assert simulation.config.delta == 0.03
    assert trajectories[0] == trajectories[1]
    print("  delta : `new` alias exact de `all`, config effectivement modifiée  OK")


def test_meaningless_scopes_are_refused():
    """`fraction` est REFUSÉE là où elle n'a pas de sens, avec un message."""
    simulation = build()
    refused = []
    for param in ("K0", "lam", "delta", "sigma", "rho", "eta_beta", "eta_n_ref"):
        try:
            simulation.submit(Intervention(param=param, value=1.0, scope="fraction", phi=0.5))
        except ValueError as exc:
            refused.append(param)
            assert "portée" in str(exc)
    assert len(refused) == 7, refused
    try:
        simulation.submit(Intervention(param="target_rule", value=0.0, scope="all"))
        raise AssertionError("target_rule ne doit pas être intervenable (§2)")
    except ValueError:
        pass
    print(f"  portées sans objet refusées : {', '.join(refused)} ; target_rule exclu  OK")


def test_intervention_applies_before_births():
    """L'intervention prend effet AVANT les naissances de son pas : une
    entité née à t₀+1 hérite déjà de la nouvelle valeur sous portée `new`."""
    simulation = build()
    t0 = simulation.t
    simulation.submit(Intervention(param="A", value=4.0, scope="new"))
    simulation.step()
    born_that_step = [
        entity
        for entity in simulation.population.living()
        if simulation.population.birth[entity] == t0 + 1
    ]
    assert born_that_step, "il faut des naissances au pas de l'intervention"
    for entity in born_that_step:
        assert simulation.population.A[entity] == 4.0, entity
    print(
        f"  ordre : les {len(born_that_step)} entités nées au pas de l'intervention "
        "portent déjà la nouvelle valeur  OK"
    )


def test_composition_of_interventions():
    """Une intervention `all` sur A après une `fraction` sur gamma conserve
    les gammas hétérogènes (les technologies se composent par coordonnée)."""
    simulation = build()
    simulation.submit(Intervention(param="gamma", value=0.6, scope="fraction", phi=0.5))
    simulation.step()
    treated = set(simulation.intervention_log[0]["selected_ids"])
    simulation.submit(Intervention(param="A", value=2.0, scope="all"))
    simulation.step()
    gammas = set()
    for entity in simulation.population.living():
        assert simulation.population.A[entity] == 2.0
        gammas.add(simulation.population.g[entity])
    survivors = [entity for entity in treated if simulation.population.alive[entity]]
    assert survivors
    for entity in survivors:
        assert simulation.population.g[entity] == 0.6
    assert gammas == {0.5, 0.6}, gammas
    print(f"  composition : A=2.0 partout, γ reste hétérogène {sorted(gammas)}  OK")


def main():
    print("test_scopes.py — sémantique des portées (prompt §2, §8)")
    test_new_leaves_living_untouched()
    test_all_changes_every_living_entity()
    test_fraction_touches_only_the_drawn_entities()
    test_fraction_is_deterministic_and_uses_simulation_rng()
    test_fraction_accepts_explicit_ids_without_rng()
    test_k0_all_and_new_are_identical()
    test_population_parameter_new_is_an_alias_of_all()
    test_meaningless_scopes_are_refused()
    test_intervention_applies_before_births()
    test_composition_of_interventions()
    print("test_scopes.py : tout est passé.")


if __name__ == "__main__":
    main()
