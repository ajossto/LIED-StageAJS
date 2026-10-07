"""Convention UNIQUE pour l'exposant de queue Pareto dans M4.2B.

PROMPT_M4_2B.md §10 : « Sois parfaitement explicite sur la relation entre κ
et α, et ne mélange jamais exposant de CCDF et exposant de densité. »

Ce dépôt réutilise deux outils déjà existants (§10 : « outils existants
d'analyse des distributions et des queues ») qui utilisent la même clé
"alpha" pour DEUX grandeurs différentes :

- ``families.fit_pareto_1p`` (scripts/families.py) renvoie le paramètre de
  forme ``b`` de ``scipy.stats.pareto`` : c'est l'exposant de la CCDF,
  P(X>x)=(x_min/x)^κ. On l'appelle ici **κ (kappa_ccdf)**.
- ``tail_test.fit_powerlaw_xmin`` (scripts/tail_test.py) renvoie l'exposant
  de DENSITÉ standard (Clauset-Shalizi-Newman), p(x)∝x^-α,
  α=1+n/Σlog(x/x_min). On l'appelle ici **α (alpha_density)**.

Relation : **α = κ + 1**. Ce module ne réimplémente aucun ajustement : il ne
fait que renommer et convertir explicitement la sortie des deux outils vers
un format commun {alpha_density, kappa_ccdf, x_min, n_tail, ...}, pour que
plus aucun code d'analyse n'ait à se souvenir de laquelle des deux
conventions un "alpha" donné représente.

Toute nouvelle fonction d'ajustement ajoutée pour M4.2B doit produire ses
résultats via ``from_alpha_density`` ou ``from_kappa_ccdf`` ci-dessous, pas
directement un dict ad hoc avec une clé "alpha" ambiguë.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import stats


def from_alpha_density(alpha_density: float, x_min: float, **extra) -> dict:
    return {"alpha_density": float(alpha_density), "kappa_ccdf": float(alpha_density) - 1.0,
            "x_min": float(x_min), **extra}


def from_kappa_ccdf(kappa_ccdf: float, x_min: float, **extra) -> dict:
    return {"alpha_density": float(kappa_ccdf) + 1.0, "kappa_ccdf": float(kappa_ccdf),
            "x_min": float(x_min), **extra}


def from_families_pareto_1p(fit: dict | None) -> dict | None:
    """Convertit la sortie de families.fit_pareto_1p (κ=CCDF, x_min=min(data))."""
    if fit is None:
        return None
    kappa = float(fit["params"]["alpha"])  # scipy pareto b == kappa (CCDF), PAS alpha_density
    x_min = float(fit["params"]["x_min"])
    return from_kappa_ccdf(
        kappa, x_min,
        neg_ll=fit.get("neg_ll"), aic=fit.get("aic"), bic=fit.get("bic"),
        source="families.fit_pareto_1p (x_min=min(data), pas un seuil de queue)",
    )


def from_tail_test_xmin(fit: dict | None) -> dict | None:
    """Convertit la sortie de tail_test.fit_powerlaw_xmin (déjà alpha_density)."""
    if fit is None:
        return None
    return from_alpha_density(
        float(fit["alpha"]), float(fit["x_min"]),
        n_tail=int(fit["n_tail"]), ks=float(fit["ks"]),
        source="tail_test.fit_powerlaw_xmin (seuil x_min scanné par KS)",
    )


def _self_test_synthetic_pareto(
    alpha_density_true: float = 2.5, x_min_true: float = 1.0, n: int = 20_000, seed: int = 0
) -> None:
    """Vérifie que les deux outils, une fois passés par ce module, s'accordent
    sur alpha_density (à l'incertitude d'échantillonnage près) et retrouvent
    la vraie valeur — condition nécessaire avant tout usage en production."""
    kappa_true = alpha_density_true - 1.0
    rng = np.random.default_rng(seed)
    # scipy.stats.pareto(b=kappa, scale=x_min) a la CCDF (x_min/x)^kappa,
    # donc densité d'exposant kappa+1 = alpha_density_true.
    sample = stats.pareto.rvs(b=kappa_true, scale=x_min_true, size=n, random_state=rng)

    import families
    import tail_test

    fit_families = families.fit_pareto_1p(sample)
    converted_families = from_families_pareto_1p(fit_families)
    assert converted_families is not None

    fit_tail = tail_test.fit_powerlaw_xmin(sample, min_tail=200)
    assert fit_tail is not None
    converted_tail = from_tail_test_xmin(fit_tail)

    for name, converted in (("families.fit_pareto_1p", converted_families),
                             ("tail_test.fit_powerlaw_xmin", converted_tail)):
        error = abs(converted["alpha_density"] - alpha_density_true)
        assert error <= 0.15, (name, converted["alpha_density"], alpha_density_true, error)

    cross_diff = abs(converted_families["alpha_density"] - converted_tail["alpha_density"])
    assert cross_diff <= 0.25, (
        "les deux outils convertis doivent s'accorder sur alpha_density",
        converted_families, converted_tail, cross_diff,
    )
    print(
        f"  auto-test Pareto synthétique (alpha_density_vrai={alpha_density_true}) : "
        f"families->{converted_families['alpha_density']:.4f}  "
        f"tail_test->{converted_tail['alpha_density']:.4f}"
    )


def test_convention_self_consistent_on_synthetic_pareto() -> None:
    _self_test_synthetic_pareto(alpha_density_true=2.5, x_min_true=1.0, seed=0)
    _self_test_synthetic_pareto(alpha_density_true=1.8, x_min_true=5.0, seed=1)
    _self_test_synthetic_pareto(alpha_density_true=3.5, x_min_true=0.1, seed=2)


def test_conversion_helpers_invert_each_other() -> None:
    for alpha in (1.5, 2.0, 3.7):
        converted = from_alpha_density(alpha, 1.0)
        back = from_kappa_ccdf(converted["kappa_ccdf"], 1.0)
        assert abs(back["alpha_density"] - alpha) <= 1e-12


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
