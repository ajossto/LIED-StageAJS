"""Phases réelles d'un pas M4 : choc multiplicatif, production, dépréciation.

Convention de drift : chaque composante du choc est centrée à -var/2, de sorte
que E[exp(eta)] = 1 composante par composante et au total (C1 de M2, étendue
aux chocs corrélés).

Refonte fusionnée : la production est entièrement retenue en K (plus de
partage s / liquidité L / consommation c — voir config.py).
"""
import math


def apply_shock(pop, cfg, rng, alive):
    """Phase 2 : K <- K * exp(eta), sur le capital réel seulement.

    eta = eta_macro + eta_secteur(i) + xi_i, variances
    (rho_m, rho_s, 1-rho_m-rho_s) * sigma^2. Baseline M4 : rho_m = rho_s = 0
    (un seul appel normal(size=n_alive), même séquence RNG que M2).
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
    """Phase 3 : P = alpha*sqrt(K) ; K += P (production entièrement retenue).
    Retourne la production totale du pas."""
    total = 0.0
    for i in alive:
        p = cfg.alpha * math.sqrt(pop.K[i])
        pop.prod[i] = p
        pop.K[i] += p
        total += p
    return total


def apply_depreciation(pop, cfg, alive):
    """Phase 5 : K <- (1-delta)K (réel). Dettes et créances nominales :
    inchangées (asymétrie nominal/réel constitutive). Retourne le capital
    déprécié pour le bilan I4."""
    f_k = 1.0 - cfg.delta
    depreciated = 0.0
    for i in alive:
        k_i = pop.K[i]
        depreciated += k_i * cfg.delta
        k_i *= f_k
        pop.K[i] = k_i if k_i > cfg.w_clamp else 0.0
    return depreciated
