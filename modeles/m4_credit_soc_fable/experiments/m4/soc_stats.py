"""Statistiques SOC d'un run M4 : distribution des tailles d'avalanches.

Critères du brief (PROMPT_M4_SOC.md, « Critères de succès ») :
1. régression log-log sur densité log-binnée, AVEC et HORS taille 1 —
   le marqueur principal est r² > 0,90 hors taille 1 ;
2. scaling en taille finie : cutoff (s_max, p99, <s²>/<s>) vs taille système ;
3. fit de loi de puissance DISCRÈTE (zêta de Hurwitz, MLE, scan de s_min par
   KS) + test LR de Vuong contre une lognormale DISCRÈTE normalisée sur le
   même support x >= s_min — pièges M2/M3 évités : pas de MLE continu sur des
   entiers presque tous égaux à 1 (rapport 05), pas de lognormale non
   renormalisée (piège n°1) ;
7. garde anti-effondrement : fraction de la population emportée par la plus
   grande avalanche, bimodalité (trou entre le gros événement et le reste).

Usage : /home/anatole/jupyter/.venv/bin/python3 soc_stats.py <run_dir> ...
Écrit <run_dir>/figures/soc_stats.json et affiche un résumé une ligne.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.special import zeta as hurwitz_zeta

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))

from m4.metrics import load_avalanches, load_series  # noqa: E402


# ------------------------------------------------------- régression log-log

def _log_bin_edges(smax: float, n_bins: int) -> np.ndarray:
    """Bins log-espacés sur tailles entières 1..smax (copie de la recette
    webapp/mpl_figures.py : une taille par bin près de 1, regroupement
    progressif dans la queue clairsemée)."""
    edges = np.unique(np.round(np.logspace(0, np.log10(smax), n_bins)))
    if len(edges) < 2:
        edges = np.array([1.0, smax + 1.0])
    elif edges[-1] < smax:
        edges = np.append(edges, smax)
    edges = edges.astype(float)
    edges[-1] += 1e-9
    return edges


def loglog_regression(sizes: np.ndarray, exclude_one: bool) -> dict | None:
    """Pente/r² OLS de ln(densité) vs ln(taille) sur bins log (comptage > 0).
    exclude_one : retire les bins dont le bord gauche est <= 1 (taille 1)."""
    if len(sizes) == 0:
        return None
    smax = sizes.max()
    if smax < 2:
        return None
    n_bins = max(8, min(30, int(np.ceil(np.log2(len(sizes)) + 1))))
    edges = _log_bin_edges(float(smax), n_bins)
    counts, edges = np.histogram(sizes, bins=edges)
    widths = np.diff(edges)
    centres = np.sqrt(edges[:-1] * edges[1:])
    density = counts / widths
    mask = counts > 0
    if exclude_one:
        mask &= edges[:-1] > 1
    if mask.sum() < 3:
        return None
    x = np.log(centres[mask])
    y = np.log(density[mask])
    n = len(x)
    A = np.vstack([np.ones(n), x]).T
    coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    y_hat = A @ coef
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    dof = max(n - 2, 1)
    var_x = float(np.sum((x - x.mean()) ** 2))
    slope_se = math.sqrt(ss_res / dof / var_x) if var_x > 0 else float("nan")
    return dict(slope=float(coef[1]), slope_se=slope_se, r2=r2, n_bins=n,
                n_events=int(mask.sum() and counts[mask].sum()))


# ------------------------------------------- loi de puissance discrète (MLE)

def _discrete_pl_negll(alpha: float, sizes: np.ndarray, s_min: int) -> float:
    if alpha <= 1.0:
        return 1e12
    z = hurwitz_zeta(alpha, s_min)
    if not (z > 0 and math.isfinite(z)):
        return 1e12
    return len(sizes) * math.log(z) + alpha * float(np.sum(np.log(sizes)))


def _fit_alpha_discrete(sizes: np.ndarray, s_min: int) -> float | None:
    """MLE de alpha par recherche ternaire sur [1.01, 20]."""
    lo, hi = 1.01, 20.0
    for _ in range(200):
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        if _discrete_pl_negll(m1, sizes, s_min) < _discrete_pl_negll(m2, sizes, s_min):
            hi = m2
        else:
            lo = m1
    alpha = 0.5 * (lo + hi)
    if alpha >= 19.5:
        return None  # bord : pas une loi de puissance identifiable
    return alpha


def _discrete_pl_cdf(xs: np.ndarray, alpha: float, s_min: int) -> np.ndarray:
    z = hurwitz_zeta(alpha, s_min)
    pmf_support = np.arange(s_min, xs.max() + 1, dtype=float) ** (-alpha) / z
    cum = np.cumsum(pmf_support)
    return cum[(xs - s_min).astype(int)]


def fit_tail_discrete(sizes: np.ndarray, s_min_max: int = 10,
                      min_tail: int = 50) -> dict | None:
    """Scan de s_min (1..s_min_max), MLE zêta, choix par KS minimal (CSN
    discret). sizes : entiers >= 1."""
    best = None
    for s_min in range(1, s_min_max + 1):
        tail = sizes[sizes >= s_min]
        if len(tail) < min_tail or tail.max() <= s_min:
            continue
        alpha = _fit_alpha_discrete(tail, s_min)
        if alpha is None:
            continue
        xs = np.sort(np.unique(tail))
        cdf_fit = _discrete_pl_cdf(xs, alpha, s_min)
        cdf_emp = np.searchsorted(np.sort(tail), xs, side="right") / len(tail)
        ks = float(np.max(np.abs(cdf_emp - cdf_fit)))
        if best is None or ks < best["ks"]:
            best = dict(s_min=s_min, alpha=float(alpha), ks=ks,
                        n_tail=int(len(tail)))
    return best


# -------------------------- loi de puissance discrète à cutoff exponentiel

def fit_pl_cutoff(sizes: np.ndarray, s_min: int) -> dict | None:
    """MLE de p(x) ∝ x^-alpha * exp(-x/x_c) sur x >= s_min (discret,
    normalisation numérique sur s_min..X). Le modèle attendu d'un régime
    critique en taille finie : exposant + cutoff d'échelle."""
    from scipy.optimize import minimize
    tail = sizes[sizes >= s_min].astype(float)
    n = len(tail)
    if n < 30 or tail.max() <= s_min:
        return None
    x_hi = int(max(1000, 100 * tail.max()))
    support = np.arange(s_min, x_hi + 1, dtype=float)
    log_support = np.log(support)
    sum_log = float(np.sum(np.log(tail)))
    sum_x = float(np.sum(tail))

    def negll(theta):
        alpha, log_xc = theta
        if not (0.0 < alpha < 20.0 and -5.0 < log_xc < 25.0):
            return 1e12
        xc = math.exp(log_xc)
        logw = -alpha * log_support - support / xc
        m = logw.max()
        z = m + math.log(np.sum(np.exp(logw - m)))
        ll = -alpha * sum_log - sum_x / xc - n * z
        return -ll if math.isfinite(ll) else 1e12

    best = None
    for a0 in (1.5, 2.5, 4.0):
        for lxc0 in (math.log(max(tail.max(), 2.0)), 10.0):
            res = minimize(negll, [a0, lxc0], method="Nelder-Mead",
                           options={"maxiter": 2000, "xatol": 1e-6,
                                    "fatol": 1e-9})
            if best is None or res.fun < best.fun:
                best = res
    if best is None or not math.isfinite(best.fun) or best.fun >= 1e11:
        return None
    alpha, log_xc = best.x
    return dict(alpha=float(alpha), x_c=float(math.exp(log_xc)),
                negll=float(best.fun), n_tail=n, s_min=s_min)


def lr_plcutoff_vs_lognormal(sizes: np.ndarray, s_min: int) -> dict | None:
    """LR de Vuong (non emboîtés) : PL×cutoff vs lognormale discrète, tous
    deux normalisés sur x >= s_min. R > 0 favorise PL×cutoff. Le verdict
    honnête du critère 3 en taille finie : la PL PURE est toujours battue
    par la lognormale à cause du cutoff, ce qui ne discrimine pas le
    mécanisme."""
    fit = fit_pl_cutoff(sizes, s_min)
    if fit is None:
        return None
    tail = sizes[sizes >= s_min].astype(float)
    n = len(tail)
    x_hi = int(max(1000, 100 * tail.max()))
    support = np.arange(s_min, x_hi + 1, dtype=float)
    lt = np.log(tail)

    # log-pmf PL×cutoff aux points observés
    alpha, xc = fit["alpha"], fit["x_c"]
    logw = -alpha * np.log(support) - support / xc
    m = logw.max()
    z_plc = m + math.log(np.sum(np.exp(logw - m)))
    ll_plc = -alpha * lt - tail / xc - z_plc

    # MLE lognormale discrète (même recette que lr_discrete_pl_vs_lognormal)
    mu0, s0 = float(lt.mean()), max(float(lt.std()), 0.05)

    def negll_ln(mu, s):
        pmf = _discrete_pmf_ln(support, mu, s)
        zz = pmf.sum()
        if not (zz > 0):
            return 1e12
        ll = (np.sum(-((lt - mu) ** 2) / (2 * s * s) - lt) - n * math.log(zz))
        return -float(ll)

    best = (negll_ln(mu0, s0), mu0, s0)
    for _ in range(3):
        _, mu_c, s_c = best
        for mu in np.linspace(mu_c - 2, mu_c + 2, 9):
            for s in np.linspace(max(0.05, s_c / 2), s_c * 2, 9):
                v = negll_ln(mu, s)
                if v < best[0]:
                    best = (v, float(mu), float(s))
    _, mu, s = best
    pmf_ln = _discrete_pmf_ln(support, mu, s)
    z_ln = pmf_ln.sum()
    ll_ln = -((lt - mu) ** 2) / (2 * s * s) - lt - math.log(z_ln)

    diff = ll_plc - ll_ln
    R = float(np.sum(diff))
    sd = float(np.std(diff))
    if sd < 1e-12:
        return dict(R=R, z=float("nan"), p=float("nan"), n_tail=n, **{
            "alpha": alpha, "x_c": xc})
    from scipy import stats as sps
    zv = R / (sd * math.sqrt(n))
    return dict(R=R, z=float(zv), p=float(2 * (1 - sps.norm.cdf(abs(zv)))),
                n_tail=n, alpha=alpha, x_c=xc, ln_mu=mu, ln_s=s)


# ------------------------------- LR Vuong : PL discrète vs lognormale discrète

def _discrete_pmf_ln(support: np.ndarray, mu: float, s: float) -> np.ndarray:
    """Masse lognormale discrétisée (densité au point entier), non normalisée."""
    lx = np.log(support)
    return np.exp(-((lx - mu) ** 2) / (2 * s * s)) / support


def lr_discrete_pl_vs_lognormal(sizes: np.ndarray, s_min: int,
                                alpha: float) -> dict | None:
    """LR de Vuong sur x >= s_min ; les DEUX pmf normalisées numériquement sur
    le même support s_min..X (X >> max observé) — renormalisation explicite,
    piège n°1 de M2/M3 évité par construction. R > 0 favorise la loi de
    puissance."""
    tail = sizes[sizes >= s_min].astype(float)
    n = len(tail)
    if n < 30:
        return None
    x_hi = int(max(1000, 100 * tail.max()))
    support = np.arange(s_min, x_hi + 1, dtype=float)

    # MLE lognormale discrète tronquée (grille grossière puis raffinement)
    lt = np.log(tail)
    mu0, s0 = float(lt.mean()), max(float(lt.std()), 0.05)

    def negll_ln(mu, s):
        pmf = _discrete_pmf_ln(support, mu, s)
        z = pmf.sum()
        if not (z > 0):
            return 1e12
        ll = (np.sum(-((lt - mu) ** 2) / (2 * s * s) - lt) - n * math.log(z))
        return -float(ll)

    best = (negll_ln(mu0, s0), mu0, s0)
    for _ in range(3):
        _, mu_c, s_c = best
        for mu in np.linspace(mu_c - 2, mu_c + 2, 9):
            for s in np.linspace(max(0.05, s_c / 2), s_c * 2, 9):
                v = negll_ln(mu, s)
                if v < best[0]:
                    best = (v, float(mu), float(s))
    _, mu, s = best

    z_pl = hurwitz_zeta(alpha, s_min)
    ll_pl = -alpha * lt - math.log(z_pl)
    pmf_ln = _discrete_pmf_ln(support, mu, s)
    z_ln = pmf_ln.sum()
    ll_ln = -((lt - mu) ** 2) / (2 * s * s) - lt - math.log(z_ln)
    diff = ll_pl - ll_ln
    R = float(np.sum(diff))
    sd = float(np.std(diff))
    if sd < 1e-12:
        return dict(R=R, z=float("nan"), p=float("nan"), n_tail=n)
    from scipy import stats as sps
    zv = R / (sd * math.sqrt(n))
    return dict(R=R, z=float(zv), p=float(2 * (1 - sps.norm.cdf(abs(zv)))),
                n_tail=n, ln_mu=mu, ln_s=s)


# ------------------------------------------------------------ stats d'un run

def soc_stats(run_dir, t_min=None) -> dict:
    """Toutes les stats SOC d'un run. t_min : burn-in (défaut T//4)."""
    run_dir = Path(run_dir)
    series = load_series(run_dir)
    T = series[-1]["t"]
    if t_min is None:
        t_min = T // 4
    avs = [a for a in load_avalanches(run_dir) if a["t"] >= t_min]
    sizes = np.array([a["size"] for a in avs], dtype=np.int64)
    pops = np.array([s["pop"] for s in series if s["t"] >= t_min], dtype=float)
    out = dict(run=run_dir.name, T=T, t_min=t_min,
               pop_mean=float(pops.mean()), pop_final=float(pops[-1]),
               n_avalanches=int(len(sizes)))
    if len(sizes) == 0:
        return out
    out.update(
        max_size=int(sizes.max()),
        p99=float(np.quantile(sizes, 0.99)),
        mean_size=float(sizes.mean()),
        frac_multi=float(np.mean(sizes > 1)),
        var_over_mean=float(sizes.var() / sizes.mean()),
        # <s²>/<s> : échelle de cutoff (susceptibilité), croît avec le cutoff
        s2_over_s=float(np.mean(sizes.astype(float) ** 2) / sizes.mean()),
        # garde anti-effondrement (critère 7) : part de la population moyenne
        # emportée par le plus gros événement + trou relatif sous le max
        max_over_pop=float(sizes.max() / pops.mean()),
        gap_below_max=float(sizes.max() / np.sort(sizes)[-2])
        if len(sizes) >= 2 else float("nan"),
    )
    # rapport de branchement : fraction des morts induites par propagation
    out["branching_b"] = float(
        1.0 - sum(a["n_roots"] for a in avs) / sizes.sum())
    # structure causale des grosses avalanches : la loi de puissance seule ne
    # suffit pas (des grappes de racines synchronisées la passent) — il faut
    # racines/taille < 1 et profondeur > 2 pour parler de propagation
    big = [a for a in avs if a["size"] >= 5]
    if big:
        out["big_roots_over_size"] = float(
            np.mean([a["n_roots"] / a["size"] for a in big]))
        out["big_depth_mean"] = float(np.mean([a["depth"] for a in big]))
        out["depth_max"] = int(max(a["depth"] for a in big))
    out["reg_all"] = loglog_regression(sizes, exclude_one=False)
    out["reg_ex1"] = loglog_regression(sizes, exclude_one=True)
    fit = fit_tail_discrete(sizes)
    out["tail_fit"] = fit
    if fit is not None:
        out["lr_vs_lognormal"] = lr_discrete_pl_vs_lognormal(
            sizes, fit["s_min"], fit["alpha"])
        out["lr_plc_vs_lognormal"] = lr_plcutoff_vs_lognormal(
            sizes, fit["s_min"])
    return out


def _fmt(st: dict) -> str:
    r = st.get("reg_ex1")
    reg = (f"ex1: pente={r['slope']:.2f}±{r['slope_se']:.2f} r²={r['r2']:.3f}"
           if r else "ex1: n/a")
    fit = st.get("tail_fit")
    tf = (f"PL discrète: s_min={fit['s_min']} α={fit['alpha']:.2f}"
          if fit else "PL: n/a")
    lr = st.get("lr_vs_lognormal")
    lrs = f"LR z={lr['z']:.2f}" if lr and lr.get("z") == lr.get("z") else "LR n/a"
    plc = st.get("lr_plc_vs_lognormal")
    if plc and plc.get("z") == plc.get("z"):
        lrs += f" | PLC(α={plc['alpha']:.2f},xc={plc['x_c']:.0f}) z={plc['z']:.2f}"
    rs = st.get("big_roots_over_size")
    struct = (f"rac/taille={rs:.2f} prof_max={st.get('depth_max', 0)}"
              if rs is not None else "struct n/a")
    return (f"{st['run']}: pop={st['pop_mean']:.0f} n_av={st['n_avalanches']} "
            f"max={st.get('max_size', 0)} <s²>/<s>={st.get('s2_over_s', 0):.2f} "
            f"| {reg} | {tf} | {lrs} | {struct}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        st = soc_stats(arg)
        fig_dir = Path(arg) / "figures"
        fig_dir.mkdir(exist_ok=True)
        with open(fig_dir / "soc_stats.json", "w") as fh:
            json.dump(st, fh, indent=2)
        print(_fmt(st))
