"""Analyse de la distribution cross-sectionnelle des intérêts reçus I_i,t^recv
(Objectif A, PROMPT_M4_2B.md §6-10). Nouveau module écrit pour M4.2B — pas une
copie — qui ASSEMBLE les outils existants (families.py, tail_test.py,
pareto_convention.py, lib_metrics._gini) au lieu de réimplémenter un ajustement.

Trois précautions demandées explicitement par le prompt et absentes des
outils génériques réutilisés tels quels :

1. **Masse en zéro séparée du corps** (§6) : ``families.fit_all`` exclut déjà
   silencieusement les valeurs <= 0 (``pos = [v for v in values if v>0]``),
   mais ne rapporte JAMAIS p0 lui-même. ``zero_mass_and_positive`` le calcule
   explicitement en premier, avant tout ajustement.
2. **Seuil d'effectif minimal explicite** : ``families.fit_all`` utilise par
   défaut min_n=30 (pensé pour une distribution de taille/richesse globale,
   pas pour un snapshot d'intérêts où p0 peut être élevé) ; ``lib_metrics``
   utilise 100 pour les avalanches. Ce module utilise MIN_TAIL_N=100 par
   défaut et l'expose comme paramètre — jamais hérité implicitement.
3. **Décomposition I_i = Σ_j q_ij·r_ij** (§9) : une queue lourde de I peut
   provenir du degré entrant (beaucoup de petits prêts), du rq par arête
   (quelques prêts extrêmes), ou de leur corrélation. ``decompose_tail_sources``
   calcule les trois à partir d'un network_snapshot (lender, borrower, q, r),
   pour ne jamais confondre "la queue vient des intérêts" et "la queue vient
   du degré".

ATTENTION AU DÉCALAGE D'UN PAS (relevé en revue) : ``int_in`` d'une entité au
pas t est le paiement réellement perçu au pas t, calculé AVANT la phase de
marché du pas t (donc sur des contrats créés au plus tard au pas t-1). Un
network_snapshot pris au pas t inclut en revanche les prêts créés PENDANT le
marché du pas t. La décomposition contractuelle (Σq·r sur le réseau au pas t)
et le paiement réellement observé (int_in au pas t) ne portent donc pas
exactement sur le même ensemble de contrats si le réseau a bougé entre les
deux — comparer les deux est volontaire (§9) mais leur écart doit être lu
comme un diagnostic de flux (nouveaux contrats, fusions), pas comme une
erreur numérique.
"""

from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import families  # noqa: E402
import lib_metrics  # noqa: E402
import pareto_convention  # noqa: E402
import tail_test  # noqa: E402

MIN_TAIL_N = 100
THRESHOLD_STABILITY_FACTORS = (0.5, 2.0)


def zero_mass_and_positive(values) -> tuple[float, np.ndarray]:
    """p0 = P(I=0) et l'échantillon positif conditionnel I|I>0 (§6)."""
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    n = len(finite)
    if n == 0:
        return float("nan"), finite
    positive = finite[finite > 0]
    p0 = 1.0 - len(positive) / n
    return float(p0), positive


def _alpha_hill_at_threshold(positive: np.ndarray, x_min: float, min_n: int = MIN_TAIL_N) -> dict | None:
    """MLE α=1+n/Σlog(x/x_min) à seuil FIXÉ (pas re-scanné) — sert au test de
    stabilité du seuil (§10 : « vérifier la stabilité de l'exposant lorsque
    le seuil varie raisonnablement »). min_n DOIT correspondre au seuil
    d'admissibilité utilisé pour le scan KS primaire (fit_powerlaw_xmin) --
    sinon un refit à 2x le seuil peut passer avec n aussi bas que 20 alors
    que le xmin primaire exige 80-100, ce qui masque une estimation à haute
    variance derrière un critère qui a l'air symétrique (JOURNAL.md, révision
    du critère 1)."""
    tail = positive[positive >= x_min]
    n = len(tail)
    if n < min_n:
        return None
    alpha = 1.0 + n / np.sum(np.log(tail / x_min))
    if not np.isfinite(alpha) or alpha <= 1.0:
        return None
    return {"alpha_density": float(alpha), "kappa_ccdf": float(alpha) - 1.0,
            "x_min": float(x_min), "n_tail": int(n)}


def fit_income_distribution(values, min_n: int = MIN_TAIL_N) -> dict:
    """Ajustement complet d'un snapshot d'intérêts reçus : p0, ladder de
    corps (AIC/BIC), queue Pareto (seuil scanné par KS), test de Vuong
    tronqué/log-normal restreint à la queue, stabilité du seuil."""
    p0, positive = zero_mass_and_positive(values)
    out: dict = {"n_total": int(len(np.asarray(values))), "p0": p0, "n_positive": int(len(positive))}
    if len(positive) < min_n:
        out["identifiable"] = False
        return out
    out["identifiable"] = True

    ladder = families.fit_all(positive, min_n=min_n)
    out["body_ladder"] = ladder or {}
    out["body_best_per_k"] = families.best_per_k(ladder) if ladder else {}

    pareto_1p = families.fit_pareto_1p(positive)
    out["pareto_whole_support"] = pareto_convention.from_families_pareto_1p(pareto_1p)

    tail_fit = tail_test.fit_powerlaw_xmin(positive, min_tail=min_n)
    tail_converted = pareto_convention.from_tail_test_xmin(tail_fit)
    out["tail_powerlaw"] = tail_converted

    if tail_converted is not None:
        alpha = tail_converted["alpha_density"]
        x_min = tail_converted["x_min"]
        out["tail_vs_lognormal_lr"] = tail_test.lognormal_vs_powerlaw_lr(positive, x_min, alpha)
        out["tail_fraction"] = float(tail_converted["n_tail"] / len(positive))

        stability = {}
        for factor in THRESHOLD_STABILITY_FACTORS:
            refit = _alpha_hill_at_threshold(positive, x_min * factor, min_n=min_n)
            stability[f"x_min_times_{factor}"] = refit
        out["tail_threshold_stability"] = stability
    else:
        out["tail_fraction"] = 0.0
        out["tail_threshold_stability"] = None

    return out


def decompose_tail_sources(network_snapshot: dict) -> dict:
    """§9 : I_i = Σ_j q_ij·r_ij — dégroupe la concentration des intérêts
    (contractuels, pas le paiement réel après défaut partiel) entre le
    DEGRÉ SORTANT (deg_out, convention du moteur : nombre de prêts où
    l'entité est prêteuse — c'est le degré pertinent pour un revenu
    d'intérêt PERÇU, pas le degré entrant) et le rq moyen par arête, par
    prêteuse.

    Décomposition quantitative (corrigée après revue — la seule mesure
    fiable de la contribution relative des deux sources, la corrélation de
    Spearman ne suffisant pas à elle seule) :
        Var(log I) = Var(log deg_out) + Var(log mean_rq) + 2·Cov(log deg_out, log mean_rq)
    calculée sur les prêteuses à revenu contractuel strictement positif
    (nécessaire pour prendre le log). Les parts de variance qui en résultent
    répondent directement à §21 Q9 : « quel rôle jouent respectivement r, q
    et rq ? » — ici, quelle part de la variance du LOG-revenu vient du
    nombre de contrats plutôt que de leur taille/taux individuels.
    """
    lender = np.asarray(network_snapshot["lender"], dtype=np.int64)
    q = np.asarray(network_snapshot["q"], dtype=float)
    r = np.asarray(network_snapshot["r"], dtype=float)
    rq = q * r

    income_by_lender: defaultdict[int, float] = defaultdict(float)
    deg_out_by_lender: defaultdict[int, int] = defaultdict(int)
    for lender_id, value in zip(lender.tolist(), rq.tolist()):
        income_by_lender[lender_id] += value
        deg_out_by_lender[lender_id] += 1

    ids = sorted(income_by_lender)
    income = np.array([income_by_lender[i] for i in ids])
    deg_out = np.array([deg_out_by_lender[i] for i in ids], dtype=float)
    mean_rq = np.divide(income, deg_out, out=np.zeros_like(income), where=deg_out > 0)

    out = {
        "n_lenders": len(ids),
        "n_loans": int(len(lender)),
        "income_contractual_gini": lib_metrics._gini(income) if len(income) else float("nan"),
        "deg_out_gini": lib_metrics._gini(deg_out) if len(deg_out) else float("nan"),
    }
    if len(ids) > 10:
        out["spearman_income_vs_deg_out"] = float(stats.spearmanr(deg_out, income).statistic)
        out["spearman_income_vs_mean_rq"] = float(stats.spearmanr(mean_rq, income).statistic)
        out["spearman_deg_out_vs_mean_rq"] = float(stats.spearmanr(deg_out, mean_rq).statistic)
    else:
        out["spearman_income_vs_deg_out"] = float("nan")
        out["spearman_income_vs_mean_rq"] = float("nan")
        out["spearman_deg_out_vs_mean_rq"] = float("nan")

    positive = (income > 0) & (deg_out > 0) & (mean_rq > 0)
    if positive.sum() > 10:
        log_income = np.log(income[positive])
        log_deg = np.log(deg_out[positive])
        log_rq = np.log(mean_rq[positive])
        var_deg = float(np.var(log_deg, ddof=1))
        var_rq = float(np.var(log_rq, ddof=1))
        cov_deg_rq = float(np.cov(log_deg, log_rq, ddof=1)[0, 1])
        var_income = float(np.var(log_income, ddof=1))
        var_sum = var_deg + var_rq + 2 * cov_deg_rq
        out["log_variance_decomposition"] = {
            "var_log_income": var_income,
            "var_log_deg_out": var_deg,
            "var_log_mean_rq": var_rq,
            "cov_log_deg_out_mean_rq": cov_deg_rq,
            "var_sum_check": var_sum,  # doit ≈ var_log_income (identité exacte)
            "share_from_deg_out": var_deg / var_income if var_income > 0 else float("nan"),
            "share_from_mean_rq": var_rq / var_income if var_income > 0 else float("nan"),
            "share_from_covariance": 2 * cov_deg_rq / var_income if var_income > 0 else float("nan"),
            "n": int(positive.sum()),
        }
    else:
        out["log_variance_decomposition"] = None
    return out


def exponential_vs_powerlaw_lr(values, x_min: float, alpha_density: float) -> dict | None:
    """Vuong-style LR restreint à x>=x_min : exponentielle (1 paramètre,
    MLE sur la queue, support x_min+Exp) contre loi de puissance (α déjà
    estimé, ex. par tail_test.fit_powerlaw_xmin). R>0 favorise la loi de
    puissance. Symétrique en construction à
    tail_test.lognormal_vs_powerlaw_lr, mais avec la famille EXPLICITEMENT
    demandée par §10 ("exponentielle + raccord Pareto") et qui est la
    candidate structurelle après §9 (r≈const ⇒ I≈const×deg_out, et deg_out
    croît linéairement avec l'âge sous une mortalité ≈constante, donc un âge
    ≈exponentiel prédit un corps ≈exponentiel/Weibull — pas un artefact)."""
    pos = np.asarray([v for v in values if v > 0], dtype=float)
    tail = pos[pos >= x_min]
    n = len(tail)
    if n < 20:
        return None
    kappa = alpha_density - 1.0
    ll_pl = stats.pareto.logpdf(tail, b=kappa, scale=x_min)
    scale = float(np.mean(tail - x_min))
    if scale <= 0:
        return None
    ll_exp = stats.expon.logpdf(tail, loc=x_min, scale=scale)
    diff = ll_pl - ll_exp
    R = float(np.sum(diff))
    sd = float(np.std(diff))
    if sd < 1e-12:
        return {"R": R, "p": float("nan"), "n_tail": n}
    z = R / (sd * math.sqrt(n))
    p = float(2 * (1 - stats.norm.cdf(abs(z))))
    return {"R": R, "z": z, "p": p, "n_tail": n}


def load_all_entity_snapshots(directory, t_min: int | None = None, t_max: int | None = None):
    """Charge tous les entities_t*.npz d'un run M4.2B dans [t_min,t_max]."""
    directory = Path(directory)
    paths = sorted((directory / "snapshots").glob("entities_t*.npz"))
    out = []
    for path in paths:
        t = int(path.stem.split("_t")[-1])
        if t_min is not None and t < t_min:
            continue
        if t_max is not None and t > t_max:
            continue
        with np.load(path) as data:
            out.append((t, {key: data[key].copy() for key in data.files}))
    return out


def load_all_network_snapshots(directory, t_min: int | None = None, t_max: int | None = None):
    """Générateur (pas une liste) : à K0 élevé, un snapshot réseau peut
    compter plusieurs centaines de milliers de lignes ; matérialiser toute
    la fenêtre (jusqu'à ~90 snapshots) simultanément est ce qui faisait
    dépasser le budget mémoire en analyse à K0=2000 (JOURNAL.md, §11) alors
    que le moteur lui-même terminait le run sans problème. Chaque appelant
    ne traite qu'un snapshot à la fois (compare_laws/decompose_tail_sources
    n'ont besoin que de l'élément courant)."""
    directory = Path(directory)
    paths = sorted((directory / "snapshots").glob("network_t*.npz"))
    for path in paths:
        t = int(path.stem.split("_t")[-1])
        if t_min is not None and t < t_min:
            continue
        if t_max is not None and t > t_max:
            continue
        with np.load(path) as data:
            yield t, {key: data[key].copy() for key in data.files}


def fit_across_snapshots(directory, t_min: int, t_max: int, min_n: int = MIN_TAIL_N) -> tuple[list[dict], dict]:
    """§10 : « l'unité naturelle de réplication est le snapshot ». Ajuste
    CHAQUE snapshot séparément (pas de pooling temporel) et résume la série
    des α̂ obtenus — stabilité entre snapshots, pas juste au sein d'un seul."""
    snapshots = load_all_entity_snapshots(directory, t_min, t_max)
    rows = []
    for t, snap in snapshots:
        fit = fit_income_distribution(snap["int_in"], min_n=min_n)
        fit["t"] = t
        if fit["identifiable"] and fit["tail_powerlaw"] is not None:
            alpha = fit["tail_powerlaw"]["alpha_density"]
            x_min = fit["tail_powerlaw"]["x_min"]
            fit["tail_vs_exponential_lr"] = exponential_vs_powerlaw_lr(snap["int_in"], x_min, alpha)
        else:
            fit["tail_vs_exponential_lr"] = None
        rows.append(fit)

    identifiable = [row for row in rows if row["identifiable"] and row["tail_powerlaw"] is not None]
    alphas = np.array([row["tail_powerlaw"]["alpha_density"] for row in identifiable])
    p0s = np.array([row["p0"] for row in rows if np.isfinite(row["p0"])])
    summary = {
        "n_snapshots": len(rows),
        "n_identifiable": len(identifiable),
        "p0_mean": float(p0s.mean()) if len(p0s) else float("nan"),
        "p0_std": float(p0s.std(ddof=1)) if len(p0s) > 1 else float("nan"),
        "alpha_density_mean": float(alphas.mean()) if len(alphas) else float("nan"),
        "alpha_density_std": float(alphas.std(ddof=1)) if len(alphas) > 1 else float("nan"),
        "alpha_density_min": float(alphas.min()) if len(alphas) else float("nan"),
        "alpha_density_max": float(alphas.max()) if len(alphas) else float("nan"),
    }
    return rows, summary


def age_income_relationship(entity_snapshot: dict) -> dict:
    """Test discriminant (revue) de l'hypothèse structurelle §9 : si
    r≈constante, I_i≈constante×deg_out(i), et si deg_out croît avec l'âge
    (accumulation de prêts émis au fil du temps) sous une mortalité à taux
    ≈constant (âge ≈ exponentiel), alors le corps exponentiel/Weibull observé
    n'est pas un artefact de l'ajustement mais la signature attendue. Calcule
    la régression log-linéaire E[int_in|age] et un test exponentiel sur la
    distribution des âges elle-même (MLE + KS)."""
    age = np.asarray(entity_snapshot["age"], dtype=float)
    int_in = np.asarray(entity_snapshot["int_in"], dtype=float)
    positive = int_in > 0
    out: dict = {"n_entities": int(len(age)), "n_positive_income": int(positive.sum())}
    if positive.sum() > 20:
        out["spearman_income_vs_age"] = float(stats.spearmanr(age[positive], int_in[positive]).statistic)
        slope, intercept, rvalue, _, _ = stats.linregress(age[positive], int_in[positive])
        out["linear_fit_income_vs_age"] = {
            "slope": float(slope), "intercept": float(intercept), "r2": float(rvalue) ** 2,
        }
    if len(age) > 20 and age.mean() > 0:
        mean_age = float(age.mean())
        ks = stats.kstest(age, "expon", args=(0.0, mean_age))
        out["age_distribution"] = {
            "mean": mean_age, "std": float(age.std(ddof=1)),
            "exponential_ks_statistic": float(ks.statistic), "exponential_ks_pvalue": float(ks.pvalue),
        }
    return out
