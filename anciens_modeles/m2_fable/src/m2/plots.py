"""Figures standard d'un run M2 — toujours générées depuis les fichiers du
run (series.csv, snap_*.npz), jamais depuis l'état en mémoire."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .analysis import exponential_qq

DPI = 150


def _save(fig, run_dir, name):
    path = Path(run_dir) / "figures" / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_timeseries(series, run_dir):
    t = [s["t"] for s in series]
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), sharex=True)
    panels = [
        ("pop", "Population N(t)", False),
        ("w_tot", "Richesse totale W(t)", False),
        ("n_loans", "Contrats actifs", False),
        ("loan_volume", "Volume de prêts nouveaux", False),
        ("deaths", "Faillites par pas", False),
        ("interest_paid", "Intérêts payés", False),
    ]
    for ax, (key, title, log) in zip(axes.flat, panels):
        ax.plot(t, [s[key] for s in series], lw=0.7)
        ax.set_title(title, fontsize=10)
        if log:
            ax.set_yscale("log")
        ax.grid(alpha=0.3)
    for ax in axes[-1]:
        ax.set_xlabel("t")
    fig.suptitle("Séries temporelles", y=0.995)
    return _save(fig, run_dir, "timeseries")


def plot_distributions(snap, run_dir, label=""):
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for col, (var, name) in enumerate([("w", "capital w"), ("nw", "valeur nette NW"),
                                       ("income", "revenu")]):
        v = snap[var]
        pos = v[v > 0]
        ax = axes[0, col]
        if len(pos):
            ax.hist(pos, bins=60, density=True)
        ax.set_title(f"{name} (histogramme)", fontsize=10)
        ax = axes[1, col]
        if len(pos):
            x = np.sort(pos)
            ccdf = 1.0 - np.arange(1, len(x) + 1) / len(x)
            ax.loglog(x, np.maximum(ccdf, 1e-12), ".", ms=2)
        ax.set_title(f"{name} (CCDF log-log)", fontsize=10)
        ax.grid(alpha=0.3, which="both")
    fig.suptitle(f"Distributions {label}")
    return _save(fig, run_dir, f"distributions{label}")


def plot_qq_exponential(snap, run_dir, var="nw", label=""):
    v = snap[var]
    pos = v[v > 0]
    fig, ax = plt.subplots(figsize=(5, 5))
    if len(pos) > 100:
        theo, emp = exponential_qq(pos)
        ax.plot(theo, emp, ".", ms=3)
        lim = max(theo.max(), emp.max())
        ax.plot([0, lim], [0, lim], "k--", lw=0.8)
    ax.set_xlabel("quantiles exponentiels théoriques")
    ax.set_ylabel(f"quantiles empiriques ({var})")
    ax.set_title(f"QQ-plot exponentiel, corps de {var} {label}", fontsize=10)
    ax.grid(alpha=0.3)
    return _save(fig, run_dir, f"qq_expon_{var}{label}")


def plot_age_wealth(snap, run_dir, var="nw", label=""):
    v = snap[var]
    age = snap["age"]
    pos = v > 0
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(age[pos], np.log(v[pos]), ".", ms=2, alpha=0.4)
    ax.set_xlabel("âge")
    ax.set_ylabel(f"log {var}")
    ax.set_title(f"âge vs log {var} {label}", fontsize=10)
    ax.grid(alpha=0.3)
    return _save(fig, run_dir, f"age_log{var}{label}")


def plot_age_distribution(snap, run_dir, label=""):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(snap["age"], bins=60)
    ax.set_xlabel("âge")
    ax.set_ylabel("effectif")
    ax.set_title(f"Distribution des âges {label}", fontsize=10)
    return _save(fig, run_dir, f"ages{label}")


def plot_cascades(series, run_dir, t_min=500):
    sizes = np.array([s["deaths"] for s in series if s["t"] >= t_min])
    fig, ax = plt.subplots(figsize=(5, 4))
    if len(sizes) and sizes.max() > 0:
        vals, counts = np.unique(sizes[sizes > 0], return_counts=True)
        ax.loglog(vals, counts / counts.sum(), "o", ms=4)
    ax.set_xlabel("faillites par pas (taille de cascade)")
    ax.set_ylabel("fréquence")
    ax.set_title("Distribution des tailles de cascade", fontsize=10)
    ax.grid(alpha=0.3, which="both")
    return _save(fig, run_dir, "cascades")
