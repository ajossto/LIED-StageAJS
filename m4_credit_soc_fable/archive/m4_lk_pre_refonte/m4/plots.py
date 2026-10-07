"""Figures générées depuis les fichiers de résultats (jamais l'état mémoire)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_series_overview(series, out_path, title=""):
    """Vue d'ensemble d'un run : population, stocks, crédit, défauts."""
    t = [s["t"] for s in series]
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    ax = axes[0, 0]
    ax.plot(t, [s["pop"] for s in series])
    ax.set_title("Population")
    ax = axes[0, 1]
    ax.plot(t, [s["L_tot"] for s in series], label="L")
    ax.plot(t, [s["K_tot"] for s in series], label="K")
    ax.plot(t, [s["nw_tot"] for s in series], label="NW")
    ax.legend()
    ax.set_title("Stocks totaux")
    ax = axes[0, 2]
    ax.plot(t, [s["n_loans"] for s in series], label="actifs")
    ax2 = ax.twinx()
    ax2.plot(t, [s["loan_volume"] for s in series], color="C1", alpha=0.5,
             label="volume nouveau")
    ax.set_title("Crédit")
    ax.legend(loc="upper left")
    ax = axes[1, 0]
    ax.plot(t, [s["deaths"] for s in series], lw=0.5)
    ax.set_title("Morts / pas")
    ax = axes[1, 1]
    ax.plot(t, [s["roots_liquidity"] for s in series], lw=0.5, label="liquidité")
    ax.plot(t, [s["roots_insolvency"] for s in series], lw=0.5, label="insolvabilité")
    ax.legend()
    ax.set_title("Racines de faillite par cause")
    ax = axes[1, 2]
    ax.plot(t, [s["max_avalanche"] for s in series], lw=0.5)
    ax.set_title("Avalanche max / pas")
    for a in axes.flat:
        a.set_xlabel("t")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_rank_distribution(values_dict, out_path, title="", logx=True):
    """Diagramme rang-taille log-log par variable ({label: array})."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for label, v in values_dict.items():
        v = np.sort(np.asarray([x for x in v if x > 0]))[::-1]
        if len(v) == 0:
            continue
        ax.loglog(v, np.arange(1, len(v) + 1), lw=1.2, label=label)
    ax.set_xlabel("valeur")
    ax.set_ylabel("rang")
    ax.legend()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_ccdf_comparison(runs_values, out_path, title=""):
    """CCDF log-log superposées ({label: array}) pour comparer A/B/C/..."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for label, v in runs_values.items():
        v = np.sort(np.asarray([x for x in v if x > 0]))
        if len(v) < 10:
            continue
        ccdf = 1.0 - np.arange(1, len(v) + 1) / (len(v) + 1.0)
        ax.loglog(v, ccdf, lw=1.2, label=label)
    ax.set_xlabel("x")
    ax.set_ylabel("P(X > x)")
    ax.legend()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_avalanche_ccdf(avalanche_sets, out_path, title=""):
    """CCDF des tailles d'avalanches causales par variante ({label: [sizes]})."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for label, sizes in avalanche_sets.items():
        v = np.sort(np.asarray(sizes, dtype=float))
        if len(v) < 5:
            continue
        ccdf = 1.0 - np.arange(1, len(v) + 1) / (len(v) + 1.0)
        ax.loglog(v, ccdf, marker=".", ls="none", ms=4, label=label)
    ax.set_xlabel("taille d'avalanche")
    ax.set_ylabel("P(S > s)")
    ax.legend()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
