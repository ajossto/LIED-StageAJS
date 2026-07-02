"""Clauset-Shalizi-Newman-style power-law tail test (continuous data, MLE + KS xmin)."""
import math

import numpy as np
from scipy import stats


def _pareto_ks(x_tail, x_min, alpha):
    x_tail = np.sort(x_tail)
    n = len(x_tail)
    cdf_emp = np.arange(1, n + 1) / n
    cdf_fit = 1 - (x_tail / x_min) ** (-alpha)
    return float(np.max(np.abs(cdf_emp - cdf_fit)))


def fit_powerlaw_xmin(values, n_candidates=40, min_tail=30):
    """Scan candidate xmin (quantile grid), pick xmin minimizing KS distance.
    Returns dict(x_min, alpha, ks, n_tail) or None.
    """
    pos = np.sort(np.asarray([v for v in values if v > 0], dtype=float))
    n = len(pos)
    if n < min_tail * 2:
        return None
    qs = np.linspace(0, 0.90, n_candidates)
    candidates = np.unique(np.quantile(pos, qs))
    best = None
    for x_min in candidates:
        tail = pos[pos >= x_min]
        if len(tail) < min_tail:
            continue
        alpha = 1 + len(tail) / np.sum(np.log(tail / x_min))
        if not math.isfinite(alpha) or alpha <= 1.0:
            continue
        ks = _pareto_ks(tail, x_min, alpha - 1)  # note: pareto.pdf uses b=alpha-1 convention below
        # here we keep alpha as CSN alpha (exponent of pdf ~ x^-alpha); scipy pareto b = alpha-1
        if best is None or ks < best["ks"]:
            best = dict(x_min=float(x_min), alpha=float(alpha), ks=float(ks), n_tail=len(tail))
    return best


def lognormal_vs_powerlaw_lr(values, x_min, alpha):
    """Vuong-style loglik-ratio test restricted to x >= x_min.
    Returns (R, p) where R>0 favors power law, R<0 favors lognormal.
    """
    pos = np.asarray([v for v in values if v > 0], dtype=float)
    tail = pos[pos >= x_min]
    n = len(tail)
    if n < 20:
        return None
    b_pareto = alpha - 1  # scipy convention: pdf = b * xmin^b / x^(b+1)
    ll_pl = stats.pareto.logpdf(tail, b=b_pareto, scale=x_min)

    log_tail = np.log(tail)
    mu = float(np.mean(log_tail))
    sigma = float(np.std(log_tail))
    if sigma < 1e-9:
        return None
    ll_ln = stats.lognorm.logpdf(tail, s=sigma, scale=math.exp(mu))

    diff = ll_pl - ll_ln
    R = float(np.sum(diff))
    sd = float(np.std(diff))
    if sd < 1e-12:
        return dict(R=R, p=float("nan"), n_tail=n)
    z = R / (sd * math.sqrt(n))
    p = float(2 * (1 - stats.norm.cdf(abs(z))))
    return dict(R=R, z=float(z), p=p, n_tail=n)
