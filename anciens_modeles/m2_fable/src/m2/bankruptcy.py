"""Faillites en cascade (phase 7 de la séquence M2, §2.2 du rapport).

Critère : défaut de service au pas courant, ou NW < -tol_nw. À la faillite
de i (conventions C5-C7 de la spécification) :
  1. contrats où i est EMPRUNTEUSE : annulés — perte sèche des prêteurs ;
  2. contrats où i est PRÊTEUSE : transférés aux créanciers contractuels de i
     au prorata de leurs créances ('transfer', règle M2) ou annulés ('cancel',
     règle du prototype E7c — ablation) ; part allant à l'emprunteur du
     contrat lui-même : annulée (dette envers soi-même) ; parts < q_min ou
     vers un créancier mort : abandonnées ;
  3. capital résiduel w_i : réparti aux créanciers contractuels vivants au
     prorata ('prorata') ou détruit ('destroy') ; sans créancier : détruit ;
  4. d0 éteinte (détenue par personne).
Itération jusqu'à ce qu'aucune vivante n'ait NW < -tol_nw (I8).
"""


def net_worth(pop, book, cfg, i):
    return pop.w[i] + book.claims[i] - book.debts[i] - cfg.d0


def _fail_one(pop, book, cfg, i):
    """Faillite complète de l'entité i (supposée vivante)."""
    # créanciers contractuels de i, AVANT toute annulation
    creditor_claims = {}
    for lid in list(book.by_borrower[i]):
        lender, _, q, _ = book.loans[lid]
        creditor_claims[lender] = creditor_claims.get(lender, 0.0) + q
        book.remove(lid)  # 1. dette contractuelle annulée : perte sèche du prêteur
    total_claims = sum(creditor_claims.values())

    # 2. contrats où i est prêteuse
    for lid in list(book.by_lender[i]):
        _, borrower, q, r = book.loans[lid]
        book.remove(lid)
        if cfg.fail_lender_loans == "cancel" or total_claims <= 0.0:
            continue  # créance annulée (gain pour l'emprunteur)
        for creditor, qc in creditor_claims.items():
            share = q * qc / total_claims
            if share < cfg.q_min:
                continue  # part abandonnée
            if creditor == borrower or not pop.alive[creditor]:
                continue  # dette envers soi-même / créancier mort : annulée
            book.add(creditor, borrower, share, r)

    # 3. capital résiduel
    residual = max(pop.w[i], 0.0)
    if residual > 0.0 and total_claims > 0.0 and cfg.fail_residual == "prorata":
        living = {c: qc for c, qc in creditor_claims.items() if pop.alive[c]}
        living_total = sum(living.values())
        if living_total > 0.0:
            for creditor, qc in living.items():
                pop.w[creditor] += residual * qc / living_total
    # sinon : résiduel détruit ; d0 éteinte dans tous les cas (4.)
    pop.kill(i)


def resolve_bankruptcies(pop, book, cfg):
    """Résout défauts et insolvabilités jusqu'à stabilité.
    Retourne (ids morts dans l'ordre de traitement, nombre d'itérations)."""
    dead = []
    queue = sorted(
        i for i in pop.alive_ids()
        if pop.defaulted[i] or net_worth(pop, book, cfg, i) < -cfg.tol_nw
    )
    iters = 0
    max_iters = pop.n_alive + 1  # au moins une mort par itération, sinon bug
    while queue:
        iters += 1
        if iters > max_iters:
            raise RuntimeError("cascade sans point fixe — invariant violé")
        for i in queue:
            if pop.alive[i]:
                _fail_one(pop, book, cfg, i)
                dead.append(i)
        queue = sorted(
            i for i in pop.alive_ids()
            if net_worth(pop, book, cfg, i) < -cfg.tol_nw
        )
    return dead, iters
