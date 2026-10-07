"""Figures individuelles M4 corrigées pour Simulation Lab.

Ce module ne touche pas au moteur. Il travaille uniquement à partir des
artefacts enregistrés par un run M4.
"""
from __future__ import annotations

import csv
import math
import shutil
from pathlib import Path

import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter


REVENUE_SERIES = (
    ("prod", "Production Π", "revenue_distribution_prod.png", "#2ca02c"),
    ("int_in", "Intérêts reçus", "revenue_distribution_int_in.png", "#1f77b4"),
    ("int_out", "Intérêts payés", "revenue_distribution_int_out.png", "#d62728"),
    ("income", "Revenu total brut", "revenue_distribution_income.png", "#ff7f0e"),
    (
        "income_net",
        "Revenu net (part positive)",
        "revenue_distribution_income_net.png",
        "#9467bd",
    ),
)
_DPLN_CACHE = {}


def _save(fig, path: Path, plt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_revenue_empirical(report, members, out_dir: Path, extra: str) -> None:
    """Distribution SOC des revenus sans courbe ni statistique de fit."""
    plt = report.plt
    fig, (ax_density, ax_ccdf) = plt.subplots(1, 2, figsize=(13.5, 5.6))
    plotted = 0
    periods = []
    for index, (seed, folder, _) in enumerate(members):
        snapshots = report.load_snapshots(folder)
        if not snapshots:
            continue
        values, used = report._late_pool(snapshots, "income")
        histogram = report._log_bins_density(values, n_bins=28)
        if histogram is None:
            continue
        centres, density, _ = histogram
        color = report.SEED_COLORS[index % len(report.SEED_COLORS)]
        label = f"seed {seed} (n={len(values)})"
        ax_density.loglog(
            centres,
            density,
            marker="o",
            ms=3.5,
            ls="none",
            alpha=0.65,
            color=color,
            label=label,
        )

        ordered = np.sort(values)
        survival = (len(ordered) - np.arange(len(ordered))) / len(ordered)
        # Un sous-échantillonnage d'affichage conserve les quantiles et évite
        # de surcharger inutilement les PNG des longues simulations.
        if len(ordered) > 4000:
            positions = np.unique(
                np.linspace(0, len(ordered) - 1, 4000, dtype=int)
            )
            ordered = ordered[positions]
            survival = survival[positions]
        ax_ccdf.loglog(
            ordered,
            survival,
            marker=".",
            ms=2.0,
            ls="none",
            alpha=0.5,
            color=color,
            label=label,
        )
        periods.append(f"{used[0]}–{used[-1]}")
        plotted += 1

    if not plotted:
        plt.close(fig)
        return
    ax_density.set_title("Densité empirique (bins logarithmiques)")
    ax_density.set_xlabel("Revenu brut Π + intérêts reçus (J/pas)")
    ax_density.set_ylabel("Densité")
    ax_ccdf.set_title("CCDF empirique")
    ax_ccdf.set_xlabel("Revenu brut Π + intérêts reçus (J/pas)")
    ax_ccdf.set_ylabel("P(Revenu ≥ x)")
    for axis in (ax_density, ax_ccdf):
        axis.legend(fontsize=7.5)
        axis.grid(True, which="both", alpha=0.22)
    period_text = ", ".join(dict.fromkeys(periods))
    fig.suptitle(
        f"Distribution empirique du revenu brut — instantanés {period_text} "
        f"— {extra}",
        fontsize=11,
    )
    fig.tight_layout()
    report._save(fig, Path(out_dir), "revenue_fits.png")


def _cutoff_powerlaw(report, sizes):
    fit = report._size_fits(sizes)
    if not fit or "alpha_c" not in fit or "x_c" not in fit:
        return None
    s_min = int(fit["s_min"])
    maximum = int(sizes.max())
    support = np.arange(s_min, max(1000, 100 * maximum) + 1, dtype=float)
    log_weights = -fit["alpha_c"] * np.log(support) - support / fit["x_c"]
    weights = np.exp(log_weights - log_weights.max())
    return {
        "alpha": float(fit["alpha_c"]),
        "cutoff": float(fit["x_c"]),
        "s_min": s_min,
        "support": support,
        "pmf": weights / weights.sum(),
    }


def _wilson_density_interval(counts, total, widths):
    """Intervalle de Wilson à 68,27 % pour une densité histogramme."""
    probabilities = np.asarray(counts, dtype=float) / total
    z = 1.0
    denominator = 1.0 + z * z / total
    midpoint = (probabilities + z * z / (2.0 * total)) / denominator
    radius = (
        z
        * np.sqrt(
            probabilities * (1.0 - probabilities) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    lower = np.maximum(0.0, midpoint - radius) / widths
    upper = np.minimum(1.0, midpoint + radius) / widths
    density = probabilities / widths
    lower = np.minimum(lower, density)
    upper = np.maximum(upper, density)
    return lower, upper


def _integer_groups(frequencies, target):
    """Indices de groupes adjacents contenant environ ``target`` points."""
    groups = []
    start = 0
    accumulated = 0
    for index, frequency in enumerate(frequencies):
        accumulated += int(frequency)
        remaining = int(frequencies[index + 1 :].sum())
        if index < len(frequencies) - 1 and accumulated >= target:
            if remaining and remaining < max(5, target // 2):
                continue
            groups.append((start, index + 1))
            start = index + 1
            accumulated = 0
    groups.append((start, len(frequencies)))
    return groups


def _adaptive_integer_histogram(
    values, max_bins=40, min_per_bin=5, edges=None
):
    """Densité discrète avec davantage de résolution dans les zones denses.

    Les tailles égales ne sont jamais séparées. Les valeurs consécutives sont
    regroupées jusqu'à atteindre un effectif cible ; une taille très fréquente
    conserve donc son propre bin, tandis que la queue rare utilise des bins
    plus larges. Les intervalles verticaux sont des intervalles de Wilson à
    68 % sur la probabilité de chaque bin, ramenés à une densité.
    """
    sample = np.asarray(values, dtype=np.int64)
    sample = sample[sample > 0]
    if not len(sample):
        return None

    n = len(sample)
    if edges is None:
        support, frequencies = np.unique(sample, return_counts=True)
        n = int(frequencies.sum())
        target = max(
            int(min_per_bin),
            min(20, int(math.floor(math.sqrt(n) / 2.0))),
        )
        groups = _integer_groups(frequencies, target)
        if len(groups) > max_bins:
            target = max(target, int(math.ceil(n / max_bins)))
            groups = _integer_groups(frequencies, target)

        computed_edges = [max(0.5, float(support[0]) - 0.5)]
        for _, stop in groups[:-1]:
            computed_edges.append(
                float(support[stop - 1] + support[stop]) / 2.0
            )
        computed_edges.append(float(support[-1]) + 0.5)
        edges = np.asarray(computed_edges, dtype=float)
    else:
        edges = np.asarray(edges, dtype=float)
        target = int(round(n / max(1, len(edges) - 1)))

    counts, _ = np.histogram(sample, bins=edges)
    widths = np.diff(edges)
    centres = np.sqrt(edges[:-1] * edges[1:])
    density = counts / (n * widths)
    lower, upper = _wilson_density_interval(counts, n, widths)
    return {
        "edges": edges,
        "centres": centres,
        "counts": counts,
        "density": density,
        "density_lower": lower,
        "density_upper": upper,
        "target_count": target,
    }


def _adaptive_continuous_histogram(
    values, max_bins=40, min_per_bin=20, edges=None
):
    """Densité continue sur bins quantiles équipopulés."""
    sample = np.sort(np.asarray(values, dtype=float))
    sample = sample[np.isfinite(sample) & (sample > 0)]
    n = len(sample)
    if n < max(3, min_per_bin) or sample[0] == sample[-1]:
        return None
    if edges is None:
        n_bins = min(max_bins, max(3, n // min_per_bin))
        edges = np.unique(
            np.quantile(sample, np.linspace(0.0, 1.0, n_bins + 1))
        )
    else:
        edges = np.asarray(edges, dtype=float)
    if len(edges) < 3:
        return None
    counts, _ = np.histogram(sample, bins=edges)
    widths = np.diff(edges)
    centres = np.sqrt(edges[:-1] * edges[1:])
    density = counts / (n * widths)
    lower, upper = _wilson_density_interval(counts, n, widths)
    return {
        "edges": edges,
        "centres": centres,
        "counts": counts,
        "density": density,
        "density_lower": lower,
        "density_upper": upper,
        "target_count": int(round(n / len(counts))),
    }


def _model_density_on_integer_bins(edges, support, pmf, tail_fraction):
    """Moyenne d'une pmf discrète sur les mêmes bins que l'histogramme."""
    centres = np.sqrt(edges[:-1] * edges[1:])
    density = []
    for lower, upper in zip(edges[:-1], edges[1:]):
        inside = (support >= lower) & (support < upper)
        density.append(
            tail_fraction * float(pmf[inside].sum()) / (upper - lower)
        )
    return centres, np.asarray(density, dtype=float)


def _dpln_volume_fit(report, volumes, sub_max=50_000, edges=None):
    """Ajustement dPlN unique du volume, sans régressions de branches."""
    cache_key = (
        len(volumes),
        float(np.sum(volumes)),
        float(np.min(volumes)) if len(volumes) else 0.0,
        float(np.max(volumes)) if len(volumes) else 0.0,
        tuple(np.asarray(edges, dtype=float)) if edges is not None else None,
    )
    if cache_key in _DPLN_CACHE:
        return _DPLN_CACHE[cache_key]
    histogram = _adaptive_continuous_histogram(volumes, edges=edges)
    if histogram is None:
        return None
    centres = histogram["centres"]
    density = histogram["density"]
    counts = histogram["counts"]
    rng = np.random.default_rng(0)
    sample = (
        rng.choice(volumes, sub_max, replace=False)
        if len(volumes) > sub_max
        else volumes
    )
    fit = report.fit_dpln(sample)
    if not fit:
        return None
    params = fit["params"]
    log_density = report.dpln_logpdf(
        centres,
        params["nu"],
        params["tau"],
        params["a"],
        params["b"],
    )
    result = {
        "centres": centres,
        "density": density,
        "counts": counts,
        "edges": histogram["edges"],
        "density_lower": histogram["density_lower"],
        "density_upper": histogram["density_upper"],
        "target_count": histogram["target_count"],
        "params": params,
        "r2": report._r2_logdens(
            centres,
            density,
            log_density / math.log(10),
            weights=counts,
        ),
    }
    _DPLN_CACHE[cache_key] = result
    return result


def fig_cascades(report, members, out_dir: Path, extra: str) -> None:
    """Tailles tronquées et volumes ajustés uniquement par une dPlN."""
    plt = report.plt
    fig, axes = plt.subplots(1, 3, figsize=(22, 5.8))
    ax_density, ax_ccdf, ax_volume = axes
    size_fits = []
    volume_fits = []
    ccdf_min = 1.0

    prepared = []
    for member in members:
        seed, folder, _ = member
        t_min = report._run_T(folder) // 4
        sizes = np.asarray(
            [
                avalanche["size"]
                for avalanche in report.load_avalanches(folder)
                if avalanche["t"] >= t_min
            ],
            dtype=np.int64,
        )
        volumes = np.asarray(
            [
                volume
                for step, volume in report._volumes_cached(folder)
                if step >= t_min and volume > 0
            ],
            dtype=float,
        )
        prepared.append((member, sizes, volumes))

    size_samples = [sizes for _, sizes, _ in prepared if len(sizes)]
    volume_samples = [volumes for _, _, volumes in prepared if len(volumes)]
    shared_size_edges = None
    shared_volume_edges = None
    if len(size_samples) > 1:
        pooled = _adaptive_integer_histogram(np.concatenate(size_samples))
        shared_size_edges = pooled["edges"] if pooled else None
    if len(volume_samples) > 1:
        pooled = _adaptive_continuous_histogram(
            np.concatenate(volume_samples)
        )
        shared_volume_edges = pooled["edges"] if pooled else None

    for index, (member, sizes, volumes) in enumerate(prepared):
        seed, folder, _ = member
        color = report.SEED_COLORS[index % len(report.SEED_COLORS)]
        if len(sizes) >= 100:
            maximum = int(sizes.max())
            histogram = _adaptive_integer_histogram(
                sizes, edges=shared_size_edges
            )
            edges = histogram["edges"]
            counts = histogram["counts"]
            centres = histogram["centres"]
            density = histogram["density"]
            keep = counts > 0
            y_error = np.vstack(
                (
                    density - histogram["density_lower"],
                    histogram["density_upper"] - density,
                )
            )
            x_error = np.vstack(
                (centres - edges[:-1], edges[1:] - centres)
            )
            ax_density.errorbar(
                centres[keep],
                density[keep],
                xerr=x_error[:, keep],
                yerr=y_error[:, keep],
                fmt="o",
                ms=3.4,
                capsize=2.2,
                elinewidth=0.75,
                alpha=0.72,
                color=color,
                ecolor=color,
                label=(
                    f"seed {seed} (n={len(sizes)}, "
                    f"≈{histogram['target_count']} obs./bin)"
                ),
            )
            ordered = np.sort(sizes.astype(float))
            empirical_ccdf = 1.0 - np.arange(1, len(sizes) + 1) / (
                len(sizes) + 1.0
            )
            ccdf_min = min(ccdf_min, empirical_ccdf[-1])
            ax_ccdf.loglog(
                ordered, empirical_ccdf, ".", ms=2.5, alpha=0.55, color=color
            )

            fit = _cutoff_powerlaw(report, sizes)
            if fit:
                tail_fraction = float(np.mean(sizes >= fit["s_min"]))
                model_x, model_y = _model_density_on_integer_bins(
                    edges,
                    fit["support"],
                    fit["pmf"],
                    tail_fraction,
                )
                model_keep = model_y > 0
                ax_density.loglog(
                    model_x[model_keep],
                    model_y[model_keep],
                    "--",
                    lw=1.3,
                    color=color,
                    alpha=0.9,
                )
                grid = np.unique(ordered[ordered >= fit["s_min"]]).astype(int)
                survival = np.append(np.cumsum(fit["pmf"][::-1])[::-1], 0.0)
                after_grid = np.clip(
                    grid - fit["s_min"] + 1, 0, len(fit["pmf"])
                )
                ax_ccdf.loglog(
                    grid,
                    tail_fraction * survival[after_grid],
                    "--",
                    lw=1.3,
                    color=color,
                    alpha=0.9,
                )
                size_fits.append((fit["alpha"], fit["cutoff"], maximum))

        volume_fit = _dpln_volume_fit(
            report, volumes, edges=shared_volume_edges
        )
        if volume_fit:
            volume_keep = volume_fit["counts"] > 0
            volume_x_error = np.vstack(
                (
                    volume_fit["centres"] - volume_fit["edges"][:-1],
                    volume_fit["edges"][1:] - volume_fit["centres"],
                )
            )
            volume_y_error = np.vstack(
                (
                    volume_fit["density"] - volume_fit["density_lower"],
                    volume_fit["density_upper"] - volume_fit["density"],
                )
            )
            ax_volume.errorbar(
                volume_fit["centres"][volume_keep],
                volume_fit["density"][volume_keep],
                xerr=volume_x_error[:, volume_keep],
                yerr=volume_y_error[:, volume_keep],
                fmt="o",
                ms=3.0,
                capsize=2.0,
                elinewidth=0.7,
                alpha=0.62,
                color=color,
                ecolor=color,
                label=(
                    f"seed {seed} (n={len(volumes)}, "
                    f"≈{volume_fit['target_count']} obs./bin)"
                ),
            )
            grid = np.logspace(
                math.log10(volume_fit["centres"][0]),
                math.log10(volume_fit["centres"][-1]),
                240,
            )
            params = volume_fit["params"]
            model_density = np.exp(
                report.dpln_logpdf(
                    grid,
                    params["nu"],
                    params["tau"],
                    params["a"],
                    params["b"],
                )
            )
            ax_volume.loglog(grid, model_density, "-", lw=1.35, color=color)
            volume_fits.append(volume_fit)

    if size_fits:
        alphas = np.asarray([item[0] for item in size_fits])
        cutoffs = [
            cutoff
            for _, cutoff, maximum in size_fits
            if cutoff <= 50 * maximum
        ]
        cutoff_text = (
            f"s_c={np.mean(cutoffs):.0f}±{np.std(cutoffs):.0f}"
            if len(cutoffs) == len(size_fits)
            else "s_c au-delà de la gamme pour certains seeds"
        )
        ax_density.plot(
            [],
            [],
            "k--",
            lw=1.4,
            label=(
                "p(s) ∝ s⁻ᵅ exp(−s/s_c)\n"
                f"α={alphas.mean():.2f}±{alphas.std():.2f} ; {cutoff_text}"
            ),
        )
    if volume_fits:
        a_values = np.asarray([fit["params"]["a"] for fit in volume_fits])
        b_values = np.asarray([fit["params"]["b"] for fit in volume_fits])
        nu_values = np.asarray([fit["params"]["nu"] for fit in volume_fits])
        tau_values = np.asarray([fit["params"]["tau"] for fit in volume_fits])
        r2_values = np.asarray([fit["r2"] for fit in volume_fits])
        ax_volume.plot(
            [],
            [],
            "k-",
            lw=1.4,
            label=(
                "dPlN ajustée par MLE uniquement :\n"
                f"a={a_values.mean():.2f}±{a_values.std():.2f} ; "
                f"b={b_values.mean():.2f}±{b_values.std():.2f} ; "
                f"ν={nu_values.mean():.2f} ; τ={tau_values.mean():.2f} ; "
                f"r²={r2_values.mean():.2f}"
            ),
        )

    ax_density.set_title(
        "Taille : bins adaptatifs, IC Wilson 68 % et loi tronquée",
        fontsize=10,
    )
    ax_density.set_xlabel("Taille s (entités)")
    ax_density.set_ylabel("Densité")
    ax_density.legend(fontsize=7, loc="lower left")
    ax_ccdf.set_title("Taille : fonction de survie", fontsize=10)
    ax_ccdf.set_xlabel("Taille s (entités)")
    ax_ccdf.set_ylabel("P(S > s)")
    if ccdf_min < 1:
        ax_ccdf.set_ylim(bottom=ccdf_min * 0.3)
    ax_volume.set_title(
        "Volume : bins adaptatifs, IC Wilson 68 % et dPlN",
        fontsize=10,
    )
    ax_volume.set_xlabel("Volume v (Σ pertes de créances, J)")
    ax_volume.set_ylabel("Densité")
    ax_volume.legend(fontsize=7, loc="lower left")
    for axis in axes:
        axis.grid(True, which="both", alpha=0.25)
    fig.suptitle(f"Cascades rank-size — burn-in T/4 — {extra}", fontsize=11)
    fig.tight_layout()
    _save(fig, Path(out_dir) / "cascades_rank_size.png", plt)


def fig_volume_dpln(report, members, out_dir: Path, extra: str) -> None:
    """Figure dédiée du volume : histogramme empirique et seule dPlN."""
    plt = report.plt
    fig, axis = plt.subplots(figsize=(10.5, 6.5))
    fits = []
    prepared = []
    for member in members:
        seed, folder, _ = member
        t_min = report._run_T(folder) // 4
        volumes = np.asarray(
            [
                volume
                for step, volume in report._volumes_cached(folder)
                if step >= t_min and volume > 0
            ],
            dtype=float,
        )
        prepared.append((member, volumes))
    samples = [volumes for _, volumes in prepared if len(volumes)]
    shared_edges = None
    if len(samples) > 1:
        pooled = _adaptive_continuous_histogram(np.concatenate(samples))
        shared_edges = pooled["edges"] if pooled else None

    for index, (member, volumes) in enumerate(prepared):
        seed, _, _ = member
        fit = _dpln_volume_fit(report, volumes, edges=shared_edges)
        if not fit:
            continue
        color = report.SEED_COLORS[index % len(report.SEED_COLORS)]
        keep = fit["counts"] > 0
        x_error = np.vstack(
            (
                fit["centres"] - fit["edges"][:-1],
                fit["edges"][1:] - fit["centres"],
            )
        )
        y_error = np.vstack(
            (
                fit["density"] - fit["density_lower"],
                fit["density_upper"] - fit["density"],
            )
        )
        axis.errorbar(
            fit["centres"][keep],
            fit["density"][keep],
            xerr=x_error[:, keep],
            yerr=y_error[:, keep],
            fmt="o",
            ms=3.2,
            capsize=2.0,
            elinewidth=0.7,
            alpha=0.62,
            color=color,
            ecolor=color,
            label=(
                f"seed {seed} (n={len(volumes)}, "
                f"≈{fit['target_count']} obs./bin)"
            ),
        )
        grid = np.logspace(
            math.log10(fit["centres"][0]),
            math.log10(fit["centres"][-1]),
            260,
        )
        params = fit["params"]
        axis.loglog(
            grid,
            np.exp(
                report.dpln_logpdf(
                    grid,
                    params["nu"],
                    params["tau"],
                    params["a"],
                    params["b"],
                )
            ),
            "-",
            lw=1.35,
            color=color,
        )
        fits.append(fit)
    if not fits:
        plt.close(fig)
        return
    a_values = np.asarray([fit["params"]["a"] for fit in fits])
    b_values = np.asarray([fit["params"]["b"] for fit in fits])
    r2_values = np.asarray([fit["r2"] for fit in fits])
    axis.plot(
        [],
        [],
        "k-",
        lw=1.4,
        label=(
            "dPlN (MLE), sans régression de branches : "
            f"a={a_values.mean():.2f}±{a_values.std():.2f} ; "
            f"b={b_values.mean():.2f}±{b_values.std():.2f} ; "
            f"r²={r2_values.mean():.2f}"
        ),
    )
    axis.set_xlabel("Volume de l'avalanche (Σ pertes de créances, J)")
    axis.set_ylabel("Densité (bins log)")
    axis.set_title(
        "Volume des avalanches : bins adaptatifs, IC Wilson 68 % et dPlN "
        f"— {extra}"
    )
    axis.legend(fontsize=8, loc="lower left")
    axis.grid(True, which="both", alpha=0.25)
    old_path = Path(out_dir) / "volume_double_pareto.png"
    if old_path.exists():
        old_path.unlink()
    _save(fig, Path(out_dir) / "volume_dpln.png", plt)


def fig_volume_ccdf(report, members, out_dir: Path, extra: str) -> None:
    """CCDF empirique des volumes d'avalanches en joules, sans fit."""
    plt = report.plt
    fig, axis = plt.subplots(figsize=(10.5, 6.5))
    plotted = False
    for index, (seed, folder, _) in enumerate(members):
        t_min = report._run_T(folder) // 4
        volumes = np.asarray(
            [
                volume
                for step, volume in report._volumes_cached(folder)
                if step >= t_min and volume > 0
            ],
            dtype=float,
        )
        if len(volumes) < 2:
            continue
        ordered = np.sort(volumes)
        survival = (len(ordered) - np.arange(len(ordered))) / len(ordered)
        if len(ordered) > 5000:
            # Davantage de résolution dans la queue rare de la CCDF.
            reverse_ranks = np.unique(
                np.ceil(
                    np.logspace(0, math.log10(len(ordered)), 5000)
                ).astype(int)
            )
            positions = np.sort(len(ordered) - reverse_ranks)
            ordered = ordered[positions]
            survival = survival[positions]
        color = report.SEED_COLORS[index % len(report.SEED_COLORS)]
        axis.loglog(
            ordered,
            survival,
            ".",
            ms=2.0,
            alpha=0.55,
            color=color,
            label=f"seed {seed} (n={len(volumes)})",
        )
        plotted = True
    if not plotted:
        plt.close(fig)
        return
    axis.set_xlabel("Volume de l'avalanche (Σ pertes de créances, J)")
    axis.set_ylabel("P(V ≥ v)")
    axis.set_title(
        f"CCDF empirique des volumes d'avalanches — burn-in T/4 — {extra}"
    )
    axis.legend(fontsize=8)
    axis.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    _save(fig, Path(out_dir) / "volume_ccdf.png", plt)


def fig_revenues_split(report, members, out_dir: Path, extra: str) -> list[str]:
    """Un fichier par flux, avec les mêmes vues complète et zoomée."""
    plt = report.plt
    generated = []
    snapshots = [
        (seed, report.load_snapshots(folder)) for seed, folder, _ in members
    ]
    snapshots = [(seed, snaps) for seed, snaps in snapshots if snaps]
    if not snapshots:
        return generated
    all_steps = sorted(set().union(*(set(snaps) for _, snaps in snapshots)))
    selected = report._select_steps(all_steps, all_steps[-1], n_max=4)[-4:]

    for key, label, filename, color in REVENUE_SERIES:
        fig, axes = plt.subplots(
            len(selected), 2, figsize=(14, 3.6 * len(selected)), squeeze=False
        )
        plotted = False
        for row, step in enumerate(selected):
            ax_full, ax_zoom = axes[row]
            points = []
            positive_values = []
            for seed_index, (seed, snaps) in enumerate(snapshots):
                if step not in snaps:
                    continue
                values = snaps[step][key]
                values = values[values > 0]
                result = report._adaptive_log_hist(values)
                if result is None:
                    continue
                centres, density, counts = result
                plotted = True
                positive_values.extend(values.tolist())
                points.extend(zip(centres, density))
                line_color = (
                    color
                    if len(snapshots) == 1
                    else report.SEED_COLORS[seed_index % len(report.SEED_COLORS)]
                )
                for axis in (ax_full, ax_zoom):
                    axis.plot(
                        centres,
                        density,
                        "o-",
                        ms=2.8,
                        lw=0.9,
                        alpha=0.8,
                        color=line_color,
                        label=f"seed {seed} (méd. {int(np.median(counts))}/bin)",
                    )
            zoom = None
            if positive_values:
                logged = np.log10(positive_values)
                zoom = (10 ** np.percentile(logged, 10), 10 ** logged.max())
            for axis, is_zoom in ((ax_full, False), (ax_zoom, True)):
                axis.set_xscale("log")
                axis.set_yscale("log")
                axis.set_xlabel("Flux positif (J/pas)")
                axis.set_ylabel("Densité")
                axis.grid(True, which="both", alpha=0.2)
                axis.legend(fontsize=7)
                axis.set_title(
                    f"Pas {step} — {'zoom P10–P100' if is_zoom else 'vue complète'}",
                    fontsize=9,
                )
                if is_zoom and zoom and zoom[1] > zoom[0]:
                    axis.set_xlim(*zoom)
                    visible = [y for x, y in points if zoom[0] <= x <= zoom[1]]
                    if visible:
                        axis.set_ylim(min(visible) / 3, max(visible) * 3)
        if plotted:
            fig.suptitle(f"{label} — distributions par pas — {extra}", fontsize=11)
            fig.tight_layout()
            _save(fig, Path(out_dir) / filename, plt)
            generated.append(filename)
        else:
            plt.close(fig)
    return generated


def _temporal_log_densities(snapshots, key, n_bins=32):
    """Densités par instantané sur un support fixe, donc moyennables."""
    steps = sorted(snapshots)
    values_by_step = []
    for step in steps:
        values = np.asarray(snapshots[step][key], dtype=float)
        values_by_step.append(values[np.isfinite(values) & (values > 0)])
    non_empty = [values for values in values_by_step if len(values)]
    if not non_empty:
        return None
    pooled = np.concatenate(non_empty)
    if len(pooled) < 50 or pooled.min() == pooled.max():
        return None
    edges = np.logspace(
        math.log10(float(pooled.min())),
        math.log10(float(pooled.max()) * 1.0001),
        n_bins + 1,
    )
    widths = np.diff(edges)
    centres = np.sqrt(edges[:-1] * edges[1:])
    densities = []
    counts = []
    for values in values_by_step:
        if len(values):
            histogram, _ = np.histogram(values, bins=edges)
            density = histogram / (len(values) * widths)
        else:
            density = np.zeros(n_bins, dtype=float)
        densities.append(density)
        counts.append(len(values))
    return (
        np.asarray(steps, dtype=int),
        centres,
        np.asarray(densities, dtype=float),
        np.asarray(counts, dtype=int),
    )


def _snapshot_time_weights(steps):
    """Poids trapézoïdaux : chaque snapshot représente une durée en pas."""
    steps = np.asarray(steps, dtype=float)
    if len(steps) <= 1:
        return np.ones(len(steps), dtype=float)
    weights = np.empty(len(steps), dtype=float)
    weights[0] = (steps[1] - steps[0]) / 2.0
    weights[-1] = (steps[-1] - steps[-2]) / 2.0
    if len(steps) > 2:
        weights[1:-1] = (steps[2:] - steps[:-2]) / 2.0
    return weights / weights.sum()


def _weighted_quantile_by_time(values, weights, quantile):
    """Quantile pondéré d'une série temporelle discrètement observée."""
    order = np.argsort(values)
    ordered = np.asarray(values, dtype=float)[order]
    cumulative = np.cumsum(np.asarray(weights, dtype=float)[order])
    return float(np.interp(quantile, cumulative, ordered))


def _save_temporal_distribution(
    report,
    prepared,
    out_dir: Path,
    *,
    label: str,
    color: str,
    xlabel: str,
    extra: str,
    mean_name: str,
    animation_name: str,
    max_frames: int,
) -> list[str]:
    """Écrit la moyenne temporelle et l'animation d'une distribution."""
    plt = report.plt
    steps, centres, densities, counts = prepared
    time_weights = _snapshot_time_weights(steps)
    mean_density = np.average(densities, axis=0, weights=time_weights)
    q10 = np.asarray(
        [
            _weighted_quantile_by_time(densities[:, column], time_weights, 0.1)
            for column in range(densities.shape[1])
        ]
    )
    q90 = np.asarray(
        [
            _weighted_quantile_by_time(densities[:, column], time_weights, 0.9)
            for column in range(densities.shape[1])
        ]
    )
    positive = densities[densities > 0]
    if not len(positive):
        return []
    y_min = max(float(positive.min()) / 2.0, 1e-12)
    y_max = float(max(positive.max(), mean_density.max())) * 2.0

    fig, axis = plt.subplots(figsize=(9.5, 5.8))
    valid_band = q90 > 0
    axis.fill_between(
        centres[valid_band],
        np.maximum(q10[valid_band], y_min),
        q90[valid_band],
        color=color,
        alpha=0.2,
        label="enveloppe temporelle D1–D9",
    )
    valid_mean = mean_density > 0
    axis.plot(
        centres[valid_mean],
        mean_density[valid_mean],
        "o-",
        ms=3.2,
        lw=1.5,
        color="black",
        label=(
            f"moyenne temporelle pondérée — {len(steps)} snapshots, "
            f"Δt={steps[-1] - steps[0]} pas"
        ),
    )
    axis.set(xscale="log", yscale="log", ylim=(y_min, y_max))
    axis.set_xlabel(xlabel)
    axis.set_ylabel("Densité")
    axis.set_title(f"{label} — distribution moyenne dans le temps — {extra}")
    axis.grid(True, which="both", alpha=0.22)
    axis.legend(fontsize=8)
    fig.tight_layout()
    _save(fig, Path(out_dir) / mean_name, plt)

    frame_count = min(max_frames, len(steps))
    frame_indices = np.unique(
        np.linspace(0, len(steps) - 1, frame_count, dtype=int)
    )
    fig, axis = plt.subplots(figsize=(9.5, 5.8))
    current_line, = axis.plot(
        [],
        [],
        "o-",
        ms=3.0,
        lw=1.0,
        color=color,
        alpha=0.85,
        label="distribution à l'instant t",
    )
    axis.plot(
        centres[valid_mean],
        mean_density[valid_mean],
        "-",
        lw=2.0,
        color="black",
        alpha=0.9,
        label="moyenne temporelle",
    )
    axis.set(
        xscale="log",
        yscale="log",
        xlim=(centres[0] / 1.15, centres[-1] * 1.15),
        ylim=(y_min, y_max),
    )
    axis.set_xlabel(xlabel)
    axis.set_ylabel("Densité")
    axis.grid(True, which="both", alpha=0.22)
    axis.legend(fontsize=8)

    def update(frame_position):
        step_index = int(frame_indices[frame_position])
        density = densities[step_index]
        valid = density > 0
        current_line.set_data(centres[valid], density[valid])
        axis.set_title(
            f"{label} — pas {steps[step_index]} — "
            f"n={counts[step_index]} — {extra}"
        )
        return (current_line,)

    animation = FuncAnimation(
        fig,
        update,
        frames=len(frame_indices),
        interval=170,
        blit=False,
        repeat=True,
    )
    animation.save(
        Path(out_dir) / animation_name,
        writer=PillowWriter(fps=6),
        dpi=90,
    )
    plt.close(fig)
    return [mean_name, animation_name]


def fig_revenues_animations(
    report,
    folder: Path,
    out_dir: Path,
    extra: str,
    max_frames: int = 48,
) -> list[str]:
    """Animations temporelles et moyennes des cinq distributions de flux."""
    snapshots = report.load_snapshots(folder)
    if not snapshots:
        return []
    generated = []
    for key, label, filename, color in REVENUE_SERIES:
        prepared = _temporal_log_densities(snapshots, key)
        if prepared is None:
            continue
        mean_name = filename.replace(".png", "_temporal_mean.png")
        animation_name = filename.replace(".png", "_evolution.gif")
        generated.extend(
            _save_temporal_distribution(
                report,
                prepared,
                out_dir,
                label=label,
                color=color,
                xlabel="Flux positif (J/pas)",
                extra=extra,
                mean_name=mean_name,
                animation_name=animation_name,
                max_frames=max_frames,
            )
        )
    return generated


def fig_entity_size_animation(
    report,
    folder: Path,
    out_dir: Path,
    extra: str,
    max_frames: int = 48,
) -> list[str]:
    """Animation et moyenne temporelle de la distribution du capital K."""
    snapshots = report.load_snapshots(folder)
    if not snapshots:
        return []
    prepared = _temporal_log_densities(snapshots, "K")
    if prepared is None:
        return []
    return _save_temporal_distribution(
        report,
        prepared,
        out_dir,
        label="Capital productif K",
        color="#1f77b4",
        xlabel="Capital K (J)",
        extra=extra,
        mean_name="entity_size_histo_temporal_mean.png",
        animation_name="entity_size_histo_evolution.gif",
        max_frames=max_frames,
    )


def _lifespan_records(report, members):
    """États terminaux exhaustifs : décès et survivantes censurées."""
    records = []
    for seed, folder, _ in members:
        births = {row["id"]: row for row in report.load_births(folder)}
        dead_ids = set()
        for row in report.load_death_registry(folder):
            entity_id = row["id"]
            dead_ids.add(entity_id)
            birth = births.get(entity_id, {}).get("birth")
            lifespan = row.get("age")
            if lifespan is None and birth is not None:
                lifespan = row["t"] - birth
            if lifespan is None or lifespan < 0:
                continue
            capital = float(row["K"])
            assets = capital + float(row["claims"])
            leverage = float(row["debts"]) / assets if assets > 0 else 0.0
            records.append((capital, leverage, float(lifespan), False, seed))

        snapshots = report.load_snapshots(folder)
        if not snapshots:
            continue
        final_t = max(snapshots)
        summary_path = Path(folder) / "summary.json"
        summary = (
            report.json.loads(summary_path.read_text(encoding="utf-8"))
            if summary_path.exists()
            else {}
        )
        # Une censure fiable exige un snapshot pris exactement à l'arrêt.
        if final_t != int(summary.get("t_final", final_t)):
            continue
        final = snapshots[final_t]
        for index, raw_id in enumerate(final["id"]):
            entity_id = int(raw_id)
            birth_row = births.get(entity_id)
            if (
                entity_id in dead_ids
                or not birth_row
                or not bool(birth_row.get("alive_final", 0))
            ):
                continue
            lifespan = final_t - birth_row["birth"]
            if lifespan < 0:
                continue
            capital = float(final["K"][index])
            assets = capital + float(final["claims"][index])
            leverage = (
                float(final["debts"][index]) / assets if assets > 0 else 0.0
            )
            records.append((capital, leverage, float(lifespan), True, seed))
    return records


def fig_lifespan_heatmaps(report, members, out_dir: Path, extra: str) -> None:
    """Tous les décès, plus les survivantes censurées au dernier snapshot."""
    records = _lifespan_records(report, members)
    if len(records) < 5:
        return
    plt = report.plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    specs = (
        (0, "Capital K au décès / à la fin (J)", True),
        (1, "Levier dettes/actifs au décès / à la fin", True),
    )
    for axis, (column, xlabel, log_x) in zip(axes, specs):
        values = np.asarray(
            [(row[column], row[2]) for row in records if row[column] > 0]
        )
        if not len(values):
            continue
        heatmap = axis.hexbin(
            values[:, 0],
            values[:, 1],
            gridsize=60,
            mincnt=1,
            bins="log",
            xscale="log" if log_x else "linear",
            cmap="YlOrRd",
            alpha=0.8,
        )
        fig.colorbar(
            heatmap, ax=axis, label="Effectif par hexagone (échelle log)"
        )
        dead = np.asarray(
            [(row[column], row[2]) for row in records if not row[3] and row[column] > 0]
        )
        alive = np.asarray(
            [(row[column], row[2]) for row in records if row[3] and row[column] > 0]
        )
        dead_count = len(dead)
        alive_count = len(alive)
        if dead_count > 25_000:
            keep = np.unique(
                np.linspace(0, dead_count - 1, 25_000, dtype=int)
            )
            dead = dead[keep]
        if alive_count > 25_000:
            keep = np.unique(
                np.linspace(0, alive_count - 1, 25_000, dtype=int)
            )
            alive = alive[keep]
        if len(dead):
            axis.scatter(
                dead[:, 0],
                dead[:, 1],
                s=0.45,
                alpha=0.08,
                color="#5b0000",
                label=f"Décédées : {dead_count:,} (points affichés : {len(dead):,})",
            )
        if len(alive):
            axis.scatter(
                alive[:, 0],
                alive[:, 1],
                s=1.2,
                alpha=0.22,
                color="#006d2c",
                marker="^",
                label=f"Survivantes censurées : {alive_count:,}",
            )
        axis.set_xlabel(xlabel)
        axis.set_ylabel("Durée de vie (pas)")
        axis.legend(fontsize=7)
        axis.grid(True, alpha=0.18)
    dead_total = sum(not row[3] for row in records)
    censored_total = len(records) - dead_total
    fig.suptitle(
        "Durées de vie exhaustives : états terminaux, points et heatmaps "
        f"— {dead_total:,} décès, {censored_total:,} censurées — {extra}"
    )
    fig.tight_layout()
    _save(fig, Path(out_dir) / "lifespan_analysis.png", plt)


def _instantaneous_life_records(report, members, horizon=100):
    """Observations landmark avec suivi complet sur ``horizon`` pas."""
    records = []
    burn_ins = []
    for seed, folder, _ in members:
        summary_path = Path(folder) / "summary.json"
        if not summary_path.exists():
            continue
        summary = report.json.loads(summary_path.read_text(encoding="utf-8"))
        final_t = int(summary.get("t_final", report._run_T(folder)))
        burn_in = report._run_T(folder) // 4
        burn_ins.append(burn_in)
        deaths = {
            int(row["id"]): int(row["t"])
            for row in report.load_death_registry(folder)
        }
        snapshots = report.load_snapshots(folder)
        for step in sorted(snapshots):
            if step < burn_in or step > final_t - horizon:
                continue
            snapshot = snapshots[step]
            snapshot_weight = 1.0 / max(1, len(snapshot["id"]))
            for index, raw_id in enumerate(snapshot["id"]):
                entity_id = int(raw_id)
                capital = float(snapshot["K"][index])
                claims = float(snapshot["claims"][index])
                debts = float(snapshot["debts"][index])
                assets = capital + claims
                leverage = debts / assets if assets > 0 else 0.0
                death_t = deaths.get(entity_id)
                remaining = (
                    death_t - step
                    if death_t is not None and death_t > step
                    else horizon
                )
                event = 0 < remaining <= horizon and death_t is not None
                records.append(
                    (
                        capital,
                        leverage,
                        float(min(max(remaining, 0), horizon)),
                        bool(event),
                        seed,
                        step,
                        snapshot_weight,
                    )
                )
    return records, min(burn_ins) if burn_ins else None


def _conditional_life_bins(records, predictor_index, log_predictor, n_bins=15):
    values = np.asarray([row[predictor_index] for row in records], dtype=float)
    durations = np.asarray([row[2] for row in records], dtype=float)
    events = np.asarray([row[3] for row in records], dtype=bool)
    weights = np.asarray([row[6] for row in records], dtype=float)
    valid = np.isfinite(values) & (values >= 0)
    if log_predictor:
        valid &= values > 0
    values = values[valid]
    durations = durations[valid]
    events = events[valid]
    weights = weights[valid]
    if len(values) < 100:
        return [], values, durations, events
    transformed = np.log10(values) if log_predictor else values
    normalized_weights = weights / weights.sum()
    edges = np.unique(
        [
            _weighted_quantile_by_time(
                transformed, normalized_weights, quantile
            )
            for quantile in np.linspace(0, 1, n_bins + 1)
        ]
    )
    rows = []
    for index in range(len(edges) - 1):
        inside = (transformed >= edges[index]) & (
            transformed < edges[index + 1]
            if index < len(edges) - 2
            else transformed <= edges[index + 1]
        )
        if inside.sum() < 50:
            continue
        x = values[inside]
        y = durations[inside]
        event_bin = events[inside]
        bin_weights = weights[inside]
        bin_weights = bin_weights / bin_weights.sum()
        rows.append(
            {
                "lower": float(x.min()),
                "upper": float(x.max()),
                "center": float(np.median(x)),
                "n": int(len(x)),
                "events": int(event_bin.sum()),
                "rmst": float(np.average(y, weights=bin_weights)),
                "median": _weighted_quantile_by_time(y, bin_weights, 0.5),
                "q10": _weighted_quantile_by_time(y, bin_weights, 0.1),
                "q90": _weighted_quantile_by_time(y, bin_weights, 0.9),
                "event_probability": float(
                    np.average(event_bin.astype(float), weights=bin_weights)
                ),
            }
        )
    return rows, values, durations, events


def _write_instantaneous_life_csv(rows_by_predictor, out_dir, horizon, burn_in):
    path = Path(out_dir) / "instantaneous_life_expectancy.csv"
    fields = (
        "predictor",
        "bin_lower",
        "bin_upper",
        "bin_center",
        "n_observations",
        "deaths_within_horizon",
        "survives_beyond_horizon",
        "weighted_death_probability",
        "rmst_steps",
        "median_steps",
        "q10_steps",
        "q90_steps",
        "horizon_steps",
        "burn_in_step",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for predictor, rows in rows_by_predictor.items():
            for row in rows:
                writer.writerow(
                    {
                        "predictor": predictor,
                        "bin_lower": row["lower"],
                        "bin_upper": row["upper"],
                        "bin_center": row["center"],
                        "n_observations": row["n"],
                        "deaths_within_horizon": row["events"],
                        "survives_beyond_horizon": row["n"] - row["events"],
                        "weighted_death_probability": row["event_probability"],
                        "rmst_steps": row["rmst"],
                        "median_steps": row["median"],
                        "q10_steps": row["q10"],
                        "q90_steps": row["q90"],
                        "horizon_steps": horizon,
                        "burn_in_step": burn_in,
                    }
                )
    return path.name


def fig_instantaneous_life_expectancy(
    report, members, out_dir: Path, extra: str, horizon=100
) -> list[str]:
    """Vie restante conditionnelle aux états financiers instantanés."""
    records, burn_in = _instantaneous_life_records(report, members, horizon)
    if len(records) < 100:
        return []
    plt = report.plt
    specs = (
        (
            "capital_K",
            0,
            True,
            "Capital instantané K(t) (J)",
            "instantaneous_life_expectancy_by_size.png",
            "Espérance de vie restante selon la taille instantanée",
        ),
        (
            "debt_asset_ratio",
            1,
            False,
            "Ratio instantané dettes / actifs",
            "instantaneous_life_expectancy_by_leverage.png",
            "Espérance de vie restante selon le levier instantané",
        ),
    )
    generated = []
    rows_by_predictor = {}
    for predictor, column, log_x, xlabel, filename, title in specs:
        binned, values, durations, events = _conditional_life_bins(
            records, column, log_x
        )
        if not binned:
            continue
        rows_by_predictor[predictor] = binned
        fig, (heatmap_axis, mean_axis) = plt.subplots(1, 2, figsize=(14, 5.7))
        heatmap = heatmap_axis.hexbin(
            values,
            durations,
            gridsize=60,
            mincnt=1,
            bins="log",
            xscale="log" if log_x else "linear",
            cmap="YlOrRd",
        )
        fig.colorbar(
            heatmap,
            ax=heatmap_axis,
            label="Effectif par hexagone (échelle log)",
        )
        point_count = min(len(values), 25_000)
        positions = np.unique(
            np.linspace(0, len(values) - 1, point_count, dtype=int)
        )
        heatmap_axis.scatter(
            values[positions],
            durations[positions],
            s=0.4,
            alpha=0.07,
            color="#3f0000",
        )
        heatmap_axis.set_xlabel(xlabel)
        heatmap_axis.set_ylabel(
            f"Durée de vie restante, tronquée à {horizon} pas"
        )
        heatmap_axis.set_title(
            f"Landmarks individuels (n={len(values):,})", fontsize=10
        )
        heatmap_axis.grid(True, alpha=0.18)

        x = np.asarray([row["center"] for row in binned])
        mean = np.asarray([row["rmst"] for row in binned])
        q10 = np.asarray([row["q10"] for row in binned])
        q90 = np.asarray([row["q90"] for row in binned])
        mean_axis.fill_between(
            x, q10, q90, alpha=0.18, color="#3182bd", label="D1–D9"
        )
        mean_axis.plot(
            x,
            mean,
            "o-",
            ms=4,
            lw=1.8,
            color="black",
            label=f"RMRL restreinte à {horizon} pas",
        )
        if log_x:
            mean_axis.set_xscale("log")
        mean_axis.set_ylim(0, horizon * 1.03)
        mean_axis.set_xlabel(xlabel)
        mean_axis.set_ylabel("Espérance restreinte de vie restante (pas)")
        mean_axis.set_title(
            "Moyenne conditionnelle — snapshots équipondérés, classes équipopulées"
        )
        mean_axis.grid(True, alpha=0.22)
        mean_axis.legend(fontsize=8)
        fig.suptitle(
            f"{title} — burn-in {burn_in}, suivi complet {horizon} pas — {extra}"
        )
        fig.tight_layout()
        _save(fig, Path(out_dir) / filename, plt)
        generated.append(filename)
    if rows_by_predictor:
        generated.append(
            _write_instantaneous_life_csv(
                rows_by_predictor, out_dir, horizon, burn_in
            )
        )
    return generated


def _select_entities(history, births, n_max=10):
    if not history:
        return []
    first = sorted(history, key=lambda entity: births.get(entity, 0))[:5]
    largest = max(history, key=lambda entity: max(row["K"] for row in history[entity]))
    later = sorted(
        (entity for entity in history if entity not in first and entity != largest),
        key=lambda entity: births.get(entity, 0),
    )
    spread = (
        [later[index] for index in range(0, len(later), max(1, len(later) // 5))][
            :5
        ]
        if later
        else []
    )
    return list(dict.fromkeys(first + [largest] + spread))[:n_max]


def _life_block(balance_axis, flow_axis, rows, show_legend=True):
    times = np.asarray([row["t"] for row in rows])
    capital = np.asarray([row["K"] for row in rows])
    claims = np.asarray([row["claims"] for row in rows])
    debts = np.asarray([row["debts"] for row in rows])
    net_worth = np.asarray([row["nw"] for row in rows])
    production = np.asarray([row["prod"] for row in rows])
    interest_in = np.asarray([row["int_in"] for row in rows])
    interest_out = np.asarray([row["int_out"] for row in rows])

    balance_axis.stackplot(
        times,
        capital,
        claims,
        labels=("Capital K", "Créances"),
        colors=("#1f77b4", "#ff7f0e"),
        alpha=0.72,
    )
    balance_axis.fill_between(
        times, 0, -debts, color="#d62728", alpha=0.55, label="Dettes (−)"
    )
    balance_axis.plot(
        times, net_worth, color="black", lw=1.25, label="Valeur nette"
    )
    balance_axis.axhline(0, color="black", lw=0.7)
    balance_axis.set_ylabel("Bilan (J)")

    flow_axis.fill_between(
        times, 0, production, alpha=0.65, color="#2ca02c", label="Production Π"
    )
    flow_axis.fill_between(
        times,
        production,
        production + interest_in,
        alpha=0.65,
        color="#1f77b4",
        label="Intérêts reçus",
    )
    flow_axis.fill_between(
        times, 0, -interest_out, alpha=0.65, color="#d62728", label="Intérêts payés"
    )
    flow_axis.axhline(0, color="black", lw=0.7)
    flow_axis.set_ylabel("Flux (J/pas)")
    flow_axis.set_xlabel("Pas de simulation")

    padding = max(1.0, 0.02 * max(float(times[-1] - times[0]), 1.0))
    for axis in (balance_axis, flow_axis):
        axis.set_xlim(times[0] - padding, times[-1] + padding)
        axis.grid(True, alpha=0.18)
    if show_legend:
        balance_axis.legend(fontsize=7, loc="best", ncol=2)
        flow_axis.legend(fontsize=7, loc="best", ncol=2)


def fig_entity_lives(report, folder: Path, out_dir: Path, extra: str) -> list[str]:
    plt = report.plt
    history = {}
    for row in report.load_watch(folder):
        history.setdefault(row["id"], []).append(row)
    for rows in history.values():
        rows.sort(key=lambda row: row["t"])
    births = {row["id"]: row["birth"] for row in report.load_births(folder)}
    entity_ids = _select_entities(history, births, n_max=12)
    if not entity_ids:
        return []

    overview_ids = entity_ids[:10]
    fig = plt.figure(figsize=(24, 11), constrained_layout=True)
    outer = fig.add_gridspec(2, 5, wspace=0.3, hspace=0.28)
    for index, entity_id in enumerate(overview_ids):
        inner = outer[index // 5, index % 5].subgridspec(2, 1, hspace=0.08)
        balance = fig.add_subplot(inner[0, 0])
        flow = fig.add_subplot(inner[1, 0], sharex=balance)
        _life_block(balance, flow, history[entity_id], show_legend=index == 0)
        duration = history[entity_id][-1]["t"] - history[entity_id][0]["t"]
        balance.set_title(f"Entité {entity_id} — vie observée {duration} pas", fontsize=8)
        balance.tick_params(labelbottom=False, labelsize=6)
        flow.tick_params(labelsize=6)
    fig.suptitle(
        f"Vies individuelles : bilan fusionné, dettes négatives et zoom — {extra}",
        fontsize=12,
    )
    _save(fig, Path(out_dir) / "entity_lives_overview.png", plt)

    detail_dir = Path(out_dir) / "detail_vie_entites"
    if detail_dir.exists():
        shutil.rmtree(detail_dir)
    detail_dir.mkdir(parents=True)
    generated = ["entity_lives_overview.png"]
    for entity_id in entity_ids:
        fig, (balance, flow) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        _life_block(balance, flow, history[entity_id], show_legend=True)
        duration = history[entity_id][-1]["t"] - history[entity_id][0]["t"]
        fig.suptitle(
            f"Entité {entity_id} — zoom sur sa vie ({duration} pas) — {extra}",
            fontsize=11,
        )
        fig.tight_layout()
        filename = f"entity_{entity_id}.png"
        _save(fig, detail_dir / filename, plt)
        generated.append(f"detail_vie_entites/{filename}")
    return generated


def generate_individual(report, folder: Path, seed: int):
    """Écrase uniquement les anciennes figures individuelles concernées."""
    folder = Path(folder)
    out_dir = folder / "figures"
    out_dir.mkdir(exist_ok=True)
    config = report.json.loads((folder / "config.json").read_text())
    extra = (
        f"λ={config['lam']:g}, k={config['k']}, σ={config['sigma']}, "
        f"T={config['T']}, seed {seed}"
    )
    members = [(seed, folder, "single")]
    generated = []
    errors = []

    # Ne jamais conserver une ancienne version trompeuse si une nouvelle
    # recette ne dispose pas d'assez de données pour produire sa figure.
    for obsolete in (
        "cascades_rank_size.png",
        "entity_size_histos.png",
        "volume_ccdf.png",
        "entity_size_histo_temporal_mean.png",
        "entity_size_histo_evolution.gif",
        "lifespan_analysis.png",
        "instantaneous_life_expectancy_by_size.png",
        "instantaneous_life_expectancy_by_leverage.png",
        "instantaneous_life_expectancy.csv",
        "revenue_distributions.png",
        "entity_lives_overview.png",
        *(series[2] for series in REVENUE_SERIES),
        *(series[2].replace(".png", "_temporal_mean.png") for series in REVENUE_SERIES),
        *(series[2].replace(".png", "_evolution.gif") for series in REVENUE_SERIES),
    ):
        path = out_dir / obsolete
        if path.exists():
            path.unlink()
    detail_dir = out_dir / "detail_vie_entites"
    if detail_dir.exists():
        shutil.rmtree(detail_dir)

    actions = (
        ("cascades_rank_size", lambda: fig_cascades(report, members, out_dir, extra)),
        ("volume_ccdf", lambda: fig_volume_ccdf(report, members, out_dir, extra)),
        ("entity_size_histos", lambda: report.fig_size_histos(members, out_dir, extra)),
        ("lifespan_analysis", lambda: fig_lifespan_heatmaps(report, members, out_dir, extra)),
    )
    for name, action in actions:
        try:
            action()
            filename = f"{name}.png"
            if (out_dir / filename).exists():
                generated.append(filename)
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    try:
        generated.extend(
            fig_instantaneous_life_expectancy(
                report, members, out_dir, extra
            )
        )
    except Exception as exc:
        errors.append(f"instantaneous_life_expectancy: {exc}")

    try:
        generated.extend(fig_entity_size_animation(report, folder, out_dir, extra))
    except Exception as exc:
        errors.append(f"entity_size_animation: {exc}")

    try:
        generated.extend(fig_revenues_split(report, members, out_dir, extra))
    except Exception as exc:
        errors.append(f"revenue_distributions: {exc}")

    try:
        generated.extend(fig_revenues_animations(report, folder, out_dir, extra))
    except Exception as exc:
        errors.append(f"revenue_animations: {exc}")

    try:
        generated.extend(fig_entity_lives(report, folder, out_dir, extra))
    except Exception as exc:
        errors.append(f"entity_lives: {exc}")
    return generated, errors
