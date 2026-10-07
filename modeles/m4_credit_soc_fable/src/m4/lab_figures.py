"""Batterie de figures « façon m0 » (27-04-WIP) pour un dossier de run M4.

Reproduit, adaptées au moteur fusionné (une variable d'état K, revenus
Π + intérêts, avalanches causales), les 13 figures de l'analyse du modèle
m0 (anciens_modeles/modele-27-04-WIP/src/analysis.py) :

  1. macro_overview.png            — K total, NW, encours nominal, population
  2. cascades_rank_size.png        — taille/volume vs fréquence, log-log
  3. entity_size_histos.png        — histogrammes bâtons de K aux pas choisis
  4. extraction_power.png          — Π = α√K : médiane, moyenne, max, Q10, Q90
  5. destruction_moving_avg.png    — destruction (K + créances) vs production
  6. internal_rate_evolution.png   — r* = α/(2√K) : min, max, moy, méd, D1, D9
  7. gini_evolution.png            — Gini du capital, de la NW et du revenu
  8. gini_lorenz_snapshots.png     — courbes de Lorenz par snapshot
  9. revenue_distributions.png     — distributions des revenus et charges
 10. entity_lives_overview.png     — 10 entités suivies, 3 graphes par entité
 11. detail_vie_entites/entity_{id}.png — vie individuelle des suivies
 12. loan_network_final.png        — réseau final des prêts actifs
 13. lifespan_analysis.png         — durée de vie vs taille / levier moyens

Source des données : UNIQUEMENT les artefacts disque du run (consigne de
traçabilité) — series.csv, avalanches.csv, dist_series.csv, watch.csv,
death_registry.csv, births.csv, loss_edges.csv/deaths.csv, snap_t*.npz,
net_t*.npz. Les figures dont l'artefact manque sont sautées sans erreur
(runs antérieurs à la journalisation enrichie).

Équivalences m0 -> m4 explicites :
  actif total   -> K (+ créances pour le bilan) ; passif total -> dettes ;
  extraction    -> production Π = α√K (pop.prod) ;
  taux interne  -> r* = α/(2√K), rendement marginal du capital ;
  volume d'une cascade -> somme des pertes de créances (arêtes de perte)
  de la composante, reconstruite depuis loss_edges.csv + deaths.csv.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .metrics import (load_avalanches, load_births, load_death_registry,
                      load_dist_series, load_series, load_snapshots,
                      load_watch)

FIXED_STEPS = [10, 50, 100, 200, 500, 1000, 2000]

plt.rcParams.update({
    "figure.dpi": 150, "font.size": 11, "axes.titlesize": 12,
    "axes.labelsize": 11, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "legend.fontsize": 9, "axes.grid": True, "grid.alpha": 0.25,
})


# ------------------------------------------------------------------ commun

def _fig_dir(run_dir):
    d = Path(run_dir) / "figures"
    d.mkdir(exist_ok=True)
    return d


def _save(fig, path):
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _config(run_dir):
    with open(Path(run_dir) / "config.json") as fh:
        return json.load(fh)


def _title_extra(cfg):
    return (f"λ={cfg.get('lam')}, k={cfg.get('k')}, σ={cfg.get('sigma')}, "
            f"T={cfg.get('T')}, seed={cfg.get('seed')}")


def _select_steps(all_steps, n_total=None, n_max=8):
    """Pas à afficher : FIXED_STEPS + mi-parcours + final (politique m0)."""
    if not all_steps:
        return []
    max_step = all_steps[-1]
    target = set(FIXED_STEPS)
    if n_total is not None:
        target.add(n_total // 2)
        target.add(n_total)
    target.add(max_step)
    selected = []
    for t in sorted(target):
        if t > max_step:
            continue
        closest = min(all_steps, key=lambda s: abs(s - t))
        if closest not in selected:
            selected.append(closest)
    selected = sorted(selected)
    if len(selected) > n_max:
        idx = np.linspace(0, len(selected) - 1, n_max).round().astype(int)
        selected = [selected[i] for i in sorted(set(idx))]
    return selected


def _gini(values):
    xs = np.sort(np.clip(np.asarray(values, dtype=float), 0.0, None))
    n = len(xs)
    total = xs.sum()
    if n < 2 or total <= 0:
        return 0.0
    return float(2.0 * np.sum(np.arange(1, n + 1) * xs) / (n * total)
                 - (n + 1.0) / n)


def _rolling_mean(values, window):
    v = np.asarray(values, dtype=float)
    out = np.empty_like(v)
    for i in range(len(v)):
        lo = max(0, i - window // 2)
        hi = min(len(v), i + window // 2 + 1)
        out[i] = v[lo:hi].mean()
    return out


def _weighted_linreg(xs, ys, ws):
    xs, ys, ws = (np.asarray(a, dtype=float) for a in (xs, ys, ws))
    wsum = ws.sum()
    xm = (ws * xs).sum() / wsum
    ym = (ws * ys).sum() / wsum
    var = (ws * (xs - xm) ** 2).sum()
    if var <= 0:
        return 0.0, ym
    slope = (ws * (xs - xm) * (ys - ym)).sum() / var
    return slope, ym - slope * xm


# ------------------------------------------------------- 1. vue macro

def plot_macro_overview(run_dir, title_extra=""):
    rows = load_series(run_dir)
    if not rows:
        return
    t = [r["t"] for r in rows]
    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()
    # NB : la valeur nette totale est identiquement égale à K_tot
    # (Σ créances = Σ dettes) — on ne la trace pas.
    ax1.plot(t, [r["K_tot"] for r in rows], color="#1f77b4", lw=1.6,
             label="Capital réel total K")
    nets = load_snapshots(run_dir, prefix="net")
    if nets:
        ts = sorted(nets)
        ax1.plot(ts, [float(nets[s]["q"].sum()) for s in ts], color="#9C27B0",
                 lw=1.2, ls="--", marker="o", ms=3,
                 label="Encours nominal du crédit (snapshots)")
    ax1.set_xlabel("Pas de simulation")
    ax1.set_ylabel("Joules")
    ax2.plot(t, [r["pop"] for r in rows], color="#e67e22", lw=1.3,
             label="Entités vivantes")
    ax2.set_ylabel("Nombre d'entités vivantes")
    l1, lb1 = ax1.get_legend_handles_labels()
    l2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lb1 + lb2, loc="upper left")
    title = "Capital agrégé, crédit et population vivante"
    if title_extra:
        title += f" — {title_extra}"
    ax1.set_title(title)
    ax1.grid(True, alpha=0.25)
    _save(fig, _fig_dir(run_dir) / "macro_overview.png")


# ---------------------------------------- 2. cascades taille vs fréquence

def _avalanche_volumes(run_dir, with_t=False):
    """Volume (Σ pertes de créances) par avalanche, reconstruit par
    composantes du graphe de pertes entre mortes du même pas — même
    définition que bankruptcy._build_avalanches. Avec with_t=True,
    retourne les paires (t, volume) au lieu des volumes seuls."""
    d_path = Path(run_dir) / "deaths.csv"
    e_path = Path(run_dir) / "loss_edges.csv"
    if not d_path.exists() or not e_path.exists():
        return []
    deaths_by_t = defaultdict(set)
    with open(d_path) as fh:
        next(fh)
        for line in fh:
            t, i = line.split(",")
            deaths_by_t[int(t)].add(int(i))
    edges_by_t = defaultdict(list)
    with open(e_path) as fh:
        next(fh)
        for line in fh:
            t, src, dst, q = line.split(",")
            edges_by_t[int(t)].append((int(src), int(dst), float(q)))
    volumes = []
    for t, members in deaths_by_t.items():
        parent = {i: i for i in members}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        vol = defaultdict(float)
        for src, dst, q in edges_by_t.get(t, ()):
            if src in parent and dst in parent:
                ra, rb = find(src), find(dst)
                if ra != rb:
                    parent[rb] = ra
        for src, dst, q in edges_by_t.get(t, ()):
            if src in parent:
                vol[find(src)] += q
        for i in members:
            r = find(i)
            if r == i:
                volumes.append((t, vol[r]))
    if with_t:
        return volumes
    return [v for _, v in volumes]


def _rank_size_panel(ax, values, xlabel, n_bins=25):
    """Panneau taille-fréquence façon m0 : CCDF brute grise + densité
    log-binnée ± √n + régression log-log pondérée."""
    vals = sorted((v for v in values if v > 0), reverse=True)
    n = len(vals)
    if n < 5:
        ax.set_visible(False)
        return
    ax.scatter(vals, [(i + 1) / n for i in range(n)], s=10, alpha=0.18,
               color="gray", label="CCDF empirique brute")
    log_min, log_max = math.log10(vals[-1]), math.log10(vals[0])
    if log_max <= log_min:
        return
    nb = min(n_bins, max(4, int(math.sqrt(n)) * 2))
    edges = np.logspace(log_min, log_max, nb + 1)
    v = np.asarray(vals[::-1])
    bx, by, be, counts = [], [], [], []
    for i in range(nb):
        lo, hi = edges[i], edges[i + 1]
        sel = v[(v >= lo) & ((v < hi) | (i == nb - 1) & (v <= hi))]
        c = len(sel)
        if c == 0:
            continue
        width = hi - lo
        dens = c / (n * width)
        bx.append(10 ** float(np.mean(np.log10(sel))))
        by.append(dens)
        be.append(math.sqrt(c) / (n * width))
        counts.append(c)
    if len(bx) < 3:
        return
    ax.errorbar(bx, by, yerr=[np.minimum(np.array(by) * 0.95, be), be],
                fmt="o", ms=5, lw=1.1, capsize=3, color="#d62728",
                label="Densité log-binnée ± √n_bin")
    for x, y, c in zip(bx, by, counts):
        ax.annotate(str(c), (x, y), textcoords="offset points",
                    xytext=(3, 4), fontsize=7, alpha=0.7)
    pts = [(x, y, c) for x, y, c in zip(bx, by, counts) if c >= 2 and y > 0]
    if len(pts) < 3:
        pts = [(x, y, c) for x, y, c in zip(bx, by, counts) if y > 0]
    slope, inter = _weighted_linreg([math.log10(x) for x, _, _ in pts],
                                    [math.log10(y) for _, y, _ in pts],
                                    [c for _, _, c in pts])
    fx = [min(x for x, _, _ in pts), max(x for x, _, _ in pts)]
    ax.plot(fx, [10 ** (inter + slope * math.log10(x)) for x in fx], "k--",
            lw=1.2, alpha=0.8, label=f"Pente pondérée ≈ {slope:.2f}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Densité log-binnée / CCDF brute")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)


def plot_cascades_rank_size(run_dir, title_extra=""):
    avs = load_avalanches(run_dir)
    if not avs:
        return
    sizes = [a["size"] for a in avs]
    volumes = _avalanche_volumes(run_dir)
    two = len(volumes) >= 5
    fig, axes = plt.subplots(1, 2 if two else 1,
                             figsize=(16 if two else 8, 5.5), squeeze=False)
    _rank_size_panel(axes[0][0], sizes, "Taille de l'avalanche (entités)")
    if two:
        _rank_size_panel(axes[0][1], volumes,
                         "Volume de l'avalanche (Σ pertes de créances, J)")
    title = "Avalanches de faillite : taille, fréquence et incertitude"
    if title_extra:
        title += f"\n{title_extra}"
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    _save(fig, _fig_dir(run_dir) / "cascades_rank_size.png")


# ------------------------------------- 3. histogrammes des tailles (K)

def plot_entity_size_histograms(run_dir, title_extra=""):
    snaps = load_snapshots(run_dir)
    if not snaps:
        return
    cfg = _config(run_dir)
    selected = _select_steps(sorted(snaps), cfg.get("T"))
    selected = [s for s in selected if (snaps[s]["K"] > 0).sum() >= 5]
    if not selected:
        return
    n = len(selected)
    ncols = min(n, 4)
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows),
                             squeeze=False)
    cmap = plt.cm.viridis
    for idx, step in enumerate(selected):
        ax = axes[idx // ncols][idx % ncols]
        color = cmap(idx / max(n - 1, 1))
        values = snaps[step]["K"]
        values = values[values > 0]
        log_min, log_max = np.log10(values.min()), np.log10(values.max())
        if log_max <= log_min:
            ax.set_visible(False)
            continue
        nb = min(20, max(5, len(values) // 3))
        edges = np.logspace(log_min, log_max, nb + 1)
        counts, _ = np.histogram(values, bins=edges)
        cmax = counts.max() if counts.max() > 0 else 1
        for i in range(nb):
            if counts[i] == 0:
                continue
            ax.bar(edges[i], counts[i], width=edges[i + 1] - edges[i],
                   align="edge", facecolor=color, alpha=0.75,
                   edgecolor="white", linewidth=0.5)
            centre = math.sqrt(edges[i] * edges[i + 1])
            ax.text(centre, counts[i] + cmax * 0.025, str(counts[i]),
                    ha="center", va="bottom", fontsize=5.5, clip_on=True)
        # ajustement log-normal simple en surimpression (repère visuel)
        logs = np.log(values)
        mu, s = logs.mean(), logs.std()
        if s > 0:
            x = np.logspace(log_min, log_max, 400)
            pdf = np.exp(-0.5 * ((np.log(x) - mu) / s) ** 2) / (
                x * s * math.sqrt(2 * math.pi))
            scale = len(values) * math.log(10) * (log_max - log_min) / nb
            ax.plot(x, pdf * x * scale, color="black", lw=1.0, alpha=0.7,
                    label=f"LN μ={mu / math.log(10):.2f} "
                          f"σ={s / math.log(10):.2f}")
            ax.legend(fontsize=6, loc="upper left")
        ax.set_xscale("log")
        ax.set_xlim(edges[0] * 0.9, edges[-1] * 1.1)
        ax.set_title(f"Pas {step} (n={len(values)})", fontsize=9)
        ax.set_xlabel("Capital K (J)", fontsize=8)
        ax.set_ylabel("Effectif", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, which="both", alpha=0.2)
    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)
    title = "Histogrammes des tailles d'entités (capital K)"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12, y=1.01)
    fig.tight_layout()
    _save(fig, _fig_dir(run_dir) / "entity_size_histos.png")


# ------------------------------------------- 4-6. évolutions par pas

def _stat_evolution(run_dir, prefix, ylabel, title, fname, title_extra="",
                    with_min=False):
    rows = load_dist_series(run_dir)
    if not rows:
        return
    t = [r["t"] for r in rows]
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.fill_between(t, [r[f"{prefix}_q10"] for r in rows],
                    [r[f"{prefix}_q90"] for r in rows],
                    alpha=0.15, color="#1f77b4", label="D1–D9")
    ax.plot(t, [r[f"{prefix}_med"] for r in rows], color="#1f77b4", lw=2.0,
            label="Médiane")
    ax.plot(t, [r[f"{prefix}_mean"] for r in rows], color="#ff7f0e", lw=1.4,
            ls="--", label="Moyenne")
    ax.plot(t, [r[f"{prefix}_max"] for r in rows], color="#d62728", lw=1.0,
            ls=":", label="Maximum")
    if with_min:
        ax.plot(t, [r[f"{prefix}_min"] for r in rows], color="#2ca02c",
                lw=1.0, ls=":", label="Minimum")
    ax.plot(t, [r[f"{prefix}_q10"] for r in rows], color="#9467bd", lw=1.0,
            ls="-.", label="D1 (10e pct)")
    ax.plot(t, [r[f"{prefix}_q90"] for r in rows], color="#8c564b", lw=1.0,
            ls="-.", label="D9 (90e pct)")
    ax.set_xlabel("Pas de simulation")
    ax.set_ylabel(ylabel)
    if title_extra:
        title += f" — {title_extra}"
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.25)
    _save(fig, _fig_dir(run_dir) / fname)


def plot_extraction_power(run_dir, title_extra=""):
    cfg = _config(run_dir)
    _stat_evolution(run_dir, "prod",
                    f"Production Π = α√K  (α = {cfg.get('alpha')})",
                    "Puissance productive des entités",
                    "extraction_power.png", title_extra)


def plot_internal_rate_evolution(run_dir, title_extra=""):
    _stat_evolution(run_dir, "r", "Taux interne marginal r* = α/(2√K)",
                    "Évolution du taux interne marginal r*",
                    "internal_rate_evolution.png", title_extra, with_min=True)


def plot_destruction_moving_average(run_dir, window=100, title_extra=""):
    rows = load_series(run_dir)
    if not rows:
        return
    t = [r["t"] for r in rows]
    destroyed = [r["destroyed"] + r["claim_losses"] for r in rows]
    prod = _rolling_mean([r["prod_tot"] for r in rows], window)
    moving = _rolling_mean(destroyed, window)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.fill_between(t, 0, prod, alpha=0.18, color="#4fc3f7",
                    label=f"Production totale (moy. {window})")
    ax.plot(t, prod, lw=1.0, alpha=0.5, color="#0288d1")
    ax.plot(t, destroyed, lw=0.8, alpha=0.25, color="#d62728",
            label="Destruction brute (K + créances)")
    ax.plot(t, moving, lw=2.0, color="black",
            label=f"Destruction (moy. {window})")
    ax.set_xlabel("Pas de simulation")
    ax.set_ylabel("Joules par pas")
    title = "Destruction de capital vs puissance productive"
    if title_extra:
        title += f" — {title_extra}"
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.25)
    _save(fig, _fig_dir(run_dir) / "destruction_moving_avg.png")


# ------------------------------------------------- 7-8. inégalités

def plot_gini_evolution(run_dir, title_extra=""):
    rows = load_dist_series(run_dir)
    if not rows:
        return
    t = [r["t"] for r in rows]
    fig, ax = plt.subplots(figsize=(12, 5))
    for label, key, color in [("Capital K", "gini_K", "#1f77b4"),
                              ("Valeur nette (part positive)", "gini_nw",
                               "#2ca02c"),
                              ("Revenu brut (Π + intérêts)", "gini_income",
                               "#ff7f0e")]:
        ax.plot(t, [r[key] for r in rows], lw=1.5, color=color, label=label)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Pas de simulation")
    ax.set_ylabel("Coefficient de Gini")
    title = "Inégalités : capital et revenus"
    if title_extra:
        title += f" — {title_extra}"
    ax.set_title(title)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.25)
    _save(fig, _fig_dir(run_dir) / "gini_evolution.png")


def _lorenz(values):
    xs = np.sort(np.clip(np.asarray(values, dtype=float), 0.0, None))
    total = xs.sum()
    if len(xs) == 0 or total <= 0:
        return None
    cum = np.concatenate([[0.0], np.cumsum(xs) / total])
    pop = np.arange(len(xs) + 1) / len(xs)
    return pop, cum, _gini(xs)


def plot_gini_lorenz_snapshots(run_dir, title_extra=""):
    snaps = load_snapshots(run_dir)
    if not snaps:
        return
    cfg = _config(run_dir)
    selected = _select_steps(sorted(snaps), cfg.get("T"))[-6:]
    if not selected:
        return
    datasets = [("Capital K", "K", "#1f77b4"),
                ("Revenu brut (Π + intérêts)", "income", "#ff7f0e")]
    fig, axes = plt.subplots(len(selected), len(datasets),
                             figsize=(5.2 * len(datasets),
                                      3.6 * len(selected)), squeeze=False)
    for ri, step in enumerate(selected):
        for ci, (label, key, color) in enumerate(datasets):
            ax = axes[ri][ci]
            ax.plot([0, 1], [0, 1], color="gray", lw=0.9, ls="--",
                    alpha=0.55, label="Égalité parfaite")
            res = _lorenz(snaps[step][key])
            if res is not None:
                pop, share, g = res
                ax.plot(pop, share, color=color, lw=2.0,
                        label=f"Gini = {g:.3f}")
                ax.fill_between(pop, pop, share, color=color, alpha=0.12)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_title(f"{label} — pas {step}", fontsize=10)
            ax.set_xlabel("Part cumulée des entités", fontsize=9)
            ax.set_ylabel("Part cumulée de la grandeur", fontsize=9)
            ax.grid(True, alpha=0.25)
            ax.legend(fontsize=8, loc="upper left")
    title = "Courbes de Lorenz par snapshot"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12, y=1.01)
    fig.tight_layout()
    _save(fig, _fig_dir(run_dir) / "gini_lorenz_snapshots.png")


# --------------------------------------------- 9. distributions de revenus

def _adaptive_log_hist(values, min_per_bin=8, max_bins=40):
    """Densité log-binnée à bins de quantiles (≈ même effectif par bin)."""
    v = np.sort(np.asarray([x for x in values if x > 0], dtype=float))
    n = len(v)
    if n < min_per_bin * 3:
        return None
    nb = min(max_bins, max(3, n // min_per_bin))
    edges = np.unique(np.quantile(v, np.linspace(0, 1, nb + 1)))
    if len(edges) < 4:
        return None
    counts, _ = np.histogram(v, bins=edges)
    widths = np.diff(edges)
    dens = counts / (n * widths)
    centres = np.sqrt(edges[:-1] * edges[1:])
    keep = counts > 0
    return centres[keep], dens[keep], counts[keep]


def plot_revenue_distributions(run_dir, title_extra=""):
    snaps = load_snapshots(run_dir)
    if not snaps:
        return
    cfg = _config(run_dir)
    selected = _select_steps(sorted(snaps), cfg.get("T"))[-4:]
    if not selected:
        return
    candidates = [("prod", "Production Π", "#2ca02c"),
                  ("int_in", "Intérêts reçus", "#1f77b4"),
                  ("int_out", "Intérêts payés", "#d62728"),
                  ("income", "Revenu total brut", "#ff7f0e"),
                  ("income_net", "Revenu net (part positive)", "#9467bd")]
    fig, axes = plt.subplots(len(selected), 2,
                             figsize=(15, 3.8 * len(selected)), squeeze=False)
    for ri, step in enumerate(selected):
        ax_full, ax_zoom = axes[ri]
        all_vals, series_pts = [], []
        for key, label, color in candidates:
            values = snaps[step][key]
            values = values[values > 0]
            res = _adaptive_log_hist(values)
            if res is None:
                continue
            centres, dens, counts = res
            all_vals.extend(values.tolist())
            series_pts.append((centres, dens))
            med = int(np.median(counts))
            for ax in (ax_full, ax_zoom):
                ax.plot(centres, dens, marker="o", ms=3, lw=0.9, alpha=0.85,
                        color=color, label=f"{label} (méd. {med} ind./bin)")
        zoom = None
        if all_vals:
            la = np.log10(all_vals)
            zoom = (10 ** float(np.percentile(la, 10)), 10 ** float(la.max()))
            dens_in = [d for cs, ds in series_pts
                       for c, d in zip(cs, ds) if zoom[0] <= c <= zoom[1]]
            zoom_y = ((min(dens_in) / 3.0, max(dens_in) * 3.0)
                      if dens_in else None)
        for ax, is_zoom in ((ax_full, False), (ax_zoom, True)):
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel("Flux (valeurs positives)", fontsize=9)
            ax.set_ylabel("Densité", fontsize=9)
            ax.grid(True, which="both", alpha=0.2)
            ax.legend(fontsize=7)
            if is_zoom and zoom is not None and zoom[1] > zoom[0]:
                ax.set_xlim(*zoom)
                if zoom_y is not None:
                    ax.set_ylim(*zoom_y)
                ax.set_title(f"Pas {step} — zoom P10–P100", fontsize=10)
            elif is_zoom:
                ax.set_visible(False)
            else:
                ax.set_title(f"Pas {step} — vue complète", fontsize=10)
    title = "Distributions des revenus et charges financières"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12, y=1.01)
    fig.tight_layout()
    _save(fig, _fig_dir(run_dir) / "revenue_distributions.png")


# ------------------------------------------- 10-11. vies des entités

def _watch_by_id(run_dir):
    rows = load_watch(run_dir)
    hist = defaultdict(list)
    for r in rows:
        hist[r["id"]].append(r)
    for recs in hist.values():
        recs.sort(key=lambda r: r["t"])
    return dict(hist)


def _select_watched(hist, births_by_id, n_max=10):
    """Politique m0 : premières nées (≤5), la plus grosse, ≤5 étalées."""
    if not hist:
        return []
    first_born = sorted(hist, key=lambda i: births_by_id.get(i, 0))[:5]
    largest = max(hist, key=lambda i: max(r["K"] for r in hist[i]))
    later = sorted((i for i in hist
                    if i not in first_born and i != largest),
                   key=lambda i: births_by_id.get(i, 0))
    spread = ([later[j] for j in
               range(0, len(later), max(1, len(later) // 5))][:5]
              if later else [])
    out = list(dict.fromkeys(first_born + [largest] + spread))
    return out[:n_max]


def _entity_block(ax1, ax2, ax3, recs, sys_t, sys_K, show_legend=False):
    t = [r["t"] for r in recs]
    ax1.stackplot(t, [r["K"] for r in recs], [r["claims"] for r in recs],
                  labels=["Capital K", "Créances"],
                  colors=["#1f77b4", "#ff7f0e"], alpha=0.75)
    ax1.set_ylabel("Actifs", fontsize=8)
    ax2.stackplot(t, [r["debts"] for r in recs], labels=["Dettes"],
                  colors=["#e377c2"], alpha=0.75)
    ax2.plot(t, [r["nw"] for r in recs], color="black", lw=0.9,
             label="Valeur nette")
    ax2.set_ylabel("Passifs / NW", fontsize=8)
    prod = [r["prod"] for r in recs]
    int_in = [r["int_in"] for r in recs]
    int_out = [-r["int_out"] for r in recs]
    ax3.fill_between(t, 0, prod, alpha=0.7, color="#2ca02c",
                     label="Production Π")
    ax3.fill_between(t, prod, [p + i for p, i in zip(prod, int_in)],
                     alpha=0.7, color="#1f77b4", label="Intérêts reçus")
    ax3.fill_between(t, 0, int_out, alpha=0.7, color="#d62728",
                     label="Intérêts payés")
    ax3.axhline(0, color="black", lw=0.8)
    ax3.set_ylabel("Flux", fontsize=8)
    ax3.set_xlabel("Pas", fontsize=8)
    for ax in (ax1, ax2, ax3):
        ax.grid(True, alpha=0.18)
        if sys_t:
            ax_s = ax.twinx()
            ax_s.fill_between(sys_t, 0, sys_K, alpha=0.035, color="gray")
            ax_s.plot(sys_t, sys_K, color="lightgray", lw=0.55, alpha=0.38,
                      ls="--")
            ax_s.set_yticks([])
            ax_s.grid(False)
    if show_legend:
        ax1.legend(fontsize=6, loc="upper left")
        ax2.legend(fontsize=6, loc="upper left")
        ax3.legend(fontsize=6, loc="upper left", ncol=2)


def plot_entity_lives_overview(run_dir, title_extra=""):
    hist = _watch_by_id(run_dir)
    if not hist:
        return
    births_by_id = {b["id"]: b["birth"] for b in load_births(run_dir)}
    ids = _select_watched(hist, births_by_id)
    if not ids:
        return
    series = load_series(run_dir)
    sys_t = [r["t"] for r in series]
    sys_K = [r["K_tot"] for r in series]
    fig = plt.figure(figsize=(25, 14), constrained_layout=True)
    outer = fig.add_gridspec(2, 5, wspace=0.42, hspace=0.34)
    for idx, eid in enumerate(ids):
        inner = outer[idx // 5, idx % 5].subgridspec(3, 1, hspace=0.12)
        ax1 = fig.add_subplot(inner[0, 0])
        ax2 = fig.add_subplot(inner[1, 0], sharex=ax1)
        ax3 = fig.add_subplot(inner[2, 0], sharex=ax1)
        _entity_block(ax1, ax2, ax3, hist[eid], sys_t, sys_K,
                      show_legend=(idx == 0))
        ax1.set_title(f"Entité {eid}", fontsize=9, pad=4)
        ax1.tick_params(labelbottom=False, labelsize=6)
        ax2.tick_params(labelbottom=False, labelsize=6)
        ax3.tick_params(labelsize=6)
        ax3.set_xlim(0, max(sys_t) if sys_t else None)
    title = f"Vie comparée de {len(ids)} entités suivies"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=13)
    _save(fig, _fig_dir(run_dir) / "entity_lives_overview.png")


def plot_entity_lives(run_dir, title_extra=""):
    hist = _watch_by_id(run_dir)
    if not hist:
        return
    births_by_id = {b["id"]: b["birth"] for b in load_births(run_dir)}
    ids = _select_watched(hist, births_by_id, n_max=12)
    series = load_series(run_dir)
    sys_t = [r["t"] for r in series]
    sys_K = [r["K_tot"] for r in series]
    detail_dir = _fig_dir(run_dir) / "detail_vie_entites"
    detail_dir.mkdir(exist_ok=True)
    for eid in ids:
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 8),
                                            sharex=True)
        _entity_block(ax1, ax2, ax3, hist[eid], sys_t, sys_K,
                      show_legend=True)
        title = f"Entité {eid}"
        if title_extra:
            title += f" — {title_extra}"
        fig.suptitle(title, fontsize=12)
        fig.tight_layout()
        _save(fig, detail_dir / f"entity_{eid}.png")


# ------------------------------------------------ 12. réseau final

def plot_loan_network_final(run_dir, title_extra="", max_nodes=180,
                            max_edges=500):
    nets = load_snapshots(run_dir, prefix="net")
    snaps = load_snapshots(run_dir)
    if not nets or not snaps:
        return
    t_final = max(nets)
    net = nets[t_final]
    snap = snaps[max(snaps)]
    if len(net["q"]) < 2:
        return
    ent = {int(i): j for j, i in enumerate(snap["id"])}
    flow = net["q"] * net["r"]
    order = np.argsort(flow)[::-1]
    edges, nodes = [], set()
    for j in order:
        lender, borrower = int(net["lender"][j]), int(net["borrower"][j])
        if lender not in ent or borrower not in ent:
            continue
        if len(edges) >= max_edges:
            break
        if len(nodes | {lender, borrower}) > max_nodes:
            continue
        edges.append((lender, borrower, float(flow[j])))
        nodes.update((lender, borrower))
    if len(edges) < 2:
        return
    node_list = sorted(nodes)
    try:
        import networkx as nx
        g = nx.DiGraph()
        g.add_nodes_from(node_list)
        for lender, borrower, w in edges:
            g.add_edge(borrower, lender, weight=w)
        pos = nx.spring_layout(g, seed=42, weight="weight", iterations=80)
    except Exception:
        pos = {node: (math.cos(2 * math.pi * i / len(node_list)),
                      math.sin(2 * math.pi * i / len(node_list)))
               for i, node in enumerate(node_list)}
    K_vals = np.array([snap["K"][ent[i]] for i in node_list])
    net_int = np.array([snap["int_in"][ent[i]] - snap["int_out"][ent[i]]
                        for i in node_list])
    sizes = 20 + 180 * (K_vals / K_vals.max()) if K_vals.max() > 0 else 40
    vmax = float(np.abs(net_int).max()) or 1.0
    fig, ax = plt.subplots(figsize=(11, 9))
    for lender, borrower, w in edges:
        x0, y0 = pos[borrower]
        x1, y1 = pos[lender]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color="gray",
                                    alpha=0.35, lw=0.6))
    sc = ax.scatter([pos[i][0] for i in node_list],
                    [pos[i][1] for i in node_list],
                    s=sizes, c=net_int, cmap="coolwarm_r",
                    vmin=-vmax, vmax=vmax, edgecolors="black",
                    linewidths=0.4, zorder=3)
    fig.colorbar(sc, ax=ax, shrink=0.8,
                 label="Intérêts nets reçus (J/pas)")
    ax.set_axis_off()
    title = (f"Réseau final des prêts actifs (t={t_final}, "
             f"{len(node_list)} nœuds, {len(edges)} arêtes, flèche = "
             "emprunteuse → prêteuse, taille ∝ K)")
    if title_extra:
        title += f"\n{title_extra}"
    ax.set_title(title, fontsize=11)
    _save(fig, _fig_dir(run_dir) / "loan_network_final.png")


# -------------------------------------------- 13. durées de vie

def plot_lifespan_analysis(run_dir, title_extra=""):
    hist = _watch_by_id(run_dir)
    births = {b["id"]: b for b in load_births(run_dir)}
    deaths = {r["id"]: r for r in load_death_registry(run_dir)}
    if not hist or not births:
        return
    records = []
    for eid, recs in hist.items():
        if len(recs) < 3:
            continue
        birth = births.get(eid, {}).get("birth", recs[0]["t"])
        if eid in deaths:
            lifespan, censored = deaths[eid]["t"] - birth, False
        elif births.get(eid, {}).get("alive_final", 0):
            lifespan, censored = recs[-1]["t"] - birth, True
        else:
            lifespan, censored = recs[-1]["t"] - birth, False
        if lifespan <= 0:
            continue
        mean_K = float(np.mean([r["K"] for r in recs]))
        assets = [r["K"] + r["claims"] for r in recs]
        debts = [r["debts"] for r in recs]
        mean_assets = float(np.mean(assets))
        leverage = (float(np.mean(debts)) / mean_assets
                    if mean_assets > 0 else 0.0)
        records.append((lifespan, mean_K, leverage, censored))
    if len(records) < 5:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, xi, xlabel, logx in ((axes[0], 1, "Capital K moyen (J)", True),
                                 (axes[1], 2, "Levier moyen dettes/actifs",
                                  False)):
        dead = [(r[xi], r[0]) for r in records if not r[3] and r[xi] > 0]
        alive = [(r[xi], r[0]) for r in records if r[3] and r[xi] > 0]
        if dead:
            ax.scatter(*zip(*dead), s=18, alpha=0.6, color="#d62728",
                       label="Décédée")
        if alive:
            ax.scatter(*zip(*alive), s=18, alpha=0.6, color="#2ca02c",
                       marker="^", label="Survivante")
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel("Durée de vie (pas)", fontsize=10)
        if logx:
            ax.set_xscale("log")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.25)
    title = "Espérance de vie des entités suivies"
    if title_extra:
        title += f" — {title_extra}"
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    _save(fig, _fig_dir(run_dir) / "lifespan_analysis.png")


# ------------------------------------------------------------ pilotage

ALL_PLOTS = [
    plot_macro_overview,
    plot_cascades_rank_size,
    plot_entity_size_histograms,
    plot_extraction_power,
    plot_destruction_moving_average,
    plot_internal_rate_evolution,
    plot_gini_evolution,
    plot_gini_lorenz_snapshots,
    plot_revenue_distributions,
    plot_entity_lives_overview,
    plot_entity_lives,
    plot_loan_network_final,
    plot_lifespan_analysis,
]


def analyze_run(run_dir, verbose=False):
    """Génère toutes les figures disponibles pour un dossier de run.
    Les figures dont les artefacts manquent sont sautées silencieusement."""
    run_dir = Path(run_dir)
    extra = _title_extra(_config(run_dir))
    done = []
    for fn in ALL_PLOTS:
        fn(run_dir, title_extra=extra)
        name = fn.__name__.replace("plot_", "")
        if verbose:
            print(f"  figure {name}", flush=True)
        done.append(name)
    return done
