"""Test §9 — amplitude exacte et prédiction naïve (§4.2, §4.3 du prompt v2).

L'AMPLITUDE d'une intervention, notée m, est le facteur par lequel elle
multiplie la production des entités qu'elle touche, au pas où elle agit pour
la première fois (horizon h = 1) :

    m = Σ_{i traitée} A'_i K_i^{γ'_i}  /  Σ_{i traitée} A_i K_i^{γ_i},

les deux sommes portant sur le MÊME capital K_i, celui de l'instant de la
production. v1 la reconstruisait depuis les agrégats de `tech_series` ; v2
l'enregistre au moment où elle a lieu, dans le journal d'intervention.

Ce que le test vérifie, sur des cas où la réponse est connue d'avance :

1. levier sur A, portée `all` : m = A'/A exactement, part traitée p = 1 ;
2. levier sur A, portée `fraction` : m = A'/A quand même — l'amplitude ne
   dépend pas de qui est traité tant que le facteur est commun — et p vaut la
   part de production de la cohorte, strictement entre 0 et 1 ;
3. levier sur γ : m vaut Σ K^{γ'} / Σ K^{γ}, qui N'EST PAS choisi et doit être
   mesuré ; la prédiction naïve « K = 1 », qui donne m = 1, est fausse d'un
   facteur que le test affiche ;
4. l'identité E = (Π/Π_cf − 1)/((m−1)p) vaut 1 — et c'est une RÉÉCRITURE des
   définitions, pas une confirmation empirique : son écart à 1 ne mesure que
   la propreté de l'aller-retour flottant.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_amplitude.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.model import Config, Intervention, Simulation  # noqa: E402

WARMUP = 200


def _intervene(param: str, value: float, scope: str, phi: float | None = None) -> dict:
    simulation = Simulation(Config(seed=1, T=WARMUP + 1, lam=30.0, sigma=0.01, K0=25.0))
    while simulation.t < WARMUP:
        simulation.step()
    capitals = {e: simulation.population.K[e] for e in simulation.population.living()}
    coefficients = {e: simulation.population.A[e] for e in simulation.population.living()}
    exponents = {e: simulation.population.g[e] for e in simulation.population.living()}
    simulation.submit(Intervention(param=param, value=value, scope=scope, phi=phi))
    simulation.step()
    entry = simulation.intervention_log[-1]
    assert "amplitude" in entry, entry
    return {
        "entry": entry,
        "amplitude": entry["amplitude"],
        "capitals": capitals,
        "A": coefficients,
        "gamma": exponents,
        "simulation": simulation,
    }


def test_A_lever_all():
    out = _intervene("A", 1.5, "all")
    amplitude = out["amplitude"]
    assert abs(amplitude["m_exact"] - 1.5) < 1e-12, amplitude["m_exact"]
    assert amplitude["p_ex_ante"] == 1.0, amplitude["p_ex_ante"]
    assert abs(amplitude["identity_E"] - 1.0) < 1e-9, amplitude["identity_E"]
    assert abs(amplitude["m_naive_unit_capital"] - 1.5) < 1e-15
    print(
        f"  levier A×1,5 portée `toutes` : m = {amplitude['m_exact']:.15f}, "
        f"p = {amplitude['p_ex_ante']:.1f}, E = {amplitude['identity_E']:.15f}  OK"
    )


def test_A_lever_fraction():
    out = _intervene("A", 1.25, "fraction", phi=0.2)
    amplitude = out["amplitude"]
    entry = out["entry"]
    assert abs(amplitude["m_exact"] - 1.25) < 1e-12, amplitude["m_exact"]
    assert 0.0 < amplitude["p_ex_ante"] < 1.0, amplitude["p_ex_ante"]
    assert abs(amplitude["identity_E"] - 1.0) < 1e-9, amplitude["identity_E"]
    treated = len(entry["selected_ids"])
    assert treated == entry["n_selected"] > 0
    print(
        f"  levier A×1,25 portée `fraction` φ=0,2 : m = {amplitude['m_exact']:.12f} sur "
        f"{treated} entités, part de production traitée p = {amplitude['p_ex_ante']:.4f}  OK"
    )


def test_gamma_lever_is_measured_not_chosen():
    out = _intervene("gamma", 0.6, "all")
    amplitude = out["amplitude"]
    measured = amplitude["m_exact"]
    naive = amplitude["m_naive_unit_capital"]
    by_K_eq = amplitude["m_naive_K_eq"]
    assert naive == 1.0, naive
    assert measured > 1.5, measured
    # La prédiction par K_eq doit être bien meilleure que « K = 1 » sans être
    # exacte : K_eq^{Δγ} ignore la dispersion des capitaux (Jensen).
    assert abs(by_K_eq / measured - 1.0) < 0.10, (by_K_eq, measured)
    assert abs(amplitude["identity_E"] - 1.0) < 1e-9, amplitude["identity_E"]
    print(
        f"  levier γ 0,5 → 0,6 : amplitude MESURÉE m = {measured:.6f} ; prédiction "
        f"naïve à K = 1 : {naive:.6f} ; prédiction par K_eq : {by_K_eq:.6f} "
        f"(écart {100 * (by_K_eq / measured - 1):+.2f} %)  OK"
    )


def test_amplitude_matches_a_hand_computation():
    """m recalculé à la main depuis l'état d'avant l'intervention.

    Le capital de l'instant de la production n'est PAS celui d'avant le pas :
    le choc multiplicatif frappe entre les deux. La vérification porte donc
    sur la structure de m (rapport de deux sommes sur le même capital), en
    reconstruisant le capital exact depuis la production enregistrée :
    K_i = (prod_i / A'_i)^{1/γ'_i}.

    Les entités NÉES au pas de l'intervention n'existaient pas avant elle :
    leur technologie de référence est celle de naissance d'avant, ici
    (A, γ) = (1,0 ; 0,5). Elles font bien partie de la cohorte traitée — sans
    elles, la part traitée d'une portée `toutes` ne vaudrait pas exactement 1.
    """
    OLD_DEFAULT_A, OLD_DEFAULT_GAMMA = 1.0, 0.5
    out = _intervene("gamma", 0.6, "all")
    simulation = out["simulation"]
    population = simulation.population
    treated_now = 0.0
    treated_before = 0.0
    for entity in population.living():
        produced = population.prod[entity]
        if produced <= 0.0:
            continue
        capital = (produced / population.A[entity]) ** (1.0 / population.g[entity])
        coefficient = out["A"].get(entity, OLD_DEFAULT_A)
        exponent = out["gamma"].get(entity, OLD_DEFAULT_GAMMA)
        treated_now += produced
        treated_before += coefficient * capital**exponent
    rebuilt = treated_now / treated_before
    measured = out["amplitude"]["m_exact"]
    assert abs(rebuilt / measured - 1.0) < 1e-9, (rebuilt, measured)
    print(
        f"  m recalculé depuis les productions enregistrées : {rebuilt:.12f} contre "
        f"{measured:.12f} enregistré (écart relatif {abs(rebuilt/measured - 1):.2e})  OK"
    )


def test_new_scope_treats_only_the_newborns():
    """Portée `new` : aucune vivante rebasculée, mais les entités NÉES au pas
    de l'intervention portent déjà la nouvelle technologie. La cohorte
    traitée à h = 1 est donc exactement cette fournée de naissances, et sa
    part de production est de l'ordre de K0^γ / K_eq^γ — quelques millièmes."""
    simulation = Simulation(Config(seed=1, T=WARMUP + 1, lam=30.0, sigma=0.01, K0=25.0))
    while simulation.t < WARMUP:
        simulation.step()
    before = len(simulation.population)
    simulation.submit(Intervention(param="A", value=1.5, scope="new"))
    simulation.step()
    entry = simulation.intervention_log[-1]
    births = len(simulation.population) - before
    amplitude = entry["amplitude"]
    assert entry["n_selected"] == 0, entry["n_selected"]
    assert amplitude["n_treated"] == births > 0, (amplitude["n_treated"], births)
    assert abs(amplitude["m_exact"] - 1.5) < 1e-12, amplitude["m_exact"]
    assert 0.0 < amplitude["p_ex_ante"] < 0.02, amplitude["p_ex_ante"]
    assert abs(amplitude["identity_E"] - 1.0) < 1e-9, amplitude["identity_E"]
    print(
        f"  portée `nouvelles` : 0 vivante rebasculée, {births} naissances traitées, "
        f"m = {amplitude['m_exact']:.12f}, p = {amplitude['p_ex_ante']:.6f}  OK"
    )


def main() -> int:
    print("test_amplitude.py — amplitude exacte enregistrée (prompt v2 §4.2, §4.3)")
    test_A_lever_all()
    test_A_lever_fraction()
    test_gamma_lever_is_measured_not_chosen()
    test_amplitude_matches_a_hand_computation()
    test_new_scope_treats_only_the_newborns()
    print("test_amplitude.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
