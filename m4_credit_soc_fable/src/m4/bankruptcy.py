"""Faillites en cascade avec traçage des avalanches causales (phase 7).

Valeur nette : NW_i = K_i + créances_i - dettes_i — PAS de d0 (retiré du
code à la refonte 2026-07-14) : le plancher d'absorption est purement
contractuel, une entité sans dette ne peut pas mourir.

Critère d'entrée : défaut de service au pas courant, ou NW < -tol_nw.
À la faillite de i (règle par défaut, la plus simple — et la seule observée
produire de vraies cascades propagées, NOTES 2026-07-14) :
  1. contrats où i est EMPRUNTEUSE : annulés — perte sèche (stock + flux)
     chez les prêteuses ; arête causale i -> prêteuse de poids q.
  2. contrats où i est PRÊTEUSE : annulés (« cancel », gain pour les
     emprunteuses de i) ; variante M3 « transfer » : transférés aux
     créancières contractuelles de i au prorata (fragmente le carnet —
     c'est ce qui étouffait la contagion en M3).
  3. actifs résiduels K_i : détruits (« destroy ») ; variante M3
     « prorata » : répartis aux créancières vivantes (coussin qui amortit
     les pertes).

Avalanche causale : composante faiblement connexe du graphe des arêtes de
perte restreint aux faillies de la même résolution. Les racines (itération 1)
sont classées par cause : "liquidity" (défaut de service, NW >= -tol),
"insolvency" (NW < -tol sans défaut), "both". Les lots de racines
indépendantes ne sont PAS agrégés (correction de la mesure M2).
"""


def net_worth(pop, book, cfg, i):
    return pop.K[i] + book.claims[i] - book.debts[i]


def _fail_one(pop, book, cfg, i, ledger):
    """Faillite complète de l'entité i (supposée vivante).
    ledger : dict de la résolution courante —
      loss_edges : list [(source, victime, q)] ;
      claim_losses, recovered, destroyed : accumulateurs float."""
    # bilan au moment de la mort (avant toute annulation) — registre des morts
    ledger["dead_info"][i] = dict(
        K=pop.K[i], claims=book.claims[i], debts=book.debts[i],
        nw=pop.K[i] + book.claims[i] - book.debts[i],
    )
    # créancières contractuelles de i, AVANT toute annulation
    creditor_claims = {}
    for lid in list(book.by_borrower[i]):
        lender, _, q, r = book.loans[lid]
        creditor_claims[lender] = creditor_claims.get(lender, 0.0) + q
        book.remove(lid)
        ledger["claim_losses"] += q
        ledger["loss_edges"].append((i, lender, q))
    total_claims = sum(creditor_claims.values())

    # 2. contrats où i est prêteuse
    for lid in list(book.by_lender[i]):
        _, borrower, q, r = book.loans[lid]
        book.remove(lid)
        if cfg.fail_lender_loans == "cancel" or total_claims <= 0.0:
            continue  # créance annulée (gain pour l'emprunteuse)
        for creditor, qc in creditor_claims.items():
            share = q * qc / total_claims
            if share < cfg.q_min:
                continue  # part abandonnée
            if creditor == borrower or not pop.alive[creditor]:
                continue  # dette envers soi-même / créancière morte : annulée
            book.add(creditor, borrower, share, r)

    # 3. actifs résiduels
    res_K = max(pop.K[i], 0.0)
    living = {c: qc for c, qc in creditor_claims.items() if pop.alive[c]}
    living_total = sum(living.values())
    if living_total > 0.0 and cfg.fail_residual == "prorata":
        for creditor, qc in living.items():
            pop.K[creditor] += res_K * qc / living_total
        ledger["recovered"] += res_K
    else:
        ledger["destroyed"] += res_K
    pop.kill(i)


def resolve_bankruptcies(pop, book, cfg):
    """Résout défauts et insolvabilités jusqu'à stabilité (I9).

    Retourne (dead, ledger) où dead = ids dans l'ordre de traitement et
    ledger contient : loss_edges, claim_losses, recovered, destroyed,
    iters, roots {id: cause}, death_iter {id: itération},
    avalanches [{size, depth, n_roots, causes, members}]."""
    ledger = dict(loss_edges=[], claim_losses=0.0, recovered=0.0,
                  destroyed=0.0, iters=0, roots={},
                  death_iter={}, avalanches=[], dead_info={})
    dead = []
    queue = []
    for i in sorted(pop.alive_ids()):
        insolvent = net_worth(pop, book, cfg, i) < -cfg.tol_nw
        if pop.defaulted[i] and insolvent:
            ledger["roots"][i] = "both"
        elif pop.defaulted[i]:
            ledger["roots"][i] = "liquidity"
        elif insolvent:
            ledger["roots"][i] = "insolvency"
        else:
            continue
        queue.append(i)
    iters = 0
    max_iters = pop.n_alive + 1  # au moins une mort par itération, sinon bug
    while queue:
        iters += 1
        if iters > max_iters:
            raise RuntimeError("cascade sans point fixe — invariant I9 violé")
        for i in queue:
            if pop.alive[i]:
                _fail_one(pop, book, cfg, i, ledger)
                dead.append(i)
                ledger["death_iter"][i] = iters
        queue = sorted(
            i for i in pop.alive_ids()
            if net_worth(pop, book, cfg, i) < -cfg.tol_nw
        )
    ledger["iters"] = iters
    ledger["avalanches"] = _build_avalanches(ledger)
    return dead, ledger


def _build_avalanches(ledger):
    """Composantes faiblement connexes du graphe de pertes entre faillies."""
    death_iter = ledger["death_iter"]
    if not death_iter:
        return []
    parent = {i: i for i in death_iter}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for src, dst, _q in ledger["loss_edges"]:
        if src in parent and dst in parent:
            ra, rb = find(src), find(dst)
            if ra != rb:
                parent[rb] = ra
    comps = {}
    for i in death_iter:
        comps.setdefault(find(i), []).append(i)
    roots = ledger["roots"]
    out = []
    for members in comps.values():
        causes = sorted(roots[m] for m in members if m in roots)
        out.append(dict(
            size=len(members),
            depth=max(death_iter[m] for m in members),
            n_roots=sum(1 for m in members if m in roots),
            causes=causes,
            members=sorted(members),
        ))
    out.sort(key=lambda a: -a["size"])
    return out
