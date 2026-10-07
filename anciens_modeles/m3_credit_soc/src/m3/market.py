"""Marché du crédit local (phase 6 de la séquence M3, rapport 02 §3).

floor(N_pool/k) rounds ; par round : échantillon uniforme sans remise de k
entités vivantes non défaillantes. Sélection assortative (baseline) :
prêteuse = liquidité prêtable A = max(0, L - beta_L * service dû) maximale,
emprunteuse = K minimal (rendement marginal alpha/(2 sqrt K) maximal).
Ablation F : prêteuse et emprunteuse tirées au hasard dans l'échantillon,
mêmes conditions de faisabilité, même formule de volume.

Le prêt transfère q de la liquidité de la prêteuse vers le CAPITAL de
l'emprunteuse (crédit productif, baseline) ou vers sa liquidité (ablation C).
Transfert conservatif (I4) + contrat nominal (q, r) perpétuel.
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


def lendable(pop, book, cfg, i):
    """Liquidité prêtable : L moins le tampon de service beta_L * (r*q dus)."""
    return max(0.0, pop.L[i] - cfg.beta_L * book.due[i])


def run_market(pop, book, cfg, rng):
    """Exécute la phase de marché. Retourne (prêts créés, volume)."""
    if not cfg.credit:
        return 0, 0.0
    pool = [i for i in pop.alive_ids() if not pop.defaulted[i]]
    n = len(pool)
    n_rounds = n // cfg.k
    n_new, volume = 0, 0.0
    alpha, delta = cfg.alpha, cfg.delta
    K = pop.K
    for _ in range(n_rounds):
        idx = _sample_without_replacement(rng, n, cfg.k)
        sample = [pool[j] for j in idx]
        if cfg.market_selection == "assortative":
            lender = max(sample, key=lambda i: lendable(pop, book, cfg, i))
            borrower = min(sample, key=lambda i: K[i])
        elif cfg.market_selection == "random_lender":
            # F'' exploratoire : emprunteuse assortative, prêteuse uniforme
            # parmi les candidates faisables — casse les hubs créanciers en
            # gardant un volume comparable à la baseline.
            borrower = min(sample, key=lambda i: K[i])
            cands = [i for i in sample
                     if i != borrower and K[i] > K[borrower]
                     and lendable(pop, book, cfg, i) >= cfg.q_min]
            if not cands:
                continue
            lender = cands[int(rng.integers(0, len(cands)))]
        else:  # "random" (ablation F) : topologie aléatoire, règles identiques
            pick = rng.permutation(len(sample))[:2]
            lender, borrower = sample[int(pick[0])], sample[int(pick[1])]
        if lender == borrower or K[lender] <= K[borrower]:
            continue  # gain à l'échange requis (C4)
        a_l = lendable(pop, book, cfg, lender)
        if a_l < cfg.q_min:
            continue
        r_l = alpha / (2.0 * math.sqrt(max(K[lender], 1e-9)))
        r_b = alpha / (2.0 * math.sqrt(max(K[borrower], 1e-9)))
        if cfg.rate_rule == "geom":
            r = math.sqrt(r_l * r_b)
        else:
            r = 0.5 * (r_l + r_b)
        # coût effectif : r+delta (objectif richesse, baseline M3) ou r seul
        # (objectif revenu, X1 — la dépréciation n'ampute pas le revenu)
        rho = r + delta if cfg.objective == "wealth" else r
        k_star = (alpha / (2.0 * rho)) ** 2
        q = min(a_l, max(0.0, k_star - K[borrower]))
        if q < cfg.q_min:
            continue
        pop.L[lender] -= q
        if cfg.loan_target == "K":
            pop.K[borrower] += q      # crédit productif (baseline)
        else:
            pop.L[borrower] += q      # crédit comptable seul (ablation C)
        book.add(lender, borrower, q, r)
        n_new += 1
        volume += q
    return n_new, volume
