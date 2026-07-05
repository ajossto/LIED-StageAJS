"""Double Pareto-lognormale (dPlN, Reed & Jorgensen 2004).

X = exp(Y) avec Y ~ Normal-Laplace NL(nu, tau, a, b) : Y = Z + W,
Z ~ N(nu, tau^2), W ~ Laplace asymétrique (queue droite exp(-a w), queue
gauche exp(b w)). X a une queue droite Pareto d'exposant de pdf a+1 et une
queue gauche en x^{b-1} — c'est le modèle nul démographique de Reed pour le
revenu (GBM x âges exponentiels).

Densité NL (forme numériquement stable, en log) :
  f(y) = (a b / (a+b)) [ A(y) + B(y) ]
  log A = a(nu - y) + a^2 tau^2 / 2 + log Phi((y - nu - a tau^2)/tau)
  log B = b(y - nu) + b^2 tau^2 / 2 + log Phi(-(y - nu + b tau^2)/tau)
MLE en log-paramètres (tau, a, b > 0), multi-départs Nelder-Mead.
Validé sur données synthétiques avant tout usage réel (tests/test_analysis.py).
"""
import math

import numpy as np
from scipy import stats
from scipy.optimize import minimize


def nl_logpdf(y, nu, tau, a, b):
    """log-pdf Normal-Laplace, vectorisée, stable numériquement."""
    y = np.asarray(y, dtype=float)
    z = (y - nu) / tau
    log_a_term = a * (nu - y) + 0.5 * a * a * tau * tau \
        + stats.norm.logcdf(z - a * tau)
    log_b_term = b * (y - nu) + 0.5 * b * b * tau * tau \
        + stats.norm.logcdf(-(z + b * tau))
    return math.log(a) + math.log(b) - math.log(a + b) \
        + np.logaddexp(log_a_term, log_b_term)


def dpln_logpdf(x, nu, tau, a, b):
    """log-pdf de X = exp(Y) : f_X(x) = f_Y(ln x)/x, x > 0."""
    x = np.asarray(x, dtype=float)
    return nl_logpdf(np.log(x), nu, tau, a, b) - np.log(x)


def dpln_rvs(nu, tau, a, b, size, rng):
    """Échantillon dPlN : exp(nu + tau*Z + E1/a - E2/b)."""
    z = rng.normal(0.0, 1.0, size)
    e1 = rng.exponential(1.0, size)
    e2 = rng.exponential(1.0, size)
    return np.exp(nu + tau * z + e1 / a - e2 / b)


def fit_dpln(x, n_starts=4):
    """MLE de la dPlN sur x > 0. Retourne dict(params, loglik, aic, bic, n)
    ou None si échec. Paramétrage optimisé : (nu, log tau, log a, log b)."""
    x = np.asarray([v for v in x if v > 0], dtype=float)
    n = len(x)
    if n < 100:
        return None
    y = np.log(x)
    m, sd = float(np.mean(y)), max(float(np.std(y)), 1e-3)

    def negll(theta):
        nu, lt, la, lb = theta
        tau, a, b = math.exp(lt), math.exp(la), math.exp(lb)
        if tau > 50 or a > 1e4 or b > 1e4:
            return 1e12
        ll = float(np.sum(nl_logpdf(y, nu, tau, a, b)))
        return -ll if math.isfinite(ll) else 1e12

    starts = [
        (m, math.log(sd), math.log(2.0 / sd), math.log(2.0 / sd)),
        (m, math.log(sd * 0.5), math.log(1.0 / sd), math.log(3.0 / sd)),
        (m - sd, math.log(sd), math.log(3.0 / sd), math.log(1.0 / sd)),
        (m, math.log(sd * 0.25), math.log(0.5 / sd), math.log(0.5 / sd)),
    ][:n_starts]
    best = None
    for th0 in starts:
        res = minimize(negll, th0, method="Nelder-Mead",
                       options={"maxiter": 4000, "xatol": 1e-7, "fatol": 1e-7})
        if best is None or res.fun < best.fun:
            best = res
    if best is None or not math.isfinite(best.fun) or best.fun >= 1e11:
        return None
    nu, lt, la, lb = best.x
    tau, a, b = math.exp(lt), math.exp(la), math.exp(lb)
    ll_y = -float(best.fun)
    # vraisemblance sur x (jacobienne 1/x) pour comparaison AIC avec les
    # familles ajustées sur x : ll_x = ll_y - sum(log x)
    ll_x = ll_y - float(np.sum(y))
    k = 4
    return dict(params=dict(nu=float(nu), tau=float(tau), a=float(a), b=float(b)),
                loglik=ll_x, aic=2 * k - 2 * ll_x,
                bic=k * math.log(n) - 2 * ll_x, n=n,
                tail_alpha_pdf=float(a) + 1.0)
