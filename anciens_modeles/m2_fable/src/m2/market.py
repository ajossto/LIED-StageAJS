"""Marché du crédit local (phase 6 de la séquence M2, §2.2 du rapport).

floor(N/k) rounds ; par round : échantillon uniforme sans remise de k entités
vivantes non défaillantes (C3), prêteur = w max, emprunteur = w min, taux
moyenne géométrique des taux marginaux (variante 'arith' disponible), cible
commune w*(rho) avec rho = r + delta, volume q = min(demande, offre),
transfert conservatif du principal (I4) et création du contrat nominal.
"""
import math


def _sample_without_replacement(rng, n, k):
    """k indices distincts uniformes dans [0, n). Rejet pour k << n (O(k)),
    permutation partielle sinon — distribution identique dans les deux cas."""
    if k * 8 >= n:
        return rng.permutation(n)[:k]
    while True:
        idx = rng.integers(0, n, size=k)
        if len(set(idx.tolist())) == k:
            return idx


def run_market(pop, book, cfg, rng):
    """Exécute la phase de marché. Retourne (nombre de prêts créés, volume)."""
    if not cfg.credit:
        return 0, 0.0
    pool = [i for i in pop.alive_ids() if not pop.defaulted[i]]
    n = len(pool)
    n_rounds = n // cfg.k
    n_new, volume = 0, 0.0
    alpha, delta = cfg.alpha, cfg.delta
    w = pop.w
    for _ in range(n_rounds):
        idx = _sample_without_replacement(rng, n, cfg.k)
        sample = [pool[j] for j in idx]
        lender = max(sample, key=lambda i: w[i])
        borrower = min(sample, key=lambda i: w[i])
        # C4 : gain à l'échange strict ; garde numérique sur w ~ 0
        if lender == borrower or w[lender] <= w[borrower]:
            continue
        r_l = alpha / (2.0 * math.sqrt(max(w[lender], 1e-9)))
        r_b = alpha / (2.0 * math.sqrt(max(w[borrower], 1e-9)))
        if cfg.rate_rule == "geom":
            r = math.sqrt(r_l * r_b)
        else:
            r = 0.5 * (r_l + r_b)
        rho = r + delta
        w_star = (alpha / (2.0 * rho)) ** 2
        q_dem = max(0.0, w_star - w[borrower])
        q_off = max(0.0, w[lender] - w_star)
        q = min(q_dem, q_off)
        if q < cfg.q_min:
            continue
        w[lender] -= q
        w[borrower] += q
        book.add(lender, borrower, q, r)
        n_new += 1
        volume += q
    return n_new, volume
