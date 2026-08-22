"""
plot_utils.py — Fonctions partagées pour la création de graphiques scientifiques.

Règles de bonne-séance appliquées ici :
  - Barres d'incertitude de Poisson toujours présentes sur les histogrammes
  - Normalisation correcte : density = count / (N × Δx)
  - Bins adaptatifs (Sturges ou Freedman-Diaconis)
  - Zoom inset pour les queues ou les pics scientifiquement importants
  - DPI ≥ 150 via apply_style()
"""

import math

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
from scipy import stats


def apply_style():
    """Applique le style global pour tous les graphiques du projet."""
    matplotlib.rcParams.update({
        "figure.dpi": 150,
        "figure.figsize": (10, 5),
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "figure.autolayout": True,
    })


def _sturges_bins(n: int) -> int:
    return max(5, min(50, math.ceil(math.log2(n) + 1)))


def log_histogram(
    values,
    n_bins="auto",
    ax=None,
    color=None,
    label=None,
    error_bars=True,
    title=None,
    xlabel=None,
    alpha=0.75,
):
    """
    Histogramme de densité avec axe X en échelle log.

    Normalisation : density_i = count_i / (N × Δx_linéaire_i)
    Incertitude Poisson : sigma_i = sqrt(count_i) / (N × Δx_linéaire_i)

    Pour un bin avec count=1 : sigma = density (100 % d'incertitude — visible !)

    Returns: (ax, edges, densities, errors)  — tous numpy arrays
    """
    if ax is None:
        _, ax = plt.subplots()

    arr = np.array([v for v in values if np.isfinite(v) and v > 0], dtype=float)
    n = len(arr)
    if n < 2:
        return ax, np.array([]), np.array([]), np.array([])

    if n_bins == "auto":
        n_bins = _sturges_bins(n)

    log_min = np.log10(arr.min())
    log_max = np.log10(arr.max())
    if log_max <= log_min:
        return ax, np.array([]), np.array([]), np.array([])

    edges = np.logspace(log_min, log_max, n_bins + 1)
    counts, _ = np.histogram(arr, bins=edges)
    widths = np.diff(edges)

    densities = np.where((widths > 0) & (n > 0), counts / (n * widths), 0.0)
    errors = np.where(counts > 0, np.sqrt(counts) / (n * widths), 0.0)
    centres = np.sqrt(edges[:-1] * edges[1:])

    for lo, hi, d, c in zip(edges[:-1], edges[1:], densities, counts):
        if c > 0:
            ax.bar(
                lo, d, width=hi - lo, align="edge",
                color=color or "#1f77b4", alpha=alpha,
                edgecolor="white", linewidth=0.5,
            )

    if error_bars:
        mask = counts > 0
        ax.errorbar(
            centres[mask], densities[mask], yerr=errors[mask],
            fmt="none", color="black", capsize=2, linewidth=0.8, alpha=0.7,
        )

    ax.set_xscale("log")
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.set_ylabel("Densité")

    parts = []
    if title:
        parts.append(title)
    if label:
        parts.append(label)
    parts.append(f"n={n}")
    ax.set_title("  —  ".join(parts))
    ax.grid(True, which="both", alpha=0.25)

    return ax, edges, densities, errors


def linear_histogram(
    values,
    n_bins="auto",
    ax=None,
    color=None,
    label=None,
    error_bars=True,
    title=None,
    xlabel=None,
    alpha=0.75,
):
    """
    Histogramme de densité en échelle linéaire.

    Largeur des bins : règle de Freedman-Diaconis (2 × IQR × n^{-1/3}).
    Incertitude Poisson : sigma_i = sqrt(count_i) / (N × Δx_i)

    Returns: (ax, edges, densities, errors)
    """
    if ax is None:
        _, ax = plt.subplots()

    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    n = len(arr)
    if n < 2:
        return ax, np.array([]), np.array([]), np.array([])

    if n_bins == "auto":
        iqr = float(np.percentile(arr, 75) - np.percentile(arr, 25))
        if iqr > 0:
            bw = 2 * iqr * n ** (-1 / 3)
            data_range = float(arr.max() - arr.min())
            n_bins = max(5, min(50, int(data_range / bw) + 1))
        else:
            n_bins = _sturges_bins(n)

    counts, edges = np.histogram(arr, bins=n_bins)
    widths = np.diff(edges)
    densities = np.where((widths > 0) & (n > 0), counts / (n * widths), 0.0)
    errors = np.where(counts > 0, np.sqrt(counts) / (n * widths), 0.0)
    centres = (edges[:-1] + edges[1:]) / 2

    ax.bar(
        edges[:-1], densities, width=widths, align="edge",
        color=color or "#1f77b4", alpha=alpha,
        edgecolor="white", linewidth=0.5,
    )

    if error_bars:
        mask = counts > 0
        ax.errorbar(
            centres[mask], densities[mask], yerr=errors[mask],
            fmt="none", color="black", capsize=2, linewidth=0.8, alpha=0.7,
        )

    if xlabel:
        ax.set_xlabel(xlabel)
    ax.set_ylabel("Densité")

    parts = []
    if title:
        parts.append(title)
    if label:
        parts.append(label)
    parts.append(f"n={n}")
    ax.set_title("  —  ".join(parts))
    ax.grid(True, alpha=0.25)

    return ax, edges, densities, errors


def add_zoom_inset(ax, x_range, y_range=None, loc="upper right", width="40%", height="30%"):
    """
    Ajoute un zoom inset sur ax et trace les lignes de connexion.

    x_range : (xmin, xmax) de la zone à zoomer
    y_range : (ymin, ymax) ou None (auto)
    Retourne l'axe inset (à utiliser pour y reproduire les tracés).
    """
    axins = inset_axes(ax, width=width, height=height, loc=loc)
    axins.set_xlim(*x_range)
    if y_range is not None:
        axins.set_ylim(*y_range)
    axins.tick_params(labelsize=7)
    axins.grid(True, alpha=0.2)
    try:
        mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.5", linewidth=0.8)
    except Exception:
        pass
    return axins


def plot_regression(ax, x_vals, y_vals, log_space=False, confidence=True, add_label=True, color="black", label_prefix=None):
    """
    Régression linéaire avec bande de confiance à 95 %.

    log_space=True : régression sur log10(x) vs log10(y).
    Retourne (slope, intercept, r_value) ou (None, None, None) si insuffisant.
    """
    x = np.asarray(x_vals, dtype=float)
    y = np.asarray(y_vals, dtype=float)

    if log_space:
        mask = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
        x_fit = np.log10(x[mask])
        y_fit = np.log10(y[mask])
    else:
        mask = np.isfinite(x) & np.isfinite(y)
        x_fit = x[mask]
        y_fit = y[mask]

    if len(x_fit) < 3:
        return None, None, None

    result = stats.linregress(x_fit, y_fit)
    slope, intercept, r_value, _, stderr = (
        result.slope, result.intercept, result.rvalue,
        result.pvalue, result.stderr,
    )

    x_line = np.linspace(x_fit.min(), x_fit.max(), 300)
    y_line = slope * x_line + intercept

    if confidence:
        n = len(x_fit)
        t_val = stats.t.ppf(0.975, df=max(n - 2, 1))
        ss_x = float(np.sum((x_fit - x_fit.mean()) ** 2))
        se_line = (result.stderr * np.sqrt(1 / n + (x_line - x_fit.mean()) ** 2 / (ss_x or 1)))
        y_lo = y_line - t_val * se_line
        y_hi = y_line + t_val * se_line

    prefix = f"{label_prefix} — " if label_prefix else ""
    lbl = f"{prefix}pente = {slope:.2f} ± {stderr:.2f}  (r²={r_value**2:.2f})" if add_label else None

    if log_space:
        x_plot = 10 ** x_line
        y_plot = 10 ** y_line
        ax.plot(x_plot, y_plot, "--", color=color, linewidth=1.2, alpha=0.8, label=lbl)
        if confidence:
            ax.fill_between(x_plot, 10 ** y_lo, 10 ** y_hi, alpha=0.12, color=color)
    else:
        ax.plot(x_line, y_line, "--", color=color, linewidth=1.2, alpha=0.8, label=lbl)
        if confidence:
            ax.fill_between(x_line, y_lo, y_hi, alpha=0.12, color=color)

    if add_label:
        ax.legend(fontsize=8)

    return slope, intercept, r_value
