"""Figures matplotlib par run M4, dans le style de simulation_lab (fork de
anciens_modeles/m3_credit_soc/webapp/mpl_figures.py, mêmes recettes de figures).

Réutilise directement simulation_lab.plot_utils (histogrammes de densité avec
incertitudes de Poisson, bins adaptatifs, régressions avec bande de confiance,
style DPI 150) — mêmes conventions que les figures des anciennes lignées
(macro_overview, *_distribution, entity_size_histos, cascades_rank_size…).

Les PNG sont écrits dans <run_dir>/figures/ et servis par l'explorateur web ;
ils sont générés depuis les fichiers de résultats, jamais depuis l'état mémoire.

Usage autonome (pré-génération) :
  /home/anatole/jupyter/.venv/bin/python3 webapp/mpl_figures.py [--force] [run_dir ...]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent            # m4_credit_soc/
JUPYTER = ROOT.parent.parent                                     # jupyter/
for p in (str(JUPYTER), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from simulation_lab.plot_utils import (apply_style, linear_histogram,  # noqa: E402
                                       log_histogram, plot_regression)
from m4.analysis import _frequency_regression, fit_discrete_powerlaw, \
                        lr_discrete_powerlaw_vs_lognormal  # noqa: E402

FIGURES = ("macro_overview.png", "distributions_taille.png",
           "cascades_rank_size.png", "ages_richesse.png", "credit_market.png")


# ------------------------------------------------------------------ données

def _read_series(run_dir: Path) -> dict:
    rows = []
    with open(run_dir / "series.csv") as fh:
        for row in csv.DictReader(fh):
            rows.append({k: float(v) for k, v in row.items()})
    return {k: np.array([r[k] for r in rows]) for k in rows[0]} if rows else {}


def _last_snapshot(run_dir: Path):
    snaps = sorted(run_dir.glob("snap_t*.npz"))
    if not snaps:
        return None, None
    with np.load(snaps[-1]) as z:
        return int(snaps[-1].stem.split("t")[-1]), {k: z[k].copy() for k in z.files}


def _snapshot_encours(run_dir: Path):
    """Encours total du marché du crédit (somme des dettes actives) à chaque
    instant de snapshot disponible (snap_t*.npz) — pas de série continue par
    pas, seulement aux instants effectivement sauvegardés sur disque."""
    ts, encours = [], []
    for p in sorted(run_dir.glob("snap_t*.npz")):
        t = int(p.stem.split("t")[-1])
        with np.load(p) as z:
            encours.append(float(z["debts"].sum()))
        ts.append(t)
    return np.asarray(ts, dtype=float), np.asarray(encours, dtype=float)


def _avalanche_sizes(run_dir: Path, t_min: int = 500) -> np.ndarray:
    path = run_dir / "avalanches.csv"
    if not path.exists():
        return np.array([])
    sizes = []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            if int(row["t"]) >= t_min:
                sizes.append(int(row["size"]))
    return np.asarray(sizes, dtype=float)


def _write_cascade_stats(fig_dir: Path, sizes: np.ndarray) -> None:
    """Cache léger (n, max, var/moyenne) pour l'index web — évite de reparser
    avalanches.csv (parfois plusieurs Mo) à chaque chargement de l'index."""
    tail = fit_discrete_powerlaw(sizes[sizes > 1]) if len(sizes) else None
    stats = {
        "n_avalanches": int(len(sizes)),
        "max_avalanche": int(sizes.max()) if len(sizes) else 0,
        "var_over_mean": (float(sizes.var() / sizes.mean())
                          if len(sizes) and sizes.mean() > 0 else None),
        "regression_all": _frequency_regression(sizes, False),
        "regression_no_singletons": _frequency_regression(sizes, True),
        "discrete_powerlaw_no_singletons": tail,
        "lr_powerlaw_vs_truncated_lognormal": (
            lr_discrete_powerlaw_vs_lognormal(sizes, tail["x_min"], tail["alpha"])
            if tail else None),
    }
    (fig_dir / "cascade_stats.json").write_text(json.dumps(stats))


# ------------------------------------------------------------------ figures

def _fig_macro(series: dict, out: Path, run_id: str):
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    t = series["t"]
    ax = axes[0, 0]
    ax.plot(t, series["pop"], color="#1f77b4", lw=1.4, label="population")
    ax2 = ax.twinx()
    ax2.plot(t, series["births"], color="#ff7f0e", lw=0.4, alpha=0.5, label="naissances/pas")
    ax2.plot(t, series["deaths"], color="#2ca02c", lw=0.4, alpha=0.5, label="morts/pas")
    ax2.set_ylabel("flux par pas")
    ax.set_title("Population et flux démographiques")
    ax.set_xlabel("t"); ax.set_ylabel("N vivantes")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=8)

    ax = axes[0, 1]
    ax.plot(t, series["L_tot"], lw=1.1, label="L total")
    ax.plot(t, series["K_tot"], lw=1.1, label="K total")
    ax.plot(t, series["nw_tot"], lw=1.1, label="NW total")
    ax.set_title("Stocks réels et richesse nette")
    ax.set_xlabel("t"); ax.set_ylabel("joules")
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ax.plot(t, series["n_loans"], color="#1f77b4", lw=1.2, label="contrats actifs")
    ax.set_ylabel("contrats actifs")
    ax2 = ax.twinx()
    ax2.plot(t, series["loan_volume"], color="#ff7f0e", lw=0.4, alpha=0.6,
             label="volume prêté/pas")
    ax2.plot(t, series["interest_paid"], color="#2ca02c", lw=0.4, alpha=0.6,
             label="intérêts payés/pas")
    ax2.set_ylabel("flux par pas")
    ax.set_title("Marché du crédit")
    ax.set_xlabel("t")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)

    ax = axes[1, 1]
    ax.plot(t, series["roots_insolvency"], color="#1f77b4", lw=0.5, alpha=0.8,
            label="racines insolvabilité")
    ax.plot(t, series["roots_liquidity"], color="#d62728", lw=0.9,
            label="racines défaut de liquidité")
    ax.set_ylabel("faillites racines / pas")
    ax2 = ax.twinx()
    ax2.plot(t, series["max_avalanche"], color="#2ca02c", lw=0.5, alpha=0.6,
             label="avalanche max du pas")
    ax2.set_ylabel("taille d'avalanche")
    ax.set_title("Faillites par cause et avalanches")
    ax.set_xlabel("t")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=8)

    fig.suptitle(f"{run_id} — vue macroscopique", fontsize=13)
    fig.savefig(out)
    plt.close(fig)


def _fig_distributions(snap: dict, t_snap: int, out: Path, run_id: str):
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    for ax, (var, label) in zip(
        axes.flat,
        [("L", "liquidité L"), ("K", "capital productif K"),
         ("nw", "richesse nette NW (part > 0)"), ("income", "revenu brut Y")],
    ):
        log_histogram(snap[var], ax=ax, title=label, xlabel="valeur (joules)")
    fig.suptitle(f"{run_id} — distributions individuelles à t = {t_snap} "
                 f"(histogrammes de densité, barres de Poisson)", fontsize=13)
    fig.savefig(out)
    plt.close(fig)


def _log_bin_edges(smax: float, n_bins: int) -> np.ndarray:
    """Bins log-espacés (largeur croissante) sur les tailles entières 1..smax.

    Une taille par bin près de 1 (résolution fine sur le corps, dominé par des
    avalanches triviales), regroupement progressif dans la queue clairsemée où
    des bins de largeur 1 ne contiendraient que du bruit à comptage 0/1."""
    edges = np.unique(np.round(np.logspace(0, np.log10(smax), n_bins)))
    if len(edges) < 2:
        edges = np.array([1.0, smax + 1.0])
    elif edges[-1] < smax:
        edges = np.append(edges, smax)
    edges = edges.astype(float)
    edges[-1] += 1e-9
    return edges


def _bootstrap_bin_std(counts: np.ndarray, n: int, widths: np.ndarray,
                        n_boot: int = 2000, seed: int = 12345) -> np.ndarray:
    """Écart-type bootstrap des densités par bin.

    Rééchantillonnage non-paramétrique (n tirages avec remise parmi les n
    avalanches d'origine) : comme l'appartenance à un bin est une fonction
    fixe de la taille tirée, ce ré-échantillonnage équivaut exactement à un
    tirage Multinomial(n, p̂) sur les comptages — pas une approximation, la
    même distribution que le bootstrap explicite (tirage un par un), en
    beaucoup plus rapide. Diffère de l'erreur de Poisson sqrt(count) quand
    p̂ = count/n n'est pas petit (le bin dominant proche de p̂ ≈ 1 a une
    vraie variance bootstrap bien plus faible que sqrt(count))."""
    rng = np.random.default_rng(seed)
    p_hat = counts / n
    boot_counts = rng.multinomial(n, p_hat, size=n_boot)
    return boot_counts.std(axis=0) / widths


def _fig_cascades(sizes: np.ndarray, out: Path, run_id: str, t_min: int):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    if len(sizes) == 0:
        ax.set_title("Aucune avalanche enregistrée")
    else:
        smax = sizes.max()
        n_bins = max(8, min(30, int(np.ceil(np.log2(len(sizes)) + 1))))
        edges = _log_bin_edges(smax, n_bins)
        counts, edges = np.histogram(sizes, bins=edges)
        widths = np.diff(edges)
        centres = np.sqrt(edges[:-1] * edges[1:])
        density = counts / widths
        err = _bootstrap_bin_std(counts, len(sizes), widths)
        mask = counts > 0
        xerr = np.array([centres - edges[:-1], edges[1:] - centres])
        ax.errorbar(centres[mask], density[mask], yerr=err[mask],
                    xerr=xerr[:, mask], fmt="o", ms=4, capsize=3,
                    color="#1f77b4", ecolor="black", elinewidth=0.8,
                    label="tailles d'avalanches (bin log, erreur bootstrap ; "
                    "barre horizontale = largeur du bin)")
        for c, d, cnt in zip(centres[mask], density[mask], counts[mask]):
            ax.annotate(f"n={cnt}", (c, d), textcoords="offset points",
                        xytext=(5, 5), fontsize=7, color="#555555")
        ax.set_xscale("log"); ax.set_yscale("log")
        if mask.sum() >= 3:
            plot_regression(ax, centres[mask], density[mask], log_space=True,
                            color="#2ca02c", label_prefix="toutes tailles")
        fit_mask = mask & (edges[:-1] > 1)
        if fit_mask.sum() >= 3:
            plot_regression(ax, centres[fit_mask], density[fit_mask],
                            log_space=True, color="#d62728",
                            label_prefix="hors taille 1")
        ax.set_xlabel("taille d'avalanche causale")
        ax.set_ylabel("occurrences / largeur de bin")
        vm = sizes.var() / sizes.mean() if sizes.mean() > 0 else float("nan")
        ax.set_title(f"Tailles d'avalanches (t ≥ {t_min}) — n={len(sizes)}, "
                     f"max={int(sizes.max())}, var/moy={vm:.2f}")
        ax.grid(True, which="both", alpha=0.25)
    fig.suptitle(f"{run_id} — avalanches causales\n"
                 "(composantes du graphe de pertes, pas les lots par pas)",
                 fontsize=12)
    fig.savefig(out)
    plt.close(fig)


def _fig_ages(snap: dict, t_snap: int, out: Path, run_id: str):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    ages = snap["age"].astype(float)
    linear_histogram(ages, ax=axes[0], title="Âges des vivantes",
                     xlabel="âge (pas)")
    ax = axes[1]
    nw = snap["nw"]
    mask = nw > 0
    ax.semilogy(ages[mask], nw[mask], ".", ms=2.5, alpha=0.5, color="#1f77b4")
    if mask.sum() > 10 and np.std(ages[mask]) > 0:
        lognw = np.log(nw[mask])
        corr = float(np.corrcoef(ages[mask], lognw)[0, 1])
        ax.set_title(f"Âge vs NW (NW > 0) — corr(âge, log NW) = {corr:.3f}")
    else:
        ax.set_title("Âge vs NW (NW > 0)")
    ax.set_xlabel("âge (pas)")
    ax.set_ylabel("NW (échelle log)")
    ax.grid(True, which="both", alpha=0.25)
    fig.suptitle(f"{run_id} — structure d'âge à t = {t_snap} "
                 "(diagnostic anti-cohorte)", fontsize=13)
    fig.savefig(out)
    plt.close(fig)


def _fig_credit_market(ts: np.ndarray, encours: np.ndarray, out: Path, run_id: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    if len(ts) == 0:
        ax.set_title("Aucun snapshot disponible")
    else:
        ax.plot(ts, encours, "o-", ms=4, lw=1.2, color="#1f77b4")
        ax.set_xlabel("t")
        ax.set_ylabel("encours total (joules)")
        ax.set_title("Taille du marché du crédit "
                     f"(encours total, aux instants de snapshot — n={len(ts)})")
        ax.grid(True, alpha=0.25)
    fig.suptitle(f"{run_id} — taille du marché du crédit\n"
                 "(somme des dettes actives, pas le nombre de contrats)",
                 fontsize=12)
    fig.savefig(out)
    plt.close(fig)


# ------------------------------------------------------------------ pilotage

def ensure_figures(run_dir: Path, force: bool = False) -> list[str]:
    """Génère les figures manquantes (ou toutes si force). Retourne la liste
    des figures effectivement présentes, dans l'ordre canonique."""
    run_dir = Path(run_dir)
    fig_dir = run_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    if not force and all((fig_dir / f).exists() for f in FIGURES):
        return [f for f in FIGURES if (fig_dir / f).exists()]
    apply_style()
    run_id = run_dir.name
    series = _read_series(run_dir)
    if series:
        _fig_macro(series, fig_dir / "macro_overview.png", run_id)
    t_snap, snap = _last_snapshot(run_dir)
    if snap is not None:
        _fig_distributions(snap, t_snap, fig_dir / "distributions_taille.png", run_id)
        _fig_ages(snap, t_snap, fig_dir / "ages_richesse.png", run_id)
    with open(run_dir / "summary.json") as fh:
        t_final = int(json.load(fh)["t_final"])
    burn_in = max(400, t_final // 4)
    sizes = _avalanche_sizes(run_dir, t_min=burn_in)
    _fig_cascades(sizes, fig_dir / "cascades_rank_size.png", run_id, burn_in)
    _write_cascade_stats(fig_dir, sizes)
    ts, encours = _snapshot_encours(run_dir)
    _fig_credit_market(ts, encours, fig_dir / "credit_market.png", run_id)
    return [f for f in FIGURES if (fig_dir / f).exists()]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv[1:]
    targets = ([Path(a) for a in args] if args else
               sorted(p for p in (ROOT / "experiments" / "m4" / "results").iterdir()
                      if (p / "series.csv").exists()))
    for rd in targets:
        figs = ensure_figures(rd, force=force)
        print(f"[figs] {rd.name}: {len(figs)}")
