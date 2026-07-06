"""Figures matplotlib par run M3, dans le style de simulation_lab.

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
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent            # m3_credit_soc/
JUPYTER = ROOT.parent                                     # jupyter/
for p in (str(JUPYTER), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from simulation_lab.plot_utils import (apply_style, linear_histogram,  # noqa: E402
                                       log_histogram, plot_regression)

FIGURES = ("macro_overview.png", "distributions_taille.png",
           "rank_size.png", "cascades_rank_size.png", "ages_richesse.png")


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


def _rank_size(ax, values, label, top_frac=0.10):
    v = np.sort(np.asarray([x for x in values if x > 0]))[::-1]
    if len(v) < 10:
        ax.set_title(f"{label} — n insuffisant")
        return
    ranks = np.arange(1, len(v) + 1)
    ax.loglog(v, ranks, ".", ms=2.5, color="#1f77b4", label=label)
    n_top = max(10, int(top_frac * len(v)))
    plot_regression(ax, v[:n_top], ranks[:n_top], log_space=True, color="#d62728")
    ax.set_xlabel("valeur (joules)")
    ax.set_ylabel("rang")
    ax.set_title(f"{label} — rang-taille (régression sur le top {int(100*top_frac)} %)")
    ax.grid(True, which="both", alpha=0.25)


def _fig_rank_size(snap: dict, t_snap: int, out: Path, run_id: str):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    _rank_size(axes[0], snap["nw"], "richesse nette NW")
    _rank_size(axes[1], snap["income"], "revenu brut Y")
    fig.suptitle(f"{run_id} — diagrammes rang-taille à t = {t_snap}", fontsize=13)
    fig.savefig(out)
    plt.close(fig)


def _fig_cascades(sizes: np.ndarray, out: Path, run_id: str):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    ax = axes[0]
    if len(sizes) == 0:
        ax.set_title("Aucune avalanche enregistrée")
    else:
        vals, counts = np.unique(sizes, return_counts=True)
        errs = np.sqrt(counts)
        ax.errorbar(vals, counts, yerr=errs, fmt="o", ms=4, capsize=3,
                    color="#1f77b4", ecolor="black", elinewidth=0.8)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("taille d'avalanche causale")
        ax.set_ylabel("occurrences")
        vm = sizes.var() / sizes.mean() if sizes.mean() > 0 else float("nan")
        ax.set_title(f"Tailles d'avalanches (t ≥ 500) — n={len(sizes)}, "
                     f"max={int(sizes.max())}, var/moy={vm:.2f}")
        ax.grid(True, which="both", alpha=0.25)
    ax = axes[1]
    if len(sizes) and (sizes > 1).sum() >= 10:
        _rank_size(ax, sizes, "tailles d'avalanches", top_frac=0.05)
    else:
        multi = int((sizes > 1).sum()) if len(sizes) else 0
        ax.text(0.5, 0.5, f"Trop peu d'avalanches multi-entités ({multi})\n"
                          "pour un diagramme rang-taille",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Rang-taille des avalanches")
    fig.suptitle(f"{run_id} — avalanches causales "
                 "(composantes du graphe de pertes, pas les lots par pas)",
                 fontsize=13)
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
        _fig_rank_size(snap, t_snap, fig_dir / "rank_size.png", run_id)
        _fig_ages(snap, t_snap, fig_dir / "ages_richesse.png", run_id)
    _fig_cascades(_avalanche_sizes(run_dir), fig_dir / "cascades_rank_size.png", run_id)
    return [f for f in FIGURES if (fig_dir / f).exists()]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv[1:]
    targets = ([Path(a) for a in args] if args else
               sorted(p for p in (ROOT / "experiments" / "m3" / "results").iterdir()
                      if (p / "series.csv").exists()))
    for rd in targets:
        figs = ensure_figures(rd, force=force)
        print(f"[figs] {rd.name}: {len(figs)}")
