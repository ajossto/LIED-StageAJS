"""Outils statistiques du screening global M4B.

Implémente, sans dépendance au-delà de numpy/scipy :
- corrélations de rang partielles (PRCC) avec intervalles bootstrap ;
- régressions linéaires standardisées (SRC) avec intervalles bootstrap ;
- surface de réponse polynomiale de degré 2 (interactions comprises)
  validée par validation croisée par groupes de points du plan ;
- importance par permutation sur la surface validée ;
- décomposition de la variance entre cellules (paramètres) et
  intra-cellule (graines).

Convention : X est un tableau (n, p) des paramètres, y un vecteur (n,).
Les lignes correspondent à des runs ; `point_ids` regroupe les runs d'une
même cellule (mêmes paramètres, graines différentes).
"""

from __future__ import annotations

import numpy as np
from scipy import stats

DEFAULT_BOOTSTRAP = 2000


# ------------------------------------------------------------- régressions

def _rank(values: np.ndarray) -> np.ndarray:
    return stats.rankdata(values, axis=0)


def _partial_corr(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Corrélation partielle de chaque colonne de X avec y, les autres fixées."""
    n, p = X.shape
    out = np.full(p, np.nan)
    ones = np.ones((n, 1))
    for j in range(p):
        others = np.hstack([ones, np.delete(X, j, axis=1)])
        beta_x, *_ = np.linalg.lstsq(others, X[:, j], rcond=None)
        beta_y, *_ = np.linalg.lstsq(others, y, rcond=None)
        res_x = X[:, j] - others @ beta_x
        res_y = y - others @ beta_y
        sx, sy = res_x.std(), res_y.std()
        if sx > 0 and sy > 0:
            out[j] = float(np.corrcoef(res_x, res_y)[0, 1])
    return out


def prcc(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return _partial_corr(_rank(X), _rank(y))


def src(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Coefficients de régression standardisés."""
    Xs = (X - X.mean(axis=0)) / X.std(axis=0)
    ys = (y - y.mean()) / y.std() if y.std() > 0 else y - y.mean()
    design = np.hstack([np.ones((len(y), 1)), Xs])
    beta, *_ = np.linalg.lstsq(design, ys, rcond=None)
    return beta[1:]


def bootstrap_ci(estimator, X: np.ndarray, y: np.ndarray,
                 groups: np.ndarray, n_boot: int = DEFAULT_BOOTSTRAP,
                 rng_seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """IC bootstrap (2.5–97.5 %) par rééchantillonnage des cellules du plan.

    On rééchantillonne des groupes entiers (cellules) pour respecter la
    structure runs-par-graine, puis on recalcule l'estimateur.
    """
    rng = np.random.default_rng(rng_seed)
    unique_groups = np.unique(groups)
    estimates = []
    for _ in range(n_boot):
        chosen = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        index = np.concatenate([np.flatnonzero(groups == g) for g in chosen])
        try:
            estimates.append(estimator(X[index], y[index]))
        except np.linalg.LinAlgError:
            continue
    estimates = np.asarray(estimates)
    point = estimator(X, y)
    return point, np.nanpercentile(estimates, 2.5, axis=0), \
        np.nanpercentile(estimates, 97.5, axis=0)


# ---------------------------------------------------- surface de réponse

def quadratic_design(X: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """Degré 2 complet : constantes, linéaires, carrés, interactions."""
    n, p = X.shape
    columns = [np.ones(n)]
    names = ["1"]
    for j in range(p):
        columns.append(X[:, j]); names.append(f"x{j}")
    for j in range(p):
        columns.append(X[:, j] ** 2); names.append(f"x{j}^2")
    for a in range(p):
        for b in range(a + 1, p):
            columns.append(X[:, a] * X[:, b]); names.append(f"x{a}*x{b}")
    return np.column_stack(columns), names


class QuadraticSurface:
    """Surface de réponse quadratique sur variables standardisées."""

    def __init__(self) -> None:
        self.mean = None
        self.std = None
        self.beta = None

    def _standardize(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mean) / self.std

    def fit(self, X: np.ndarray, y: np.ndarray) -> "QuadraticSurface":
        self.mean = X.mean(axis=0)
        self.std = np.where(X.std(axis=0) > 0, X.std(axis=0), 1.0)
        design, self.names = quadratic_design(self._standardize(X))
        self.beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        design, _ = quadratic_design(self._standardize(X))
        return design @ self.beta


def cv_r2_by_group(model_factory, X: np.ndarray, y: np.ndarray,
                   groups: np.ndarray, n_folds: int = 8,
                   rng_seed: int = 1) -> float:
    """R² hors échantillon, plis constitués de cellules entières du plan."""
    rng = np.random.default_rng(rng_seed)
    unique_groups = rng.permutation(np.unique(groups))
    folds = np.array_split(unique_groups, n_folds)
    predictions = np.full(len(y), np.nan)
    for fold in folds:
        test = np.isin(groups, fold)
        train = ~test
        if train.sum() < 10 or test.sum() == 0:
            continue
        model = model_factory().fit(X[train], y[train])
        predictions[test] = model.predict(X[test])
    valid = np.isfinite(predictions)
    ss_res = float(np.sum((y[valid] - predictions[valid]) ** 2))
    ss_tot = float(np.sum((y[valid] - y[valid].mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def permutation_importance(model, X: np.ndarray, y: np.ndarray,
                           n_repeats: int = 30, rng_seed: int = 2) -> np.ndarray:
    """Perte moyenne de R² lorsque chaque colonne est permutée."""
    rng = np.random.default_rng(rng_seed)
    baseline_pred = model.predict(X)
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 0:
        return np.full(X.shape[1], np.nan)
    baseline_r2 = 1.0 - float(np.sum((y - baseline_pred) ** 2)) / ss_tot
    importances = np.zeros(X.shape[1])
    for j in range(X.shape[1]):
        losses = []
        for _ in range(n_repeats):
            Xp = X.copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            pred = model.predict(Xp)
            r2 = 1.0 - float(np.sum((y - pred) ** 2)) / ss_tot
            losses.append(baseline_r2 - r2)
        importances[j] = float(np.mean(losses))
    return importances


# ------------------------------------------------- décomposition variance

def variance_decomposition(y: np.ndarray, groups: np.ndarray) -> dict:
    """Part de variance entre cellules (paramètres) et intra-cellule (graines).

    Estimateur ANOVA à effets aléatoires (méthode des moments, groupes
    équilibrés ou non).
    """
    unique_groups = np.unique(groups)
    n = len(y)
    grand_mean = y.mean()
    ss_between = 0.0
    ss_within = 0.0
    sizes = []
    for g in unique_groups:
        values = y[groups == g]
        sizes.append(len(values))
        ss_between += len(values) * (values.mean() - grand_mean) ** 2
        ss_within += float(np.sum((values - values.mean()) ** 2))
    k = len(unique_groups)
    df_between, df_within = k - 1, n - k
    if df_within <= 0 or df_between <= 0:
        return {"var_between_frac": float("nan"), "var_within_frac": float("nan")}
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    sizes = np.asarray(sizes)
    n0 = (n - float(np.sum(sizes ** 2)) / n) / df_between
    var_between = max(0.0, (ms_between - ms_within) / n0)
    total = var_between + ms_within
    return {
        "var_between_frac": var_between / total if total > 0 else float("nan"),
        "var_within_frac": ms_within / total if total > 0 else float("nan"),
        "sd_between": float(np.sqrt(var_between)),
        "sd_within": float(np.sqrt(ms_within)),
    }
