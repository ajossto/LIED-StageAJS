"""Boucle de simulation M2 — séquence à 7 phases, ordre fixé (§2.2 du rapport).

1. naissances Poisson(lam), dotation w0, dette d'amorçage d0, N(0) = 0 ;
2. choc multiplicatif commun en loi : w <- w * exp(eta),
   eta ~ N(-sigma^2/2, sigma^2) i.i.d. par entité (C1) — capital réel seul ;
3. extraction : w += alpha * sqrt(w) ;
4. service des intérêts : r*q par contrat, ordre de création (C2), paiement
   partiel = transfert du disponible + défaut ;
5. dépréciation : w <- (1-delta) * w — contrats et d0 non dépréciés (I6) ;
6. marché du crédit (market.py) ;
7. faillites en cascade (bankruptcy.py).
"""
import math

import numpy as np

from .bankruptcy import net_worth, resolve_bankruptcies
from .contracts import LoanBook
from .entities import Population
from .market import run_market


class Simulation:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.pop = Population()
        self.book = LoanBook(merge_pairs=cfg.merge_pairs)
        self.t = 0
        self.series = []       # une ligne dict par pas
        self.status = "ok"     # "ok" | "extinction" | "explosion"

    # ------------------------------------------------------------------ étape
    def step(self):
        cfg, pop, book, rng = self.cfg, self.pop, self.book, self.rng
        self.t += 1

        # 1. naissances
        births = int(rng.poisson(cfg.lam))
        for _ in range(births):
            pop.born(cfg.w0, self.t)

        alive = pop.alive_ids()
        for i in alive:
            pop.int_in[i] = 0.0
            pop.int_out[i] = 0.0
            pop.extract[i] = 0.0
            pop.defaulted[i] = False

        # 2. choc multiplicatif commun en loi (capital réel seulement)
        if cfg.sigma > 0 and alive:
            eta = rng.normal(-0.5 * cfg.sigma ** 2, cfg.sigma, size=len(alive))
            for j, i in enumerate(alive):
                pop.w[i] *= math.exp(eta[j])

        # 3. extraction
        for i in alive:
            e = cfg.alpha * math.sqrt(pop.w[i])
            pop.w[i] += e
            pop.extract[i] = e

        # 4. service des intérêts (ordre de création des contrats, C2)
        n_defaults = 0
        interest_paid = 0.0
        for lender, borrower, q, r in book.loans.values():
            due = r * q
            wb = pop.w[borrower]
            if wb >= due:
                pop.w[borrower] = wb - due
                pop.w[lender] += due
                pop.int_in[lender] += due
                pop.int_out[borrower] += due
                interest_paid += due
            else:
                # paiement partiel : tout le disponible, puis défaut
                if wb > 0.0:
                    pop.w[lender] += wb
                    pop.int_in[lender] += wb
                    pop.int_out[borrower] += wb
                    interest_paid += wb
                    pop.w[borrower] = 0.0
                if not pop.defaulted[borrower]:
                    n_defaults += 1
                pop.defaulted[borrower] = True

        # 5. dépréciation (capital réel seulement, I6)
        f = 1.0 - cfg.delta
        for i in alive:
            wi = pop.w[i] * f
            pop.w[i] = wi if wi > cfg.w_clamp else 0.0

        # 6. marché du crédit
        n_new_loans, loan_volume = run_market(pop, book, cfg, rng)

        # 7. faillites en cascade — avec repérage du top décile de NW (6.4)
        top_threshold = None
        if pop.n_alive >= 10:
            nws = [net_worth(pop, book, cfg, i) for i in pop.alive_ids()]
            top_threshold = float(np.quantile(nws, 0.9))
        pre_nw = {}
        if top_threshold is not None:
            pre_nw = {i: net_worth(pop, book, cfg, i) for i in pop.alive_ids()}
        dead, cascade_iters = resolve_bankruptcies(pop, book, cfg)
        top_deaths = sum(
            1 for i in dead
            if top_threshold is not None and pre_nw.get(i, -1e18) >= top_threshold
        )

        # série du pas
        alive = pop.alive_ids()
        w_tot = sum(pop.w[i] for i in alive)
        nw_tot = sum(net_worth(pop, book, self.cfg, i) for i in alive)
        self.series.append(dict(
            t=self.t, births=births, deaths=len(dead), pop=pop.n_alive,
            w_tot=w_tot, nw_tot=nw_tot, n_loans=len(book),
            new_loans=n_new_loans, loan_volume=loan_volume,
            interest_paid=interest_paid, defaults=n_defaults,
            cascade_iters=cascade_iters, top_decile_deaths=top_deaths,
        ))

        if pop.n_alive == 0:
            self.status = "extinction"
        elif pop.n_alive > self.cfg.pop_max:
            self.status = "explosion"
        return self.status

    # -------------------------------------------------------------- exécution
    def run(self, T=None, snapshot_times=(), on_snapshot=None, log_every=0):
        """Exécute jusqu'à T pas (défaut cfg.T). on_snapshot(t, snap) est
        appelé aux pas listés dans snapshot_times avec le snapshot courant."""
        T = T if T is not None else self.cfg.T
        snap_set = set(snapshot_times)
        while self.t < T and self.status == "ok":
            self.step()
            if self.t in snap_set and on_snapshot is not None:
                on_snapshot(self.t, self.snapshot())
            if log_every and self.t % log_every == 0:
                s = self.series[-1]
                print(f"t={s['t']:5d} pop={s['pop']:6d} loans={s['n_loans']:6d} "
                      f"deaths={s['deaths']:3d} W={s['w_tot']:.3e}", flush=True)
        return self.status

    # -------------------------------------------------------------- snapshot
    def snapshot(self):
        """Vecteurs alignés des vivantes (fin de pas)."""
        pop, book, cfg = self.pop, self.book, self.cfg
        ids = pop.alive_ids()
        n = len(ids)
        out = {
            "id": np.array(ids, dtype=np.int64),
            "w": np.empty(n), "claims": np.empty(n), "debts": np.empty(n),
            "nw": np.empty(n), "income": np.empty(n), "income_net": np.empty(n),
            "age": np.empty(n, dtype=np.int64),
        }
        for j, i in enumerate(ids):
            out["w"][j] = pop.w[i]
            out["claims"][j] = book.claims[i]
            out["debts"][j] = book.debts[i]
            out["nw"][j] = pop.w[i] + book.claims[i] - book.debts[i] - cfg.d0
            out["income"][j] = pop.extract[i] + pop.int_in[i]
            out["income_net"][j] = out["income"][j] - pop.int_out[i]
            out["age"][j] = self.t - pop.birth[i]
        return out
