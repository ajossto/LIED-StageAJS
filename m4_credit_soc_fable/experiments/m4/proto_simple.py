"""Prototype JETABLE du modèle fusionné « M4-simple » : une seule variable
d'état K par entité (fusion L/K du brief), AUCUN d0, règle de revenu.

But : tester la viabilité du régime (population bornée, avalanches, familles)
AVANT de refondre src/m4/. Si le régime existe, la refonte est promue dans le
moteur avec tests ; sinon on garde L/K et on ne retire que d0.

Séquence par pas (M2 + crédit-revenu + plancher endogène) :
 1. naissances Poisson(lam) : K0, pas de dette d'amorçage ;
 2. choc multiplicatif K *= exp(eta) (option sectorielle identique à m4) ;
 3. production K += alpha*sqrt(K) ;
 4. service des intérêts depuis K (paiement partiel -> defaulted) ;
 5. dépréciation K *= (1-delta) — les contrats nominaux ne se déprécient pas ;
 6. marché : cible commune K*(r) = (alpha/2r)^2, r = sqrt(r_l r_b) ;
    q = min(K_l - K*, K* - K_b) ; transfert conservatif K ;
 7. faillites : NW = K + claims - debts ; entrée = défaut de service ou
    NW < -tol ; cascade identique à bankruptcy.py (arêtes de perte,
    transfert des prêts au prorata, K résiduel aux créancières).

Usage : /home/anatole/jupyter/.venv/bin/python3 proto_simple.py [lam] [T] [seed]
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))
sys.path.insert(0, str(HERE))

from m4.contracts import LoanBook  # noqa: E402


class ProtoSim:
    def __init__(self, lam=10.0, T=2000, seed=0, alpha=1.0, delta=0.05,
                 sigma=0.25, K0=25.0, k=6, rho_sector=0.8, n_sectors=5,
                 birth_loan=False, birth_equity=0.0, birth_lender="rich",
                 rounds_div=None, fail_lender_loans="transfer",
                 fail_residual="prorata", tol=1e-9, q_min=1e-9):
        # rounds_div : dénominateur du nombre de rounds (défaut k) — permet
        # de séparer la force du tri (k) du volume d'appariement (n//rounds_div)
        self.p = dict(lam=lam, T=T, seed=seed, alpha=alpha, delta=delta,
                      sigma=sigma, K0=K0, k=k, rho_sector=rho_sector,
                      n_sectors=n_sectors, birth_loan=birth_loan,
                      birth_equity=birth_equity, birth_lender=birth_lender,
                      rounds_div=rounds_div if rounds_div is not None else k,
                      fail_lender_loans=fail_lender_loans,
                      fail_residual=fail_residual)
        self.rng = np.random.default_rng(seed)
        self.tol, self.q_min = tol, q_min
        self.K, self.alive, self.sector, self.birth = [], [], [], []
        self.defaulted = []
        self.n_alive = 0
        self._alive_set = set()   # maintenu incrémentalement — alive_ids()
        # scannait toutes les entités jamais nées : O(lam*t) par appel
        self.book = LoanBook()
        self.t = 0
        self.series = []
        self.av_log = []

    # ------------------------------------------------------------- helpers
    def born(self, n):
        """Naissances. birth_loan : la dotation K0 est FINANCÉE par une
        prêteuse réelle (transfert de K + contrat nominal) — NW de naissance
        = 0, chaque mort infantile est une perte réelle pour une créancière ;
        fallback en fonds propres (K0 ex nihilo) si aucune prêteuse faisable
        dans l'échantillon (sinon la démographie se verrouille à t=0)."""
        p, rng = self.p, self.rng
        for _ in range(n):
            i = len(self.K)
            self.K.append(p["K0"])
            self.alive.append(True)
            self._alive_set.add(i)
            self.sector.append(int(rng.integers(0, p["n_sectors"]))
                               if p["rho_sector"] > 0 else 0)
            self.birth.append(self.t)
            self.defaulted.append(False)
            self.n_alive += 1
            if not p["birth_loan"]:
                continue
            pool = [j for j in self.alive_ids()
                    if j != i and not self.defaulted[j]]
            if len(pool) < p["k"]:
                self.n_equity_births = getattr(self, "n_equity_births", 0) + 1
                continue
            idx = rng.permutation(len(pool))[:p["k"]]
            sample = [pool[int(j)] for j in idx]
            q_loan = p["K0"] * (1.0 - p["birth_equity"])
            r_b = p["alpha"] / (2.0 * math.sqrt(p["K0"]))
            feasible = []
            for l in sample:
                r_l = p["alpha"] / (2.0 * math.sqrt(max(self.K[l], 1e-9)))
                r = math.sqrt(r_l * r_b)
                k_star = (p["alpha"] / (2.0 * r)) ** 2
                if self.K[l] - k_star >= q_loan:
                    feasible.append((l, r))
            if not feasible:
                self.n_equity_births = getattr(self, "n_equity_births", 0) + 1
                continue
            if p["birth_lender"] == "rich":
                l, r = max(feasible, key=lambda t: self.K[t[0]])
            else:  # "random" : la classe moyenne faisable s'expose aussi
                l, r = feasible[int(rng.integers(0, len(feasible)))]
            # la part financée devient un transfert réel : q sort de la
            # prêteuse ; l'apport birth_equity*K0 reste ex nihilo (injection)
            self.K[l] -= q_loan
            self.book.add(l, i, q_loan, r)

    def alive_ids(self):
        return sorted(self._alive_set)

    def nw(self, i):
        return self.K[i] + self.book.claims[i] - self.book.debts[i]

    # ------------------------------------------------------------- cascade
    def _fail_one(self, i, ledger):
        book = self.book
        creditor_claims = {}
        for lid in list(book.by_borrower[i]):
            lender, _, q, r = book.loans[lid]
            creditor_claims[lender] = creditor_claims.get(lender, 0.0) + q
            book.remove(lid)
            ledger["loss_edges"].append((i, lender, q))
        total_claims = sum(creditor_claims.values())
        for lid in list(book.by_lender[i]):
            _, borrower, q, r = book.loans[lid]
            book.remove(lid)
            if self.p["fail_lender_loans"] == "cancel" or total_claims <= 0.0:
                continue  # créance annulée (gain pour l'emprunteuse)
            for creditor, qc in creditor_claims.items():
                share = q * qc / total_claims
                if share < self.q_min or creditor == borrower \
                        or not self.alive[creditor]:
                    continue
                book.add(creditor, borrower, share, r)
        res_K = max(self.K[i], 0.0)
        living = {c: qc for c, qc in creditor_claims.items() if self.alive[c]}
        living_total = sum(living.values())
        if living_total > 0.0 and self.p["fail_residual"] == "prorata":
            for creditor, qc in living.items():
                self.K[creditor] += res_K * qc / living_total
        self.alive[i] = False
        self._alive_set.discard(i)
        self.K[i] = 0.0
        self.n_alive -= 1

    def resolve(self):
        ledger = dict(loss_edges=[], roots={}, death_iter={})
        queue = []
        for i in sorted(self.alive_ids()):
            insolvent = self.nw(i) < -self.tol
            if self.defaulted[i] or insolvent:
                ledger["roots"][i] = ("both" if self.defaulted[i] and insolvent
                                      else "liquidity" if self.defaulted[i]
                                      else "insolvency")
                queue.append(i)
        iters = 0
        max_iters = self.n_alive + 1
        dead = []
        while queue:
            iters += 1
            if iters > max_iters:
                raise RuntimeError("cascade sans point fixe")
            for i in queue:
                if self.alive[i]:
                    self._fail_one(i, ledger)
                    dead.append(i)
                    ledger["death_iter"][i] = iters
            queue = sorted(i for i in self.alive_ids()
                           if self.nw(i) < -self.tol)
        # avalanches : composantes du graphe de pertes (même déf que m4)
        parent = {i: i for i in ledger["death_iter"]}

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
        for i in ledger["death_iter"]:
            comps.setdefault(find(i), []).append(i)
        for members in comps.values():
            ages = sorted(self.t - self.birth[m] for m in members)
            n = len(ages)
            self.av_log.append(dict(
                t=self.t, size=n,
                n_roots=sum(1 for m in members if m in ledger["roots"]),
                depth=max(ledger["death_iter"][m] for m in members),
                age_med=ages[n // 2],
                age_iqr=ages[(3 * n) // 4] - ages[n // 4]))
        return dead

    # ---------------------------------------------------------------- step
    def step(self):
        p, rng, book = self.p, self.rng, self.book
        self.t += 1
        self.born(int(rng.poisson(p["lam"])))
        ids = self.alive_ids()
        for i in ids:
            self.defaulted[i] = False
        # 2. choc
        var = p["sigma"] ** 2
        var_s = p["rho_sector"] * var
        var_i = var - var_s
        eta_s = (rng.normal(-0.5 * var_s, math.sqrt(var_s),
                            size=p["n_sectors"]) if var_s > 0 else None)
        xi = rng.normal(-0.5 * var_i, math.sqrt(var_i), size=len(ids)) \
            if var_i > 0 else np.zeros(len(ids))
        for j, i in enumerate(ids):
            e = xi[j] + (eta_s[self.sector[i]] if eta_s is not None else 0.0)
            self.K[i] *= math.exp(e)
        # 3. production
        prod_tot = 0.0
        for i in ids:
            pr = p["alpha"] * math.sqrt(self.K[i])
            self.K[i] += pr
            prod_tot += pr
        # 4. service des intérêts depuis K
        interest = 0.0
        for b in list(book.by_borrower.keys()):
            lids = book.by_borrower[b]
            if not lids:
                continue
            due = book.due[b]
            kb = self.K[b]
            if kb >= due:
                ratio = 1.0
                self.K[b] = kb - due
            else:
                ratio = kb / due if due > 0 else 0.0
                self.K[b] = 0.0
                self.defaulted[b] = True
            if ratio > 0.0:
                for lid in lids:
                    lender, _, q, r = book.loans[lid]
                    self.K[lender] += ratio * r * q
                    interest += ratio * r * q
        # 5. dépréciation
        f = 1.0 - p["delta"]
        for i in ids:
            self.K[i] *= f
        # 6. marché (règle de revenu : cible commune K*(r) = sqrt(K_l K_b))
        pool = [i for i in self.alive_ids() if not self.defaulted[i]]
        n = len(pool)
        n_new, volume = 0, 0.0
        for _ in range(int(n / p["rounds_div"])):
            idx = rng.permutation(n)[:p["k"]] if p["k"] * 8 >= n else None
            if idx is None:
                while True:
                    idx = rng.integers(0, n, size=p["k"])
                    if len(set(idx.tolist())) == p["k"]:
                        break
            sample = [pool[j] for j in idx]
            lender = max(sample, key=lambda i: self.K[i])
            borrower = min(sample, key=lambda i: self.K[i])
            if lender == borrower or self.K[lender] <= self.K[borrower]:
                continue
            r_l = p["alpha"] / (2.0 * math.sqrt(max(self.K[lender], 1e-9)))
            r_b = p["alpha"] / (2.0 * math.sqrt(max(self.K[borrower], 1e-9)))
            r = math.sqrt(r_l * r_b)
            k_star = (p["alpha"] / (2.0 * r)) ** 2
            q = min(self.K[lender] - k_star,
                    max(0.0, k_star - self.K[borrower]))
            if q < self.q_min:
                continue
            self.K[lender] -= q
            self.K[borrower] += q
            book.add(lender, borrower, q, r)
            n_new += 1
            volume += q
        # 7. faillites
        dead = self.resolve()
        ids = self.alive_ids()
        self.series.append(dict(
            t=self.t, pop=self.n_alive, deaths=len(dead),
            K_tot=sum(self.K[i] for i in ids), prod_tot=prod_tot,
            n_loans=len(book), interest=interest, volume=volume))

    def run(self, log_every=500):
        # N(0)=0 : les naissances ont lieu dans step(), ne tester l'extinction
        # qu'après le premier pas
        while self.t < self.p["T"] and (self.t == 0 or 0 < self.n_alive < 50000):
            self.step()
            if log_every and self.t % log_every == 0:
                s = self.series[-1]
                print(f"t={s['t']:5d} pop={s['pop']:6d} "
                      f"loans={s['n_loans']:6d} deaths={s['deaths']:3d} "
                      f"K={s['K_tot']:.3e}", flush=True)
        return "ok" if 0 < self.n_alive else "extinction"


if __name__ == "__main__":
    lam = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    T = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    import time
    t0 = time.time()
    sim = ProtoSim(lam=lam, T=T, seed=seed)
    status = sim.run()
    sizes = np.array([a["size"] for a in sim.av_log if a["t"] >= T // 4])
    from soc_stats import loglog_regression, fit_tail_discrete
    reg = loglog_regression(sizes, exclude_one=True) if len(sizes) else None
    fit = fit_tail_discrete(sizes) if len(sizes) else None
    pops = [s["pop"] for s in sim.series[T // 4:]]
    print(f"status={status} wall={time.time()-t0:.0f}s "
          f"pop_moy={np.mean(pops):.0f} n_av={len(sizes)} "
          f"max={sizes.max() if len(sizes) else 0}")
    if reg:
        print(f"ex1: pente={reg['slope']:.2f}±{reg['slope_se']:.2f} "
              f"r²={reg['r2']:.3f}")
    if fit:
        print(f"PL discrète: s_min={fit['s_min']} α={fit['alpha']:.2f}")
    vals, cnts = np.unique(sizes, return_counts=True)
    print("histo:", dict(zip(vals.tolist()[:20], cnts.tolist()[:20])))
