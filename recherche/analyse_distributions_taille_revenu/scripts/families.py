"""Ladder of candidate distribution families for positive economic variables
(entity size / income), fit by MLE, compared by AIC/BIC.

Reuses the existing lognormal-mixture and lognormal+Pareto-tail fitters from
modele-27-04-WIP/src/analysis.py (already MLE-based) instead of reimplementing them.
"""
import math
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)
from scipy import stats
from scipy.optimize import minimize
from scipy.special import betaln

# scripts/ -> analyse_distributions_taille_revenu/ -> recherche/ -> jupyter/ (repo root)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "modele-27-04-WIP", "src"))
import analysis as _an  # noqa: E402


def _aic_bic(neg_ll, k, n):
    aic = 2 * k + 2 * neg_ll
    bic = k * math.log(n) + 2 * neg_ll
    return aic, bic


def fit_pareto_1p(pos):
    x_min = float(np.min(pos))
    n = len(pos)
    alpha = n / np.sum(np.log(pos / x_min))
    if not math.isfinite(alpha) or alpha <= 0:
        return None
    neg_ll = -np.sum(stats.pareto.logpdf(pos, b=alpha, scale=x_min))
    aic, bic = _aic_bic(neg_ll, 1, n)
    return dict(name="pareto_1p", k=1, params=dict(alpha=alpha, x_min=x_min),
                neg_ll=float(neg_ll), aic=aic, bic=bic)


def fit_expon_1p(pos):
    # loc fixed at data min (support boundary known), 1 free scale param
    x_min = float(np.min(pos))
    loc, scale = stats.expon.fit(pos, floc=x_min)
    neg_ll = -np.sum(stats.expon.logpdf(pos, loc=loc, scale=scale))
    n = len(pos)
    aic, bic = _aic_bic(neg_ll, 1, n)
    return dict(name="expon_1p", k=1, params=dict(loc=loc, scale=scale),
                neg_ll=float(neg_ll), aic=aic, bic=bic)


def _scipy_fit(dist, pos, k, name, **fitkw):
    try:
        params = dist.fit(pos, **fitkw)
    except Exception:
        return None
    neg_ll = -np.sum(dist.logpdf(pos, *params))
    if not math.isfinite(neg_ll):
        return None
    n = len(pos)
    aic, bic = _aic_bic(neg_ll, k, n)
    return dict(name=name, k=k, params=params, neg_ll=float(neg_ll), aic=aic, bic=bic)


def fit_lognorm_2p(pos):
    return _scipy_fit(stats.lognorm, pos, 2, "lognorm_2p", floc=0)


def fit_gamma_2p(pos):
    return _scipy_fit(stats.gamma, pos, 2, "gamma_2p", floc=0)


def fit_weibull_2p(pos):
    return _scipy_fit(stats.weibull_min, pos, 2, "weibull_2p", floc=0)


def fit_fisk_2p(pos):
    return _scipy_fit(stats.fisk, pos, 2, "fisk_2p", floc=0)  # loglogistic


def fit_lognorm_3p(pos):
    return _scipy_fit(stats.lognorm, pos, 3, "lognorm_3p")  # free loc


def fit_gengamma_3p(pos):
    return _scipy_fit(stats.gengamma, pos, 3, "gengamma_3p", floc=0)


def fit_singhmaddala_3p(pos):
    # Burr Type XII == Singh-Maddala
    return _scipy_fit(stats.burr12, pos, 3, "singhmaddala_3p", floc=0)


def fit_dagum_3p(pos):
    # scipy 'burr' == Burr Type III == Dagum
    return _scipy_fit(stats.burr, pos, 3, "dagum_3p", floc=0)


def _gb2_negll(p, x):
    a, b, pp, q = p
    if a <= 1e-6 or b <= 1e-6 or pp <= 1e-6 or q <= 1e-6:
        return 1e12
    log_z = np.log(x) - np.log(b)
    # log(1 + z**a) computed stably via logaddexp(0, a*log_z) to avoid overflow for large z
    log1p_za = np.logaddexp(0.0, a * log_z)
    log_f = (math.log(a) + (a * pp - 1) * log_z - betaln(pp, q)
              - (pp + q) * log1p_za) - math.log(b)
    if not np.all(np.isfinite(log_f)):
        return 1e12
    return -np.sum(log_f)


def fit_gb2_4p(pos, seed_fits=None):
    """Generalized Beta of the Second Kind (McDonald 1984). 4 free params a,b,p,q."""
    n = len(pos)
    scale0 = float(np.median(pos))
    starts = [
        (2.0, scale0, 1.0, 1.0),
        (1.5, scale0, 2.0, 1.0),
        (1.5, scale0, 1.0, 2.0),
        (3.0, scale0, 0.5, 0.5),
        (0.7, scale0, 4.0, 4.0),
        (4.0, scale0, 0.3, 0.3),
    ]
    if seed_fits:
        sm = seed_fits.get("singhmaddala_3p")
        if sm is not None:
            c, d, _, scale = sm["params"]
            starts.append((c, scale, d, 1.0))
        dg = seed_fits.get("dagum_3p")
        if dg is not None:
            c, d, _, scale = dg["params"]
            starts.append((c, scale, 1.0, d))
    bounds = [(1e-3, 50), (scale0 * 1e-4, scale0 * 1e4), (1e-3, 50), (1e-3, 50)]
    best = None
    for x0 in starts:
        for method in ("Nelder-Mead", "Powell"):
            try:
                res = minimize(_gb2_negll, x0, args=(pos,), method=method, bounds=bounds,
                                options={"maxiter": 8000, "xatol": 1e-10, "fatol": 1e-10})
                if res.fun >= 1e11:
                    continue
                if best is None or res.fun < best.fun:
                    best = res
            except Exception:
                continue
    if best is None:
        return None
    a, b, pp, q = best.x
    neg_ll = float(best.fun)
    aic, bic = _aic_bic(neg_ll, 4, n)
    return dict(name="gb2_4p", k=4, params=dict(a=a, b=b, p=pp, q=q),
                neg_ll=neg_ll, aic=aic, bic=bic)


def fit_lognormal_mixture_5p(values):
    fit = _an._fit_lognormal_mixture(values)
    if fit is None:
        return None
    lam, mu1, s1, mu2, s2 = fit
    pos = np.array([v for v in values if v > 0])
    f1 = stats.lognorm.pdf(pos, s=s1, scale=np.exp(mu1))
    f2 = stats.lognorm.pdf(pos, s=s2, scale=np.exp(mu2))
    neg_ll = -np.sum(np.log(np.maximum(lam * f1 + (1 - lam) * f2, 1e-300)))
    n = len(pos)
    aic, bic = _aic_bic(neg_ll, 5, n)
    return dict(name="lognorm_mix_5p", k=5,
                params=dict(lam=lam, mu1=mu1, s1=s1, mu2=mu2, s2=s2),
                neg_ll=float(neg_ll), aic=aic, bic=bic)


def fit_lognormal_pareto_mixture_5p(values):
    fit = _an._fit_lognormal_pareto(values)
    if fit is None:
        return None
    lam, mu, s, alpha, x_min = fit
    pos = np.array([v for v in values if v > 0])
    f1 = stats.lognorm.pdf(pos, s=s, scale=np.exp(mu))
    f2 = stats.pareto.pdf(pos, b=alpha, scale=x_min)
    neg_ll = -np.sum(np.log(np.maximum(lam * f1 + (1 - lam) * f2, 1e-300)))
    n = len(pos)
    aic, bic = _aic_bic(neg_ll, 5, n)
    return dict(name="lognorm_pareto_mix_5p", k=5,
                params=dict(lam=lam, mu=mu, s=s, alpha=alpha, x_min=x_min),
                neg_ll=float(neg_ll), aic=aic, bic=bic)


LADDER = [
    fit_pareto_1p, fit_expon_1p,
    fit_lognorm_2p, fit_gamma_2p, fit_weibull_2p, fit_fisk_2p,
    fit_lognorm_3p, fit_gengamma_3p, fit_singhmaddala_3p, fit_dagum_3p,
    fit_gb2_4p,
    fit_lognormal_mixture_5p, fit_lognormal_pareto_mixture_5p,
]


def fit_all(values, min_n=30):
    pos = np.asarray([v for v in values if v is not None and v > 0], dtype=float)
    if len(pos) < min_n:
        return None
    results = {}
    for fn in LADDER:
        try:
            if fn is fit_gb2_4p:
                r = fn(pos, seed_fits=results)
            else:
                r = fn(pos)
        except Exception:
            r = None
        if r is not None and math.isfinite(r["aic"]):
            results[r["name"]] = r
    return results


def best_per_k(results):
    """Best (lowest AIC) model for each parameter count present."""
    by_k = {}
    for r in results.values():
        k = r["k"]
        if k not in by_k or r["aic"] < by_k[k]["aic"]:
            by_k[k] = r
    return by_k
