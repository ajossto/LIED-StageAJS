"""Test §9 — `loan_direction="richest_lends"` rejoue le moteur v1 bit à bit.

C'est la condition qui rend la campagne A/B du §3.1 APPARIÉE. Si le bras de
référence n'était pas exactement v1, la comparaison « ancienne règle contre
sens libre » ne mesurerait pas le sens du prêt mais la différence entre deux
lignées de code.

Le test fait tourner, sur la MÊME graine et le MÊME plan d'intervention :

- le moteur v1 (`m4_3live_credit_soc/m4_3live/model.py`), importé en LECTURE
  SEULE — il n'est jamais modifié, c'est la règle du fork ;
- le moteur v2 avec `loan_direction="richest_lends"`.

L'intervention (A = 1,5 sur une fraction de 20 %) est indispensable : sans
elle une seule technologie vit, toutes les paires passent par le chemin
identité du noyau, et le test ne prouverait rien sur les régimes (b) et (c),
ni sur la direction du prêt — qui ne peut se poser qu'entre technologies
différentes.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_v1_equivalence.py
"""

from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
V1_ROOT = os.path.join(os.path.dirname(V2_ROOT), "m4_3live_credit_soc")
sys.path.insert(0, V2_ROOT)
sys.path.insert(0, V1_ROOT)

STEPS = 300
INTERVENTION_T = 100
BASE = dict(gamma=0.5, A=1.0, lam=30.0, delta=0.01, sigma=0.01, K0=25.0, seed=0)


_CACHE: dict[tuple, list[dict]] = {}


def _run(module_name: str, extra: dict) -> list[dict]:
    key = (module_name, tuple(sorted(extra.items())))
    if key in _CACHE:
        return _CACHE[key]
    _CACHE[key] = _series(module_name, extra)
    return _CACHE[key]


def _series(module_name: str, extra: dict) -> list[dict]:
    model = __import__(f"{module_name}.model", fromlist=["model"])
    known = set(model.Config.__dataclass_fields__)
    kwargs = {k: v for k, v in {**BASE, **extra}.items() if k in known}
    simulation = model.Simulation(model.Config(**kwargs, T=STEPS))
    plan = model.Intervention(param="A", value=1.5, scope="fraction", phi=0.2)
    while simulation.t < STEPS and simulation.status == "ok":
        if simulation.t + 1 == INTERVENTION_T:
            simulation.submit(plan)
        simulation.step()
    assert simulation.status == "ok", (module_name, simulation.status)
    return simulation.series


def test_v1_is_replayable():
    started = time.time()
    reference = _run("m4_3live", {"transfer_cap": "optimum"})
    obtained = _run("m4_3live_v2", {"loan_direction": "richest_lends"})
    assert len(reference) == len(obtained) == STEPS

    columns = sorted(set(reference[0]) & set(obtained[0]))
    # Colonnes que v2 ajoute ou retire : elles ne peuvent pas être comparées.
    assert "mkt_capped" not in columns and "mkt_reversed" not in columns
    for index, (left, right) in enumerate(zip(reference, obtained)):
        for column in columns:
            assert left[column] == right[column], (
                f"divergence à t={index + 1}, colonne {column} : "
                f"v1={left[column]!r} v2={right[column]!r}"
            )
    techs = obtained[-1]["n_tech_alive"]
    assert techs >= 2, f"une seule technologie vivante ({techs}) : test sans portée"
    blocked = sum(row["mkt_blocked_dir"] for row in obtained[INTERVENTION_T:])
    assert blocked > 0, "aucune paire refusée pour cause de sens : test sans portée"
    print(
        f"  {STEPS} pas × {len(columns)} colonnes, intervention A×1,5 sur 20 % à "
        f"t={INTERVENTION_T} : écart maximal NUL entre v1 et v2/richest_lends"
    )
    print(
        f"  {techs} technologies vivantes en fin de run, {blocked} paires refusées "
        f"pour cause de sens dans les deux moteurs ; {time.time() - started:.0f} s  OK"
    )


def test_free_direction_actually_differs():
    """Contrôle négatif : sous `free`, la trajectoire DOIT diverger."""
    reference = _run("m4_3live_v2", {"loan_direction": "richest_lends"})
    free = _run("m4_3live_v2", {"loan_direction": "free"})
    first = None
    for index, (left, right) in enumerate(zip(reference, free)):
        if left["loan_volume"] != right["loan_volume"]:
            first = index + 1
            break
    assert first is not None, "sens libre et règle v1 donnent la même trajectoire"
    # Avant l'intervention, une seule technologie vit : δ* = (K_b − K_a)/2 ≥ 0
    # et le sens libre coïncide avec la règle v1. La première divergence
    # possible est donc le pas de l'intervention lui-même, dont la phase de
    # marché voit déjà les technologies mélangées.
    assert first >= INTERVENTION_T, (
        f"divergence à t={first}, AVANT l'intervention (t={INTERVENTION_T}) : le "
        "sens libre ne devrait rien changer en régime homogène"
    )
    reversed_total = sum(row["mkt_reversed"] for row in free)
    assert reversed_total > 0
    print(
        f"  contrôle négatif : première divergence à t={first} (intervention à "
        f"t={INTERVENTION_T}), {reversed_total} prêts conclus dans le sens interdit  OK"
    )


def main() -> int:
    print("test_v1_equivalence.py — la v1 est rejouable dans le moteur v2 (§9)")
    test_v1_is_replayable()
    test_free_direction_actually_differs()
    print("test_v1_equivalence.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
