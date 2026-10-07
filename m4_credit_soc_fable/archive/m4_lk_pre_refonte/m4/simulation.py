"""Boucle de simulation M3 — séquence à 8 phases, ordre fixé (rapport 02 §3).

1. naissances Poisson(lam) : L0, K0, dette d'amorçage d0, N(0)=0 (ou cohorte
   n_init à t=1 pour l'ablation I) ;
2. choc multiplicatif sur K seul (production.apply_shock) ;
3. production P = alpha*sqrt(K) : K += s*P, L += (1-s)*P ;
4. service des intérêts depuis L seulement, simultané au prorata par
   emprunteuse ; insuffisance -> paiement partiel + défaut de liquidité ;
5. dépréciation K <- (1-delta)K et consommation L <- (1-c)L ;
6. marché du crédit (market.py) ;
7. faillites en cascade avec avalanches causales (bankruptcy.py) ;
8. mesure (séries, instantanés, réseau, journal d'avalanches).

Propriété de réduction R1 : s=1, c=0, L0=0, credit=False reproduit
exactement M2 (m2_fable, credit=False) à seed égale — même séquence RNG
(poisson puis normal(size=n_alive)), mêmes opérations flottantes sur K.
"""
import math

import numpy as np

from .bankruptcy import net_worth, resolve_bankruptcies
from .contracts import LoanBook
from .entities import Population
from .market import run_market
from .production import apply_shock, apply_production, apply_depreciation_consumption


class Simulation:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.pop = Population()
        self.book = LoanBook(merge_pairs=cfg.merge_pairs)
        self.t = 0
        self.series = []       # une ligne dict par pas
        self.avalanche_log = []  # une ligne dict par avalanche
        self.status = "ok"     # "ok" | "extinction" | "explosion"

    # ------------------------------------------------------------------ étape
    def _born(self, n):
        cfg, pop, rng = self.cfg, self.pop, self.rng
        draw_sector = cfg.shock_rho_sector > 0.0
        for _ in range(n):
            sector = int(rng.integers(0, cfg.n_sectors)) if draw_sector else 0
            pop.born(cfg.L0, cfg.K0, self.t, sector)

    def step(self):
        cfg, pop, book, rng = self.cfg, self.pop, self.book, self.rng
        self.t += 1

        # 1. naissances (ablation I : cohorte unique n_init au premier pas)
        if cfg.n_init > 0:
            births = cfg.n_init if self.t == 1 else 0
        else:
            births = int(rng.poisson(cfg.lam))
        self._born(births)

        alive = pop.alive_ids()
        for i in alive:
            pop.int_in[i] = 0.0
            pop.int_out[i] = 0.0
            pop.prod[i] = 0.0
            pop.defaulted[i] = False

        real_before = sum(pop.L[i] + pop.K[i] for i in alive)

        # 2. choc multiplicatif (capital réel seulement)
        apply_shock(pop, cfg, rng, alive)
        shock_gain = sum(pop.L[i] + pop.K[i] for i in alive) - real_before

        # 3. production et partage
        prod_tot = apply_production(pop, cfg, alive)

        # 4. service des intérêts (simultané au prorata par emprunteuse)
        injected = 0.0
        if cfg.flow_loss == "annuity":
            # rente fantôme (ablation E) versée avant le service
            for i in alive:
                a = pop.annuity[i]
                if a > 0.0:
                    pop.L[i] += a
                    pop.int_in[i] += a
                    injected += a
        n_defaults = 0
        interest_paid = 0.0
        for b in list(book.by_borrower.keys()):
            lids = book.by_borrower[b]
            if not lids:
                continue
            due = book.due[b]
            lb = pop.L[b]
            if lb >= due:
                ratio = 1.0
                pop.L[b] = lb - due
            else:
                ratio = lb / due if due > 0.0 else 0.0
                pop.L[b] = 0.0
                pop.defaulted[b] = True
                n_defaults += 1
            if ratio > 0.0:
                for lid in lids:
                    lender, _, q, r = book.loans[lid]
                    pay = ratio * r * q
                    pop.L[lender] += pay
                    pop.int_in[lender] += pay
                    pop.int_out[b] += pay
                    interest_paid += pay

        # 5. dépréciation réelle et consommation (nominal inchangé, I6)
        depreciated, consumed = apply_depreciation_consumption(pop, cfg, alive)

        # 6. marché du crédit
        n_new_loans, loan_volume = run_market(pop, book, cfg, rng)

        # 7. faillites en cascade — avec repérage du top décile de NW
        top_threshold = None
        pre_nw = {}
        if pop.n_alive >= 10:
            ids_now = pop.alive_ids()
            nws = [net_worth(pop, book, cfg, i) for i in ids_now]
            top_threshold = float(np.quantile(nws, 0.9))
            pre_nw = dict(zip(ids_now, nws))
        dead, ledger = resolve_bankruptcies(pop, book, cfg)
        injected += ledger["injected"]
        top_deaths = sum(
            1 for i in dead
            if top_threshold is not None and pre_nw.get(i, -1e18) >= top_threshold
        )
        roots = ledger["roots"]
        for av in ledger["avalanches"]:
            self.avalanche_log.append(dict(
                t=self.t, size=av["size"], depth=av["depth"],
                n_roots=av["n_roots"], causes=",".join(av["causes"]),
            ))

        # 8. série du pas
        alive = pop.alive_ids()
        L_tot = sum(pop.L[i] for i in alive)
        K_tot = sum(pop.K[i] for i in alive)
        nw_tot = sum(net_worth(pop, book, cfg, i) for i in alive)
        avs = ledger["avalanches"]
        self.series.append(dict(
            t=self.t, births=births, deaths=len(dead), pop=pop.n_alive,
            L_tot=L_tot, K_tot=K_tot, nw_tot=nw_tot, prod_tot=prod_tot,
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
            injected=injected, depreciated=depreciated, consumed=consumed,
            shock_gain=shock_gain, top_decile_deaths=top_deaths,
        ))

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
                      f"deaths={s['deaths']:3d} L={s['L_tot']:.3e} "
                      f"K={s['K_tot']:.3e}", flush=True)
        return self.status

    # -------------------------------------------------------------- snapshot
    def snapshot(self):
        """Vecteurs alignés des vivantes (fin de pas)."""
        pop, book, cfg = self.pop, self.book, self.cfg
        ids = pop.alive_ids()
        n = len(ids)
        out = {
            "id": np.array(ids, dtype=np.int64),
            "L": np.empty(n), "K": np.empty(n),
            "claims": np.empty(n), "debts": np.empty(n), "nw": np.empty(n),
            "prod": np.empty(n), "int_in": np.empty(n), "int_out": np.empty(n),
            "income": np.empty(n), "income_net": np.empty(n),
            "age": np.empty(n, dtype=np.int64),
            "deg_out": np.empty(n, dtype=np.int64),
            "deg_in": np.empty(n, dtype=np.int64),
        }
        # accès en .get uniquement : book.* sont des defaultdict, un accès
        # par [] insérerait des clés vides et changerait l'ordre d'itération
        # du service des intérêts — violation de I8 (bug trouvé par les tests)
        for j, i in enumerate(ids):
            out["L"][j] = pop.L[i]
            out["K"][j] = pop.K[i]
            claims = book.claims.get(i, 0.0)
            debts = book.debts.get(i, 0.0)
            out["claims"][j] = claims
            out["debts"][j] = debts
            out["nw"][j] = pop.L[i] + pop.K[i] + claims - debts - cfg.d0
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
