"""Boucle de simulation M4 fusionnée — séquence à 7 phases, ordre fixé.

1. naissances Poisson(lam) : dotation K0 ; si birth_loan, la part
   (1-birth_equity)*K0 est FINANCÉE par une prêteuse réelle (transfert de K
   + contrat nominal) tirée dans un échantillon de k candidates faisables ;
   repli en fonds propres (injection) si aucune faisable ;
2. choc multiplicatif sur K (production.apply_shock) ;
3. production P = alpha*sqrt(K), entièrement retenue : K += P ;
4. service des intérêts depuis K, simultané au prorata par emprunteuse ;
   insuffisance -> paiement partiel + défaut de service ;
5. dépréciation K <- (1-delta)K ;
6. marché du crédit (market.py) ;
7. faillites en cascade avec avalanches causales (bankruptcy.py) ;
8. mesure (séries, instantanés, réseau, journal d'avalanches).

Propriété de réduction R1' (remplace la R1 du fork L/K, qui reposait sur le
plancher d0 de M2) : avec credit=False, aucune entité n'a jamais de dette,
NW = K > 0 toujours, donc AUCUNE mort — testé, avec l'identité de
trajectoire K_t = (1-delta)*(K*e^eta + alpha*sqrt(K*e^eta)) pas à pas.
"""
import math

import numpy as np

from .bankruptcy import net_worth, resolve_bankruptcies
from .contracts import LoanBook
from .entities import Population
from .market import pair_terms, run_market
from .production import apply_shock, apply_production, apply_depreciation


class Simulation:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.pop = Population()
        self.book = LoanBook(merge_pairs=True)
        self.t = 0
        self.series = []       # une ligne dict par pas
        self.avalanche_log = []  # une ligne dict par avalanche
        self.status = "ok"     # "ok" | "extinction" | "explosion"
        self.equity_births = 0  # naissances en fonds propres (birth_loan)
        # journal optionnel des arêtes de perte datées (t, source, victime, q)
        # — pour l'analyse causale inter-pas des avalanches ; désactivé par
        # défaut (mémoire) ; activer AVANT run().
        self.log_loss_edges = False
        self.loss_edge_log = []
        self.death_log = []    # (t, id) si log_loss_edges
        # journalisation enrichie optionnelle (richlog.py) — attacher AVANT
        # run() ; aucun effet sur la dynamique (RNG isolés, lecture seule)
        self.dist_log = None   # richlog.DistLog
        self.watcher = None    # richlog.Watcher
        self.log_death_registry = False
        self.death_registry = []  # dicts t/id/age/cause/K/claims/debts/nw/iter

    # ------------------------------------------------------------------ étape
    def _born(self, n):
        """Naissances du pas. Retourne l'injection réelle (fonds propres)."""
        cfg, pop, book, rng = self.cfg, self.pop, self.book, self.rng
        draw_sector = cfg.shock_rho_sector > 0.0
        injected = 0.0
        for _ in range(n):
            sector = int(rng.integers(0, cfg.n_sectors)) if draw_sector else 0
            i = pop.born(cfg.K0, self.t, sector)
            if not cfg.birth_loan:
                injected += cfg.K0
                continue
            q_loan = cfg.K0 * (1.0 - cfg.birth_equity)
            pool = [j for j in pop.alive_ids()
                    if j != i and not pop.defaulted[j]]
            feasible = []
            if pool:
                # échantillon de min(k, |pool|) candidates — au démarrage le
                # pool est plus petit que k, on ne bloque pas les naissances
                idx = rng.permutation(len(pool))[:cfg.k]
                for j in idx:
                    l = pool[int(j)]
                    r, k_star = pair_terms(cfg, pop.K[l], cfg.K0)
                    if pop.K[l] - k_star >= q_loan:
                        feasible.append((l, r))
            if not feasible:
                self.equity_births += 1
                injected += cfg.K0
                continue
            if cfg.birth_lender == "rich":
                l, r = max(feasible, key=lambda t_: pop.K[t_[0]])
            else:
                l, r = feasible[int(rng.integers(0, len(feasible)))]
            # la part financée est un transfert réel ; seul l'apport en
            # fonds propres est une injection ex nihilo
            pop.K[l] -= q_loan
            book.add(l, i, q_loan, r)
            injected += cfg.K0 - q_loan
        return injected

    def step(self):
        cfg, pop, book, rng = self.cfg, self.pop, self.book, self.rng

        self.t += 1

        # 1. naissances (ablation I : cohorte unique n_init au premier pas)
        if cfg.n_init > 0:
            births = cfg.n_init if self.t == 1 else 0
        else:
            births = int(rng.poisson(cfg.lam))
        alive_pre = pop.alive_ids()
        for i in alive_pre:
            pop.int_in[i] = 0.0
            pop.int_out[i] = 0.0
            pop.prod[i] = 0.0
            pop.defaulted[i] = False
        injected = self._born(births)

        alive = pop.alive_ids()

        # 2. choc multiplicatif
        pre_shock = sum(pop.K[i] for i in alive)
        apply_shock(pop, cfg, rng, alive)
        shock_gain = sum(pop.K[i] for i in alive) - pre_shock

        # 3. production (entièrement retenue)
        prod_tot = apply_production(pop, cfg, alive)

        # 4. service des intérêts depuis K (simultané, prorata par emprunteuse)
        n_defaults = 0
        interest_paid = 0.0
        for b in list(book.by_borrower.keys()):
            lids = book.by_borrower[b]
            if not lids:
                continue
            due = book.due[b]
            kb = pop.K[b]
            if kb >= due:
                ratio = 1.0
                pop.K[b] = kb - due
            else:
                ratio = kb / due if due > 0.0 else 0.0
                pop.K[b] = 0.0
                pop.defaulted[b] = True
                n_defaults += 1
            if ratio > 0.0:
                for lid in lids:
                    lender, _, q, r = book.loans[lid]
                    pay = ratio * r * q
                    pop.K[lender] += pay
                    pop.int_in[lender] += pay
                    pop.int_out[b] += pay
                    interest_paid += pay

        # 5. dépréciation réelle (nominal inchangé, I6)
        depreciated = apply_depreciation(pop, cfg, alive)

        # 6. marché du crédit
        n_new_loans, loan_volume = run_market(pop, book, cfg, rng)

        # 7. faillites en cascade
        dead, ledger = resolve_bankruptcies(pop, book, cfg)
        roots = ledger["roots"]
        if self.log_loss_edges:
            for src, dst, q in ledger["loss_edges"]:
                self.loss_edge_log.append((self.t, src, dst, q))
            for i in dead:
                self.death_log.append((self.t, i))
        if self.log_death_registry:
            for i in dead:
                info = ledger["dead_info"][i]
                self.death_registry.append(dict(
                    t=self.t, id=i, age=self.t - pop.birth[i],
                    cause=roots.get(i, "cascade"),
                    death_iter=ledger["death_iter"][i], **info,
                ))
        for av in ledger["avalanches"]:
            self.avalanche_log.append(dict(
                t=self.t, size=av["size"], depth=av["depth"],
                n_roots=av["n_roots"], causes=",".join(av["causes"]),
            ))

        # 8. série du pas
        alive = pop.alive_ids()
        K_tot = sum(pop.K[i] for i in alive)
        nw_tot = sum(net_worth(pop, book, cfg, i) for i in alive)
        avs = ledger["avalanches"]
        self.series.append(dict(
            t=self.t, births=births, deaths=len(dead), pop=pop.n_alive,
            K_tot=K_tot, nw_tot=nw_tot, prod_tot=prod_tot,
            n_loans=len(book), new_loans=n_new_loans, loan_volume=loan_volume,
            interest_paid=interest_paid, defaults=n_defaults,
            roots_liquidity=sum(1 for c in roots.values() if c == "liquidity"),
            roots_insolvency=sum(1 for c in roots.values() if c == "insolvency"),
            roots_both=sum(1 for c in roots.values() if c == "both"),
            cascade_iters=ledger["iters"],
            n_avalanches=len(avs),
            max_avalanche=max((a["size"] for a in avs), default=0),
            claim_losses=ledger["claim_losses"],
            recovered=ledger["recovered"], destroyed=ledger["destroyed"],
            injected=injected, depreciated=depreciated,
            shock_gain=shock_gain,
        ))

        if self.dist_log is not None:
            self.dist_log.record(self)
        if self.watcher is not None:
            self.watcher.record(self)

        if pop.n_alive == 0:
            self.status = "extinction"
        elif pop.n_alive > cfg.pop_max:
            self.status = "explosion"
        return self.status

    # -------------------------------------------------------------- exécution
    def run(self, T=None, snapshot_times=(), on_snapshot=None, log_every=0):
        """Exécute jusqu'à T pas (défaut cfg.T). on_snapshot(t, snap, net) est
        appelé aux pas listés avec l'instantané individus + réseau."""
        T = T if T is not None else self.cfg.T
        snap_set = set(snapshot_times)
        while self.t < T and self.status == "ok":
            self.step()
            if self.t in snap_set and on_snapshot is not None:
                on_snapshot(self.t, self.snapshot(), self.network_snapshot())
            if log_every and self.t % log_every == 0:
                s = self.series[-1]
                print(f"t={s['t']:5d} pop={s['pop']:6d} loans={s['n_loans']:6d} "
                      f"deaths={s['deaths']:3d} K={s['K_tot']:.3e}", flush=True)
        return self.status

    # -------------------------------------------------------------- snapshot
    def snapshot(self):
        """Vecteurs alignés des vivantes (fin de pas)."""
        pop, book, cfg = self.pop, self.book, self.cfg
        ids = pop.alive_ids()
        n = len(ids)
        out = {
            "id": np.array(ids, dtype=np.int64),
            "K": np.empty(n),
            "claims": np.empty(n), "debts": np.empty(n), "nw": np.empty(n),
            "prod": np.empty(n), "int_in": np.empty(n), "int_out": np.empty(n),
            "income": np.empty(n), "income_net": np.empty(n),
            "age": np.empty(n, dtype=np.int64),
            "deg_out": np.empty(n, dtype=np.int64),
            "deg_in": np.empty(n, dtype=np.int64),
        }
        # accès en .get uniquement : book.* sont des defaultdict, un accès
        # par [] insérerait des clés vides et changerait l'ordre d'itération
        # du service des intérêts — violation de I8 (bug M3 trouvé par les tests)
        for j, i in enumerate(ids):
            out["K"][j] = pop.K[i]
            claims = book.claims.get(i, 0.0)
            debts = book.debts.get(i, 0.0)
            out["claims"][j] = claims
            out["debts"][j] = debts
            out["nw"][j] = pop.K[i] + claims - debts
            out["prod"][j] = pop.prod[i]
            out["int_in"][j] = pop.int_in[i]
            out["int_out"][j] = pop.int_out[i]
            out["income"][j] = pop.prod[i] + pop.int_in[i]
            out["income_net"][j] = out["income"][j] - pop.int_out[i]
            out["age"][j] = self.t - pop.birth[i]
            out["deg_out"][j] = len(book.by_lender.get(i, ()))
            out["deg_in"][j] = len(book.by_borrower.get(i, ()))
        return out

    def network_snapshot(self):
        """Liste d'arêtes du réseau de crédit (fin de pas)."""
        book = self.book
        n = len(book.loans)
        out = {
            "lender": np.empty(n, dtype=np.int64),
            "borrower": np.empty(n, dtype=np.int64),
            "q": np.empty(n), "r": np.empty(n),
        }
        for j, (lender, borrower, q, r) in enumerate(book.loans.values()):
            out["lender"][j] = lender
            out["borrower"][j] = borrower
            out["q"][j] = q
            out["r"][j] = r
        return out
