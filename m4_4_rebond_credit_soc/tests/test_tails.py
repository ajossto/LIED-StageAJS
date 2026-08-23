"""Test M4.4 §7 — les estimateurs de queue sur données SYNTHÉTIQUES.

Exigence du plan : « sur un échantillon synthétique tiré d'une Pareto
d'exposant connu, l'estimateur rend l'exposant et son bootstrap couvre la
vraie valeur au taux nominal. Sans ce test, une dérive de l'estimateur
serait lue comme un effet de modèle. »

C'est le seul endroit du programme où la vraie valeur est connue. Tout ce
qui suit — lots C, D, E — lit des α̂ dont personne ne connaît la cible ; si
l'estimateur biaisait, rien dans les données du modèle ne le dirait.

    /home/anatole/jupyter/.venv/bin/python3 m4_4_rebond_credit_soc/tests/test_tails.py
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_4.tails import (  # noqa: E402
    bootstrap_tail,
    fit_powerlaw_discrete,
    compare_tail_families,
    fit_composite,
    fit_tail,
    hill,
    ks_distance,
    scan_xmin,
    vuong,
)


def pareto(rng, n: int, alpha: float, xmin: float = 1.0) -> np.ndarray:
    """Tirage exact d'une Pareto continue : x = x_min · U^(−1/(α−1))."""
    return xmin * rng.random(n) ** (-1.0 / (alpha - 1.0))


def test_hill_recovers_a_known_exponent():
    """Seuil CONNU : l'estimateur doit tomber sur α à quelques erreurs-types."""
    rng = np.random.default_rng(0)
    for alpha in (2.0, 2.5, 3.5):
        sample = pareto(rng, 200_000, alpha)
        fit = hill(sample, 1.0)
        deviation = abs(fit["alpha"] - alpha) / fit["se"]
        assert deviation < 4.0, (alpha, fit)
    print("  seuil connu : α̂ à moins de 4 erreurs-types de α pour α ∈ {2,0 ; 2,5 ; 3,5}  OK")


def test_scan_finds_the_threshold_of_a_contaminated_sample():
    """Seuil ESTIMÉ : un corps exponentiel collé sous une queue de Pareto.

    C'est la situation réelle — le revenu d'intérêt n'est pas une Pareto
    partout — et c'est là que le balayage sert à quelque chose.
    """
    rng = np.random.default_rng(1)
    alpha, cut = 2.8, 10.0
    tail = pareto(rng, 4000, alpha, xmin=cut)
    body = rng.exponential(2.0, size=16_000)
    body = body[body < cut]
    sample = np.concatenate([tail, body])
    fit = scan_xmin(sample)
    assert fit["n_tail"] >= 1000, fit
    assert abs(fit["alpha"] - alpha) < 0.25, fit
    assert 0.3 * cut < fit["xmin"] < 3.0 * cut, fit
    print(f"  corps exponentiel + queue Pareto(α={alpha}) : seuil trouvé "
          f"{fit['xmin']:.2f} (vrai {cut}), α̂ = {fit['alpha']:.3f}, "
          f"n_tail = {fit['n_tail']}, KS = {fit['ks']:.4f}  OK")


def test_bootstrap_covers_at_the_nominal_rate():
    """Couverture de l'intervalle bootstrap à 95 %, mesurée par répétition.

    Le seuil est re-balayé à chaque tirage : c'est ce qui rend l'intervalle
    honnête, et c'est aussi ce qui l'élargit. On exige une couverture d'au
    moins 85 % sur 40 répétitions — en deçà du nominal, parce que
    l'estimateur de Clauset–Shalizi–Newman est biaisé en petit échantillon,
    et au-dessus de ce qu'un intervalle à seuil figé donnerait.
    """
    alpha = 2.5
    covered = 0
    widths = []
    repetitions = 40
    for repetition in range(repetitions):
        rng = np.random.default_rng(100 + repetition)
        sample = pareto(rng, 2000, alpha)
        boot = bootstrap_tail(sample, draws=100, seed=repetition)
        widths.append(boot["alpha_q975"] - boot["alpha_q025"])
        if boot["alpha_q025"] <= alpha <= boot["alpha_q975"]:
            covered += 1
    rate = covered / repetitions
    assert rate >= 0.85, (rate, covered, repetitions)
    print(f"  bootstrap à seuil re-balayé : couverture {rate:.0%} sur {repetitions} "
          f"répétitions (nominal 95 %), largeur médiane "
          f"{float(np.median(widths)):.3f}  OK")


def test_bootstrap_is_wider_than_the_fixed_threshold_error():
    """Le seuil coûte de l'incertitude, et il faut pouvoir le montrer."""
    rng = np.random.default_rng(7)
    sample = pareto(rng, 2000, 2.5)
    fixed = hill(sample, 1.0)
    boot = bootstrap_tail(sample, draws=200, seed=3)
    ratio = boot["alpha_sd"] / fixed["se"]
    assert ratio > 1.5, (boot["alpha_sd"], fixed["se"])
    print(f"  incertitude à seuil estimé {boot['alpha_sd']:.4f} contre "
          f"{fixed['se']:.4f} à seuil connu : rapport ×{ratio:.1f}  OK")


def test_lognormal_degenerates_into_a_power_law():
    """LA limite du couple loi de puissance / log-normale, mesurée.

    Sur une Pareto EXACTE, l'ajustement log-normal tronqué ne rate pas : il
    s'échappe vers σ ≫ 1, où la log-normale tronquée à gauche converge vers
    une loi de puissance. Vuong rend alors z ≈ 0 — non parce que les données
    manquent, mais parce que les deux familles se recouvrent dans ce coin de
    l'espace des paramètres.

    Ce test fige ce fait pour que personne, au lot C, ne lise un z proche de
    zéro comme « les deux lois vont ».
    """
    rng = np.random.default_rng(11)
    power = compare_tail_families(pareto(rng, 20_000, 2.5))
    z_ln = power["vuong_pl_vs_ln"]["z"]
    assert abs(z_ln) < 1.96, power["vuong_pl_vs_ln"]
    assert power["lognormal_degenerate"] is True, power["lognormal"]
    assert power["lognormal"]["sigma"] > 10.0, power["lognormal"]
    # Ce que la vraisemblance sait quand même trancher :
    assert power["vuong_pl_vs_exp"]["z"] > 1.96, power["vuong_pl_vs_exp"]
    print(f"  Pareto exacte : log-normale ajustée σ = {power['lognormal']['sigma']:.1f} "
          f"(dégénérée), Vuong pl/ln z = {z_ln:+.2f} — SANS POUVOIR ; "
          f"pl/exp z = {power['vuong_pl_vs_exp']['z']:+.1f} — décisif  OK")


def test_vuong_points_the_right_way_but_rarely_concludes():
    """Sur des données VRAIMENT log-normales, le test vise juste — et n'en
    conclut presque jamais.

    Le signe est stable : sur six graines, z < 0 partout. La significativité,
    elle, ne l'est pas : |z| franchit 1,96 dans une minorité des cas, à
    100 000 tirages. C'est la même limite que dans l'autre sens, et elle
    n'est pas une question de volume : elle tient à ce que les deux familles
    se recouvrent dans la queue.

    Ce test fige donc une CONTRAINTE DE MÉTHODE pour le lot C : sur ce couple,
    seul le SIGNE est exploitable, et il faut plusieurs instantanés pour en
    faire quelque chose.
    """
    values = []
    for seed in range(12, 18):
        rng = np.random.default_rng(seed)
        fit = compare_tail_families(np.exp(rng.normal(0.0, 0.5, size=100_000)))
        assert fit["lognormal_degenerate"] is False, fit["lognormal"]
        values.append(fit["vuong_pl_vs_ln"]["z"])
    assert all(z < 0 for z in values), values
    significant = sum(z < -1.96 for z in values)
    print(f"  log-normale vraie, 6 graines : z tous négatifs "
          f"(médiane {float(np.median(values)):+.2f}), mais "
          f"{significant}/6 seulement au-delà de −1,96  OK")


def test_the_vuong_statistic_is_invariant_under_power_transforms():
    """Pourquoi σ n'est pas un axe pour ce test — et c'est une identité.

    Une transformation x ↦ x^c envoie une log-normale(μ, σ) sur une
    log-normale(cμ, cσ) et une Pareto(α) sur une Pareto(1 + (α−1)/c). Les
    deux familles sont donc STABLES par cette transformation, et le jacobien
    est le même pour les deux : il disparaît du rapport de vraisemblance.
    La statistique de Vuong est par conséquent invariante. Exactement en
    théorie ; à 10⁻⁵ près en pratique, parce que les deux ajustements passent
    par un optimiseur numérique dont le point d'arrêt diffère.

    Conséquence pratique : faire varier σ d'une log-normale ne rend pas le
    test plus puissant. Seul l'effectif compte.
    """
    rng = np.random.default_rng(31)
    normal = rng.normal(0.0, 1.0, size=40_000)
    first = compare_tail_families(np.exp(0.4 * normal))
    second = compare_tail_families(np.exp(0.9 * normal))
    assert abs(first["vuong_pl_vs_ln"]["z"] - second["vuong_pl_vs_ln"]["z"]) < 1e-4, (
        first["vuong_pl_vs_ln"], second["vuong_pl_vs_ln"]
    )
    print(f"  invariance par puissance : z = {first['vuong_pl_vs_ln']['z']:+.4f} "
          f"pour σ = 0,4 et {second['vuong_pl_vs_ln']['z']:+.4f} pour σ = 0,9  OK")


def test_composite_recovers_its_own_parameters():
    """Le composite « corps exponentiel × queue de Pareto » de M4 fable."""
    rng = np.random.default_rng(13)
    T, cut, alpha = 3.0, 12.0, 4.0
    # Mélange exact : masse du corps et de la queue dans les proportions du
    # modèle, chacune tirée de sa loi conditionnelle.
    body_mass = T * (1.0 - math.exp(-cut / T))
    tail_mass = math.exp(-cut / T) * cut / (alpha - 1.0)
    share = body_mass / (body_mass + tail_mass)
    n = 60_000
    uniform = rng.random(n)
    from_body = uniform < share
    sample = np.empty(n)
    # Corps : exponentielle tronquée à droite en `cut`, par inversion.
    u = rng.random(int(from_body.sum()))
    sample[from_body] = -T * np.log(1.0 - u * (1.0 - math.exp(-cut / T)))
    sample[~from_body] = pareto(rng, int((~from_body).sum()), alpha, xmin=cut)
    fit = fit_composite(sample)
    assert abs(fit["T"] - T) / T < 0.10, fit
    assert abs(fit["x_b"] - cut) / cut < 0.25, fit
    assert abs(fit["alpha"] - alpha) / alpha < 0.15, fit
    print(f"  composite : T = {fit['T']:.2f} (vrai {T}), x_b = {fit['x_b']:.2f} "
          f"(vrai {cut}), α = {fit['alpha']:.2f} (vrai {alpha})  OK")


def test_discrete_fit_matches_the_m4b_implementation():
    """La comparaison inter-lignées exige le MÊME estimateur.

    `m4_4.tails.fit_powerlaw_discrete` est une réécriture de
    `recherche/sensibilite_m4b/scripts/lib_metrics.fit_powerlaw_discrete` —
    le paquet `m4_4` n'importe aucun autre dossier du dépôt. Ce test importe
    l'original, le seul endroit du programme où il est chargé, et vérifie que
    les deux rendent le même α sur les mêmes tailles. Sans lui, le α∞ ≈ 2,31
    de M4B et celui de cette lignée seraient deux nombres sans rapport
    démontré.
    """
    import importlib.util  # noqa: PLC0415

    path = "/home/anatole/jupyter/recherche/sensibilite_m4b/scripts/lib_metrics.py"
    if not os.path.exists(path):
        print("  (lib_metrics.py de M4B absent : comparaison sautée)")
        return
    spec = importlib.util.spec_from_file_location("m4b_lib_metrics", path)
    m4b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m4b)

    rng = np.random.default_rng(21)
    # Tailles entières d'exposant connu, tirées par inversion discrète.
    support = np.arange(2, 4000)
    weights = support.astype(float) ** -2.3
    weights /= weights.sum()
    sizes = rng.choice(support, size=20_000, p=weights)

    ours = fit_powerlaw_discrete(sizes)
    theirs = m4b.fit_powerlaw_discrete(sizes.astype(float))
    assert ours is not None and theirs is not None
    assert abs(ours["alpha"] - theirs["alpha"]) < 1e-9, (ours, theirs)
    assert ours["n_tail"] == theirs["n_tail"]
    assert abs(ours["alpha"] - 2.3) < 0.05, ours
    print(f"  loi de puissance discrète : α̂ = {ours['alpha']:.4f} contre "
          f"{theirs['alpha']:.4f} pour M4B (écart "
          f"{abs(ours['alpha'] - theirs['alpha']):.1e}), vrai 2,30  OK")


def test_degenerate_samples_do_not_raise():
    """Une fenêtre sans queue existe ; elle doit rendre `nan`, pas lever."""
    empty = fit_tail(np.zeros(50))
    assert empty["n_tail"] == 0 and empty["alpha"] != empty["alpha"]
    tiny = compare_tail_families(np.array([1.0, 2.0, 3.0]))
    assert tiny["identifiable"] is False
    assert math.isnan(vuong(np.array([1.0]), np.array([1.0]))["z"])
    assert not math.isfinite(ks_distance(np.array([1.0]), 1.0, 2.0))
    print("  échantillons dégénérés : nan rendu, aucune exception  OK")


def main() -> int:
    print("test_tails.py — estimateurs de queue sur données synthétiques (plan §7)")
    test_hill_recovers_a_known_exponent()
    test_scan_finds_the_threshold_of_a_contaminated_sample()
    test_bootstrap_covers_at_the_nominal_rate()
    test_bootstrap_is_wider_than_the_fixed_threshold_error()
    test_lognormal_degenerates_into_a_power_law()
    test_vuong_points_the_right_way_but_rarely_concludes()
    test_the_vuong_statistic_is_invariant_under_power_transforms()
    test_composite_recovers_its_own_parameters()
    test_discrete_fit_matches_the_m4b_implementation()
    test_degenerate_samples_do_not_raise()
    print("test_tails.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
