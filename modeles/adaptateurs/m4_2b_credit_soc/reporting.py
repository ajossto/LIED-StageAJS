"""Recettes des 28 figures M4.2/M4.2B (copie adaptée des recettes M4B).

Copié SANS MODIFICATION de
modeles-systeme-physicoeconomique/m4_2_credit_soc/reporting.py (parité
graphique stricte, PROMPT_M4_2B.md §20). Vérifié avant la copie : ce module
ne connaît pas le moteur, ne lit que config.json/series.csv/snapshots par
nom de colonne, et ne suppose nulle part que le principal suit la cible
géométrique K*=√(K_ℓK_b) — aucune figure ne recalcule un principal attendu à
partir de q,r pour le comparer à une formule ; le taux marginal interne
r*=A·γ·K^(γ-1) (lu depuis γ,A de la config) reste valide sous les deux
target_rule. Il est donc réutilisable tel quel pour M4.2B, target_rule
inclus (le champ config["parameters"]["target_rule"] est simplement ignoré
par ce module, comme les nouveaux champs rho/eta_beta/eta_n_ref).
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import LogNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy import stats
from scipy.optimize import minimize


COLORS = plt.cm.tab10.colors
REVENUES = (
    ("prod", "Production Π", "revenue_distribution_prod", "#2ca02c"),
    ("int_in", "Intérêts reçus", "revenue_distribution_int_in", "#1f77b4"),
    ("int_out", "Intérêts payés", "revenue_distribution_int_out", "#d62728"),
    ("income", "Revenu total brut", "revenue_distribution_income", "#ff7f0e"),
    ("income_net", "Revenu net positif", "revenue_distribution_income_net", "#9467bd"),
)

# Copie machine-readable de la sélection validée dans l'ODS. Cette liste est
# volontairement explicite : ajouter une figure redevient une décision visible.
SELECTED_FAMILIES = (
    "R01", "R02", "R03", "R05", "R06", "R07", "R08", "R09", "R10",
    "R11", "R12", "R14", "R15", "R17", "R18", "R19", "R20",
    "S06", "S08", "S10", "S11", "L02", "L04", "L12", "L13", "L14",
    "L15", "Y03",
)

OBSOLETE_OUTPUTS = (
    "avalanche_sizes.png", "avalanche_sizes_semilog.png",
    "avalanche_sizes_linear.png", "entity_distributions_final.png",
    "entity_distributions_final_semilog.png",
    "entity_distributions_final_linear.png", "entity_size_histos.png",
    "revenue_distributions.png", "soc_revenue_fit.png",
)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as stream:
        rows = []
        for row in csv.DictReader(stream):
            converted = {}
            for key, value in row.items():
                if value in (None, ""):
                    converted[key] = ""
                    continue
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = value
            rows.append(converted)
        return rows


def config(folder: Path) -> dict:
    payload = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    return payload.get("parameters", payload)


def snapshots(folder: Path) -> dict[int, dict[str, np.ndarray]]:
    result = {}
    for path in sorted((folder / "snapshots").glob("entities_t*.npz")):
        step = int(path.stem.split("t")[-1])
        with np.load(path) as data:
            result[step] = {key: np.asarray(data[key]) for key in data.files}
    return result


def save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=145, bbox_inches="tight")
    plt.close(fig)


def rolling(values, window: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if not len(values):
        return values
    window = max(1, min(window, len(values)))
    return np.convolve(values, np.ones(window) / window, mode="same")


def gini(values) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values >= 0)]
    if not len(values) or values.sum() <= 0:
        return 0.0
    values.sort()
    n = len(values)
    return float((2 * np.dot(np.arange(1, n + 1), values) / values.sum() - n - 1) / n)


def lorenz(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values >= 0)]
    if not len(values) or values.sum() <= 0:
        return None
    cumulative = np.r_[0.0, np.cumsum(np.sort(values))]
    return np.linspace(0, 1, len(cumulative)), cumulative / cumulative[-1], gini(values)


def wilson(counts, total, widths):
    p = counts / total
    denominator = 1.0 + 1.0 / total
    midpoint = (p + 1.0 / (2.0 * total)) / denominator
    radius = np.sqrt(p * (1.0 - p) / total + 1.0 / (4.0 * total**2)) / denominator
    density = p / widths
    return density, np.maximum(0, midpoint - radius) / widths, np.minimum(1, midpoint + radius) / widths


def adaptive_hist(values, *, integer=False, max_bins=42):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    if len(values) < 2 or values.min() == values.max():
        return None
    bins = max(5, min(max_bins, int(np.sqrt(len(values)))))
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(values, quantiles))
    if integer:
        edges = np.unique(np.r_[max(0.5, edges[0] - 0.5), np.floor(edges[1:-1]) + 0.5, edges[-1] + 0.5])
    else:
        edges[0] = max(np.nextafter(0.0, 1.0), edges[0] * 0.999999)
        edges[-1] *= 1.000001
    if len(edges) < 3:
        return None
    counts, _ = np.histogram(values, edges)
    widths = np.diff(edges)
    centres = np.sqrt(edges[:-1] * edges[1:])
    density, lower, upper = wilson(counts, len(values), widths)
    return edges, centres, counts, density, lower, upper


def nl_logpdf(y, nu, tau, a, b):
    z = (y - nu) / tau
    left = a * (nu - y) + 0.5 * (a * tau) ** 2 + stats.norm.logcdf(z - a * tau)
    right = b * (y - nu) + 0.5 * (b * tau) ** 2 + stats.norm.logcdf(-(z + b * tau))
    return math.log(a) + math.log(b) - math.log(a + b) + np.logaddexp(left, right)


def dpln_logpdf(x, nu, tau, a, b):
    x = np.asarray(x, dtype=float)
    return nl_logpdf(np.log(x), nu, tau, a, b) - np.log(x)


def fit_dpln(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    if len(values) < 40:
        return None
    if len(values) > 50_000:
        values = np.random.default_rng(0).choice(values, 50_000, replace=False)
    y = np.log(values)
    mean, sd = float(y.mean()), max(float(y.std()), 1e-3)

    def objective(theta):
        nu, lt, la, lb = theta
        tau, a, b = np.exp([lt, la, lb])
        if tau > 50 or a > 1e4 or b > 1e4:
            return 1e100
        value = -float(nl_logpdf(y, nu, tau, a, b).sum())
        return value if np.isfinite(value) else 1e100

    starts = (
        (mean, math.log(sd), math.log(2 / sd), math.log(2 / sd)),
        (mean, math.log(sd / 2), math.log(1 / sd), math.log(3 / sd)),
        (mean - sd, math.log(sd), math.log(3 / sd), math.log(1 / sd)),
    )
    results = [minimize(objective, start, method="Nelder-Mead", options={"maxiter": 1800}) for start in starts]
    best = min(results, key=lambda result: result.fun)
    if not np.isfinite(best.fun) or best.fun >= 1e99:
        return None
    nu, lt, la, lb = best.x
    return {"nu": float(nu), "tau": float(np.exp(lt)), "a": float(np.exp(la)), "b": float(np.exp(lb))}


def fit_cutoff_powerlaw(values):
    """MLE discrète de p(s) ∝ s^-alpha exp(-s/s_c), s >= 2."""
    values=np.asarray(values,dtype=int); values=values[values>=2]
    if len(values)<20: return None
    maximum=int(values.max()); support=np.arange(2,max(maximum+1,4),dtype=float)
    def objective(theta):
        alpha,log_cutoff=theta; cutoff=math.exp(log_cutoff); logw=-alpha*np.log(support)-support/cutoff; logz=np.logaddexp.reduce(logw)
        return float(np.sum(alpha*np.log(values)+values/cutoff+logz))
    result=minimize(objective,(1.5,math.log(max(2,maximum))),method="Nelder-Mead",options={"maxiter":1200})
    if not result.success or not np.isfinite(result.fun): return None
    alpha,log_cutoff=result.x; cutoff=math.exp(log_cutoff)
    if alpha<=0 or cutoff<=0: return None
    logw=-alpha*np.log(support)-support/cutoff; pmf=np.exp(logw-np.logaddexp.reduce(logw))
    return {"alpha":float(alpha),"cutoff":float(cutoff),"support":support,"pmf":pmf}


def _plot_adaptive(axis, values, color, label=None, integer=False):
    result = adaptive_hist(values, integer=integer)
    if result is None:
        return None
    edges, centres, counts, density, lower, upper = result
    keep = counts > 0
    axis.errorbar(
        centres[keep], density[keep],
        xerr=np.vstack((centres - edges[:-1], edges[1:] - centres))[:, keep],
        yerr=np.vstack((density - lower, upper - density))[:, keep],
        fmt="o", ms=3.1, capsize=2, elinewidth=.7, alpha=.72, color=color,
        label=label,
    )
    return result


def macro(members, out: Path, title: str):
    # Un seul graphe, trois échelles superposées (host + 2 axes parasites) :
    # capital (J), crédit nouveau (J/pas), population (effectif), plus
    # ΣDettes/ΣCapital (sans unité). nw_tot est omis : par identité comptable
    # (créances = dettes agrégées) il est égal à K_tot au bruit numérique près,
    # donc redondant avec la courbe K. Le ratio ΣD/ΣK n'est pas stocké pas à
    # pas dans series.csv (seuls des flux y figurent) — il est reconstruit ici
    # à partir des instantanés (npz), donc à la cadence (plus lâche) de
    # snapshot_every : c'est pourquoi il apparaît en pointillés/marqueurs
    # plutôt qu'en trait continu comme les séries pas-à-pas.
    fig, host = plt.subplots(figsize=(12, 6.5))
    ax_credit, ax_pop, ax_ratio = host.twinx(), host.twinx(), host.twinx()
    ax_pop.spines["right"].set_position(("outward", 55))
    ax_ratio.spines["right"].set_position(("outward", 110))
    for axis in (ax_pop, ax_ratio):
        axis.set_frame_on(True); axis.patch.set_visible(False)

    c_k, c_credit, c_pop, c_ratio = "#1f77b4", "#d62728", "#2ca02c", "#7f2aa3"
    host.set_ylabel("Capital K (J)", color=c_k)
    ax_credit.set_ylabel("Nouveau crédit (J/pas)", color=c_credit)
    ax_pop.set_ylabel("Population", color=c_pop)
    ax_ratio.set_ylabel("ΣDettes / ΣCapital (aux instantanés)", color=c_ratio)
    for axis, color in ((host, c_k), (ax_credit, c_credit), (ax_pop, c_pop), (ax_ratio, c_ratio)):
        axis.tick_params(axis="y", colors=color)

    handles = []; any_ratio = False
    for index, (seed, folder) in enumerate(members):
        rows = read_csv(folder / "series.csv")
        if not rows:
            continue
        t = [row["t"] for row in rows]
        fade = 1.0 if index == 0 else 0.5
        h1, = host.plot(t, [row["K_tot"] for row in rows], color=c_k, alpha=.85 * fade, label=f"K — seed {seed}")
        h3, = ax_credit.plot(t, [row["loan_volume"] for row in rows], color=c_credit, alpha=.7 * fade, label=f"nouveau crédit — seed {seed}")
        h4, = ax_pop.plot(t, [row["pop"] for row in rows], color=c_pop, alpha=.8 * fade, label=f"population — seed {seed}")
        handles += [h1, h3, h4]

        snaps = snapshots(folder)
        if snaps:
            steps = sorted(snaps)
            ratio = []
            for step in steps:
                snap = snaps[step]
                k_sum = float(np.sum(snap["K"]))
                ratio.append(float(np.sum(snap["debts"])) / k_sum if k_sum > 0 else np.nan)
            h5, = ax_ratio.plot(steps, ratio, color=c_ratio, ls=":", marker="o", ms=3, lw=1.1, alpha=.85 * fade, label=f"ΣD/ΣK — seed {seed}")
            handles.append(h5); any_ratio = True
    if not any_ratio:
        ax_ratio.set_visible(False)
    host.set_xlabel("Pas"); host.grid(True, alpha=.22)
    host.legend(handles=handles, fontsize=7, loc="upper left", ncol=2)
    fig.suptitle(f"Vue macro : capital, crédit, population et levier — {title}")
    fig.tight_layout(); save(fig, out / "macro_overview.png")


def avalanche_samples(folder: Path):
    rows = read_csv(folder / "avalanches.csv")
    burn = int(config(folder).get("T", 0)) // 4
    selected = [row for row in rows if row.get("t", 0) >= burn and row.get("size", 0) >= 2]
    sizes = np.asarray([row["size"] for row in selected], dtype=int)
    if selected and "volume_j" not in selected[0]:
        # Migration en lecture seule des runs m4b-mini-2 : la dette capturée
        # juste avant chaque décès est exactement le principal détruit.
        debts = {(int(row["t"]), int(row["id"])): float(row["debts"]) for row in read_csv(folder / "deaths.csv")}
        members = defaultdict(float)
        for row in read_csv(folder / "avalanche_members.csv"):
            members[int(row["avalanche_id"])] += debts.get((int(row["t"]), int(row["id"])), 0.0)
        volumes = np.asarray([members[int(row["avalanche_id"])] for row in selected], dtype=float)
    else:
        volumes = np.asarray([row.get("volume_j", 0) for row in selected], dtype=float)
    return selected, sizes, volumes[volumes > 0]


def avalanche_figures(members, out: Path, title: str, volume_ccdf_output=True):
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.7))
    any_data = False
    for index, (seed, folder) in enumerate(members):
        _, sizes, volumes = avalanche_samples(folder)
        color = COLORS[index % len(COLORS)]
        if len(sizes) >= 2:
            any_data = True
            histogram=_plot_adaptive(axes[0], sizes, color, f"seed {seed}, n={len(sizes)}", integer=True)
            ordered = np.sort(sizes); ccdf = (len(ordered) - np.arange(len(ordered))) / len(ordered)
            axes[1].plot(ordered, ccdf, ".", ms=2.2, alpha=.55, color=color)
            fit_size=fit_cutoff_powerlaw(sizes)
            if fit_size and histogram is not None:
                edges,centres,_,_,_,_=histogram; model=[]
                for lower,upper in zip(edges[:-1],edges[1:]):
                    inside=(fit_size["support"]>=lower)&(fit_size["support"]<upper); model.append(fit_size["pmf"][inside].sum()/(upper-lower))
                model=np.asarray(model); keep=model>0
                axes[0].plot(centres[keep],model[keep],"--",color=color,lw=1.3,label=f"s⁻ᵅe⁻ˢ/ˢᶜ : α={fit_size['alpha']:.2f}, s_c={fit_size['cutoff']:.1f}")
                survival=np.cumsum(fit_size["pmf"][::-1])[::-1]
                axes[1].plot(fit_size["support"],survival,"--",color=color,lw=1.3)
        if len(volumes) >= 2:
            histogram = _plot_adaptive(axes[2], volumes, color, f"seed {seed}, n={len(volumes)}")
            # La dPlN est ajustée uniquement sur la branche descendante.
            if histogram is not None:
                fit = fit_dpln(volumes)
                if fit:
                    grid = np.logspace(np.log10(volumes.min()), np.log10(volumes.max()), 240)
                    model = np.exp(dpln_logpdf(grid, **fit)); mode = grid[int(np.argmax(model))]; descending = grid >= mode
                    axes[2].plot(grid[descending], model[descending], "-", lw=1.3, color=color,
                                 label=f"dPlN descendante v≥{mode:.2g} J, α={fit['a']+1:.2f}")
    if not any_data:
        plt.close(fig)
    else:
        for axis in axes: axis.set_xscale("log"); axis.set_yscale("log"); axis.grid(True, which="both", alpha=.2)
        axes[0].set(title="Taille : bins adaptatifs + IC Wilson 68 %", xlabel="Taille s≥2", ylabel="Densité")
        axes[1].set(title="CCDF des tailles", xlabel="Taille s≥2", ylabel="P(S≥s)")
        axes[2].set(title="Volume : dPlN sur branche descendante", xlabel="Pertes de créances (J)", ylabel="Densité")
        axes[0].legend(fontsize=7); axes[2].legend(fontsize=7)
        fig.suptitle(f"Cascades rank-size — burn-in T/4 — {title}"); fig.tight_layout()
        save(fig, out / "cascades_rank_size.png")

    if not volume_ccdf_output:
        return
    fig, axis = plt.subplots(figsize=(9.5, 6))
    plotted = False
    for index, (seed, folder) in enumerate(members):
        _, _, volumes = avalanche_samples(folder)
        if len(volumes) < 2: continue
        plotted = True; ordered = np.sort(volumes)
        axis.plot(ordered, (len(ordered) - np.arange(len(ordered))) / len(ordered), ".", ms=2.3, alpha=.58, color=COLORS[index % 10], label=f"seed {seed}, n={len(ordered)}")
    if plotted:
        axis.set(xscale="log", yscale="log", xlabel="Volume d'avalanche (pertes de créances, J)", ylabel="P(V≥v)")
        axis.set_title(f"CCDF des volumes d'avalanches — tailles ≥ 2 — {title}"); axis.grid(True, which="both", alpha=.22); axis.legend(fontsize=8)
        fig.tight_layout(); save(fig, out / "volume_ccdf.png")
    else: plt.close(fig)


def temporal_density(snaps, key, bins=32):
    steps = sorted(snaps)
    arrays = []
    for step in steps:
        values = np.asarray(snaps[step][key], dtype=float)
        arrays.append(values[np.isfinite(values) & (values > 0)])
    nonempty = [values for values in arrays if len(values)]
    if not nonempty: return None
    pooled = np.concatenate(nonempty)
    if len(pooled) < 10 or pooled.min() == pooled.max(): return None
    edges = np.logspace(np.log10(pooled.min()), np.log10(pooled.max() * 1.0001), bins + 1)
    widths = np.diff(edges); centres = np.sqrt(edges[:-1] * edges[1:])
    densities = np.asarray([np.histogram(values, edges)[0] / (max(1, len(values)) * widths) for values in arrays])
    return np.asarray(steps), centres, densities, np.asarray([len(values) for values in arrays])


def _time_weights(steps):
    steps = np.asarray(steps, dtype=float)
    if len(steps) == 1: return np.ones(1)
    weights = np.r_[steps[1] - steps[0], steps[2:] - steps[:-2], steps[-1] - steps[-2]] / 2
    return weights / weights.sum()


def _weighted_quantile(values, weights, quantile):
    order = np.argsort(values)
    ordered = np.asarray(values, dtype=float)[order]
    cumulative = np.cumsum(np.asarray(weights, dtype=float)[order])
    return float(np.interp(quantile, cumulative, ordered))


def temporal_distribution(folder, out, key, label, stem, color, title):
    prepared = temporal_density(snapshots(folder), key)
    if prepared is None: return
    steps, centres, densities, counts = prepared
    weights = _time_weights(steps); mean = np.average(densities, axis=0, weights=weights)
    # Enveloppe D1-D9 : dispersion temporelle (inter-instantanés) de la densité
    # à chaque bin, pas une incertitude d'échantillonnage — remise en place à
    # l'identique de la convention M4 (cf. individual_figures.py, M4).
    q10 = np.asarray([_weighted_quantile(densities[:, j], weights, .1) for j in range(densities.shape[1])])
    q90 = np.asarray([_weighted_quantile(densities[:, j], weights, .9) for j in range(densities.shape[1])])
    positive = densities[densities > 0]
    if not len(positive): return
    ymin, ymax = max(1e-14, positive.min() / 2), max(positive.max(), mean.max()) * 2
    fig, axis = plt.subplots(figsize=(9.5, 5.8))
    band = q90 > 0
    axis.fill_between(centres[band], np.maximum(q10[band], ymin), q90[band], color=color, alpha=.2, label="enveloppe temporelle D1–D9")
    valid = mean > 0; axis.plot(centres[valid], mean[valid], "o-", ms=3, lw=1.5, color="black", label=f"moyenne pondérée, {len(steps)} snapshots")
    axis.set(xscale="log", yscale="log", ylim=(ymin, ymax), xlabel=label, ylabel="Densité")
    axis.set_title(f"Distribution moyenne dans le temps — {title}"); axis.grid(True, which="both", alpha=.22); axis.legend()
    fig.tight_layout(); save(fig, out / f"{stem}_temporal_mean.png")
    if len(steps) < 2:
        return
    frame_ids = np.unique(np.linspace(0, len(steps) - 1, min(48, len(steps)), dtype=int))
    fig, axis = plt.subplots(figsize=(9.5, 5.8)); line, = axis.plot([], [], "o-", ms=3, color=color)
    axis.plot(centres[valid], mean[valid], color="black", lw=1.7, label="moyenne temporelle")
    axis.set(xscale="log", yscale="log", xlim=(centres[0] / 1.1, centres[-1] * 1.1), ylim=(ymin, ymax), xlabel=label, ylabel="Densité")
    axis.grid(True, which="both", alpha=.22); axis.legend()
    def update(frame):
        index = frame_ids[frame]; density = densities[index]; keep = density > 0
        line.set_data(centres[keep], density[keep]); axis.set_title(f"{title} — t={steps[index]}, n={counts[index]}")
        return line,
    FuncAnimation(fig, update, frames=len(frame_ids), interval=170).save(out / f"{stem}_evolution.gif", writer=PillowWriter(fps=6), dpi=90)
    plt.close(fig)


def temporal_selected(folder: Path, out: Path, title: str):
    temporal_distribution(folder, out, "K", "Capital K (J)", "entity_size_histo", "#1f77b4", title)
    temporal_distribution(folder, out, "nw", "Valeur nette NW (J)", "entity_networth_histo", "#663399", title)
    for key, label, stem, color in REVENUES:
        temporal_distribution(folder, out, key, f"{label} (J/pas)", stem, color, title)


def series_figures(members, out: Path, title: str):
    fig, axis = plt.subplots(figsize=(12, 5))
    for index, (seed, folder) in enumerate(members):
        snaps=snapshots(folder); steps=sorted(snaps); color=COLORS[index%10]
        if not steps: continue
        med=[]; q10=[]; q90=[]
        for step in steps:
            values=np.asarray(snaps[step]["prod"],dtype=float); values=values[np.isfinite(values)&(values>=0)]
            med.append(np.median(values) if len(values) else 0); q10.append(np.quantile(values,.1) if len(values) else 0); q90.append(np.quantile(values,.9) if len(values) else 0)
        axis.fill_between(steps,q10,q90,color=color,alpha=.14); axis.plot(steps,med,color=color,label=f"médiane seed {seed}")
    axis.set(title=f"Production individuelle (médiane et D1–D9) — {title}", xlabel="Pas", ylabel="Production Π (J/pas)"); axis.grid(True, alpha=.22); axis.legend(fontsize=7)
    fig.tight_layout(); save(fig, out / "extraction_power.png")

    fig, axis = plt.subplots(figsize=(12, 5))
    for index, (seed, folder) in enumerate(members):
        rows = read_csv(folder / "series.csv"); t = [row["t"] for row in rows]
        if not rows: continue
        window = max(5, min(100, len(rows) // 10)); color = COLORS[index % 10]
        axis.plot(t, rolling([row["prod_tot"] for row in rows], window), color=color, alpha=.55, label=f"production seed {seed}")
        axis.plot(t, rolling([row["destroyed"] + row["claim_losses"] for row in rows], window), color=color, ls="--", label=f"destruction seed {seed}")
    axis.set(title=f"Destruction moyenne face à la production — {title}", xlabel="Pas", ylabel="J/pas"); axis.grid(True, alpha=.22); axis.legend(fontsize=7)
    fig.tight_layout(); save(fig, out / "destruction_moving_avg.png")

    fig, axis = plt.subplots(figsize=(12, 5))
    for index, (seed, folder) in enumerate(members):
        cfg = config(folder)
        gamma = float(cfg.get("gamma", 0.5)); scale_A = float(cfg.get("A", 1.0))
        snaps = snapshots(folder); steps=[]; values=[]
        for step, snap in snaps.items():
            k = np.asarray(snap["K"]); k = k[k > 0]
            if len(k): steps.append(step); values.append(float(np.median(scale_A * gamma * np.power(k, gamma - 1.0))))
        if steps: axis.plot(steps, values, "o-", ms=3, color=COLORS[index % 10], label=f"seed {seed}, γ={gamma:g}")
    axis.set(title=f"Évolution du taux marginal interne médian — {title}", xlabel="Pas", ylabel="r*=A·γ·K^(γ−1)"); axis.grid(True, alpha=.22); axis.legend(fontsize=8)
    fig.tight_layout(); save(fig, out / "internal_rate_evolution.png")


def inequality_figures(members, out: Path, title: str):
    fig, axis = plt.subplots(figsize=(12, 5))
    for index, (seed, folder) in enumerate(members):
        snaps = snapshots(folder); steps = sorted(snaps)
        color = COLORS[index % 10]
        if steps:
            axis.plot(steps, [gini(snaps[t]["K"]) for t in steps], color=color, label=f"taille seed {seed}")
            axis.plot(steps, [gini(np.maximum(snaps[t]["int_in"], 0)) for t in steps], color=color, ls="--", label=f"intérêts reçus seed {seed}")
    axis.set(ylim=(0, 1), title=f"Évolution des coefficients de Gini — {title}", xlabel="Pas", ylabel="Gini")
    axis.grid(True, alpha=.22); axis.legend(fontsize=7, ncol=2); fig.tight_layout(); save(fig, out / "gini_evolution.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for axis, (key, label) in zip(axes, (("K", "Taille K"), ("int_in", "Intérêts reçus"))):
        axis.plot([0, 1], [0, 1], "--", color="gray")
        for index, (seed, folder) in enumerate(members):
            snaps = snapshots(folder)
            for step in sorted(snaps):
                result = lorenz(np.maximum(snaps[step][key], 0))
                if result:
                    x, y, value = result
                    axis.plot(x, y, color=COLORS[index % 10], alpha=.18 if step != max(snaps) else .9, lw=.6 if step != max(snaps) else 1.8,
                              label=f"seed {seed} final G={value:.3f}" if step == max(snaps) else None)
        axis.set(title=label, xlabel="Part cumulée des entités", ylabel="Part cumulée"); axis.grid(True, alpha=.2); axis.legend(fontsize=7)
    fig.suptitle(f"Courbes de Lorenz aux snapshots et Ginis finaux — {title}"); fig.tight_layout(); save(fig, out / "gini_lorenz_snapshots.png")


def network_figure(folder: Path, out: Path, title: str):
    rows = read_csv(folder / "final_loans.csv")
    if not rows: return
    # Vue structurelle matricielle : lisible même pour des milliers de nœuds.
    lenders = np.asarray([row["lender"] for row in rows]); borrowers = np.asarray([row["borrower"] for row in rows]); q = np.asarray([row["q"] for row in rows])
    payments = q * np.asarray([row["r"] for row in rows], dtype=float)
    entities = np.unique(np.r_[lenders, borrowers])
    lend_count = {entity: int(np.sum(lenders == entity)) for entity in entities}
    borrow_count = {entity: int(np.sum(borrowers == entity)) for entity in entities}
    lend_power = {entity: float(np.sum(payments[lenders == entity])) for entity in entities}
    borrow_power = {entity: float(np.sum(payments[borrowers == entity])) for entity in entities}
    degree = {entity: lend_count[entity] + borrow_count[entity] for entity in entities}
    order = {entity: index for index, entity in enumerate(sorted(entities, key=lambda e: degree[e], reverse=True))}
    x = np.asarray([order[value] for value in borrowers]); y = np.asarray([order[value] for value in lenders])
    fig, (axis, hist, roles, power) = plt.subplots(1, 4, figsize=(25, 6), gridspec_kw={"width_ratios": [2.0, 1, 1.15, 1.15]})
    image = axis.hexbin(x, y, C=np.log10(q), reduce_C_function=np.mean, gridsize=70, mincnt=1, cmap="viridis")
    fig.colorbar(image, ax=axis, label="log10 principal moyen (J)")
    axis.set(title="Matrice prêteuse → emprunteuse, rangée par degré", xlabel="Rang emprunteuse", ylabel="Rang prêteuse")
    degrees = np.asarray(list(degree.values())); hist.hist(degrees, bins="auto", color="#4c78a8"); hist.set(title="Distribution des degrés", xlabel="Degré total (contrats)", ylabel="Entités")

    # Distribution jointe : nombre de contrats actifs par entité, séparément en
    # tant que prêteuse et en tant qu'emprunteuse (un même contrat ne compte
    # que d'un côté ; un binôme prêteur-emprunteur récurrent compte plusieurs fois).
    lend_vals = np.asarray([lend_count[e] for e in entities]); borrow_vals = np.asarray([borrow_count[e] for e in entities])
    edges_l = np.arange(-0.5, int(lend_vals.max()) + 1.5); edges_b = np.arange(-0.5, int(borrow_vals.max()) + 1.5)
    counts2d, _, _ = np.histogram2d(borrow_vals, lend_vals, bins=(edges_b, edges_l))
    masked = np.ma.masked_where(counts2d.T == 0, counts2d.T)
    image2 = roles.pcolormesh(edges_b, edges_l, masked, cmap="magma", norm=LogNorm(vmin=1, vmax=max(1, counts2d.max())))
    fig.colorbar(image2, ax=roles, label="Entités (log)")
    if len(entities) >= 3 and borrow_vals.std() > 0:
        # Régression linéaire (moindres carrés ordinaires) y = a x + b.
        slope, intercept, r_value, _, stderr = stats.linregress(borrow_vals, lend_vals)
        x_line = np.array([edges_b[0], edges_b[-1]]); y_line = slope * x_line + intercept
        sign = "+" if intercept >= 0 else "−"
        roles.plot(x_line, y_line, "--", color="tab:blue", lw=1.5,
                   label=f"MCO : y = {slope:.2f}x {sign} {abs(intercept):.2f}, R²={r_value**2:.3f}")
        roles.legend(fontsize=7, loc="upper left")
    roles.set(title="Contrats actifs : rôle prêteuse vs emprunteuse", xlabel="Contrats en tant qu'emprunteuse", ylabel="Contrats en tant que prêteuse")

    # Même distribution jointe, mais en puissance (J/pas) plutôt qu'en nombre de
    # contrats : paiement d'intérêt courant par prêt = q x r (cf. model.py,
    # payment = ratio * principal * rate). Échelle log-log au centre, donc
    # limitée aux entités à la fois prêteuses et emprunteuses actives ; les
    # rôles purs (puissance nulle sur un axe, non représentable en log) sont
    # reportés sur deux bandes marginales contiguës aux axes, avec un
    # découpage plus grossier (moins de classes, seule une dimension est peuplée).
    lend_p = np.asarray([lend_power[e] for e in entities]); borrow_p = np.asarray([borrow_power[e] for e in entities])
    dual = (lend_p > 0) & (borrow_p > 0)
    pure_lender = (lend_p > 0) & (borrow_p == 0)
    pure_borrower = (borrow_p > 0) & (lend_p == 0)
    inactive = int(((lend_p == 0) & (borrow_p == 0)).sum())
    if dual.sum() >= 5:
        divider = make_axes_locatable(power)
        ax_left = divider.append_axes("left", size="20%", pad=0.06, sharey=power)
        ax_bottom = divider.append_axes("bottom", size="20%", pad=0.06, sharex=power)
        cax = divider.append_axes("right", size="4%", pad=0.12)

        image3 = power.hexbin(borrow_p[dual], lend_p[dual], gridsize=40, mincnt=1, bins="log", xscale="log", yscale="log", cmap="magma")
        fig.colorbar(image3, cax=cax, label="Entités (log)")

        def _coarse_log_edges(values, max_bins=10):
            values = values[values > 0]
            if len(values) < 2 or values.min() == values.max():
                return None
            n_bins = max(3, min(max_bins, int(round(math.sqrt(len(values))))))
            return np.logspace(math.log10(values.min()), math.log10(values.max() * 1.0001), n_bins + 1)

        edges = _coarse_log_edges(lend_p[pure_lender])
        if edges is not None:
            counts, _ = np.histogram(lend_p[pure_lender], bins=edges)
            ax_left.barh(edges[:-1], counts, height=np.diff(edges), align="edge", color="#7f2aa3", alpha=.75)
        ax_left.set_yscale("log"); ax_left.invert_xaxis()
        ax_left.set_ylabel("Puissance prêtée Σq·r (J/pas)"); ax_left.set_xlabel(f"Prêteuses\npures (n={int(pure_lender.sum())})", fontsize=8)
        ax_left.tick_params(labelbottom=False)

        edges = _coarse_log_edges(borrow_p[pure_borrower])
        if edges is not None:
            counts, _ = np.histogram(borrow_p[pure_borrower], bins=edges)
            ax_bottom.bar(edges[:-1], counts, width=np.diff(edges), align="edge", color="#2ca02c", alpha=.75)
        ax_bottom.set_xscale("log"); ax_bottom.invert_yaxis()
        ax_bottom.set_xlabel("Puissance empruntée Σq·r (J/pas)"); ax_bottom.set_ylabel(f"Emprunteuses\npures (n={int(pure_borrower.sum())})", fontsize=8)
        ax_bottom.tick_params(labelleft=False)

        power.tick_params(labelleft=False, labelbottom=False)
        note = f", {inactive} inactives" if inactive else ""
        power.set_title(f"Puissance agrégée : prêteuse vs emprunteuse\n(bi-rôles n={int(dual.sum())}/{len(entities)}{note})", fontsize=10)
    else:
        power.set_visible(False)

    fig.suptitle(f"Structure du réseau final de crédit — {title}"); fig.tight_layout(); save(fig, out / "loan_network_final.png")


def individual_history(folder: Path):
    history = defaultdict(list)
    for row in read_csv(folder / "individual_series.csv.gz"):
        history[int(row["id"])].append(row)
    for rows in history.values(): rows.sort(key=lambda row: row["t"])
    return history


def _life_block(balance, flow, rows, legend=True):
    t = np.asarray([row["t"] for row in rows]); k = np.asarray([row["K"] for row in rows]); claims = np.asarray([row["claims"] for row in rows]); debts = np.asarray([row["debts"] for row in rows]); nw = np.asarray([row["nw"] for row in rows])
    prod = np.asarray([row["prod"] for row in rows]); received = np.asarray([row["int_in"] for row in rows]); paid = np.asarray([row["int_out"] for row in rows])
    balance.stackplot(t, k, claims, labels=("Capital K", "Créances"), colors=("#4c78a8", "#f2cf5b"), alpha=.72)
    balance.fill_between(t, 0, -debts, color="#e45756", alpha=.58, label="Dettes (−)")
    balance.plot(t, nw, color="black", lw=1.25, label="Valeur nette"); balance.axhline(0, color="black", lw=.7); balance.set_ylabel("Bilan (J)")
    flow.fill_between(t, 0, prod, color="#54a24b", alpha=.65, label="Production")
    flow.fill_between(t, prod, prod + received, color="#4c78a8", alpha=.65, label="Intérêts reçus")
    flow.fill_between(t, 0, -paid, color="#e45756", alpha=.65, label="Intérêts payés"); flow.axhline(0, color="black", lw=.7); flow.set_ylabel("Flux (J/pas)"); flow.set_xlabel("Pas")
    for axis in (balance, flow): axis.set_xlim(t.min(), t.max()); axis.grid(True, alpha=.18)
    if legend: balance.legend(fontsize=6, ncol=2); flow.legend(fontsize=6, ncol=2)


def entity_lives(folder: Path, out: Path, title: str):
    history = individual_history(folder)
    eligible = [entity for entity, rows in history.items() if len(rows) >= 3]
    if not eligible: return
    births = {int(row["id"]): row["birth_t"] for row in read_csv(folder / "entities.csv")}
    early = sorted(eligible, key=lambda entity: births.get(entity, 0))[:4]
    largest = sorted(eligible, key=lambda entity: max(row["K"] for row in history[entity]), reverse=True)[:4]
    longest = sorted(eligible, key=lambda entity: len(history[entity]), reverse=True)[:4]
    selected = list(dict.fromkeys(early + largest + longest))[:10]
    fig = plt.figure(figsize=(22, 9), constrained_layout=True); grid = fig.add_gridspec(2, 5)
    for index, entity in enumerate(selected):
        inner = grid[index // 5, index % 5].subgridspec(2, 1, hspace=.05)
        balance = fig.add_subplot(inner[0]); flow = fig.add_subplot(inner[1], sharex=balance)
        _life_block(balance, flow, history[entity], legend=index == 0); balance.set_title(f"Entité {entity}", fontsize=8); balance.tick_params(labelbottom=False, labelsize=6); flow.tick_params(labelsize=6)
    fig.suptitle(f"Vies individuelles comparées — bilan fusionné et zoom — {title}"); save(fig, out / "entity_lives_overview.png")
    detail = out / "detail_vie_entites"
    if detail.exists(): shutil.rmtree(detail)
    detail.mkdir(parents=True)
    for entity in selected:
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True); _life_block(*axes, history[entity])
        axes[0].set_title(f"Entité {entity} — fenêtre exacte de sa vie observée — {title}"); fig.tight_layout(); save(fig, detail / f"entity_{entity}.png")


def _adaptive_horizon(prepared, quantile=0.999, floor=15, cap_fraction=0.4):
    """Fenêtre de vie restante calée sur l'échelle de vie réelle du run,
    jamais une constante fixe : 99,9e percentile des âges au décès observés
    après burn-in (toutes graines confondues), plafonné pour laisser assez
    de pas de recul aux landmarks (final_t - horizon doit rester net du burn-in).
    Un quantile aussi extrême exige plus de décès pour ne pas n'être qu'un
    maximum bruité — seuil minimal proportionnel à 1/(1-quantile)."""
    pooled_ages = [age for *_, ages in prepared for age in ages]
    caps = [max(floor, int(cap_fraction * max(final_t - burn, 0))) for _, _, burn, final_t, _, _ in prepared]
    cap = min(caps) if caps else 100
    min_samples = max(30, int(math.ceil(5.0 / max(1e-6, 1 - quantile))))
    if len(pooled_ages) >= min_samples:
        horizon = int(round(min(float(np.quantile(pooled_ages, quantile)), cap)))
    else:
        # Pas assez de décès pour estimer l'échelle à ce quantile : on ne
        # retombe jamais sur une constante arbitraire, on garde la fraction
        # du run disponible.
        horizon = cap
    return max(floor, horizon)


def landmark_records(members, horizon=None):
    prepared = []
    for seed, folder in members:
        cfg = config(folder); burn = int(cfg.get("T", 0)) // 4
        summary_path = folder / "summary.json"
        final_t = int(json.loads(summary_path.read_text()).get("t_final", cfg.get("T", 0))) if summary_path.exists() else int(cfg.get("T", 0))
        deaths_rows = read_csv(folder / "deaths.csv")
        deaths = {int(row["id"]): int(row["t"]) for row in deaths_rows}
        ages = [row["age"] for row in deaths_rows if row.get("age", 0) > 0 and row.get("t", 0) >= burn]
        prepared.append((seed, folder, burn, final_t, deaths, ages))

    if horizon is None:
        horizon = _adaptive_horizon(prepared)

    records = []
    for seed, folder, burn, final_t, deaths, _ in prepared:
        for step, snap in snapshots(folder).items():
            if step < burn or step > final_t - horizon: continue
            weight = 1 / max(1, len(snap["id"]))
            for index, raw_id in enumerate(snap["id"]):
                entity = int(raw_id); assets = float(snap["K"][index] + snap["claims"][index]); leverage = float(snap["debts"][index] / assets) if assets > 0 else 0
                death = deaths.get(entity); remaining = death - step if death is not None and death > step else horizon
                records.append((float(snap["K"][index]), leverage, float(np.clip(remaining, 0, horizon)), bool(death and 0 < remaining <= horizon), seed, weight))
    return records, horizon


def instantaneous_life(members, out: Path, title: str, horizon=None):
    records, horizon = landmark_records(members, horizon)
    if len(records) < 100: return
    for column, log_x, xlabel, filename in (
        (0, True, "Taille instantanée K(t) (J)", "instantaneous_life_expectancy_by_size.png"),
        (1, False, "Ratio instantané dettes/actifs", "instantaneous_life_expectancy_by_leverage.png"),
    ):
        x = np.asarray([row[column] for row in records]); y = np.asarray([row[2] for row in records]); weights = np.asarray([row[5] for row in records])
        valid = np.isfinite(x) & (x > 0 if log_x else x >= 0); x=x[valid]; y=y[valid]; weights=weights[valid]
        if len(x) < 100: continue
        # Résolution adaptative (règle sqrt(n), comme adaptive_hist) plutôt qu'un
        # nombre de classes fixe : le plancher de 20 observations/classe reste le
        # garde-fou de fiabilité, indépendant de la finesse de découpage.
        n_bins = max(8, min(50, int(round(math.sqrt(len(x))))))
        transformed = np.log10(x) if log_x else x; edges = np.unique(np.quantile(transformed, np.linspace(0, 1, n_bins + 1)))
        centres=[]; means=[]; q10=[]; q90=[]
        for index in range(len(edges)-1):
            inside=(transformed >= edges[index]) & (transformed <= edges[index+1] if index == len(edges)-2 else transformed < edges[index+1])
            if inside.sum() < 20: continue
            values=y[inside]; w=weights[inside]; order=np.argsort(values); values=values[order]; w=w[order]/w.sum(); cumulative=np.cumsum(w)
            centres.append(np.median(x[inside])); means.append(np.average(values, weights=w)); q10.append(np.interp(.1, cumulative, values)); q90.append(np.interp(.9, cumulative, values))
        if not centres: continue
        fig, (heat, mean_axis) = plt.subplots(1, 2, figsize=(14, 5.6))
        density = heat.hexbin(x, y, gridsize=60, mincnt=1, bins="log", xscale="log" if log_x else "linear", cmap="YlOrRd")
        fig.colorbar(density, ax=heat, label="Effectif (log)"); positions=np.unique(np.linspace(0, len(x)-1, min(25000, len(x)), dtype=int)); heat.scatter(x[positions], y[positions], s=.35, alpha=.06, color="#3f0000")
        heat.set(xlabel=xlabel, ylabel=f"Vie restante, tronquée à {horizon} pas", title=f"Tous les landmarks (n={len(x):,})")
        centres=np.asarray(centres); means=np.asarray(means); q10=np.asarray(q10); q90=np.asarray(q90)
        mean_axis.fill_between(centres, q10, q90, alpha=.2); mean_axis.plot(centres, means, "o-", color="black", ms=4, label="Espérance restreinte")
        if log_x: mean_axis.set_xscale("log")
        mean_axis.set(xlabel=xlabel, ylabel="Vie restante moyenne (pas)", ylim=(0, horizon*1.03), title="Moyenne conditionnelle par classes équipopulées"); mean_axis.legend(); mean_axis.grid(True, alpha=.2)
        fig.suptitle(f"Espérance de vie instantanée — fenêtre adaptative H={horizon} pas (≈99,9ᵉ percentile des âges au décès post burn-in, plafonnée par la marge de recul disponible) — {title}")
        fig.tight_layout(); save(fig, out / filename)


def lifespan(members, out: Path, title: str):
    rows=[]
    for seed, folder in members:
        dead_ids=set()
        for row in read_csv(folder / "deaths.csv"):
            dead_ids.add(int(row["id"])); assets=row["K"]+row["claims"]; rows.append((row["K"], row["debts"]/assets if assets>0 else 0, row["age"], False, seed))
        snaps=snapshots(folder)
        if not snaps: continue
        final_t=max(snaps); snap=snaps[final_t]
        births={int(row["id"]): row for row in read_csv(folder / "entities.csv")}
        for index, raw_id in enumerate(snap["id"]):
            entity=int(raw_id); data=births.get(entity)
            if not data or entity in dead_ids or not data["alive_final"]: continue
            assets=float(snap["K"][index]+snap["claims"][index]); rows.append((float(snap["K"][index]), float(snap["debts"][index]/assets) if assets>0 else 0, final_t-data["birth_t"], True, seed))
    if len(rows)<5: return
    fig, axes=plt.subplots(1,2,figsize=(13,5.5))
    for axis, (column, xlabel, logx) in zip(axes, ((0,"Taille terminale K (J)",True),(1,"Ratio dettes/actifs terminal",False))):
        values=np.asarray([(row[column],row[2]) for row in rows if row[column]>0 or not logx])
        image=axis.hexbin(values[:,0],values[:,1],gridsize=65,mincnt=1,bins="log",xscale="log" if logx else "linear",cmap="YlOrRd")
        fig.colorbar(image,ax=axis,label="Effectif (log)")
        dead=np.asarray([(row[column],row[2]) for row in rows if not row[3] and (row[column]>0 or not logx)])
        alive=np.asarray([(row[column],row[2]) for row in rows if row[3] and (row[column]>0 or not logx)])
        if len(dead): axis.scatter(dead[:25000,0],dead[:25000,1],s=.35,alpha=.06,color="#4a0000",label=f"décès {len(dead):,}")
        if len(alive): axis.scatter(alive[:25000,0],alive[:25000,1],s=.8,alpha=.15,color="#006d2c",marker="^",label=f"censurées {len(alive):,}")
        axis.set(xlabel=xlabel,ylabel="Durée de vie (pas)"); axis.legend(fontsize=7); axis.grid(True,alpha=.16)
    fig.suptitle(f"Lifespan analysis : tous les états terminaux — n={len(rows):,} — {title}"); fig.tight_layout(); save(fig,out/"lifespan_analysis.png")


def soc_figures(folder: Path, out: Path, title: str):
    avalanches=read_csv(folder/"avalanches.csv")
    if avalanches:
        size=np.asarray([row["size"] for row in avalanches]); roots=np.asarray([row["n_roots"] for row in avalanches]); depth=np.asarray([row["depth"] for row in avalanches])
        fig,axes=plt.subplots(1,2,figsize=(12,5)); a=axes[0].hexbin(size,roots/size,gridsize=45,mincnt=1,bins="log",xscale="log",cmap="viridis"); fig.colorbar(a,ax=axes[0],label="effectif (log)")
        b=axes[1].hexbin(size,depth,gridsize=45,mincnt=1,bins="log",xscale="log",cmap="magma"); fig.colorbar(b,ax=axes[1],label="effectif (log)")
        axes[0].set(xlabel="Taille",ylabel="Racines / taille",title="Part des racines"); axes[1].set(xlabel="Taille",ylabel="Profondeur",title="Profondeur causale")
        fig.suptitle(f"Structure des avalanches — {title}"); fig.tight_layout(); save(fig,out/"soc_avalanche_structure.png")
    snaps=snapshots(folder)
    if snaps:
        incomes=np.concatenate([np.asarray(snap["income"])[np.asarray(snap["income"])>0] for snap in snaps.values()])
        if len(incomes)>2:
            fig,axis=plt.subplots(figsize=(9,5.5)); _plot_adaptive(axis,incomes,"#ff7f0e",f"empirique n={len(incomes):,}"); axis.set(xscale="log",yscale="log",xlabel="Revenu brut (J/pas)",ylabel="Densité",title=f"Revenu brut empirique — aucun fit — {title}"); axis.legend(); axis.grid(True,which="both",alpha=.2); fig.tight_layout(); save(fig,out/"soc_revenue_fits.png")
    deaths=read_csv(folder/"deaths.csv")
    ages=np.asarray([row["age"] for row in deaths if row["age"]>0])
    if len(ages)>5:
        # Fit unique log-normal (retenu sur la campagne de sensibilité) : pas
        # de Weibull ni d'exponentielle, qui n'apportent rien de plus ici.
        fig,axis=plt.subplots(figsize=(9,5.5)); counts,edges,_=axis.hist(ages,bins="auto",density=True,alpha=.35,label=f"empirique n={len(ages)}")
        grid=np.linspace(max(.01,ages.min()),ages.max(),250)
        shape,loc,scale=stats.lognorm.fit(ages,floc=0)
        # R² du fit : accord densité empirique / densité log-normale, bin à bin
        # (mêmes classes que l'histogramme), pas un R² de régression linéaire.
        centres=(edges[:-1]+edges[1:])/2; fitted=stats.lognorm.pdf(centres,shape,loc,scale)
        ss_res=float(np.sum((counts-fitted)**2)); ss_tot=float(np.sum((counts-counts.mean())**2))
        r2=1-ss_res/ss_tot if ss_tot>0 else float("nan")
        axis.plot(grid,stats.lognorm.pdf(grid,shape,loc,scale),color="#d62728",lw=1.6,label=f"log-normale, μ={math.log(scale):.2f}, σ={shape:.2f}, R²={r2:.3f}")
        axis.set(xlabel="Âge au décès (pas)",ylabel="Densité",title=f"Distribution et fit log-normal d'âge au décès — {title}"); axis.legend(); axis.grid(True,alpha=.2); fig.tight_layout(); save(fig,out/"soc_age_at_death_fits.png")
    if len(snaps)>=2:
        steps=sorted(snaps); first=snaps[steps[0]]; base=set(first["id"][np.asarray(first["nw"])>=np.quantile(first["nw"],.9)].astype(int)); x=[]; persistence=[]
        for step in steps:
            snap=snaps[step]; top=set(snap["id"][np.asarray(snap["nw"])>=np.quantile(snap["nw"],.9)].astype(int)); x.append(step-steps[0]); persistence.append(len(base&top)/max(1,len(base)))
        fig,axis=plt.subplots(figsize=(9,5.5)); axis.plot(x,persistence,"o-"); axis.set(xlabel="Décalage depuis le premier snapshot",ylabel="Part du top décile initial encore présente",ylim=(0,1.03),title=f"Renouvellement du top décile — {title}"); axis.grid(True,alpha=.2); fig.tight_layout(); save(fig,out/"soc_top_decile_renewal.png")


def empirical_revenue(members, out: Path, title: str, filename="revenue_fits.png"):
    fig,axis=plt.subplots(figsize=(9.5,6)); plotted=False
    for index,(seed,folder) in enumerate(members):
        snaps=snapshots(folder)
        values=np.concatenate([np.asarray(snap["income"])[np.asarray(snap["income"])>0] for snap in snaps.values()]) if snaps else np.asarray([])
        if len(values)>2:
            _plot_adaptive(axis,values,COLORS[index%10],f"seed {seed}, n={len(values):,}"); plotted=True
    if plotted:
        axis.set(xscale="log",yscale="log",xlabel="Revenu brut (J/pas)",ylabel="Densité",title=f"Revenu brut empirique agrégé — sans fit — {title}"); axis.legend(fontsize=8); axis.grid(True,which="both",alpha=.2); fig.tight_layout(); save(fig,out/filename)
    else: plt.close(fig)


def volume_dpln(members, out: Path, title: str):
    fig,axis=plt.subplots(figsize=(10,6)); plotted=False
    for index,(seed,folder) in enumerate(members):
        _,_,volumes=avalanche_samples(folder)
        if len(volumes)<2: continue
        histogram=_plot_adaptive(axis,volumes,COLORS[index%10],f"seed {seed}, n={len(volumes)}")
        if histogram:
            fit=fit_dpln(volumes)
            if fit:
                grid=np.logspace(np.log10(volumes.min()),np.log10(volumes.max()),300); density=np.exp(dpln_logpdf(grid,**fit)); mode=grid[np.argmax(density)]; keep=grid>=mode
                axis.plot(grid[keep],density[keep],color=COLORS[index%10],lw=1.4,label=f"dPlN descendante seed {seed}, α={fit['a']+1:.2f}")
        plotted=True
    if plotted:
        axis.set(xscale="log",yscale="log",xlabel="Volume (pertes de créances, J)",ylabel="Densité",title=f"Volumes d'avalanches s≥2 — dPlN, branche descendante seule — {title}"); axis.legend(fontsize=7); axis.grid(True,which="both",alpha=.2); fig.tight_layout(); save(fig,out/"volume_dpln.png")
    else: plt.close(fig)


def generate_run(folder: Path, title: str) -> list[str]:
    folder=Path(folder); out=folder/"figures"; out.mkdir(exist_ok=True)
    for filename in OBSOLETE_OUTPUTS:
        path=out/filename
        if path.exists(): path.unlink()
    recipes=(
        lambda: macro([(config(folder).get("seed",0),folder)],out,title),
        lambda: avalanche_figures([(config(folder).get("seed",0),folder)],out,title),
        lambda: temporal_selected(folder,out,title),
        lambda: series_figures([(config(folder).get("seed",0),folder)],out,title),
        lambda: inequality_figures([(config(folder).get("seed",0),folder)],out,title),
        lambda: network_figure(folder,out,title),
        lambda: instantaneous_life([(config(folder).get("seed",0),folder)],out,title),
        lambda: entity_lives(folder,out,title),
        lambda: soc_figures(folder,out,title),
    )
    errors=[]
    for recipe in recipes:
        try: recipe()
        except Exception as exc: errors.append(f"{getattr(recipe,'__name__','figure')}: {exc}")
    return errors


def generate_batch(members, out: Path, title: str) -> list[str]:
    out.mkdir(parents=True,exist_ok=True); errors=[]
    recipes=(
        lambda: avalanche_figures(members,out,title,volume_ccdf_output=False),
        lambda: volume_dpln(members,out,title),
        lambda: empirical_revenue(members,out,title),
        lambda: lifespan(members,out,title),
        lambda: instantaneous_life(members,out,title),
    )
    for recipe in recipes:
        try: recipe()
        except Exception as exc: errors.append(str(exc))
    return errors


def generate_synthesis(lots, out: Path, title: str) -> bool:
    """Y03 : invariants par run, puis position du lot selon sa taille."""
    points=[]
    for lot_label,members in lots:
        for seed,folder in members:
            rows=read_csv(folder/"series.csv"); avalanches=read_csv(folder/"avalanches.csv")
            if not rows or not avalanches: continue
            burn=int(config(folder).get("T",0))//4
            late_rows=[row for row in rows if row["t"]>=burn]; late=[row for row in avalanches if row["t"]>=burn]
            if not late_rows or not late: continue
            mean_population=float(np.mean([row["pop"] for row in late_rows])); total_size=sum(row["size"] for row in late); total_roots=sum(row["n_roots"] for row in late)
            branching=1-total_roots/total_size if total_size else 0; depth=float(np.mean([row["depth"] for row in late])); rate=len(late)/max(1,len(late_rows))
            points.append((mean_population,branching,depth,rate,lot_label,seed))
    if len({point[4] for point in points})<2: return False
    out.mkdir(parents=True,exist_ok=True); fig,axes=plt.subplots(1,3,figsize=(16,5.2))
    lot_names=list(dict.fromkeys(point[4] for point in points))
    for index,lot in enumerate(lot_names):
        subset=[point for point in points if point[4]==lot]; x=[p[0] for p in subset]; color=COLORS[index%10]
        for axis,column,label in zip(axes,(1,2,3),("Rapport de branchement","Profondeur moyenne","Avalanches / pas")):
            axis.scatter(x,[p[column] for p in subset],s=28,alpha=.75,color=color,label=lot if column==1 else None); axis.set(xscale="log",xlabel="Population moyenne post burn-in",ylabel=label); axis.grid(True,which="both",alpha=.2)
    axes[0].legend(fontsize=7); fig.suptitle(f"Invariants SOC selon la taille du système — {title}"); fig.tight_layout(); save(fig,out/"invariants_soc.png"); return True
