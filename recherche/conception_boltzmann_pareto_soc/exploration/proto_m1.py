"""Prototype d'exploration M1 — modèle réduit à capital scalaire.

But : tester AVANT conception finale si le couple
  (extraction concave √w  +  crédit conservatif à intérêts  +  faillite NW<0  +  naissances)
peut produire simultanément :
  - un corps exponentiel (mode en 0) sur capital et/ou revenu,
  - une queue de Pareto d'exposant stable dans le temps,
  - une population bornée endogènement,
avec des règles STRICTEMENT identiques (alpha = 1 pour tous) et un minimum de paramètres.

Ce script NE MODIFIE PAS anciens_modeles/modele-27-04-WIP/src. Il est volontairement jetable.

Mécanique d'un pas :
  1. naissances  ~ Poisson(lam), dotation w0
  2. extraction  w += sqrt(w)              (alpha = 1 : convention d'unité)
  3. intérêts    emprunteur -> prêteur, r*q par prêt ; défaut si w insuffisant
  4. dépréciation w *= (1-delta) ; option : principal des prêts déprécié au même taux
  5. marché du crédit : rounds d'appariement aléatoire local (échantillon de taille k),
     prêteur = w max de l'échantillon, emprunteur = w min, taux moyenne géométrique
     des deux r* = 1/(2 sqrt(w)), principal = min(offre, theta*qmax) TRANSFÉRÉ
     (échange conservatif)
  6. faillites en cascade : NW = w + créances - dettes < 0  -> mort,
     annulation des prêts (perte sèche du prêteur -> contagion)
"""
import math
import sys
import numpy as np

sys.path.insert(0, "/home/anatole/jupyter/recherche/analyse_distributions_taille_revenu/scripts")
from tail_test import fit_powerlaw_xmin, lognormal_vs_powerlaw_lr  # noqa: E402

from scipy import stats as st  # noqa: E402


class M1:
    def __init__(self, seed=0, delta=0.05, lam=2.0, w0=10.0, k=6, theta=0.35,
                 n0=100, deprec_loans=True, rounds_per_capita=1.0 / 6,
                 offer_frac=0.5, rate_rule="geom", service_cap=False,
                 w0_endo=False, cost_incl_delta=False, gbm_sigma=0.0, d0=0.0):
        self.rng = np.random.default_rng(seed)
        self.delta = delta
        self.lam = lam
        self.w0 = w0
        self.k = k
        self.theta = theta
        self.deprec_loans = deprec_loans
        self.rounds_per_capita = rounds_per_capita
        self.offer_frac = offer_frac
        self.rate_rule = rate_rule
        self.service_cap = service_cap
        self.w0_endo = w0_endo
        self.cost_incl_delta = cost_incl_delta
        self.gbm_sigma = gbm_sigma  # choc multiplicatif commun en loi (BM eta_i)
        self.d0 = d0  # dette d'amorçage nominale (plancher d'absorption, WIP: B=190)
        self.charges = {}  # eid -> somme r*q des dettes actives (cap de service)

        self.w = []          # capital (une seule colonne)
        self.alive = []
        self.birth = []
        self.claims = []     # somme des principaux prêtés (maintenu incrémentalement)
        self.debts = []      # somme des principaux empruntés
        self.int_in = []     # flux d'intérêts reçus au dernier pas
        self.int_out = []
        # prêts actifs : dict id -> [lender, borrower, q, r]
        self.loans = {}
        self.by_lender = {}
        self.by_borrower = {}
        self.next_loan = 0
        self.t = 0
        self.n_failures_total = 0
        self.failures_per_step = []
        for _ in range(n0):
            self._born()

    def _born(self):
        if self.w0_endo:
            ws = [self.w[i] for i in range(len(self.w)) if self.alive[i]]
            dot = float(np.mean(ws)) if ws else self.w0
        else:
            dot = self.w0
        self.w.append(dot)
        self.alive.append(True)
        self.birth.append(self.t)
        self.claims.append(0.0)
        self.debts.append(0.0)
        self.int_in.append(0.0)
        self.int_out.append(0.0)

    def _add_loan(self, l, b, q, r):
        lid = self.next_loan
        self.next_loan += 1
        self.loans[lid] = [l, b, q, r]
        self.by_lender.setdefault(l, set()).add(lid)
        self.by_borrower.setdefault(b, set()).add(lid)
        self.claims[l] += q
        self.debts[b] += q

    def _remove_loan(self, lid):
        l, b, q, r = self.loans.pop(lid)
        self.by_lender[l].discard(lid)
        self.by_borrower[b].discard(lid)
        self.claims[l] -= q
        self.debts[b] -= q

    def step(self):
        rng = self.rng
        for _ in range(rng.poisson(self.lam)):
            self._born()
        alive_idx = [i for i in range(len(self.w)) if self.alive[i]]
        # 1b. choc multiplicatif commun en loi (piste n°1) : w -> w * e^eta,
        #     eta ~ N(-sigma^2/2, sigma^2)  => E[e^eta] = 1, pas de drift moyen
        if self.gbm_sigma > 0:
            s = self.gbm_sigma
            shocks = rng.normal(-0.5 * s * s, s, size=len(alive_idx))
            for j, i in enumerate(alive_idx):
                self.w[i] *= math.exp(shocks[j])
        # 2. extraction
        for i in alive_idx:
            self.w[i] += math.sqrt(max(self.w[i], 0.0))
            self.int_in[i] = 0.0
            self.int_out[i] = 0.0
        # 3. intérêts
        defaulted = set()
        for lid in list(self.loans.keys()):
            l, b, q, r = self.loans[lid]
            due = q * r
            if self.w[b] >= due:
                self.w[b] -= due
                self.w[l] += due
                self.int_in[l] += due
                self.int_out[b] += due
            else:
                self.w[l] += self.w[b]
                self.int_in[l] += self.w[b]
                self.w[b] = 0.0
                defaulted.add(b)
        # 4. dépréciation
        f = 1.0 - self.delta
        for i in alive_idx:
            self.w[i] *= f
        if self.deprec_loans:
            dead_loans = []
            for lid, rec in self.loans.items():
                l, b, q, r = rec
                self.claims[l] -= q * self.delta
                self.debts[b] -= q * self.delta
                rec[2] = q * f
                if rec[2] < 1e-6:
                    dead_loans.append(lid)
            for lid in dead_loans:
                self._remove_loan(lid)
        # 5. marché du crédit
        pool = [i for i in alive_idx if i not in defaulted]
        n_alive = len(pool)
        n_rounds = 0 if self.rounds_per_capita <= 0 else max(1, int(self.rounds_per_capita * n_alive))
        for _ in range(n_rounds):
            if n_alive < 2:
                break
            sample = rng.choice(pool, size=min(self.k, n_alive), replace=False)
            ws = [self.w[i] for i in sample]
            lender = int(sample[int(np.argmax(ws))])
            borrower = int(sample[int(np.argmin(ws))])
            if lender == borrower or self.w[lender] <= 0 or self.w[borrower] < 0:
                continue
            rl = 1.0 / (2.0 * math.sqrt(max(self.w[lender], 1e-9)))
            rb = 1.0 / (2.0 * math.sqrt(max(self.w[borrower], 1e-9)))
            if rb <= rl * 1.0001:
                continue
            rate = math.sqrt(rl * rb) if self.rate_rule == "geom" else 0.5 * (rl + rb)
            # coût effectif de l'emprunt : r seul si la dette se déprécie comme
            # le capital ; r + delta si la dette est nominale (le capital financé
            # fond, la dette non)
            cost = rate + (self.delta if self.cost_incl_delta else 0.0)
            qmax = (1.0 / (2.0 * cost)) ** 2 - self.w[borrower]
            q = min(self.offer_frac * self.w[lender], self.theta * qmax)
            if self.service_cap:
                # plafond de service : charges existantes + r*q <= revenu courant
                charges = sum(self.loans[lid][2] * self.loans[lid][3]
                              for lid in self.by_borrower.get(borrower, ()))
                revenu = math.sqrt(max(self.w[borrower], 0.0)) + self.int_in[borrower]
                q = min(q, max(0.0, (revenu - charges) / rate))
            if q <= 1e-6:
                continue
            self.w[lender] -= q
            self.w[borrower] += q
            self._add_loan(lender, borrower, q, rate)
        # 6. faillites en cascade
        n_fail = 0
        stack = [b for b in defaulted]
        # d'abord les défauts de paiement, puis propagation NW<0
        while True:
            for i in stack:
                n_fail += self._fail(i)
            stack = [i for i in range(len(self.w))
                     if self.alive[i]
                     and self.w[i] + self.claims[i] - self.debts[i] - self.d0 < -1e-9]
            if not stack:
                break
        self.n_failures_total += n_fail
        self.failures_per_step.append(n_fail)
        self.t += 1

    def _fail(self, i):
        if not self.alive[i]:
            return 0
        self.alive[i] = False
        creditors = []
        for lid in list(self.by_borrower.get(i, ())):
            l, b, q, r = self.loans[lid]
            creditors.append((l, q))
            self._remove_loan(lid)
        for lid in list(self.by_lender.get(i, ())):
            self._remove_loan(lid)  # dette de l'emprunteur annulée (gain pour lui)
        residual = max(self.w[i], 0.0)
        total = sum(q for _, q in creditors)
        if total > 0 and residual > 0:
            for lid_, q in creditors:
                if self.alive[lid_]:
                    self.w[lid_] += residual * q / total
        self.w[i] = 0.0
        return 1

    def snapshot(self):
        rows = []
        for i in range(len(self.w)):
            if self.alive[i]:
                rows.append(dict(
                    w=self.w[i],
                    nw=self.w[i] + self.claims[i] - self.debts[i] - self.d0,
                    income=math.sqrt(max(self.w[i], 0)) + self.int_in[i],
                    income_net=math.sqrt(max(self.w[i], 0)) + self.int_in[i] - self.int_out[i],
                    age=self.t - self.birth[i],
                    claims=self.claims[i], debts=self.debts[i],
                ))
        return rows


def body_fits(values, q_body=0.95):
    v = np.sort(np.asarray([x for x in values if x > 0]))
    if len(v) < 50:
        return {}
    body = v[v <= np.quantile(v, q_body)]
    out = {}
    for name, dist, kw, k in [("expon", st.expon, dict(floc=0), 1),
                              ("gamma", st.gamma, dict(floc=0), 2),
                              ("lognorm", st.lognorm, dict(floc=0), 2),
                              ("fisk", st.fisk, dict(floc=0), 2)]:
        try:
            p = dist.fit(body, **kw)
            ll = np.sum(dist.logpdf(body, *p))
            out[name] = dict(aic=2 * k - 2 * ll, params=[round(float(x), 3) for x in p])
        except Exception:
            pass
    return out


def analyze(rows, label):
    w = np.array([r["w"] for r in rows])
    nw = np.array([r["nw"] for r in rows])
    inc = np.array([r["income"] for r in rows])
    age = np.array([r["age"] for r in rows])
    print(f"\n--- {label} : n={len(rows)} ---")
    for name, v in [("capital w", w), ("net worth", nw), ("income", inc)]:
        v = v[v > 0]
        if len(v) < 50:
            print(f"  {name}: trop peu de valeurs ({len(v)})")
            continue
        fits = body_fits(v)
        best = min(fits, key=lambda kk: fits[kk]["aic"]) if fits else "?"
        aics = {kk: round(ff["aic"], 1) for kk, ff in fits.items()}
        tail = fit_powerlaw_xmin(v)
        med, mean = np.median(v), np.mean(v)
        s = (f"  {name}: mean={mean:.1f} med={med:.1f} med/mean={med/mean:.2f} "
             f"P90/P10={np.quantile(v,0.9)/max(np.quantile(v,0.1),1e-9):.1f} best_body={best} AIC={aics}")
        if tail:
            lr = lognormal_vs_powerlaw_lr(v, tail["x_min"], tail["alpha"])
            s += f"\n      queue CSN: alpha={tail['alpha']:.2f} xmin={tail['x_min']:.1f} ntail={tail['n_tail']}"
            if lr:
                s += f" LR(pl vs ln)={lr['R']:.1f} p={lr['p']:.3f}"
        print(s)
    if len(age) > 10 and np.std(age) > 0 and np.std(w) > 0:
        lw = np.log(np.maximum(w, 1e-9))
        c = np.corrcoef(age, lw)[0, 1]
        qs = np.quantile(age, [0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
        print(f"  corr(age, log w) = {c:.3f} ; ages q10/q25/q50/q75/q90/q99 = "
              + "/".join(f"{q:.0f}" for q in qs) + f" max={age.max()}")
        # garde-fou anti-cohorte : queue CSN sur tranche d'âge contrôlée
        for lo, hi in [(20, 100), (100, 400)]:
            mask = (age >= lo) & (age < hi)
            if mask.sum() > 150:
                tail_a = fit_powerlaw_xmin(w[mask][w[mask] > 0])
                if tail_a:
                    print(f"    queue CSN capital, âge dans [{lo},{hi}): "
                          f"alpha={tail_a['alpha']:.2f} ntail={tail_a['n_tail']} (n={mask.sum()})")


def run(seed=0, T=2000, snap_at=(500, 1000, 1500, 2000), verbose=True,
        pool_every=0, **kw):
    """pool_every > 0 : collecte un snapshot tous les pool_every pas, agrégés
    par fenêtres [500,1000), [1000,1500), [1500,2000] pour l'analyse de queue."""
    m = M1(seed=seed, **kw)
    snaps = {}
    pools = {}
    for t in range(1, T + 1):
        m.step()
        n_alive = sum(m.alive)
        if t in snap_at:
            snaps[t] = m.snapshot()
        if pool_every and t >= 500 and t % pool_every == 0:
            wname = f"[{500 + 500 * ((t - 500) // 500)},{1000 + 500 * ((t - 500) // 500)})"
            pools.setdefault(wname, []).extend(m.snapshot())
        if verbose and t % 200 == 0:
            wtot = sum(w for i, w in enumerate(m.w) if m.alive[i])
            print(f"t={t:5d} pop={n_alive:5d} prets={len(m.loans):6d} "
                  f"faillites_cum={m.n_failures_total:6d} W_tot={wtot:.3e} "
                  f"w_max={max((w for i, w in enumerate(m.w) if m.alive[i]), default=0):.2e}")
        if n_alive == 0:
            print(f"EXTINCTION à t={t}")
            break
        if n_alive > 30000:
            print(f"EXPLOSION démographique à t={t}")
            break
    return m, snaps, pools


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--T", type=int, default=2000)
    ap.add_argument("--delta", type=float, default=0.05)
    ap.add_argument("--lam", type=float, default=2.0)
    ap.add_argument("--w0", type=float, default=10.0)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--theta", type=float, default=0.35)
    ap.add_argument("--offer_frac", type=float, default=0.5)
    ap.add_argument("--rounds_per_capita", type=float, default=1.0 / 6)
    ap.add_argument("--no-deprec-loans", action="store_true")
    ap.add_argument("--no-credit", action="store_true")
    ap.add_argument("--pool_every", type=int, default=0)
    ap.add_argument("--n0", type=int, default=100)
    ap.add_argument("--service-cap", action="store_true")
    ap.add_argument("--w0-endo", action="store_true")
    ap.add_argument("--cost-delta", action="store_true")
    ap.add_argument("--gbm-sigma", type=float, default=0.0)
    ap.add_argument("--d0", type=float, default=0.0)
    args = ap.parse_args()
    kw = dict(delta=args.delta, lam=args.lam, w0=args.w0, k=args.k,
              theta=args.theta, offer_frac=args.offer_frac,
              rounds_per_capita=args.rounds_per_capita, n0=args.n0,
              deprec_loans=not args.no_deprec_loans,
              service_cap=args.service_cap, w0_endo=args.w0_endo,
              cost_incl_delta=args.cost_delta, gbm_sigma=args.gbm_sigma, d0=args.d0)
    if args.no_credit:
        kw["rounds_per_capita"] = 0.0
    m, snaps, pools = run(seed=args.seed, T=args.T, pool_every=args.pool_every, **kw)
    for t, rows in snaps.items():
        analyze(rows, f"t={t} (seed={args.seed})")
    for wname in sorted(pools):
        analyze(pools[wname], f"POOL fenêtre {wname} (seed={args.seed})")
