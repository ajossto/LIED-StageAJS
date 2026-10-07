"""Figures agrégées d'un LOT Simulation Lab (multi-seeds) du modèle
m4_credit_soc_fable, exportées comme run synthétique consultable dans le lab
(même mécanisme que les exports de l'étude de sensibilité m0).

Chaque figure porte le même nom que son équivalent par run (batterie
lab_figures.py) mais superpose/enveloppe les seeds du lot :

  macro_overview            — K_tot et population par seed
  cascades_rank_size        — histogramme des tailles (bins entiers ≥ 2,
                              vue principale) + CCDF, lois PL et PL×coupure
  entity_size_histos        — densité de K par seed aux pas choisis
  extraction_power          — médiane par seed + moyenne inter-seeds ± D1-D9
  internal_rate_evolution   — idem pour r* = α/(2√K)
  destruction_moving_avg    — destruction lissée par seed
  gini_evolution            — moyenne inter-seeds ± enveloppe min-max
  gini_lorenz_snapshots     — Lorenz du pas final par seed (K et revenu)
  revenue_distributions     — densités du pas final par seed et par flux
  lifespan_analysis         — nuage poolé, couleur = seed

S'y ajoutent les figures qui illustrent les faits du rapport 01_soc_final,
avec les lois ajustées superposées (paramètres et r² en légende) :

  branching_ratio.png       — b(t) cumulé par seed → auto-stabilisation à 0,30
  avalanche_structure.png   — racines/taille (≈ 0,5) et profondeur vs taille
  accumulation_relaxation.png — carnet de prêts autour des grands événements
                                (accumulation avant, élagage après)
  volume_double_pareto.png  — densité du volume (J) : deux branches en loi de
                              puissance (régressions pondérées) + MLE dPlN
  revenue_fits.png          — revenu brut : dPlN vs Boltzmann×Pareto (MLE,
                              AIC, coupure x_min, vue semi-log)
  distribution_fits.png     — K et NW plein échantillon : familles simples
                              vs mélange de 2 lognormales (deux régimes ?)
  age_at_death_fits.png     — loi de l'âge au décès (toutes morts / > 5 pas)
  top_decile_renewal.png    — persistance du top décile vs Δt, âges au décès

et un export inter-lots « Synthèse SOC » (run m4_soc_synthese_lots) :

  scaling_ccdf.png          — CCDF par seed, couleur par λ : coupure croissante
  scaling_finite_size.png   — max vs population (∝ N^0,6-0,7) ; pop/λ ≈ 14,7
  invariants_soc.png        — b ≈ 0,30 et α (MLE discret) vs taille de système
  volume_exponents.png      — régression des paramètres double-Pareto du
                              volume (pentes, mode) sur la taille du système
  soc_criteria_table.png    — table des critères SOC par run (façon rapport §5)

Les vues intrinsèquement individuelles (vies d'entités, réseau final) restent
dans les figures de chaque run du lot. Aucun pooling inter-seed n'est utilisé
pour les ajustements (consigne M2/M3) : les pentes/MLE sont par seed ; seule
la droite max-vs-population de scaling_finite_size traverse les runs (c'est
une relation inter-tailles, pas un ajustement de distribution).

Usage :
  /home/anatole/jupyter/.venv/bin/python3 lab/batch_report.py <batch_id>
  /home/anatole/jupyter/.venv/bin/python3 lab/batch_report.py --all-m4
  (--all-m4 construit aussi la synthèse inter-lots ; --force pour réécrire)
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
JUPYTER = Path(__file__).resolve().parents[3]
if str(JUPYTER) not in sys.path:
    sys.path.insert(0, str(JUPYTER))

from m4.metrics import (load_avalanches, load_births, load_death_registry,
                        load_dist_series, load_series,
                        load_snapshots, load_watch)  # noqa: E402
from m4.lab_figures import (_avalanche_volumes, _adaptive_log_hist, _lorenz,
                            _select_steps, _rolling_mean,
                            _weighted_linreg)  # noqa: E402

from m4.analysis import fit_full_families, renewal_diagnostics  # noqa: E402
from m4.dpln import dpln_logpdf, fit_dpln  # noqa: E402
from scipy import optimize as spo  # noqa: E402
from scipy import stats as sps  # noqa: E402
from scipy.special import zeta as hurwitz_zeta  # noqa: E402

_EXPERIMENTS = str(Path(__file__).resolve().parent.parent / "experiments"
                   / "m4")
if _EXPERIMENTS not in sys.path:
    sys.path.insert(0, _EXPERIMENTS)
from soc_stats import (_fit_alpha_discrete, fit_pl_cutoff,  # noqa: E402
                       fit_tail_discrete, loglog_regression,
                       lr_discrete_pl_vs_lognormal, soc_stats)

RUNS_DIR = JUPYTER / "simulation_lab_data" / "runs"
BATCHES_DIR = JUPYTER / "simulation_lab_data" / "batches"
MODEL_ID = "m4_credit_soc_fable"
SEED_COLORS = plt.cm.tab10.colors

plt.rcParams.update({
    "figure.dpi": 150, "font.size": 11, "axes.titlesize": 12,
    "axes.labelsize": 11, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "legend.fontsize": 9, "axes.grid": True, "grid.alpha": 0.25,
})


# ------------------------------------------------------------ localisation

def load_batch(batch_id):
    with open(BATCHES_DIR / f"{batch_id}.json") as fh:
        return json.load(fh)


def run_folder(run_id):
    """Dossier d'artefacts m4 d'un run du lab (legacy_output/simu_*)."""
    candidates = sorted((RUNS_DIR / run_id / "legacy_output").glob("simu_*"))
    if not candidates:
        raise FileNotFoundError(f"pas de legacy_output/simu_* dans {run_id}")
    return candidates[0]


def batch_members(batch):
    """[(seed, dossier m4)] triés par seed, runs complets uniquement."""
    members = []
    for rid in batch["run_ids"]:
        meta_path = RUNS_DIR / rid / "run.json"
        with open(meta_path) as fh:
            meta = json.load(fh)
        if meta.get("status") != "completed":
            continue
        members.append((meta.get("seed"), run_folder(rid), rid))
    members.sort(key=lambda m: m[0])
    return members


# ------------------------------------------------------------- figures

def _save(fig, out_dir, name):
    fig.savefig(out_dir / name, dpi=150, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------- helpers d'ajustement

def _wlinreg_r2(xs, ys, ws):
    """Régression linéaire pondérée : (pente, ordonnée, r² pondéré)."""
    xs, ys, ws = (np.asarray(a, dtype=float) for a in (xs, ys, ws))
    slope, intercept = _weighted_linreg(xs, ys, ws)
    resid = ys - (intercept + slope * xs)
    ym = (ws * ys).sum() / ws.sum()
    ss_tot = (ws * (ys - ym) ** 2).sum()
    r2 = 1.0 - (ws * resid ** 2).sum() / ss_tot if ss_tot > 0 else float("nan")
    return slope, intercept, r2


def _r2_logdens(centres, dens, log10_pdf, weights=None):
    """r² entre la log10-densité binnée et la log10-pdf du fit aux centres
    (descripteur d'adéquation visuel, complément des AIC/MLE). Pondéré par
    `weights` (comptes de bins) si fourni : les bins quasi vides des queues
    ne dominent pas le descripteur, comme dans les régressions log-log."""
    y = np.log10(np.asarray(dens, dtype=float))
    yhat = np.asarray(log10_pdf, dtype=float)
    w = (np.ones_like(y) if weights is None
         else np.asarray(weights, dtype=float))
    keep = np.isfinite(y) & np.isfinite(yhat) & (w > 0)
    if keep.sum() < 3:
        return float("nan")
    y, yhat, w = y[keep], yhat[keep], w[keep]
    ym = (w * y).sum() / w.sum()
    ss_tot = (w * (y - ym) ** 2).sum()
    if ss_tot <= 0:
        return float("nan")
    return float(1.0 - (w * (y - yhat) ** 2).sum() / ss_tot)


def _log_bins_density(values, n_bins=28):
    """Densité sur bins log fixes : (centres, densité, comptes) ou None."""
    v = np.asarray([x for x in values if x > 0], dtype=float)
    if len(v) < 50 or v.min() == v.max():
        return None
    edges = np.logspace(math.log10(v.min()), math.log10(v.max() * 1.0001),
                        n_bins + 1)
    counts, _ = np.histogram(v, bins=edges)
    keep = counts > 0
    dens = counts[keep] / (len(v) * np.diff(edges)[keep])
    centres = np.sqrt(edges[:-1] * edges[1:])[keep]
    return centres, dens, counts[keep]


def _discrete_pl_survival(s_grid, alpha, s_min):
    """P(S > s | S >= s_min) de la loi de puissance discrète."""
    return hurwitz_zeta(alpha, s_grid + 1.0) / hurwitz_zeta(alpha, s_min)


def _plc_survival(s_grid, alpha, x_c, s_min, s_max):
    """P(S > s | S >= s_min) de la PL discrète × coupure exponentielle."""
    support = np.arange(s_min, max(s_max, s_grid.max()) + 1, dtype=float)
    pmf = support ** (-alpha) * np.exp(-support / x_c)
    pmf /= pmf.sum()
    cdf = np.cumsum(pmf)
    idx = np.clip((s_grid - s_min).astype(int), 0, len(cdf) - 1)
    return 1.0 - cdf[idx]


def _volumes_cached(folder):
    """Paires (t, volume) des avalanches, avec cache npz dans le run."""
    folder = Path(folder)
    cache = folder / "volumes_cache.npz"
    if cache.exists():
        d = np.load(cache)
        return list(zip(d["t"].tolist(), d["vol"].tolist()))
    pairs = _avalanche_volumes(folder, with_t=True)
    t = np.array([p[0] for p in pairs], dtype=np.int64)
    vol = np.array([p[1] for p in pairs], dtype=float)
    np.savez(cache, t=t, vol=vol)
    return pairs


def _volume_branch_fit(vols, n_bins=28):
    """Profil double-Pareto de la densité du volume (J) : régressions
    pondérées des deux branches, de part et d'autre du mode."""
    res = _log_bins_density(vols, n_bins)
    if res is None:
        return None
    centres, dens, counts = res
    i_mode = int(np.argmax(dens))
    if i_mode < 3 or len(centres) - i_mode < 4:
        return None
    lc, ld = np.log10(centres), np.log10(dens)
    sl, il, r2l = _wlinreg_r2(lc[:i_mode + 1], ld[:i_mode + 1],
                              counts[:i_mode + 1])
    sr, ir, r2r = _wlinreg_r2(lc[i_mode:], ld[i_mode:], counts[i_mode:])
    return dict(centres=centres, dens=dens, counts=counts,
                mode=float(centres[i_mode]),
                slope_left=float(sl), icpt_left=float(il), r2_left=float(r2l),
                slope_right=float(sr), icpt_right=float(ir),
                r2_right=float(r2r))


def _fit_gmm2_log(v, n_iter=300, tol=1e-9):
    """EM d'un mélange de 2 gaussiennes sur log(v) — c'est-à-dire de deux
    lognormales sur v : le test direct de « deux régimes » (hauts vs bas
    capitaux). Retourne dict(w, mu, sig, loglik, aic) trié par mu croissant,
    avec la vraisemblance exprimée sur x (jacobienne 1/x) pour être
    comparable aux AIC des familles ajustées sur x. None si échec."""
    y = np.log(np.asarray([x for x in v if x > 0], dtype=float))
    n = len(y)
    if n < 100:
        return None
    mu = np.array([np.quantile(y, 0.2), np.quantile(y, 0.8)])
    sig = np.full(2, max(float(y.std()) / 2, 1e-3))
    w = np.array([0.5, 0.5])
    ll_prev = -np.inf
    ll = ll_prev
    for _ in range(n_iter):
        logp = (-0.5 * ((y[:, None] - mu) / sig) ** 2 - np.log(sig)
                - 0.5 * math.log(2 * math.pi) + np.log(w))
        m = logp.max(axis=1, keepdims=True)
        p = np.exp(logp - m)
        tot = p.sum(axis=1, keepdims=True)
        ll = float(np.sum(np.log(tot[:, 0]) + m[:, 0]))
        r = p / tot
        nk = r.sum(axis=0)
        if (nk < 2).any():
            return None
        w = nk / n
        mu = (r * y[:, None]).sum(axis=0) / nk
        sig = np.sqrt((r * (y[:, None] - mu) ** 2).sum(axis=0) / nk) + 1e-9
        if abs(ll - ll_prev) < tol:
            break
        ll_prev = ll
    ll_x = ll - float(y.sum())
    order = np.argsort(mu)
    k = 5
    return dict(w=w[order], mu=mu[order], sig=sig[order], loglik=ll_x,
                aic=2 * k - 2 * ll_x, n=n)


def _gmm2_logpdf10(x, fit, component=None):
    """log10-pdf (sur x) du mélange de 2 lognormales, ou d'une composante."""
    x = np.asarray(x, dtype=float)
    y = np.log(x)
    parts = []
    for i in range(2):
        if component is not None and i != component:
            continue
        parts.append(fit["w"][i]
                     * np.exp(-0.5 * ((y - fit["mu"][i]) / fit["sig"][i]) ** 2)
                     / (fit["sig"][i] * x * math.sqrt(2 * math.pi)))
    return np.log10(np.maximum(np.sum(parts, axis=0), 1e-300))


def _late_pool(snaps, var, n_snaps=5, min_gap=150):
    """Échantillon élargi d'une variable d'instantané : concatène jusqu'à
    n_snaps instantanés de fin de run espacés d'au moins min_gap pas.
    L'espérance de vie (~15 pas) étant très inférieure à min_gap, les
    populations successives sont quasi indépendantes — le pooling temporel
    d'un régime stationnaire est licite (et reste PAR seed)."""
    ts = sorted(snaps)
    chosen = []
    for t in reversed(ts):
        if not chosen or chosen[-1] - t >= min_gap:
            chosen.append(t)
        if len(chosen) == n_snaps:
            break
    vals = np.concatenate([np.asarray(snaps[t][var], dtype=float)
                           for t in chosen])
    return vals[vals > 0], sorted(chosen)


def _size_fits(sizes):
    """Ajustements « rapport » des tailles d'avalanches d'un seed :
    PL discrète (MLE + Vuong vs lognormale), PL×coupure, r² hors taille 1."""
    arr = np.asarray(sizes, dtype=np.int64)
    if len(arr) < 100:
        return None
    out = {}
    fit = fit_tail_discrete(arr)
    if fit:
        out.update(alpha=fit["alpha"], s_min=fit["s_min"])
        lr = lr_discrete_pl_vs_lognormal(arr, fit["s_min"], fit["alpha"])
        if lr and lr.get("z") == lr.get("z"):
            out["z"] = lr["z"]
        plc = fit_pl_cutoff(arr, fit["s_min"])
        if plc:
            out.update(alpha_c=plc["alpha"], x_c=plc["x_c"])
    reg = loglog_regression(arr, exclude_one=True)
    if reg:
        out.update(reg_slope=reg["slope"], reg_r2=reg["r2"])
    return out or None


def fig_macro(members, out_dir, extra):
    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()
    for j, (seed, folder, _) in enumerate(members):
        rows = load_series(folder)
        t = [r["t"] for r in rows]
        ax1.plot(t, [r["K_tot"] for r in rows], color="#1f77b4",
                 lw=1.0, alpha=0.55,
                 label="Capital réel total K (par seed)" if j == 0 else None)
        ax2.plot(t, [r["pop"] for r in rows], color="#e67e22",
                 lw=1.0, alpha=0.55,
                 label="Entités vivantes (par seed)" if j == 0 else None)
    ax1.set_xlabel("Pas de simulation")
    ax1.set_ylabel("Joules")
    ax2.set_ylabel("Nombre d'entités vivantes")
    l1, lb1 = ax1.get_legend_handles_labels()
    l2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lb1 + lb2, loc="lower right")
    ax1.set_title(f"Capital agrégé et population — {extra}")
    ax1.grid(True, alpha=0.25)
    _save(fig, out_dir, "macro_overview.png")


def _int_log_edges(smax, min_width=2, ratio=1.45):
    """Bords de bins entiers ~géométriques, largeur minimale min_width
    (consigne : bins de largeur strictement supérieure à 1 entité)."""
    edges = [1.0]
    while edges[-1] <= smax:
        nxt = max(edges[-1] + min_width, float(round(edges[-1] * ratio)))
        edges.append(nxt)
    return np.asarray(edges)


def _model_bin_density(edges, pmf, s_min, frac_tail):
    """Densité moyenne par bin prédite par une pmf discrète définie sur
    s = s_min, s_min+1, … (masse totale 1), raccordée à la masse empirique
    frac_tail de la queue s >= s_min. Retourne (centres, densités)."""
    cs, ds = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        lo_i, hi_i = max(int(lo), s_min), int(hi)
        if hi_i <= lo_i:
            continue
        mass = pmf[lo_i - s_min: hi_i - s_min].sum()
        cs.append(math.sqrt(lo * hi))
        ds.append(frac_tail * mass / (hi - lo))
    return np.asarray(cs), np.asarray(ds)


def fig_cascades(members, out_dir, extra):
    """Répartition des tailles d'avalanches : HISTOGRAMME de densité
    (vue principale — bins entiers de largeur ≥ 2) + CCDF (vue
    secondaire), avec la loi de puissance discrète ajustée (MLE, zêta de
    Hurwitz) superposée. Consigne du 17/07 : aucune analyse de coupure sur
    cette figure — on ne recherche que des lois de puissance.
    Le volume en J a sa propre figure (volume_double_pareto). Burn-in T/4."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.5))
    ax_h, ax_c = axes
    fits, slopes = [], []
    ccdf_min = 1.0
    for j, (seed, folder, _) in enumerate(members):
        t_min = _run_T(folder) // 4
        sizes = np.asarray([a["size"] for a in load_avalanches(folder)
                            if a["t"] >= t_min], dtype=np.int64)
        n = len(sizes)
        if n < 100:
            continue
        smax = int(sizes.max())
        sf = _size_fits(sizes)
        # --- histogramme de densité, bins entiers de largeur >= 2
        edges = _int_log_edges(smax)
        counts, _ = np.histogram(sizes, bins=edges)
        widths = np.diff(edges)
        keep = counts > 0
        centres = np.sqrt(edges[:-1] * edges[1:])[keep]
        dens = counts[keep] / (n * widths[keep])
        ax_h.loglog(centres, dens, marker="o", ms=4.5, ls="none", alpha=0.6,
                    color=SEED_COLORS[j % 10],
                    label=f"seed {seed} (n={n})")
        slope, _, _ = _wlinreg_r2(np.log10(centres), np.log10(dens),
                                  counts[keep])
        slopes.append(slope)
        # --- CCDF (vue secondaire)
        v = np.sort(sizes.astype(float))
        ccdf = 1.0 - np.arange(1, n + 1) / (n + 1.0)
        ccdf_min = min(ccdf_min, ccdf[-1])
        ax_c.loglog(v, ccdf, marker=".", ls="none", ms=3, alpha=0.6,
                    color=SEED_COLORS[j % 10])
        # --- lois ajustées superposées sur les deux vues
        if sf and "alpha" in sf:
            fits.append(sf)
            s_min = sf["s_min"]
            frac_tail = float(np.mean(sizes >= s_min))
            support = np.arange(s_min, smax + 1, dtype=float)
            pmf_pl = (support ** (-sf["alpha"])
                      / hurwitz_zeta(sf["alpha"], s_min))
            cs, ds = _model_bin_density(edges, pmf_pl, s_min, frac_tail)
            ax_h.loglog(cs, ds, lw=1.0, color="k", alpha=0.55)
            grid = np.unique(v[v >= s_min])
            ax_c.loglog(grid, frac_tail * _discrete_pl_survival(
                grid, sf["alpha"], s_min), lw=1.0, color="k", alpha=0.55)
    # légende agrégée (sur la vue principale)
    if slopes:
        ax_h.plot([], [], " ",
                  label=f"pente densité binnée : {np.mean(slopes):.2f} "
                        f"± {np.std(slopes):.2f}")
    if fits:
        al = [f["alpha"] for f in fits]
        smins = sorted({f["s_min"] for f in fits})
        lab = (f"PL discrète (—) : α = {np.mean(al):.2f} ± {np.std(al):.2f}"
               f" (s_min {'/'.join(map(str, smins))})")
        zs = [f["z"] for f in fits if "z" in f]
        if zs:
            lab += f", z Vuong {np.mean(zs):+.1f} ± {np.std(zs):.1f}"
        ax_h.plot([], [], lw=1.0, color="k", alpha=0.55, label=lab)
        r2s = [f["reg_r2"] for f in fits if "reg_r2" in f]
        if r2s:
            ax_h.plot([], [], " ",
                      label=f"r² log-log hors taille 1 : {min(r2s):.2f}"
                            f"–{max(r2s):.2f}")
    ax_h.set_xlabel("Taille de l'avalanche (entités)")
    ax_h.set_ylabel("Densité (bins entiers, largeur ≥ 2)")
    ax_h.set_title("Histogramme de répartition et lois ajustées",
                   fontsize=10)
    ax_h.legend(fontsize=8, loc="lower left")
    if ccdf_min < 1.0:
        ax_c.set_ylim(bottom=ccdf_min * 0.3)
    ax_c.set_xlabel("Taille de l'avalanche (entités)")
    ax_c.set_ylabel("P(S > s)")
    ax_c.set_title("Fonction de survie (vue secondaire)", fontsize=10)
    for ax in axes:
        ax.grid(True, which="both", alpha=0.3)
    fig.suptitle("Avalanches de faillite — par seed, pas de pooling, "
                 f"burn-in T/4 — {extra}", fontsize=11)
    fig.tight_layout()
    _save(fig, out_dir, "cascades_rank_size.png")


def fig_size_histos(members, out_dir, extra):
    snaps_by_seed = {seed: load_snapshots(folder)
                     for seed, folder, _ in members}
    all_steps = sorted(set().union(*[set(s) for s in snaps_by_seed.values()]))
    if not all_steps:
        return
    selected = _select_steps(all_steps, all_steps[-1], n_max=4)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), squeeze=False)
    for idx, step in enumerate(selected):
        ax = axes[idx // 2][idx % 2]
        for j, (seed, snaps) in enumerate(sorted(snaps_by_seed.items())):
            if step not in snaps:
                continue
            res = _adaptive_log_hist(snaps[step]["K"])
            if res is None:
                continue
            centres, dens, _ = res
            ax.plot(centres, dens, marker="o", ms=3, lw=0.9, alpha=0.8,
                    color=SEED_COLORS[j % 10],
                    label=f"seed {seed} (n={len(snaps[step]['K'])})")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"Pas {step}", fontsize=10)
        ax.set_xlabel("Capital K (J)", fontsize=9)
        ax.set_ylabel("Densité", fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(True, which="both", alpha=0.2)
    for idx in range(len(selected), 4):
        axes[idx // 2][idx % 2].set_visible(False)
    fig.suptitle("Distribution des tailles d'entités (K) par seed — "
                 f"{extra}", fontsize=12, y=1.0)
    fig.tight_layout()
    _save(fig, out_dir, "entity_size_histos.png")


def _fig_stat_evolution(members, out_dir, prefix, ylabel, title, fname,
                        extra):
    per_seed = [(seed, load_dist_series(folder))
                for seed, folder, _ in members]
    per_seed = [(s, r) for s, r in per_seed if r]
    if not per_seed:
        return
    fig, ax = plt.subplots(figsize=(13, 5))
    # grille temporelle commune = celle du premier seed
    t0 = np.array([r["t"] for r in per_seed[0][1]])
    med, q10, q90 = [], [], []
    for seed, rows in per_seed:
        t = [r["t"] for r in rows]
        m = [r[f"{prefix}_med"] for r in rows]
        ax.plot(t, m, lw=0.8, alpha=0.45, color="#1f77b4")
        med.append(np.interp(t0, t, m))
        q10.append(np.interp(t0, t, [r[f"{prefix}_q10"] for r in rows]))
        q90.append(np.interp(t0, t, [r[f"{prefix}_q90"] for r in rows]))
    ax.plot(t0, np.mean(med, axis=0), lw=2.2, color="#1f77b4",
            label=f"Médiane (moyenne sur {len(per_seed)} seeds)")
    ax.fill_between(t0, np.mean(q10, axis=0), np.mean(q90, axis=0),
                    alpha=0.15, color="#1f77b4",
                    label="D1–D9 (moyenne inter-seeds)")
    ax.plot([], [], lw=0.8, alpha=0.45, color="#1f77b4",
            label="Médiane par seed")
    ax.set_xlabel("Pas de simulation")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} — {extra}")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.25)
    _save(fig, out_dir, fname)


def fig_destruction(members, out_dir, extra, window=100):
    fig, ax = plt.subplots(figsize=(12, 5))
    for j, (seed, folder, _) in enumerate(members):
        rows = load_series(folder)
        t = [r["t"] for r in rows]
        destroyed = [r["destroyed"] + r["claim_losses"] for r in rows]
        prod = _rolling_mean([r["prod_tot"] for r in rows], window)
        ax.plot(t, prod, lw=0.8, alpha=0.4, color="#0288d1",
                label=f"Production totale (moy. {window}, par seed)"
                if j == 0 else None)
        ax.plot(t, _rolling_mean(destroyed, window), lw=1.2, alpha=0.7,
                color=SEED_COLORS[j % 10],
                label=f"Destruction (moy. {window}) seed {seed}")
    ax.set_xlabel("Pas de simulation")
    ax.set_ylabel("Joules par pas")
    ax.set_title(f"Destruction de capital vs puissance productive — {extra}")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    _save(fig, out_dir, "destruction_moving_avg.png")


def fig_gini(members, out_dir, extra):
    per_seed = [(seed, load_dist_series(folder))
                for seed, folder, _ in members]
    per_seed = [(s, r) for s, r in per_seed if r]
    if not per_seed:
        return
    fig, ax = plt.subplots(figsize=(12, 5))
    t0 = np.array([r["t"] for r in per_seed[0][1]])
    for label, key, color in [("Capital K", "gini_K", "#1f77b4"),
                              ("Valeur nette (part positive)", "gini_nw",
                               "#2ca02c"),
                              ("Revenu brut (Π + intérêts)", "gini_income",
                               "#ff7f0e")]:
        curves = []
        for seed, rows in per_seed:
            curves.append(np.interp(t0, [r["t"] for r in rows],
                                    [r[key] for r in rows]))
        arr = np.array(curves)
        ax.plot(t0, arr.mean(axis=0), lw=1.8, color=color,
                label=f"{label} (moy. {len(per_seed)} seeds)")
        ax.fill_between(t0, arr.min(axis=0), arr.max(axis=0), alpha=0.15,
                        color=color)
    ax.axhspan(0.42, 0.44, color="#2ca02c", alpha=0.10,
               label="Gini(NW) 0,42–0,44 (rapport 01_soc_final)")
    ax.set_ylim(0, 1)
    ax.set_xlabel("Pas de simulation")
    ax.set_ylabel("Coefficient de Gini")
    ax.set_title(f"Inégalités : moyenne inter-seeds ± enveloppe — {extra}")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.25)
    _save(fig, out_dir, "gini_evolution.png")


def fig_lorenz(members, out_dir, extra):
    datasets = [("Capital K", "K"), ("Revenu brut (Π + intérêts)", "income")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), squeeze=False)
    used_step = None
    for ci, (label, key) in enumerate(datasets):
        ax = axes[0][ci]
        ax.plot([0, 1], [0, 1], color="gray", lw=0.9, ls="--", alpha=0.55)
        for j, (seed, folder, _) in enumerate(members):
            snaps = load_snapshots(folder)
            if not snaps:
                continue
            step = max(snaps)
            used_step = step
            res = _lorenz(snaps[step][key])
            if res is None:
                continue
            pop, share, g = res
            ax.plot(pop, share, lw=1.6, alpha=0.8,
                    color=SEED_COLORS[j % 10],
                    label=f"seed {seed} — Gini {g:.3f}")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"{label} — pas final", fontsize=10)
        ax.set_xlabel("Part cumulée des entités", fontsize=9)
        ax.set_ylabel("Part cumulée de la grandeur", fontsize=9)
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8, loc="upper left")
    fig.suptitle(f"Courbes de Lorenz au pas final ({used_step}) par seed — "
                 f"{extra}", fontsize=12)
    fig.tight_layout()
    _save(fig, out_dir, "gini_lorenz_snapshots.png")


def fig_revenues(members, out_dir, extra):
    candidates = [("prod", "Production Π"), ("int_in", "Intérêts reçus"),
                  ("int_out", "Intérêts payés"),
                  ("income", "Revenu total brut"),
                  ("income_net", "Revenu net (part positive)")]
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), squeeze=False)
    snaps_by_seed = [(seed, load_snapshots(folder))
                     for seed, folder, _ in members]
    for idx, (key, label) in enumerate(candidates):
        ax = axes[idx // 3][idx % 3]
        for j, (seed, snaps) in enumerate(snaps_by_seed):
            if not snaps:
                continue
            step = max(snaps)
            res = _adaptive_log_hist(snaps[step][key])
            if res is None:
                continue
            centres, dens, _ = res
            ax.plot(centres, dens, marker="o", ms=3, lw=0.9, alpha=0.8,
                    color=SEED_COLORS[j % 10], label=f"seed {seed}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Flux (valeurs positives)", fontsize=9)
        ax.set_ylabel("Densité", fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(True, which="both", alpha=0.2)
    axes[1][2].set_visible(False)
    fig.suptitle("Distributions des revenus et charges au pas final, "
                 f"par seed — {extra}", fontsize=12, y=1.0)
    fig.tight_layout()
    _save(fig, out_dir, "revenue_distributions.png")


def fig_lifespan(members, out_dir, extra):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    plotted = False
    for j, (seed, folder, _) in enumerate(members):
        watch = load_watch(folder)
        if not watch:
            continue
        hist = {}
        for r in watch:
            hist.setdefault(r["id"], []).append(r)
        births = {b["id"]: b for b in load_births(folder)}
        deaths = {r["id"]: r for r in load_death_registry(folder)}
        pts = []
        for eid, recs in hist.items():
            if len(recs) < 3:
                continue
            recs.sort(key=lambda r: r["t"])
            birth = births.get(eid, {}).get("birth", recs[0]["t"])
            end = deaths[eid]["t"] if eid in deaths else recs[-1]["t"]
            lifespan = end - birth
            if lifespan <= 0:
                continue
            mean_K = float(np.mean([r["K"] for r in recs]))
            assets = float(np.mean([r["K"] + r["claims"] for r in recs]))
            lev = (float(np.mean([r["debts"] for r in recs])) / assets
                   if assets > 0 else 0.0)
            pts.append((mean_K, lev, lifespan))
        if not pts:
            continue
        plotted = True
        ks, levs, ls = zip(*pts)
        axes[0].scatter(ks, ls, s=14, alpha=0.55,
                        color=SEED_COLORS[j % 10], label=f"seed {seed}")
        axes[1].scatter(levs, ls, s=14, alpha=0.55,
                        color=SEED_COLORS[j % 10])
    if not plotted:
        plt.close(fig)
        return
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Capital K moyen (J)")
    axes[1].set_xlabel("Levier moyen dettes/actifs")
    for ax in axes:
        ax.set_ylabel("Durée de vie (pas)")
        ax.grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Espérance de vie des entités suivies, tous seeds — "
                 f"{extra}", fontsize=12)
    fig.tight_layout()
    _save(fig, out_dir, "lifespan_analysis.png")


# ---------------------------------------------- figures « rapport » (par lot)

def _run_T(folder):
    return json.loads((folder / "config.json").read_text())["T"]


def fig_branching(members, out_dir, extra):
    """b(t) cumulé = 1 - Σracines/Σtailles : le rapport de branchement
    s'auto-stabilise à 0,30 (rapport 01_soc_final, §3.4 et §7)."""
    fig, ax = plt.subplots(figsize=(12, 5))
    for j, (seed, folder, _) in enumerate(members):
        avs = sorted(load_avalanches(folder), key=lambda a: a["t"])
        if not avs:
            continue
        t = np.array([a["t"] for a in avs], dtype=float)
        cum_size = np.cumsum([a["size"] for a in avs])
        cum_roots = np.cumsum([a["n_roots"] for a in avs])
        b = 1.0 - cum_roots / cum_size
        keep = cum_size >= 50
        ax.plot(t[keep], b[keep], lw=1.1, alpha=0.8,
                color=SEED_COLORS[j % 10],
                label=f"seed {seed} — b final {b[-1]:.3f}")
    ax.axhline(0.30, color="k", ls="--", lw=1.0, alpha=0.6,
               label="b = 0,30 (invariant, rapport 01_soc_final)")
    ax.set_ylim(0, 0.5)
    ax.set_xlabel("Pas de simulation")
    ax.set_ylabel("Rapport de branchement b (cumulé depuis t = 0)")
    ax.set_title("Auto-stabilisation du rapport de branchement — fraction "
                 f"des morts qui sont des victimes induites — {extra}")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(True, alpha=0.25)
    _save(fig, out_dir, "branching_ratio.png")


def fig_structure(members, out_dir, extra):
    """Structure causale des avalanches : racines/taille (≈ 0,5 pour les
    grands événements = moitié de victimes de cascade) et profondeur
    (jusqu'à 8-12 itérations), en fonction de la taille. Burn-in T/4."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    depth_max_all = 0
    for j, (seed, folder, _) in enumerate(members):
        t_min = _run_T(folder) // 4
        avs = [a for a in load_avalanches(folder)
               if a["t"] >= t_min and a["size"] >= 2]
        if len(avs) < 10:
            continue
        sizes = np.array([a["size"] for a in avs], dtype=float)
        ratio = np.array([a["n_roots"] / a["size"] for a in avs])
        depth = np.array([a["depth"] for a in avs], dtype=float)
        depth_max_all = max(depth_max_all, int(depth.max()))
        edges = np.unique(np.round(
            np.logspace(np.log10(2.0), np.log10(sizes.max()), 9)))
        edges = np.append(edges, sizes.max() + 1)
        for ax, values in ((axes[0], ratio), (axes[1], depth)):
            xs, ys = [], []
            for lo, hi in zip(edges[:-1], edges[1:]):
                m = (sizes >= lo) & (sizes < hi)
                if m.sum() >= 3:
                    xs.append(float(np.exp(np.mean(np.log(sizes[m])))))
                    ys.append(float(values[m].mean()))
            if xs:
                ax.plot(xs, ys, marker="o", ms=4, lw=1.2, alpha=0.8,
                        color=SEED_COLORS[j % 10],
                        label=f"seed {seed}" if ax is axes[0] else None)
    axes[0].axhline(0.5, color="k", ls="--", lw=1.0, alpha=0.55,
                    label="0,5 : moitié de victimes de cascade (rapport)")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_ylabel("Racines / taille (moyenne par classe de taille)")
    axes[0].set_title("Part des racines : < 1 = propagation réelle",
                      fontsize=10)
    axes[0].legend(fontsize=8, loc="upper right")
    axes[1].set_ylabel("Profondeur moyenne (itérations de cascade)")
    axes[1].set_title(f"Profondeur des cascades (max observé : "
                      f"{depth_max_all})", fontsize=10)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xlabel("Taille de l'avalanche (entités, ≥ 2)")
        ax.grid(True, which="both", alpha=0.25)
    fig.suptitle("Structure causale des avalanches (burn-in T/4) — "
                 f"{extra}", fontsize=11)
    fig.tight_layout()
    _save(fig, out_dir, "avalanche_structure.png")


def fig_accumulation(members, out_dir, extra, window=30):
    """Cycle accumulation-relaxation (rapport §3.4) : moyenne superposée du
    carnet de prêts n_loans autour des grands événements — le carnet croît
    dans les ~20 pas précédant un grand événement, la cascade l'élague."""
    data, pooled = [], []
    for seed, folder, _ in members:
        T = _run_T(folder)
        t_min = T // 4
        n_loans = np.full(T + 1, np.nan)
        for r in load_series(folder):
            n_loans[r["t"]] = r["n_loans"]
        avs = load_avalanches(folder)
        data.append((seed, T, t_min, n_loans, avs))
        pooled.extend(a["size"] for a in avs if a["t"] >= t_min)
    pooled = np.asarray(pooled)
    thr = 8
    for cand in (15, 12, 10, 8):
        if np.sum(pooled >= cand) >= 40 * len(members):
            thr = cand
            break
    dts = np.arange(-window, window + 1)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    curves, level_pre = [], []
    for j, (seed, T, t_min, n_loans, avs) in enumerate(data):
        times = sorted({a["t"] for a in avs if a["size"] >= thr
                        and t_min + window <= a["t"] <= T - window})
        segs = []
        for t0 in times:
            seg = n_loans[t0 - window: t0 + window + 1]
            if np.isnan(seg).any():
                continue
            segs.append(seg - seg[0])
            level_pre.append(n_loans[t0 - 1])
        if len(segs) < 5:
            continue
        mcurve = np.mean(segs, axis=0)
        curves.append(mcurve)
        ax.plot(dts, mcurve, lw=0.9, alpha=0.45, color=SEED_COLORS[j % 10],
                label=f"seed {seed} ({len(segs)} évts)")
    if not curves:
        plt.close(fig)
        return
    mean_c = np.mean(curves, axis=0)
    ax.plot(dts, mean_c, lw=2.4, color="k",
            label=f"moyenne inter-seeds ({len(curves)} seeds)")
    pre = slice(window - 20, window)  # dt de -20 à -1
    slope = float(np.polyfit(dts[pre], mean_c[pre], 1)[0])
    drop = float(mean_c[window] - mean_c[window - 1])
    drop_pct = 100.0 * drop / float(np.mean(level_pre))
    ax.axvline(0, color="#d62728", lw=1.0, ls="--", alpha=0.7)
    ax.annotate(f"accumulation : {slope:+.2f} contrat/pas (20 pas avant)\n"
                f"élagage à l'événement : {drop:+.1f} contrats "
                f"({drop_pct:+.2f} %)",
                xy=(0.02, 0.97), xycoords="axes fraction", va="top",
                fontsize=9,
                bbox=dict(boxstyle="round", fc="white", alpha=0.85))
    ax.set_xlabel("Pas relatifs à l'événement (dt = 0 : pas de l'avalanche)")
    ax.set_ylabel(f"Δ contrats actifs (référence : dt = -{window})")
    ax.set_title("Accumulation-relaxation du carnet de prêts autour des "
                 f"événements ≥ {thr} (burn-in T/4) — {extra}")
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(True, alpha=0.25)
    _save(fig, out_dir, "accumulation_relaxation.png")


# ----------------------------- figures « fits » (assertions du rapport)

def fig_volume_double_pareto(members, out_dir, extra, sub_max=50_000):
    """VOLUME (J) des avalanches : loi de puissance de la branche
    DESCENDANTE (au-dessus du mode), régression pondérée par seed.
    Consigne du 17/07 : abandon de l'étude de la branche montante (non
    directement liée aux avalanches) et du MLE dPlN ; pas de tentative
    d'explication de l'épaulement. Le mode reste marqué (borne du fit)."""
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    br_r, r2r, modes = [], [], []
    for j, (seed, folder, _) in enumerate(members):
        t_min = _run_T(folder) // 4
        vols = np.asarray([v for t, v in _volumes_cached(folder)
                           if t >= t_min and v > 0], dtype=float)
        bf = _volume_branch_fit(vols)
        if bf is None:
            continue
        ax.loglog(bf["centres"], bf["dens"], marker="o", ms=3.5, ls="none",
                  alpha=0.55, color=SEED_COLORS[j % 10],
                  label=f"seed {seed} (n={len(vols)})")
        br_r.append(bf["slope_right"])
        r2r.append(bf["r2_right"])
        modes.append(bf["mode"])
        xr = np.array([bf["mode"], bf["centres"][-1]])
        ax.loglog(xr, 10 ** (bf["icpt_right"]
                             + bf["slope_right"] * np.log10(xr)),
                  lw=1.4, ls="--", color=SEED_COLORS[j % 10], alpha=0.8)
    if not br_r:
        plt.close(fig)
        return
    ax.axvline(float(np.mean(modes)), color="gray", lw=1.0, ls=":",
               alpha=0.7)
    ax.plot([], [], ls="--", color="gray",
            label=(f"loi de puissance (au-dessus du mode) : pente "
                   f"{np.mean(br_r):+.2f} ± {np.std(br_r):.2f} "
                   f"(r² de {min(r2r):.2f} à {max(r2r):.2f})"))
    ax.plot([], [], ls=":", color="gray",
            label=f"mode ≈ {np.mean(modes):.0f} J (borne du fit)")
    ax.set_xlabel("Volume de l'avalanche (Σ pertes de créances, J)")
    ax.set_ylabel("Densité (bins log)")
    ax.set_title("Volume des avalanches : loi de puissance de la branche "
                 f"descendante (burn-in T/4) — {extra}", fontsize=11)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(True, which="both", alpha=0.25)
    _save(fig, out_dir, "volume_double_pareto.png")


def _fit_exp_pareto(v, x0):
    """MLE du modèle composite « corps exponentiel × queue Pareto » sur
    l'échantillon v > x0 (consigne du 17/07) :
        p(x) ∝ exp(-(x - x0)/T)          pour x0 < x ≤ x_b
        p(x) ∝ exp(-(x_b - x0)/T) (x/x_b)^{-α}   pour x > x_b
    (densité continue en x_b ; 3 paramètres libres : T, x_b, α).
    Retourne dict(T, x_b, alpha, loglik, aic, n) ou None."""
    v = np.asarray(v, dtype=float)
    v = v[v > x0]
    n = len(v)
    if n < 200:
        return None

    def nll(theta):
        T = math.exp(theta[0])
        xb = x0 + math.exp(theta[1])
        alpha = 1.0 + math.exp(theta[2])
        i_body = T * (1.0 - math.exp(-(xb - x0) / T))
        i_tail = math.exp(-(xb - x0) / T) * xb / (alpha - 1.0)
        log_c = -math.log(i_body + i_tail)
        body = v <= xb
        ll = n * log_c
        ll += float(np.sum(-(v[body] - x0) / T))
        ll += float(np.sum(-(xb - x0) / T
                           - alpha * np.log(v[~body] / xb)))
        return -ll

    best = None
    q9 = float(np.quantile(v, 0.9))
    for xb_init in (q9, float(np.quantile(v, 0.75)),
                    float(np.quantile(v, 0.97))):
        theta0 = (math.log(max(float(v.mean() - x0), 1e-2)),
                  math.log(max(xb_init - x0, 1e-2)), math.log(2.0))
        try:
            res = spo.minimize(nll, theta0, method="Nelder-Mead",
                               options=dict(maxiter=4000, xatol=1e-6,
                                            fatol=1e-8))
        except Exception:
            continue
        if best is None or res.fun < best.fun:
            best = res
    if best is None or not math.isfinite(best.fun):
        return None
    T = math.exp(best.x[0])
    xb = x0 + math.exp(best.x[1])
    alpha = 1.0 + math.exp(best.x[2])
    ll = -float(best.fun)
    return dict(T=T, x_b=xb, alpha=alpha, loglik=ll, aic=2 * 3 - 2 * ll,
                n=n)


def _exp_pareto_logpdf10(x, fit, x0):
    """log10-pdf du modèle composite corps exponentiel × queue Pareto."""
    x = np.asarray(x, dtype=float)
    T, xb, alpha = fit["T"], fit["x_b"], fit["alpha"]
    i_body = T * (1.0 - math.exp(-(xb - x0) / T))
    i_tail = math.exp(-(xb - x0) / T) * xb / (alpha - 1.0)
    log_c = -math.log(i_body + i_tail)
    out = np.where(x <= xb, -(x - x0) / T,
                   -(xb - x0) / T - alpha * np.log(np.maximum(x, xb) / xb))
    return (log_c + out) / math.log(10)


def _exp_pareto_ccdf(x, fit, x0):
    """Fonction de survie du modèle composite (sur x > x0)."""
    x = np.asarray(x, dtype=float)
    T, xb, alpha = fit["T"], fit["x_b"], fit["alpha"]
    i_body = T * (1.0 - math.exp(-(xb - x0) / T))
    i_tail = math.exp(-(xb - x0) / T) * xb / (alpha - 1.0)
    c = 1.0 / (i_body + i_tail)
    s_at = lambda y: (c * T * (np.exp(-(y - x0) / T)
                               - math.exp(-(xb - x0) / T)) + c * i_tail)
    tail = (c * math.exp(-(xb - x0) / T) * xb / (alpha - 1.0)
            * (np.maximum(x, xb) / xb) ** (1.0 - alpha))
    return np.where(x <= xb, s_at(np.minimum(x, xb)), tail)


def fig_revenue_fits(members, out_dir, extra, income_min=10.0):
    """Statistiques du revenu brut — consigne du 17/07 : « le corps est en
    exponentielle et la queue en pareto », refaire l'étude et le fit.
    Modèle composite corps exponentiel × queue Pareto (3 paramètres :
    température T, raccord x_b, exposant α), MLE par seed sur les revenus
    > income_min (10 J, la bosse des jeunes entités est exclue ; densité
    complète en gris). Comparaison AIC contre les familles simples
    (lognormale, gamma, exponentielle) — verdict rapporté tel quel."""
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 10))
    ax_ll, ax_semilog, ax_ccdf, ax_aic = (axes[0][0], axes[0][1],
                                          axes[1][0], axes[1][1])
    cp_T, cp_xb, cp_alpha, cp_r2 = [], [], [], []
    aic_by_family = {}
    fam_defs = (("exp×pareto", None, 3), ("lognorm", sps.lognorm, 2),
                ("gamma", sps.gamma, 2), ("expon", sps.expon, 1))
    step_used = None
    for j, (seed, folder, _) in enumerate(members):
        snaps = load_snapshots(folder)
        if not snaps:
            continue
        v_all, used = _late_pool(snaps, "income")
        v = v_all[v_all > income_min]
        step_used = f"{used[0]}–{used[-1]}, {len(used)} instantanés"
        res = _log_bins_density(v, n_bins=24)
        if res is None or len(v) < 200:
            continue
        centres, dens, counts = res
        frac_kept = len(v) / len(v_all)
        res_all = _log_bins_density(v_all, n_bins=24)
        if res_all is not None:
            ax_ll.loglog(res_all[0], res_all[1] / frac_kept, marker=".",
                         ms=2.5, ls="none", alpha=0.25, color="gray")
        ax_ll.loglog(centres, dens, marker="o", ms=3.5, ls="none",
                     alpha=0.55, color=SEED_COLORS[j % 10],
                     label=f"seed {seed} (n={len(v)} > {income_min:g} J)")
        ax_semilog.semilogy(centres, dens, marker="o", ms=3.5, ls="none",
                            alpha=0.55, color=SEED_COLORS[j % 10])
        vs = np.sort(v)
        ccdf = 1.0 - np.arange(1, len(vs) + 1) / (len(vs) + 1.0)
        ax_ccdf.loglog(vs, ccdf, ls="none", marker=".", ms=2, alpha=0.4,
                       color=SEED_COLORS[j % 10])
        # --- modèle composite corps exponentiel × queue Pareto
        cp = _fit_exp_pareto(v, income_min)
        aics = {}
        if cp:
            aics["exp×pareto"] = cp["aic"]
            cp_T.append(cp["T"])
            cp_xb.append(cp["x_b"])
            cp_alpha.append(cp["alpha"])
            grid = np.logspace(math.log10(centres[0]),
                               math.log10(centres[-1]), 300)
            pdf10 = _exp_pareto_logpdf10(grid, cp, income_min)
            ax_ll.loglog(grid, 10 ** pdf10, lw=1.2, color="k", alpha=0.65)
            ax_semilog.semilogy(grid, 10 ** pdf10, lw=1.2, color="k",
                                alpha=0.65)
            ax_ccdf.loglog(grid, _exp_pareto_ccdf(grid, cp, income_min),
                           lw=1.2, color="k", alpha=0.65)
            for ax in (ax_ll, ax_semilog, ax_ccdf):
                ax.axvline(cp["x_b"], color="#d62728", lw=0.8, ls=":",
                           alpha=0.6)
            cp_r2.append(_r2_logdens(
                centres, dens,
                _exp_pareto_logpdf10(centres, cp, income_min),
                weights=counts))
        # --- familles simples de comparaison (sur x - income_min pour
        # l'exponentielle et la gamma, floc=0 sinon impossible ; la
        # lognormale est ajustée sur x directement, floc=0)
        for name, dist, kfree in fam_defs[1:]:
            try:
                if name == "lognorm":
                    params = dist.fit(v, floc=0)
                    ll = float(np.sum(dist.logpdf(v, *params)))
                else:
                    t = v - income_min
                    params = dist.fit(t, floc=0)
                    ll = float(np.sum(dist.logpdf(t, *params)))
            except Exception:
                continue
            if math.isfinite(ll):
                aics[name] = 2 * kfree - 2 * ll
        if aics:
            best_aic = min(aics.values())
            for fam, val in aics.items():
                aic_by_family.setdefault(fam, []).append(val - best_aic)
    # légendes / habillage
    if cp_T:
        ax_ll.plot([], [], lw=1.2, color="k", alpha=0.65,
                   label=("corps exp × queue Pareto (MLE) :\n"
                          f"T = {np.mean(cp_T):.2f}±{np.std(cp_T):.2f} "
                          f"J/pas, x_b = {np.mean(cp_xb):.1f}"
                          f"±{np.std(cp_xb):.1f} J,\n"
                          f"α = {np.mean(cp_alpha):.2f}"
                          f"±{np.std(cp_alpha):.2f}"))
        ax_ll.plot([], [], ls=":", color="#d62728",
                   label="raccord x_b (corps → queue)")
        ax_ll.plot([], [], " ",
                   label=f"r² log-densité : de {min(cp_r2):.2f} "
                         f"à {max(cp_r2):.2f}")
    for ax, xlab, title in (
            (ax_ll, "Revenu brut Π + intérêts (J/pas)",
             "Vue log-log : densité et modèle composite"),
            (ax_semilog, "Revenu brut (J/pas), échelle linéaire",
             "Vue semi-log : le corps exponentiel = droite"),
            (ax_ccdf, "Revenu brut (J/pas)",
             "Fonction de survie : la queue Pareto = droite log-log")):
        ax.axvline(income_min, color="k", lw=0.8, ls="--", alpha=0.4)
        ax.set_xlabel(f"{xlab} — fits sur > {income_min:g} J")
        ax.set_ylabel("Densité (bins log)" if ax is not ax_ccdf
                      else "P(X > x)")
        ax.set_title(title, fontsize=10)
        ax.grid(True, which="both", alpha=0.25)
    ax_ll.legend(fontsize=7.5, loc="lower left")
    if aic_by_family:
        fams = [f for f, _, _ in fam_defs if f in aic_by_family]
        pos = np.arange(len(fams))
        for j in range(len(members)):
            vals = [aic_by_family[f][j] if j < len(aic_by_family[f])
                    else np.nan for f in fams]
            ax_aic.plot(pos, vals, marker="o", ms=5, lw=0.8, alpha=0.7,
                        color=SEED_COLORS[j % 10])
        wins = {f: sum(1 for d in aic_by_family[f] if d == 0.0)
                for f in fams}
        best_fam = max(wins, key=wins.get)
        ax_aic.set_xticks(pos)
        ax_aic.set_xticklabels([f"{f}\n({wins[f]}/{len(members)})"
                                for f in fams], fontsize=9)
        ax_aic.set_yscale("symlog", linthresh=10)
        ax_aic.axhline(0, color="k", lw=0.8)
        ax_aic.set_ylabel("ΔAIC vs meilleure famille (par seed)")
        ax_aic.set_title(f"Comparaison AIC (revenus > {income_min:g} J) — "
                         f"meilleure : {best_fam} "
                         f"({wins[best_fam]}/{len(members)} seeds)",
                         fontsize=10)
        ax_aic.grid(True, alpha=0.25)
    fig.suptitle(f"Distribution du revenu brut (pas {step_used}) : modèle "
                 "corps exponentiel × queue Pareto, ajusté sur les revenus "
                 f"> {income_min:g} J — {extra}", fontsize=12)
    fig.tight_layout()
    _save(fig, out_dir, "revenue_fits.png")


def fig_distribution_fits(members, out_dir, extra):
    """Distributions de K et de NW (part positive), PLEIN échantillon (pas
    de troncature au corps). Consigne du 17/07 : abandon total du mélange
    de 2 lognormales ; familles à 4 paramètres maximum, objectif 3 —
    lognorm/fisk/gamma/weibull (2 libres, floc=0) + gengamma et burr
    (3 libres). Meilleure par AIC, courbe superposée, paramètres et r²
    pondéré en légende."""
    singles = (("lognorm", sps.lognorm, 2), ("fisk", sps.fisk, 2),
               ("gamma", sps.gamma, 2), ("weibull_min", sps.weibull_min, 2),
               ("gengamma", sps.gengamma, 3), ("burr", sps.burr, 3))
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.8))
    step_used = None
    for ci, (var, label) in enumerate((("K", "Capital productif K (J)"),
                                       ("nw", "Valeur nette NW (J, > 0)"))):
        ax = axes[ci]
        wins = {}
        r2s = []
        best_single = {}
        dens_min = math.inf
        for j, (seed, folder, _) in enumerate(members):
            snaps = load_snapshots(folder)
            if not snaps:
                continue
            v, used = _late_pool(snaps, var)
            step_used = f"{used[0]}–{used[-1]}, {len(used)} instantanés"
            res = _log_bins_density(v, n_bins=26)
            if res is None:
                continue
            centres, dens, counts = res
            dens_min = min(dens_min, float(dens.min()))
            ax.loglog(centres, dens, marker="o", ms=3.5, ls="none",
                      alpha=0.55, color=SEED_COLORS[j % 10],
                      label=f"seed {seed} (n={len(v)})")
            aics = {}
            fitted = {}
            for name, dist, kfree in singles:
                try:
                    params = dist.fit(v, floc=0)
                    ll = float(np.sum(dist.logpdf(v, *params)))
                except Exception:
                    continue
                if not math.isfinite(ll):
                    continue
                aics[name] = 2 * kfree - 2 * ll
                fitted[name] = params
            if not aics:
                continue
            best = min(aics, key=aics.get)
            wins[best] = wins.get(best, 0) + 1
            grid = np.logspace(math.log10(centres[0]),
                               math.log10(centres[-1]), 250)
            dist = dict((n, d) for n, d, _ in singles)[best]
            params = fitted[best]
            ax.loglog(grid, dist.pdf(grid, *params), lw=1.3,
                      color="k", alpha=0.65)
            best_single.setdefault(best, []).append(params)
            r2s.append(_r2_logdens(
                centres, dens,
                dist.logpdf(centres, *params) / math.log(10),
                weights=counts))
        win_txt = ", ".join(f"{k} {v}/{len(members)}"
                            for k, v in sorted(wins.items(),
                                               key=lambda kv: -kv[1]))
        ax.plot([], [], lw=1.3, color="k", alpha=0.65,
                label=f"meilleure par AIC (plein échantillon) : {win_txt}")
        for name, plist in best_single.items():
            ps = np.array(plist)
            ax.plot([], [], " ",
                    label=(f"params {name} : "
                           + ", ".join(f"{m:.2f}±{s:.2f}" for m, s
                                       in zip(ps.mean(0), ps.std(0)))))
        if r2s:
            ax.plot([], [], " ",
                    label=f"r² log-densité (pondéré) : de {min(r2s):.2f} "
                          f"à {max(r2s):.2f}")
        if math.isfinite(dens_min):
            ax.set_ylim(bottom=dens_min * 0.1)
        ax.set_xlabel(label)
        ax.set_ylabel("Densité (bins log)")
        ax.legend(fontsize=7.5, loc="lower left")
        ax.grid(True, which="both", alpha=0.25)
    fig.suptitle(f"Distributions complètes de K et NW (pas {step_used}) — "
                 "familles simples (≤ 3 paramètres libres, MLE) "
                 f"— {extra}", fontsize=11)
    fig.tight_layout()
    _save(fig, out_dir, "distribution_fits.png")


def fig_age_fits(members, out_dir, extra, age_split=5):
    """Loi de l'âge au décès, deux échantillons par seed : toutes les
    morts, et les morts d'âge > age_split (5) — la mortalité infantile
    (proximité de la dotation) domine les petits âges. Consigne du 17/07 :
    on ne garde que le fit lognormal (MLE plein échantillon, correction de
    continuité +0,5 ; échantillon > 5 recalé en âge - 5), r² pondéré.
    Burn-in T/4."""
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.8))
    panels = ((axes[0], "toutes les morts", None),
              (axes[1], f"morts d'âge > {age_split} (x = âge - {age_split})",
               age_split))
    for ax, title, split in panels:
        params_all, r2s = [], []
        for j, (seed, folder, _) in enumerate(members):
            T = _run_T(folder)
            ages = np.asarray([r["age"] for r in load_death_registry(folder)
                               if r["t"] >= T // 4], dtype=float)
            if split is not None:
                ages = ages[ages > split] - split
            ages = ages + 0.5  # correction de continuité (âges entiers)
            if len(ages) < 200:
                continue
            # densité empirique : bins entiers de largeur 2
            amax = float(np.quantile(ages, 0.999))
            edges = np.arange(0.0, amax + 2.0, 2.0)
            counts, _ = np.histogram(ages, bins=edges)
            keep = counts > 0
            centres = (0.5 * (edges[:-1] + edges[1:]))[keep]
            dens = counts[keep] / (len(ages) * 2.0)
            ax.semilogy(centres, dens, marker="o", ms=3.5, ls="none",
                        alpha=0.55, color=SEED_COLORS[j % 10],
                        label=f"seed {seed} (n={len(ages)})")
            try:
                pars = sps.lognorm.fit(ages, floc=0)
            except Exception:
                continue
            params_all.append(pars)
            grid = np.linspace(max(centres[0], 0.6), centres[-1], 250)
            ax.semilogy(grid, sps.lognorm.pdf(grid, *pars), lw=1.3,
                        color="k", alpha=0.65)
            r2s.append(_r2_logdens(
                centres, dens,
                sps.lognorm.logpdf(centres, *pars) / math.log(10),
                weights=counts[keep]))
        if params_all:
            ps = np.array(params_all)
            ax.plot([], [], lw=1.3, color="k", alpha=0.65,
                    label=("lognormale (MLE) : σ_log = "
                           f"{ps[:, 0].mean():.2f}±{ps[:, 0].std():.2f}, "
                           f"médiane = {ps[:, 2].mean():.2f}"
                           f"±{ps[:, 2].std():.2f} pas"))
        if r2s:
            ax.plot([], [], " ",
                    label=f"r² log-densité (pondéré) : de {min(r2s):.2f} "
                          f"à {max(r2s):.2f}")
        ax.set_xlabel("Âge au décès (pas)")
        ax.set_ylabel("Densité (bins de 2 pas)")
        ax.set_title(title, fontsize=10)
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25)
    fig.suptitle("Loi de l'âge au décès : ajustement lognormal "
                 f"(burn-in T/4) — {extra}", fontsize=11)
    fig.tight_layout()
    _save(fig, out_dir, "age_at_death_fits.png")


def fig_top_renewal(members, out_dir, extra):
    """Renouvellement du haut de la distribution : persistance du top
    décile (NW) en fonction de l'écart temporel (rapport : persistance 0,00
    sur 1000 pas) et distribution des âges au décès (espérance ~15 pas)."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    lags = (50, 100, 200, 500, 1000)
    mean_ages = []
    for j, (seed, folder, _) in enumerate(members):
        snaps = load_snapshots(folder)
        T = _run_T(folder)
        ts = sorted(t for t in snaps if t >= T // 4)
        xs, ys = [], []
        for lag in lags:
            vals = [renewal_diagnostics(snaps[t], snaps[t + lag], t, t + lag)
                    for t in ts if t + lag in snaps]
            vals = [v["persistence"] for v in vals if v]
            if vals:
                xs.append(lag)
                ys.append(float(np.mean(vals)))
        if xs:
            axes[0].plot(xs, ys, marker="o", ms=5, lw=1.2, alpha=0.8,
                         color=SEED_COLORS[j % 10], label=f"seed {seed}")
        ages = np.asarray([r["age"] for r in load_death_registry(folder)
                           if r["t"] >= T // 4], dtype=float)
        if len(ages):
            mean_ages.append(float(np.mean(ages)))
            amax = np.quantile(ages, 0.999)
            bins = np.arange(0, amax + 2)
            counts, _ = np.histogram(ages, bins=bins)
            keep = counts > 0
            axes[1].semilogy(bins[:-1][keep] + 0.5,
                             counts[keep] / counts.sum(), lw=1.0,
                             alpha=0.7, color=SEED_COLORS[j % 10])
    axes[0].set_ylim(-0.02, 1.0)
    axes[0].set_xlabel("Écart temporel Δt (pas)")
    axes[0].set_ylabel("Persistance du top décile (NW)")
    axes[0].set_title("Fraction du top décile encore au top après Δt\n"
                      "(rapport : 0,00 à Δt = 1000)", fontsize=10)
    axes[0].legend(fontsize=8)
    if mean_ages:
        axes[1].axvline(np.mean(mean_ages), color="k", ls="--", lw=1.0,
                        alpha=0.7,
                        label=f"espérance de vie : {np.mean(mean_ages):.1f} "
                              f"± {np.std(mean_ages):.1f} pas "
                              "(rapport : ~15)")
    axes[1].set_xlabel("Âge au décès (pas)")
    axes[1].set_ylabel("Fréquence")
    axes[1].set_title("Distribution des âges au décès (burn-in T/4)",
                      fontsize=10)
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(True, alpha=0.25)
    fig.suptitle("Renouvellement démographique du haut de la distribution — "
                 f"{extra}", fontsize=11)
    fig.tight_layout()
    _save(fig, out_dir, "top_decile_renewal.png")


# ------------------------------------------------------------- export

def _summary(members):
    keys = ("pop_final", "total_deaths", "n_loans_final")
    agg = {}
    per_run = []
    for seed, folder, rid in members:
        with open(folder / "summary.json") as fh:
            s = json.load(fh)
        avs = load_avalanches(folder)
        s["avalanche_max_size"] = max((a["size"] for a in avs), default=0)
        s["n_avalanches"] = len(avs)
        per_run.append(dict(seed=seed, run_id=rid, **{
            k: s[k] for k in
            ("status", "pop_final", "total_deaths", "n_loans_final",
             "avalanche_max_size", "n_avalanches", "wall_seconds")}))
    for key in keys + ("avalanche_max_size",):
        vals = [r[key] for r in per_run if isinstance(r.get(key), (int, float))]
        if vals:
            agg[f"{key}_mean"] = round(float(np.mean(vals)), 2)
            agg[f"{key}_min"] = min(vals)
            agg[f"{key}_max"] = max(vals)
    agg["seeds"] = [r["seed"] for r in per_run]
    return agg, per_run


def export_batch(batch_id, force=False):
    """Construit le run agrégé consultable pour un lot terminé."""
    batch = load_batch(batch_id)
    members = batch_members(batch)
    if not members:
        raise RuntimeError(f"aucun run complet dans le lot {batch_id}")
    export_id = f"{batch_id}_lot"
    export_dir = RUNS_DIR / export_id
    if export_dir.exists() and not force:
        raise FileExistsError(f"{export_dir} existe (utiliser force=True)")
    fig_dir = export_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((members[0][1] / "config.json").read_text())
    extra = (f"λ={cfg['lam']:g}, k={cfg['k']}, σ={cfg['sigma']}, "
             f"T={cfg['T']}, {len(members)} seeds")
    for fn in (fig_macro, fig_cascades, fig_size_histos, fig_destruction,
               fig_gini, fig_lorenz, fig_revenues, fig_lifespan,
               fig_branching, fig_structure, fig_accumulation,
               fig_volume_double_pareto, fig_revenue_fits,
               fig_distribution_fits, fig_age_fits, fig_top_renewal):
        fn(members, fig_dir, extra)
        print(f"  {fn.__name__}", flush=True)
    _fig_stat_evolution(members, fig_dir, "prod",
                        f"Production Π = α√K  (α = {cfg['alpha']})",
                        "Puissance productive des entités",
                        "extraction_power.png", extra)
    _fig_stat_evolution(members, fig_dir, "r",
                        "Taux interne marginal r* = α/(2√K)",
                        "Évolution du taux interne marginal r*",
                        "internal_rate_evolution.png", extra)
    print("  stat_evolutions", flush=True)

    agg, per_run = _summary(members)
    with open(export_dir / "aggregate.json", "w") as fh:
        json.dump(dict(batch_id=batch_id, config=cfg, per_run=per_run),
                  fh, indent=2)

    from simulation_lab.contracts import collect_artifacts
    now = datetime.now(timezone.utc).isoformat()
    label = batch.get("label") or f"Lot {batch_id}"
    run_meta = {
        "run_id": export_id,
        "model_id": MODEL_ID,
        "parameters": {k: cfg[k] for k in ("lam", "k", "sigma", "T")},
        "seed": None,
        "label": f"{label} — figures agrégées",
        "batch_id": batch_id,
        "status": "completed",
        "keep": True,
        "important": False,
        "trashed": False,
        "trashed_at": None,
        "created_at": now,
        "updated_at": now,
        "summary": agg,
        "artifacts": [a.to_dict() for a in collect_artifacts(export_dir)],
        "message": (f"Figures agrégées du lot {batch_id} "
                    f"({len(members)} seeds)"),
        "preview_artifact": "figures/cascades_rank_size.png",
        "origin": "export",
        "deletable": True,
    }
    with open(export_dir / "run.json", "w") as fh:
        json.dump(run_meta, fh, indent=2)
    print(f"export : {export_dir}")
    return export_id


# ------------------------------- synthèse inter-lots (faits du rapport)

LOT_COLORS = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd"]
SYNTH_ID = "m4_soc_synthese_lots"


def _lot_stats(batch_ids):
    """[{batch_id, lam, cfg, members, stats}] triés par λ croissant.

    stats[i] = soc_stats du run i (mesure stricte même-pas, burn-in T/4),
    enrichi de seed/run_id et du tableau brut des tailles (clé privée
    "_sizes", non sérialisée) pour éviter de relire avalanches.csv."""
    lots = []
    for bid in batch_ids:
        batch = load_batch(bid)
        members = batch_members(batch)
        if not members:
            continue
        cfg = json.loads((members[0][1] / "config.json").read_text())
        stats = []
        for seed, folder, rid in members:
            st = soc_stats(folder)
            st["seed"], st["run_id"] = seed, rid
            t_min = cfg["T"] // 4
            st["_sizes"] = np.array(
                [a["size"] for a in load_avalanches(folder)
                 if a["t"] >= t_min], dtype=np.int64)
            stats.append(st)
        lots.append(dict(batch_id=bid, lam=cfg["lam"], cfg=cfg,
                         members=members, stats=stats))
    lots.sort(key=lambda lot: lot["lam"])
    return lots


def fig_scaling_ccdf(lots, out_dir):
    """CCDF des tailles, un trait par seed, couleur par λ : corps commun,
    coupure croissant avec la taille du système (rapport, critère 2)."""
    fig, ax = plt.subplots(figsize=(9, 6.5))
    for li, lot in enumerate(lots):
        color = LOT_COLORS[li % len(LOT_COLORS)]
        maxes = []
        for st in lot["stats"]:
            v = np.sort(st["_sizes"].astype(float))
            if len(v) < 5:
                continue
            ccdf = 1.0 - np.arange(1, len(v) + 1) / (len(v) + 1.0)
            ax.loglog(v, ccdf, lw=1.1, alpha=0.6, color=color)
            maxes.append(int(v[-1]))
        pop = np.mean([st["pop_mean"] for st in lot["stats"]])
        ax.plot([], [], color=color, lw=2,
                label=f"λ={lot['lam']:g} — pop. moy. ~{pop:.0f}, "
                      f"max {min(maxes)}–{max(maxes)}")
    ax.set_xlabel("Taille de l'avalanche s (entités)")
    ax.set_ylabel("P(S > s)")
    ax.set_title("Scaling en taille finie : corps commun, coupure croissant\n"
                 "avec la taille du système (un trait par seed, burn-in T/4)")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.3)
    _save(fig, out_dir, "scaling_ccdf.png")


def fig_scaling_finite_size(lots, out_dir):
    """Max d'avalanche vs population (∝ N^0,6-0,7 dans le rapport) et
    extensivité de la population (~14,7 vivantes par unité de λ)."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    pops, maxes = [], []
    for li, lot in enumerate(lots):
        color = LOT_COLORS[li % len(LOT_COLORS)]
        p = [st["pop_mean"] for st in lot["stats"]]
        m = [st["max_size"] for st in lot["stats"]]
        axes[0].loglog(p, m, "o", ms=7, alpha=0.85, color=color,
                       label=f"λ={lot['lam']:g}")
        axes[1].semilogx([lot["lam"]] * len(p),
                         np.asarray(p) / lot["lam"], "o", ms=7,
                         alpha=0.85, color=color)
        pops.extend(p)
        maxes.extend(m)
    lp, lm = np.log10(np.asarray(pops)), np.log10(np.asarray(maxes))
    slope, inter = np.polyfit(lp, lm, 1)
    xs = np.linspace(lp.min() - 0.05, lp.max() + 0.05, 20)
    axes[0].plot(10 ** xs, 10 ** (inter + slope * xs), "k--", lw=1.2,
                 label=f"max ∝ N^{slope:.2f} (rapport : 0,6–0,7)")
    axes[0].set_xlabel("Population moyenne (entités vivantes)")
    axes[0].set_ylabel("Plus grande avalanche observée")
    axes[0].set_title("La coupure suit la taille du système", fontsize=10)
    axes[0].legend(fontsize=9)
    axes[1].axhline(14.7, color="k", ls="--", lw=1.0, alpha=0.6,
                    label="~14,7 vivantes / unité de λ (rapport)")
    axes[1].set_xlabel("Taux de naissance λ")
    axes[1].set_ylabel("Population moyenne / λ")
    axes[1].set_title("Population stationnaire, extensive en λ", fontsize=10)
    axes[1].set_ylim(0, 20)
    axes[1].legend(fontsize=9)
    for ax in axes:
        ax.grid(True, which="both", alpha=0.3)
    fig.suptitle("Scaling en taille finie et extensivité — un point par run "
                 "(burn-in T/4)", fontsize=11)
    fig.tight_layout()
    _save(fig, out_dir, "scaling_finite_size.png")


def fig_invariants(lots, out_dir):
    """Invariants du régime : b ≈ 0,30 sur toute la gamme de taille, et
    exposant MLE discret — la dérive apparente à s_min=1 disparaît à
    s_min=2 (exposant de queue ~2,2-2,3, rapport §5)."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for li, lot in enumerate(lots):
        color = LOT_COLORS[li % len(LOT_COLORS)]
        for st in lot["stats"]:
            pop = st["pop_mean"]
            axes[0].semilogx(pop, st["branching_b"], "o", ms=7,
                             alpha=0.85, color=color)
            for s_min, mfc in ((1, color), (2, "none")):
                tail = st["_sizes"][st["_sizes"] >= s_min]
                alpha_mle = _fit_alpha_discrete(tail, s_min)
                if alpha_mle is not None:
                    axes[1].semilogx(pop, alpha_mle, "o", ms=7, alpha=0.85,
                                     color=color, mfc=mfc)
        axes[0].plot([], [], "o", color=color, label=f"λ={lot['lam']:g}")
    axes[0].axhline(0.30, color="k", ls="--", lw=1.0, alpha=0.6,
                    label="b = 0,30 (rapport)")
    axes[0].set_ylim(0, 0.4)
    axes[0].set_ylabel("Rapport de branchement b")
    axes[0].set_title("b invariant sur toute la gamme de taille", fontsize=10)
    axes[0].legend(fontsize=9, loc="lower right")
    axes[1].plot([], [], "o", color="gray", label="α MLE, s_min = 1")
    axes[1].plot([], [], "o", color="gray", mfc="none",
                 label="α MLE, s_min = 2")
    axes[1].axhspan(2.2, 2.35, color="gray", alpha=0.12,
                    label="exposant de queue ~2,2–2,3 (rapport)")
    axes[1].set_ylabel("Exposant α (MLE discret, zêta de Hurwitz)")
    axes[1].set_title("La dérive de α à s_min=1 est un artefact des "
                      "singletons", fontsize=10)
    axes[1].legend(fontsize=9, loc="upper left")
    for ax in axes:
        ax.set_xlabel("Population moyenne (entités vivantes)")
        ax.grid(True, which="both", alpha=0.3)
    fig.suptitle("Invariants du régime d'avalanches — un point par run "
                 "(burn-in T/4)", fontsize=11)
    fig.tight_layout()
    _save(fig, out_dir, "invariants_soc.png")


def fig_criteria_table(lots, out_dir):
    """Table des critères SOC par run, façon table de campagne du rapport."""
    cols = ["λ", "seed", "pop moy.", "max", "α MLE (s_min)", "z PL vs LN",
            "r² hors t.1", "x_c (PL×c)", "b", "rac./taille (≥5)",
            "prof. max", "max/pop"]
    rows = []
    for lot in lots:
        for st in lot["stats"]:
            fit = st.get("tail_fit") or {}
            lr = st.get("lr_vs_lognormal") or {}
            plc = st.get("lr_plc_vs_lognormal") or {}
            reg = st.get("reg_ex1") or {}
            z = lr.get("z")
            x_c = plc.get("x_c")
            if x_c is None:
                x_c_txt = "—"
            elif x_c > 50 * st.get("max_size", 1):
                x_c_txt = "≫ gamme"  # ajustement non borné (rapport, λ≥100)
            else:
                x_c_txt = f"{x_c:.0f}"
            rows.append([
                f"{lot['lam']:g}", str(st["seed"]),
                f"{st['pop_mean']:.0f}", str(st.get("max_size", 0)),
                f"{fit['alpha']:.2f} ({fit['s_min']})" if fit else "—",
                f"{z:+.1f}" if z is not None and z == z else "—",
                f"{reg['r2']:.3f}" if reg else "—",
                x_c_txt,
                f"{st['branching_b']:.3f}",
                (f"{st['big_roots_over_size']:.2f}"
                 if "big_roots_over_size" in st else "—"),
                str(st.get("depth_max", "—")),
                (f"{100 * st['max_over_pop']:.1f} %"
                 if "max_over_pop" in st else "—"),
            ])
    fig, ax = plt.subplots(figsize=(14.5, 0.26 * len(rows) + 1.9))
    ax.axis("off")
    ax.set_position([0.02, 0.02, 0.96, 0.80])
    tbl = ax.table(cellText=rows, colLabels=cols, bbox=[0, 0, 1, 1],
                   cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    for c in range(len(cols)):
        tbl[0, c].set_facecolor("#dfe7f0")
        tbl[0, c].set_text_props(weight="bold")
    ax.set_title(
        "Critères SOC par run (mesure stricte même-pas, burn-in T/4)\n"
        "Références rapport 01_soc_final (T=2000, 3 seeds) : α 2,39–2,54 · "
        "z +2,3 à +35 · r² 0,92–0,98 · b 0,29–0,30 ·\n"
        "rac./taille 0,48–0,51 · profondeur 8–12 · x_c ~35 (λ=10) → non "
        "borné (λ≥100) · max/pop ≤ 16 % (garde anti-effondrement)",
        fontsize=10, pad=14)
    _save(fig, out_dir, "soc_criteria_table.png")


def fig_volume_exponents(lots, out_dir):
    """Régression des paramètres de la loi de puissance du volume (J) en
    fonction de la taille du système : pente de la branche descendante
    (stabilité) et mode (échelle intensive). Consigne du 17/07 : abandon de
    la branche montante."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    pops, sr, modes = [], [], []
    for li, lot in enumerate(lots):
        color = LOT_COLORS[li % len(LOT_COLORS)]
        first = True
        for st, (seed, folder, _) in zip(lot["stats"], lot["members"]):
            t_min = lot["cfg"]["T"] // 4
            vols = [v for t, v in _volumes_cached(folder)
                    if t >= t_min and v > 0]
            bf = _volume_branch_fit(vols)
            if bf is None:
                continue
            pops.append(st["pop_mean"])
            sr.append(bf["slope_right"])
            modes.append(bf["mode"])
            axes[0].semilogx(st["pop_mean"], bf["slope_right"], "v", ms=7,
                             alpha=0.85, color=color,
                             label=f"λ={lot['lam']:g}" if first else None)
            axes[1].loglog(st["pop_mean"], bf["mode"], "o", ms=7,
                           alpha=0.85, color=color)
            first = False
    if not pops:
        plt.close(fig)
        return
    lp = np.log10(np.asarray(pops))
    coef = np.polyfit(lp, sr, 1)
    xs = np.linspace(lp.min() - 0.05, lp.max() + 0.05, 20)
    axes[0].plot(10 ** xs, np.polyval(coef, xs), "--", lw=1.1, color="gray")
    axes[0].plot([], [], "v--", color="gray",
                 label=(f"pente descendante : {np.mean(sr):+.2f} "
                        f"± {np.std(sr):.2f} ; dérive "
                        f"{coef[0]:+.2f}/décade de pop."))
    lm = np.log10(np.asarray(modes))
    coef_m = np.polyfit(lp, lm, 1)
    xs = np.linspace(lp.min() - 0.05, lp.max() + 0.05, 20)
    axes[1].plot(10 ** xs, 10 ** np.polyval(coef_m, xs), "k--", lw=1.2,
                 label=f"mode ∝ N^{coef_m[0]:.2f}")
    axes[0].set_ylabel("Pente log-log de la branche descendante")
    axes[0].set_title("Exposant de la loi de puissance du volume",
                      fontsize=10)
    axes[0].legend(fontsize=8)
    axes[1].set_ylabel("Mode de la densité du volume (J)")
    axes[1].set_title("Position du mode vs taille du système", fontsize=10)
    axes[1].legend(fontsize=9)
    for ax in axes:
        ax.set_xlabel("Population moyenne (entités vivantes)")
        ax.grid(True, which="both", alpha=0.3)
    fig.suptitle("Volume des avalanches (J) : pente de la branche "
                 "descendante et mode vs taille du système — un point par "
                 "run (burn-in T/4)", fontsize=11)
    fig.tight_layout()
    _save(fig, out_dir, "volume_exponents.png")


def export_synthesis(batch_ids, force=False):
    """Construit le run synthétique inter-lots (figures du rapport)."""
    export_dir = RUNS_DIR / SYNTH_ID
    if export_dir.exists() and not force:
        raise FileExistsError(f"{export_dir} existe (utiliser --force)")
    fig_dir = export_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    lots = _lot_stats(batch_ids)
    if len(lots) < 2:
        raise RuntimeError("synthèse : il faut au moins 2 lots complets")

    for fn in (fig_scaling_ccdf, fig_scaling_finite_size, fig_invariants,
               fig_volume_exponents, fig_criteria_table):
        fn(lots, fig_dir)
        print(f"  {fn.__name__}", flush=True)

    payload = []
    for lot in lots:
        for st in lot["stats"]:
            row = {k: v for k, v in st.items() if not k.startswith("_")}
            row["lam"] = lot["lam"]
            row["batch_id"] = lot["batch_id"]
            payload.append(row)
    with open(export_dir / "soc_summary.json", "w") as fh:
        json.dump(dict(batch_ids=[lot["batch_id"] for lot in lots],
                       stats=payload), fh, indent=2, default=float)

    from simulation_lab.contracts import collect_artifacts
    now = datetime.now(timezone.utc).isoformat()
    lams = "/".join(f"{lot['lam']:g}" for lot in lots)
    cfg = lots[0]["cfg"]
    run_meta = {
        "run_id": SYNTH_ID,
        "model_id": MODEL_ID,
        "parameters": {"lots": f"λ={lams}", "T": cfg["T"],
                       "seeds_par_lot": len(lots[0]["members"])},
        "seed": None,
        "label": f"Synthèse SOC inter-lots (λ={lams}) — figures du rapport "
                 "01_soc_final",
        "batch_id": None,
        "status": "completed",
        "keep": True,
        "important": False,
        "trashed": False,
        "trashed_at": None,
        "created_at": now,
        "updated_at": now,
        "summary": {
            "lots": len(lots),
            "runs": sum(len(lot["members"]) for lot in lots),
            "branching_b_min": round(min(st["branching_b"]
                                         for lot in lots
                                         for st in lot["stats"]), 3),
            "branching_b_max": round(max(st["branching_b"]
                                         for lot in lots
                                         for st in lot["stats"]), 3),
            "avalanche_max": max(st["max_size"] for lot in lots
                                 for st in lot["stats"]),
        },
        "artifacts": [a.to_dict() for a in collect_artifacts(export_dir)],
        "message": ("Figures inter-lots illustrant les conclusions du "
                    "rapport 01_soc_final : scaling de la coupure, "
                    "invariance de b, exposant, table des critères. "
                    "Stats par run : soc_summary.json"),
        "preview_artifact": "figures/scaling_ccdf.png",
        "origin": "export",
        "deletable": True,
    }
    with open(export_dir / "run.json", "w") as fh:
        json.dump(run_meta, fh, indent=2)
    print(f"export : {export_dir}")
    return SYNTH_ID


def m4_batches():
    out = []
    for p in sorted(BATCHES_DIR.glob("*.json")):
        with open(p) as fh:
            b = json.load(fh)
        if b.get("model_id") == MODEL_ID:
            out.append(b["batch_id"])
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    all_m4 = args == ["--all-m4"]
    ids = m4_batches() if all_m4 else args
    if not ids:
        print(__doc__)
        sys.exit(1)
    for bid in ids:
        print(f"=== lot {bid} ===")
        export_batch(bid, force=force)
    if all_m4 and len(ids) >= 2:
        print("=== synthèse inter-lots ===")
        export_synthesis(ids, force=force)
