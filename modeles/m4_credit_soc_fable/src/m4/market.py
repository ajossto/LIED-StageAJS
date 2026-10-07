"""Marché du crédit local (phase 6). Règle symétrique de la note de
conception pré-M2 (§2.2) : « viser K*(rho) ; prêter l'excédent, emprunter le
manque » — personne n'est prêteuse ou emprunteuse par nature.

floor(N_pool / rounds_div) rounds ; par round : échantillon uniforme sans
remise de k entités vivantes non défaillantes ; prêteuse = K maximal,
emprunteuse = K minimal ; taux r = sqrt(r_l * r_b) (moyenne géométrique,
constitutive — leçon M2 : la moyenne arithmétique éteint le marché) ;
rho = r (objectif revenu, baseline) ou r + delta (objectif richesse) ;
cible commune K*(rho) = (alpha/(2 rho))^2 ;
q = min(K_l - K*, K* - K_b) ; transfert conservatif K -> K + contrat
nominal (q, r) perpétuel. Avec l'objectif revenu, K*(r) = sqrt(K_l * K_b)
(identité analytique, rapport 07 de M3).
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


def pair_terms(cfg, K_l, K_b):
    """(r, k_star) du couple : taux géométrique et cible commune K*(rho)."""
    r_l = cfg.alpha / (2.0 * math.sqrt(max(K_l, 1e-9)))
    r_b = cfg.alpha / (2.0 * math.sqrt(max(K_b, 1e-9)))
    r = math.sqrt(r_l * r_b)
    rho = r + cfg.delta if cfg.objective == "wealth" else r
    k_star = (cfg.alpha / (2.0 * rho)) ** 2
    return r, k_star


def run_market(pop, book, cfg, rng):
    """Exécute la phase de marché. Retourne (prêts créés, volume)."""
    if not cfg.credit:
        return 0, 0.0
    pool = [i for i in pop.alive_ids() if not pop.defaulted[i]]
    n = len(pool)
    n_rounds = n // cfg.effective_rounds_div
    n_new, volume = 0, 0.0
    K = pop.K
    for _ in range(n_rounds):
        idx = _sample_without_replacement(rng, n, cfg.k)
        sample = [pool[j] for j in idx]
        lender = max(sample, key=lambda i: K[i])
        borrower = min(sample, key=lambda i: K[i])
        if lender == borrower or K[lender] <= K[borrower]:
            continue  # gain à l'échange requis
        r, k_star = pair_terms(cfg, K[lender], K[borrower])
        q = min(K[lender] - k_star, max(0.0, k_star - K[borrower]))
        if q < cfg.q_min:
            continue
        K[lender] -= q
        K[borrower] += q
        book.add(lender, borrower, q, r)
        n_new += 1
        volume += q
    return n_new, volume
