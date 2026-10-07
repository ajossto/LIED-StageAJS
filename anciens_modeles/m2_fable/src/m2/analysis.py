"""Outillage statistique du protocole de validation (§6 du rapport, spec §7).

Réimplémentation locale et testée des outils de
recherche/analyse_distributions_taille_revenu/scripts/ (CSN, LR Vuong),
augmentée : bootstrap de l'exposant, exposant à x_min commun, test
mécanistique T ~ B0/A0, diagnostics anti-cohorte et de renouvellement.

Conventions : alpha = exposant de la pdf (p(x) ~ x^-alpha) comme dans CSN ;
scipy pareto utilise b = alpha - 1.
"""
import math

import numpy as np
from scipy import stats
from scipy.optimize import minimize

# --------------------------------------------------------------------- corps

BODY_FAMILIES = ("expon", "gamma", "lognorm", "fisk")

# ATTENTION MÉTHODOLOGIQUE (découverte pendant les tests, cf. rapport 03) :
# ajuster des familles NON tronquées sur un corps tronqué au quantile 95 %
# biaise l'AIC contre la vraie famille (sur un échantillon exponentiel pur,
# gamma « gagne » avec dAIC ~ 30). Les ajustements du corps sont donc faits en
# MLE TRONQUÉ : pdf renormalisée par CDF(c) où c est le seuil de troncature.


def _truncated_body_fit(dist, body, cut, k_free, params0):
    """MLE de `dist` (floc=0) tronquée à droite en `cut`. params0 : point de
    départ (ajustement non tronqué). Paramètres strictement positifs,
    optimisés en log."""
    shapes0 = [p for p in params0 if p != 0.0]  # retire loc=0 (position connue)

    def negll(log_theta):
        theta = np.exp(log_theta)
        args = list(theta[:-1]) + [0.0, theta[-1]]  # shapes..., loc=0, scale
        cdf_c = dist.cdf(cut, *args)
        if not (cdf_c > 1e-12):
            return 1e12
        ll = np.sum(dist.logpdf(body, *args)) - len(body) * math.log(cdf_c)
        return -ll if math.isfinite(ll) else 1e12

    res = minimize(negll, np.log(np.maximum(shapes0, 1e-8)),
                   method="Nelder-Mead",
                   options={"maxiter": 2000, "xatol": 1e-8, "fatol": 1e-8})
    if not math.isfinite(res.fun) or res.fun >= 1e11:
        return None
    theta = np.exp(res.x)
    n = len(body)
    return dict(aic=2 * k_free + 2 * res.fun, bic=k_free * math.log(n) + 2 * res.fun,
                params=[float(t) for t in theta], n=n)


def fit_body(values, q_body=0.95):
    """MLE tronqué + AIC/BIC des familles candidates sur les q_body inférieurs.
    Retourne fits par famille, meilleure famille, dAIC de l'exponentielle."""
    v = np.asarray(values, dtype=float)
    v = np.sort(v[v > 0])
    if len(v) < 50:
        return None
    cut = float(np.quantile(v, q_body))
    body = v[v <= cut]
    out = {}
    for name, dist, kfree in (("expon", stats.expon, 1), ("gamma", stats.gamma, 2),
                              ("lognorm", stats.lognorm, 2), ("fisk", stats.fisk, 2)):
        try:
            params0 = dist.fit(body, floc=0)
        except Exception:
            continue
        fit = _truncated_body_fit(dist, body, cut, kfree, params0)
        if fit is not None:
            out[name] = fit
    if not out:
        return None
    best = min(out, key=lambda k: out[k]["aic"])
    return dict(fits=out, best=best, med_over_mean=float(np.median(body) / np.mean(body)),
                n_body=len(body), cut=cut,
                delta_aic_expon=(out["expon"]["aic"] - out[best]["aic"]) if "expon" in out else None)


def exponential_qq(values, q_body=0.95, n_points=200):
    """Points (quantiles théoriques exp, quantiles empiriques) du corps."""
    v = np.asarray(values, dtype=float)
    v = np.sort(v[v > 0])
    body = v[v <= np.quantile(v, q_body)]
    scale = float(np.mean(body))
    probs = (np.arange(1, n_points + 1) - 0.5) / n_points
    emp = np.quantile(body, probs)
    theo = -scale * np.log1p(-probs)
    return theo, emp


# --------------------------------------------------------------------- queue

def _pareto_ks(tail, x_min, alpha):
    tail = np.sort(tail)
    n = len(tail)
    cdf_emp = np.arange(1, n + 1) / n
    cdf_fit = 1.0 - (tail / x_min) ** (-(alpha - 1.0))
    return float(np.max(np.abs(cdf_emp - cdf_fit)))


def fit_tail_csn(values, n_candidates=40, min_tail=30, q_max=0.90):
    """CSN : scan de x_min sur une grille de quantiles, MLE de alpha,
    choix du x_min minimisant la distance KS."""
    pos = np.sort(np.asarray([v for v in values if v > 0], dtype=float))
    if len(pos) < 2 * min_tail:
        return None
    candidates = np.unique(np.quantile(pos, np.linspace(0.0, q_max, n_candidates)))
    best = None
    for x_min in candidates:
        if x_min <= 0:
            continue
        tail = pos[pos >= x_min]
        if len(tail) < min_tail:
            continue
        alpha = 1.0 + len(tail) / float(np.sum(np.log(tail / x_min)))
        if not math.isfinite(alpha) or alpha <= 1.0:
            continue
        ks = _pareto_ks(tail, x_min, alpha)
        if best is None or ks < best["ks"]:
            best = dict(x_min=float(x_min), alpha=float(alpha), ks=ks, n_tail=len(tail))
    return best


def fit_tail_fixed_xmin(values, x_min, min_tail=20):
    """MLE de alpha à x_min imposé (comparaison inter-fenêtres, §6.2)."""
    pos = np.asarray([v for v in values if v > 0], dtype=float)
    tail = pos[pos >= x_min]
    if len(tail) < min_tail:
        return None
    alpha = 1.0 + len(tail) / float(np.sum(np.log(tail / x_min)))
    return dict(x_min=float(x_min), alpha=float(alpha), n_tail=len(tail))


def bootstrap_tail_alpha(values, x_min, n_boot=200, seed=0, min_tail=20):
    """IC bootstrap de alpha à x_min fixé (rééchantillonnage de la queue)."""
    rng = np.random.default_rng(seed)
    pos = np.asarray([v for v in values if v > 0], dtype=float)
    tail = pos[pos >= x_min]
    n = len(tail)
    if n < min_tail:
        return None
    alphas = np.empty(n_boot)
    for b in range(n_boot):
        resamp = tail[rng.integers(0, n, size=n)]
        alphas[b] = 1.0 + n / float(np.sum(np.log(resamp / x_min)))
    return dict(alpha_lo=float(np.quantile(alphas, 0.025)),
                alpha_hi=float(np.quantile(alphas, 0.975)),
                alpha_sd=float(np.std(alphas)), n_tail=n)


def _truncated_lognormal_mle(tail, x_min):
    """MLE de la log-normale TRONQUÉE à gauche en x_min sur la queue.
    Retourne (mu, s, loglik). Nécessaire pour un LR honnête : ajuster une
    log-normale non tronquée par les moments de la queue favorise la loi de
    puissance à tort (c'est le défaut du tail_test.py historique : sur des
    données log-normales pures il donne R ~ +575, p ~ 0)."""
    log_tail = np.log(tail)
    mu0, s0 = float(np.mean(log_tail)), max(float(np.std(log_tail)), 1e-3)
    n = len(tail)
    log_xmin = math.log(x_min)

    def negll(theta):
        mu, log_s = theta
        s = math.exp(log_s)
        sf = stats.norm.sf((log_xmin - mu) / s)  # P(X >= x_min)
        if not (sf > 1e-300):
            return 1e12
        ll = float(np.sum(stats.lognorm.logpdf(tail, s=s, scale=math.exp(mu)))
                   - n * math.log(sf))
        return -ll if math.isfinite(ll) else 1e12

    best = None
    # plusieurs départs : la vraisemblance tronquée peut être plate en mu
    for mu_start in (mu0, mu0 - 2 * s0, log_xmin - s0):
        res = minimize(negll, [mu_start, math.log(s0)], method="Nelder-Mead",
                       options={"maxiter": 3000, "xatol": 1e-8, "fatol": 1e-8})
        if best is None or res.fun < best.fun:
            best = res
    if not math.isfinite(best.fun) or best.fun >= 1e11:
        return None
    mu, log_s = best.x
    return float(mu), float(math.exp(log_s)), -float(best.fun)


def lr_powerlaw_vs_lognormal(values, x_min, alpha, truncated=True):
    """LR de Vuong restreint à x >= x_min. R > 0 favorise la loi de puissance.
    truncated=True (défaut) : log-normale ajustée en MLE tronqué (correct).
    truncated=False : réplique le tail_test.py historique (biaisé pro-Pareto,
    conservé uniquement pour comparaison avec les logs E7c)."""
    pos = np.asarray([v for v in values if v > 0], dtype=float)
    tail = pos[pos >= x_min]
    n = len(tail)
    if n < 20:
        return None
    ll_pl = stats.pareto.logpdf(tail, b=alpha - 1.0, scale=x_min)
    log_tail = np.log(tail)
    if truncated:
        fit = _truncated_lognormal_mle(tail, x_min)
        if fit is None:
            return None
        mu, s, _ = fit
        log_sf = math.log(stats.norm.sf((math.log(x_min) - mu) / s))
        ll_ln = stats.lognorm.logpdf(tail, s=s, scale=math.exp(mu)) - log_sf
    else:
        mu, s = float(np.mean(log_tail)), float(np.std(log_tail))
        if s < 1e-9:
            return None
        ll_ln = stats.lognorm.logpdf(tail, s=s, scale=math.exp(mu))
    diff = ll_pl - ll_ln
    R = float(np.sum(diff))
    sd = float(np.std(diff))
    if sd < 1e-12:
        return dict(R=R, p=float("nan"), n_tail=n)
    z = R / (sd * math.sqrt(n))
    return dict(R=R, z=float(z), p=float(2 * (1 - stats.norm.cdf(abs(z)))), n_tail=n)


# --------------------------------------------- test mécanistique T ~ B0 / A0

def body_increment_moments(snap_a, snap_b, nw_lo, nw_hi):
    """Drift A0 et variance 2*B0 des incréments de NW entre deux snapshots
    consécutifs, pour les entités présentes dans les deux et dont le NW au
    premier est dans la fenêtre FIXE [nw_lo, nw_hi) (spec : pas de quantile
    mouvant). Convention Fokker-Planck [YR] : A0 = -E[dX], B0 = Var[dX]/2.
    Retourne aussi dt implicite (les snapshots ne sont pas forcément à 1 pas)."""
    ids_a = {int(i): j for j, i in enumerate(snap_a["id"])}
    ids_b = {int(i): j for j, i in enumerate(snap_b["id"])}
    common = [(ja, ids_b[i]) for i, ja in ids_a.items() if i in ids_b]
    if not common:
        return None
    nw_a = snap_a["nw"]
    nw_b = snap_b["nw"]
    dx = []
    for ja, jb in common:
        x = nw_a[ja]
        if nw_lo <= x < nw_hi:
            dx.append(nw_b[jb] - x)
    if len(dx) < 30:
        return None
    dx = np.asarray(dx)
    return dict(A0=-float(np.mean(dx)), B0=float(np.var(dx)) / 2.0, n=len(dx))


# ------------------------------------------------------------- anti-cohorte

def age_diagnostics(snap, var="nw", tails_ages=((50, 150), (150, 400))):
    """corr(âge, log var>0), âges par décile de var, queue CSN à âge contrôlé."""
    v = snap[var]
    age = snap["age"].astype(float)
    pos = v > 0
    out = {}
    if pos.sum() > 10 and np.std(age[pos]) > 0:
        lv = np.log(v[pos])
        if np.std(lv) > 0:
            out["corr_age_log"] = float(np.corrcoef(age[pos], lv)[0, 1])
    # âge médian par décile de la variable (toutes valeurs, y compris <= 0)
    deciles = np.quantile(v, np.linspace(0, 1, 11))
    med_ages = []
    for d in range(10):
        lo, hi = deciles[d], deciles[d + 1]
        mask = (v >= lo) & (v < hi if d < 9 else v <= hi)
        med_ages.append(float(np.median(age[mask])) if mask.sum() else float("nan"))
    out["median_age_by_decile"] = med_ages
    out["age_q"] = [float(np.quantile(age, q)) for q in (0.1, 0.5, 0.9)]
    ctrl = {}
    for lo, hi in tails_ages:
        mask = (age >= lo) & (age < hi)
        if mask.sum() >= 150:
            fit = fit_tail_csn(v[mask][v[mask] > 0])
            if fit:
                ctrl[f"[{lo},{hi})"] = dict(alpha=fit["alpha"], x_min=fit["x_min"],
                                            n_tail=fit["n_tail"], n=int(mask.sum()))
    out["tail_age_controlled"] = ctrl
    return out


def renewal_diagnostics(snap_a, snap_b, t_a, t_b, var="nw", recent=1000):
    """Renouvellement du top décile de var entre deux snapshots (§6.3).
    - survie : fraction du top décile de t_a encore vivante à t_b ;
    - persistance : fraction encore dans le top décile à t_b ;
    - fraction du top décile de t_b née dans les `recent` derniers pas ;
    - dispersion des dates de naissance du top de t_b."""
    va, vb = snap_a[var], snap_b[var]
    thr_a = np.quantile(va, 0.9)
    top_a = set(int(i) for i, x in zip(snap_a["id"], va) if x >= thr_a)
    ids_b = set(int(i) for i in snap_b["id"])
    thr_b = np.quantile(vb, 0.9)
    top_b_mask = vb >= thr_b
    top_b = set(int(i) for i, m in zip(snap_b["id"], top_b_mask) if m)
    births_b = t_b - snap_b["age"][top_b_mask]
    if not top_a:
        return None
    return dict(
        n_top_a=len(top_a),
        survival=len(top_a & ids_b) / len(top_a),
        persistence=len(top_a & top_b) / len(top_a),
        frac_recent=float(np.mean(births_b >= t_b - recent)),
        birth_q=[float(np.quantile(births_b, q)) for q in (0.1, 0.5, 0.9)],
    )


# ---------------------------------------------------------------------- SOC

def cascade_size_distribution(series, t_min=500):
    """Distribution des faillites par pas (proxy de taille de cascade)."""
    sizes = np.array([s["deaths"] for s in series if s["t"] >= t_min])
    if len(sizes) == 0:
        return None
    vals, counts = np.unique(sizes, return_counts=True)
    out = dict(sizes=vals.tolist(), counts=counts.tolist(),
               mean=float(np.mean(sizes)), max=int(np.max(sizes)),
               p99=float(np.quantile(sizes, 0.99)))
    big = sizes[sizes > 0]
    if len(big) >= 100:
        fit = fit_tail_csn(big.astype(float), min_tail=20)
        if fit:
            out["tail_fit"] = fit
    return out


def credit_concentration(snap):
    """Part des créances totales détenue par le top décile des créancières."""
    claims = np.sort(snap["claims"])[::-1]
    total = claims.sum()
    if total <= 0:
        return None
    n_top = max(1, len(claims) // 10)
    return float(claims[:n_top].sum() / total)
