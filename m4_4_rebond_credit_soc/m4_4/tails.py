"""Estimateurs de queue pour grandeurs CONTINUES, et comparaison de familles.

Pourquoi ce module et pas `recherche/sensibilite_m4b/scripts/lib_metrics.py`
---------------------------------------------------------------------------
La bibliothèque de M4B ajuste des lois DISCRÈTES à seuil FIXE (`S_MIN`),
parce que son objet est la taille d'avalanche, qui est un entier et dont le
seuil naturel est 1. Elle reste employée telle quelle pour les avalanches
(lot D). Les grandeurs de ce lot — revenu d'intérêt, valeur nette — sont
continues et n'ont pas de seuil naturel : le seuil est un PARAMÈTRE
ESTIMÉ, et c'est de lui que dépend tout le reste.

Ce que M4.2B a établi, et qui commande la forme de ce module
-------------------------------------------------------------
M4.2B a consacré un programme entier à décider si la queue de Pareto des
revenus d'intérêt existe, et a conclu que **la question n'est pas décidable**
avec ce volume de données. Le blocage n'est pas la finesse du critère : c'est
la COUVERTURE, le nombre de points au-delà du seuil (médiane 113 au seuil
optimal, 17 au seuil doublé). Ce module ne rouvre donc pas la question. Il
fournit :

- `n_tail`, la couverture, rendue à chaque appel et jamais implicite ;
- α̂ **caractérisé**, jamais validé — l'existence de la queue reste une
  hypothèse de travail, à marquer `\\hyp{}` à chaque emploi ;
- le seuil **re-balayé à chaque tirage bootstrap**, sans quoi l'incertitude
  rendue serait celle d'un seuil connu, qu'on n'a pas ;
- trois échelles d'incertitude que l'appelant ne doit JAMAIS fusionner :
  intra-instantané (le bootstrap d'ici), inter-instantanés, inter-graines.
  M4.2B mesure l'écart-type bootstrap ≈ 3,7 fois l'écart-type inter-graines.

Estimateurs
-----------
- loi de puissance continue au-dessus de x_min : α̂ = 1 + n/Σ ln(x/x_min),
  l'estimateur de Hill, dont l'erreur-type asymptotique est (α̂−1)/√n ;
- seuil par minimisation de la distance de Kolmogorov–Smirnov entre
  l'empirique au-dessus du seuil et la Pareto ajustée (Clauset, Shalizi,
  Newman) ;
- log-normale et exponentielle tronquées au MÊME seuil, pour que la
  comparaison porte sur les mêmes points ;
- test de Vuong non emboîté, normalisé, sur les log-vraisemblances
  ponctuelles ;
- composite « corps exponentiel × queue de Pareto » à trois paramètres
  (T, x_b, α), la famille que M4 fable retient sur le revenu d'intérêt, avec
  raccord en VALEUR au point de bascule.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = [
    "fit_powerlaw_discrete",
    "AVALANCHE_S_MIN",
    "AVALANCHE_N_MIN",
    "hill",
    "ks_distance",
    "scan_xmin",
    "fit_tail",
    "bootstrap_tail",
    "fit_lognormal_tail",
    "fit_exponential_tail",
    "vuong",
    "fit_composite",
    "compare_tail_families",
]

#: En dessous, aucun ajustement n'est tenté : l'estimateur de Hill sur une
#: poignée de points rend un nombre, pas une mesure.
N_MIN_TAIL = 30

#: Au-delà de ce σ, la log-normale tronquée N'EST PLUS une log-normale.
#:
#: \\fait{} Mesuré ici même (`tests/test_tails.py`) : sur 20 000 tirages d'une
#: Pareto EXACTE d'exposant 2,5, l'ajustement log-normal tronqué s'échappe
#: vers μ = −932 et σ = 24,7, et le test de Vuong rend z = +0,21. Ce n'est pas
#: un défaut d'optimisation : quand μ → −∞ et σ → ∞ à rapport convenable, la
#: log-normale tronquée à gauche CONVERGE vers une loi de puissance. Les deux
#: familles ne sont donc pas séparables par vraisemblance dans ce régime — et
#: cela n'a rien à voir avec le volume de données.
#:
#: Conséquence pour tout le programme : un |z| petit sur ce couple ne dit pas
#: « les deux familles vont », il dit « ces données ne les séparent pas », et
#: un σ ajusté au-delà de ce seuil dit « la log-normale ajustée EST une loi de
#: puissance ». Le couple loi de puissance / exponentielle, lui, garde tout
#: son pouvoir (z = +6,6 sur le même échantillon).
LOGNORMAL_DEGENERATE_SIGMA = 10.0


def hill(values: np.ndarray, xmin: float) -> dict:
    """α̂ de Hill au-dessus d'un seuil DONNÉ (pas estimé ici)."""
    tail = values[values >= xmin]
    n = tail.size
    if n < 2:
        return {"alpha": float("nan"), "se": float("nan"), "n_tail": int(n),
                "xmin": float(xmin), "loglik": float("nan")}
    logs = np.log(tail / xmin)
    total = float(logs.sum())
    if total <= 0:
        return {"alpha": float("nan"), "se": float("nan"), "n_tail": int(n),
                "xmin": float(xmin), "loglik": float("nan")}
    alpha = 1.0 + n / total
    # log f(x) = log(α−1) − log x_min − α log(x/x_min)
    loglik = n * (math.log(alpha - 1.0) - math.log(xmin)) - alpha * total
    return {
        "alpha": float(alpha),
        "se": float((alpha - 1.0) / math.sqrt(n)),
        "n_tail": int(n),
        "xmin": float(xmin),
        "loglik": float(loglik),
    }


def ks_distance(values: np.ndarray, xmin: float, alpha: float) -> float:
    """Distance de Kolmogorov–Smirnov entre l'empirique et la Pareto ajustée."""
    tail = np.sort(values[values >= xmin])
    n = tail.size
    if n < 2:
        return float("inf")
    theoretical = 1.0 - (tail / xmin) ** (1.0 - alpha)
    empirical_low = np.arange(n) / n
    empirical_high = np.arange(1, n + 1) / n
    return float(np.max(np.maximum(theoretical - empirical_low,
                                   empirical_high - theoretical)))


def scan_xmin(values: np.ndarray, n_min: int = N_MIN_TAIL,
              max_candidates: int = 200) -> dict:
    """Seuil qui minimise la distance KS (Clauset–Shalizi–Newman).

    Les candidats sont pris parmi les valeurs observées elles-mêmes, sur une
    grille de quantiles bornée à `max_candidates` : un balayage exhaustif sur
    100 000 points coûte cent fois plus cher pour un seuil qui bouge de
    l'épaisseur d'un point.
    """
    positive = np.sort(values[values > 0])
    if positive.size < n_min + 1:
        return {"alpha": float("nan"), "se": float("nan"), "n_tail": 0,
                "xmin": float("nan"), "ks": float("nan"), "loglik": float("nan")}
    highest = positive.size - n_min
    if highest <= 0:
        candidates = positive[:1]
    elif highest <= max_candidates:
        candidates = positive[:highest]
    else:
        index = np.unique(np.linspace(0, highest - 1, max_candidates).astype(int))
        candidates = positive[index]
    best = None
    for xmin in np.unique(candidates):
        fit = hill(positive, float(xmin))
        if not math.isfinite(fit["alpha"]) or fit["n_tail"] < n_min:
            continue
        distance = ks_distance(positive, float(xmin), fit["alpha"])
        if best is None or distance < best["ks"]:
            best = {**fit, "ks": distance}
    if best is None:
        return {"alpha": float("nan"), "se": float("nan"), "n_tail": 0,
                "xmin": float("nan"), "ks": float("nan"), "loglik": float("nan")}
    return best


def fit_tail(values: np.ndarray, xmin: float | None = None,
             n_min: int = N_MIN_TAIL) -> dict:
    """Ajustement de queue, seuil estimé (défaut) ou imposé."""
    positive = values[values > 0]
    if xmin is None:
        return scan_xmin(positive, n_min=n_min)
    fit = hill(positive, xmin)
    return {**fit, "ks": ks_distance(positive, xmin, fit["alpha"])}


def bootstrap_tail(values: np.ndarray, draws: int = 200, seed: int = 0,
                   n_min: int = N_MIN_TAIL) -> dict:
    """Incertitude INTRA-INSTANTANÉ sur α̂, seuil re-balayé à chaque tirage.

    Re-balayer est la seule façon d'inclure l'incertitude du seuil dans celle
    de l'exposant. Un bootstrap à seuil figé rend l'erreur-type d'un problème
    qu'on ne résout pas — celui où x_min serait connu.
    """
    positive = values[values > 0]
    rng = np.random.default_rng(seed)
    alphas, xmins, tails = [], [], []
    for _ in range(draws):
        sample = rng.choice(positive, size=positive.size, replace=True)
        fit = scan_xmin(sample, n_min=n_min)
        if math.isfinite(fit["alpha"]):
            alphas.append(fit["alpha"])
            xmins.append(fit["xmin"])
            tails.append(fit["n_tail"])
    if not alphas:
        return {"draws": 0, "alpha_mean": float("nan"), "alpha_sd": float("nan")}
    alphas = np.array(alphas)
    return {
        "draws": len(alphas),
        "alpha_mean": float(alphas.mean()),
        "alpha_sd": float(alphas.std(ddof=1)),
        "alpha_q025": float(np.quantile(alphas, 0.025)),
        "alpha_q975": float(np.quantile(alphas, 0.975)),
        "xmin_mean": float(np.mean(xmins)),
        "xmin_sd": float(np.std(xmins, ddof=1)) if len(xmins) > 1 else float("nan"),
        "n_tail_mean": float(np.mean(tails)),
        "n_tail_min": int(np.min(tails)),
    }


def fit_lognormal_tail(values: np.ndarray, xmin: float) -> dict:
    """Log-normale TRONQUÉE à gauche en x_min, ajustée par maximum de
    vraisemblance numérique sur (μ, σ).

    La troncature n'est pas un détail : ajuster une log-normale complète sur
    une queue tronquée puis comparer les vraisemblances comparerait deux
    modèles de supports différents, ce qui n'a pas de sens.
    """
    from scipy import optimize, special  # noqa: PLC0415

    tail = values[values >= xmin]
    n = tail.size
    if n < 2:
        return {"mu": float("nan"), "sigma": float("nan"), "loglik": float("nan"),
                "n_tail": int(n)}
    logs = np.log(tail)
    log_xmin = math.log(xmin)

    def negative_loglik(theta):
        mu, log_sigma = theta
        sigma = math.exp(log_sigma)
        if sigma <= 1e-6 or sigma > 50:
            return 1e100
        # survie au-delà de x_min : 1 − Φ((ln x_min − μ)/σ)
        z = (log_xmin - mu) / (sigma * math.sqrt(2.0))
        survival = 0.5 * special.erfc(z)
        if survival <= 0:
            return 1e100
        value = (
            n * (math.log(sigma) + 0.5 * math.log(2 * math.pi) + math.log(survival))
            + float(logs.sum())
            + float(((logs - mu) ** 2).sum()) / (2 * sigma * sigma)
        )
        return value if np.isfinite(value) else 1e100

    start_mu = float(logs.mean())
    start_sigma = max(float(logs.std(ddof=1)) if n > 1 else 1.0, 1e-3)
    best = None
    for guess in ((start_mu, math.log(start_sigma)),
                  (start_mu - 2.0, math.log(2 * start_sigma)),
                  (log_xmin, math.log(start_sigma))):
        result = optimize.minimize(negative_loglik, guess, method="Nelder-Mead",
                                   options={"maxiter": 4000, "fatol": 1e-10})
        if best is None or result.fun < best.fun:
            best = result
    mu, log_sigma = best.x
    sigma = math.exp(log_sigma)
    z = (log_xmin - mu) / (sigma * math.sqrt(2.0))
    survival = 0.5 * special.erfc(z)
    pointwise = (
        -np.log(tail) - math.log(sigma) - 0.5 * math.log(2 * math.pi)
        - ((logs - mu) ** 2) / (2 * sigma * sigma) - math.log(survival)
    )
    return {"mu": float(mu), "sigma": float(sigma), "loglik": float(-best.fun),
            "n_tail": int(n), "pointwise": pointwise}


def fit_exponential_tail(values: np.ndarray, xmin: float) -> dict:
    """Exponentielle décalée en x_min : f(x) = λ exp(−λ(x−x_min))."""
    tail = values[values >= xmin]
    n = tail.size
    if n < 2:
        return {"lam": float("nan"), "loglik": float("nan"), "n_tail": int(n)}
    mean_excess = float((tail - xmin).mean())
    if mean_excess <= 0:
        return {"lam": float("nan"), "loglik": float("nan"), "n_tail": int(n)}
    lam = 1.0 / mean_excess
    pointwise = math.log(lam) - lam * (tail - xmin)
    return {"lam": float(lam), "loglik": float(pointwise.sum()), "n_tail": int(n),
            "pointwise": pointwise}


def vuong(pointwise_a: np.ndarray, pointwise_b: np.ndarray) -> dict:
    """Test de Vuong non emboîté, normalisé. z > 0 : A est favorisé.

    Le test compare deux modèles NON EMBOÎTÉS sur les mêmes points ; il n'est
    pas un test d'adéquation. Un |z| < 1,96 ne dit pas « les deux vont » : il
    dit que ces données ne les séparent pas — la distinction est celle que
    M4.2B a payée cher.
    """
    ratio = np.asarray(pointwise_a) - np.asarray(pointwise_b)
    n = ratio.size
    if n < 2:
        return {"z": float("nan"), "n": int(n)}
    sd = float(ratio.std(ddof=1))
    if sd <= 0:
        return {"z": float("nan"), "n": int(n), "mean_lr": float(ratio.mean())}
    return {
        "z": float(ratio.mean() * math.sqrt(n) / sd),
        "mean_lr": float(ratio.mean()),
        "loglik_ratio": float(ratio.sum()),
        "n": int(n),
    }


def _pointwise_powerlaw(values: np.ndarray, xmin: float, alpha: float) -> np.ndarray:
    tail = values[values >= xmin]
    return math.log(alpha - 1.0) - math.log(xmin) - alpha * np.log(tail / xmin)


def fit_composite(values: np.ndarray, floor: float = 0.0) -> dict:
    """Composite « corps exponentiel × queue de Pareto », trois paramètres.

        f(x) ∝ exp(−x/T)                     pour  floor ≤ x < b
        f(x) ∝ exp(−b/T) · (x/b)^(−α)        pour  x ≥ b

    Raccord en VALEUR au point de bascule b (pas en pente : ce serait imposer
    α = b/T et retirer un paramètre). C'est la famille que M4 fable retient
    sur le revenu d'intérêt, où elle bat la log-normale par AIC sur 5 cas
    sur 5 — mais sur une AUTRE institution de principal, d'où la nécessité
    de la réajuster ici plutôt que d'en hériter.
    """
    from scipy import optimize  # noqa: PLC0415

    sample = np.sort(values[values >= floor])
    n = sample.size
    if n < 50:
        return {"loglik": float("nan"), "n": int(n)}

    def negative_loglik(theta):
        log_T, log_span, log_alpha_minus = theta
        T = math.exp(log_T)
        b = floor + math.exp(log_span)
        alpha = 1.0 + math.exp(log_alpha_minus)
        if not (1e-6 < T < 1e9) or not (b > floor) or alpha <= 1.0001:
            return 1e100
        # Normalisation : ∫ corps + ∫ queue
        body = T * (math.exp(-floor / T) - math.exp(-b / T))
        tail = math.exp(-b / T) * b / (alpha - 1.0)
        total = body + tail
        if total <= 0 or not np.isfinite(total):
            return 1e100
        is_body = sample < b
        loglik = -n * math.log(total)
        loglik += float((-sample[is_body] / T).sum())
        upper = sample[~is_body]
        loglik += upper.size * (-b / T) - alpha * float(np.log(upper / b).sum())
        return -loglik if np.isfinite(loglik) else 1e100

    scale = max(float(sample.mean() - floor), 1e-6)
    best = None
    for guess in (
        (math.log(scale), math.log(max(np.quantile(sample, 0.9) - floor, 1e-6)), 0.0),
        (math.log(scale / 2), math.log(max(np.quantile(sample, 0.99) - floor, 1e-6)), 1.0),
        (math.log(scale * 2), math.log(max(np.quantile(sample, 0.75) - floor, 1e-6)), 1.5),
    ):
        result = optimize.minimize(negative_loglik, guess, method="Nelder-Mead",
                                   options={"maxiter": 6000, "fatol": 1e-10})
        if best is None or result.fun < best.fun:
            best = result
    log_T, log_span, log_alpha_minus = best.x
    b = floor + math.exp(log_span)
    return {
        "T": float(math.exp(log_T)),
        "x_b": float(b),
        "alpha": float(1.0 + math.exp(log_alpha_minus)),
        "loglik": float(-best.fun),
        "n": int(n),
        "n_above_b": int((sample >= b).sum()),
        "aic": float(2 * 3 - 2 * (-best.fun)),
    }


#: Conventions de M4B pour les tailles d'avalanches, reprises À L'IDENTIQUE
#: (`recherche/sensibilite_m4b/scripts/lib_metrics.py:26-27`) : seuil bas 2,
#: effectif minimal 100. Les reprendre est la condition pour que le α∞ ≈ 2,31
#: de M4B et celui de cette lignée soient comparables.
AVALANCHE_S_MIN = 2
AVALANCHE_N_MIN = 100


def fit_powerlaw_discrete(sizes: np.ndarray, s_min: int = AVALANCHE_S_MIN,
                          n_min: int = AVALANCHE_N_MIN) -> dict | None:
    """MLE de p(s) = s^(−α) / ζ(α, s_min) sur les entiers s ≥ s_min.

    RÉÉCRITURE DÉLIBÉRÉE de `lib_metrics.fit_powerlaw_discrete`, pas un
    import : le paquet `m4_4` ne dépend d'aucun autre dossier du dépôt, c'est
    la règle du fork. L'égalité numérique des deux implémentations est
    VÉRIFIÉE, pas supposée — `tests/test_tails.py` importe celle de M4B et
    compare les deux sur les mêmes tailles.

    Consigne héritée, toujours en vigueur (plan §2.3) : sur les tailles
    d'avalanches, n'ajuster QUE des lois de puissance. Aucune analyse de
    coupure ici, volontairement.
    """
    from scipy import optimize, special  # noqa: PLC0415

    tail = np.asarray(sizes, dtype=float)
    tail = tail[tail >= s_min]
    n = tail.size
    if n < n_min:
        return None
    log_sum = float(np.log(tail).sum())

    def negative_loglik(alpha: float) -> float:
        if alpha <= 1.0001:
            return 1e100
        zeta = float(special.zeta(alpha, s_min))
        if not np.isfinite(zeta) or zeta <= 0:
            return 1e100
        return n * math.log(zeta) + alpha * log_sum

    result = optimize.minimize_scalar(negative_loglik, bounds=(1.01, 8.0),
                                      method="bounded")
    alpha = float(result.x)
    step = 1e-4
    curvature = (
        negative_loglik(alpha + step) - 2 * negative_loglik(alpha)
        + negative_loglik(alpha - step)
    ) / step**2
    return {
        "alpha": alpha,
        "se": 1.0 / math.sqrt(curvature) if curvature > 0 else float("nan"),
        "n_tail": int(n),
        "s_min": int(s_min),
        "loglik": -float(result.fun),
    }


def fit_lognormal_full(values: np.ndarray, floor: float = 0.0) -> dict:
    """Log-normale tronquée en `floor` — la famille concurrente du composite."""
    fit = fit_lognormal_tail(values[values >= floor], max(floor, 1e-300))
    fit = {key: value for key, value in fit.items() if key != "pointwise"}
    fit["aic"] = float(2 * 2 - 2 * fit["loglik"]) if fit["loglik"] == fit["loglik"] else float("nan")
    return fit


def compare_tail_families(values: np.ndarray, xmin: float | None = None,
                          draws: int = 0, seed: int = 0) -> dict:
    """Ajuste les trois familles au MÊME seuil et les compare par Vuong.

    Le seuil est celui de la loi de puissance (estimé ou imposé) : comparer
    des ajustements faits à des seuils différents comparerait des échantillons
    différents, ce qui ne veut rien dire.
    """
    positive = values[values > 0]
    powerlaw = fit_tail(positive, xmin=xmin)
    payload: dict = {"powerlaw": powerlaw}
    if not math.isfinite(powerlaw["alpha"]) or powerlaw["n_tail"] < N_MIN_TAIL:
        payload["identifiable"] = False
        return payload
    payload["identifiable"] = True
    threshold = powerlaw["xmin"]

    lognormal = fit_lognormal_tail(positive, threshold)
    exponential = fit_exponential_tail(positive, threshold)
    pointwise_pl = _pointwise_powerlaw(positive, threshold, powerlaw["alpha"])
    payload["lognormal"] = {k: v for k, v in lognormal.items() if k != "pointwise"}
    payload["exponential"] = {k: v for k, v in exponential.items() if k != "pointwise"}
    if "pointwise" in lognormal:
        payload["vuong_pl_vs_ln"] = vuong(pointwise_pl, lognormal["pointwise"])
        # Drapeau, pas garde-fou : on ne borne pas σ (ce serait biaiser
        # l'ajustement), on SIGNALE que la log-normale ajustée a dégénéré en
        # loi de puissance et que la comparaison est donc vide de sens.
        payload["lognormal_degenerate"] = bool(
            lognormal["sigma"] > LOGNORMAL_DEGENERATE_SIGMA
        )
    if "pointwise" in exponential:
        payload["vuong_pl_vs_exp"] = vuong(pointwise_pl, exponential["pointwise"])
    payload["aic"] = {
        "powerlaw": float(2 * 1 - 2 * powerlaw["loglik"]),
        "lognormal": float(2 * 2 - 2 * lognormal["loglik"]),
        "exponential": float(2 * 1 - 2 * exponential["loglik"]),
    }
    if draws:
        payload["bootstrap"] = bootstrap_tail(positive, draws=draws, seed=seed)
    return payload
