"""Phases réelles d'un pas M3 : choc multiplicatif, production/partage,
dépréciation et consommation (rapport 02 §3, phases 2, 3 et 5).

Convention de drift : chaque composante du choc est centrée à -var/2, de sorte
que E[exp(eta)] = 1 composante par composante et au total (C1 de M2, étendue
aux chocs corrélés de l'ablation G).
"""
import math


def apply_shock(pop, cfg, rng, alive):
    """Phase 2 : K <- K * exp(eta), sur le capital réel seulement.

    eta = eta_macro + eta_secteur(i) + xi_i, variances
    (rho_m, rho_s, 1-rho_m-rho_s) * sigma^2. Baseline : rho_m = rho_s = 0,
    séquence RNG identique à M2 (un seul appel normal(size=n_alive)) — requis
    par la propriété de réduction R1.
    """
    if cfg.sigma <= 0 or not alive:
        return
    var = cfg.sigma ** 2
    var_m = cfg.shock_rho_macro * var
    var_s = cfg.shock_rho_sector * var
    var_i = var - var_m - var_s
    if var_m == 0.0 and var_s == 0.0:
        eta = rng.normal(-0.5 * var, cfg.sigma, size=len(alive))
        for j, i in enumerate(alive):
            pop.K[i] *= math.exp(eta[j])
        return
    eta_m = rng.normal(-0.5 * var_m, math.sqrt(var_m)) if var_m > 0 else 0.0
    if var_s > 0:
        eta_s = rng.normal(-0.5 * var_s, math.sqrt(var_s), size=cfg.n_sectors)
    else:
        eta_s = None
    xi = (rng.normal(-0.5 * var_i, math.sqrt(var_i), size=len(alive))
          if var_i > 0 else [0.0] * len(alive))
    for j, i in enumerate(alive):
        e = eta_m + xi[j]
        if eta_s is not None:
            e += eta_s[pop.sector[i]]
        pop.K[i] *= math.exp(e)


def apply_production(pop, cfg, alive):
    """Phase 3 : P = alpha*sqrt(K) ; K += s*P (retenu) ; L += (1-s)*P (liquide).
    Retourne la production totale du pas. P est enregistrée entière comme
    revenu productif, part retenue comprise (rapport 02 §2)."""
    total = 0.0
    s = cfg.s
    one_minus_s = 1.0 - cfg.s
    for i in alive:
        p = cfg.alpha * math.sqrt(pop.K[i])
        pop.prod[i] = p
        pop.K[i] += s * p
        pop.L[i] += one_minus_s * p
        total += p
    return total


def apply_depreciation_consumption(pop, cfg, alive):
    """Phase 5 : K <- (1-delta)K (réel), L <- (1-c)L (consommation détruite).
    Dettes, créances et d0 nominales : inchangées (asymétrie nominal/réel).
    Retourne (capital déprécié, liquidité consommée) pour le bilan I4."""
    f_k = 1.0 - cfg.delta
    f_l = 1.0 - cfg.c
    depreciated = 0.0
    consumed = 0.0
    for i in alive:
        k_i = pop.K[i]
        depreciated += k_i * cfg.delta
        k_i *= f_k
        pop.K[i] = k_i if k_i > cfg.w_clamp else 0.0
        l_i = pop.L[i]
        consumed += l_i * cfg.c
        l_i *= f_l
        pop.L[i] = l_i if l_i > cfg.w_clamp else 0.0
    return depreciated, consumed
