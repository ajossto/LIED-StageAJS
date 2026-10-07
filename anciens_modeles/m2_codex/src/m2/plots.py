from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .analysis import fit_body_distributions


def _save(fig: plt.Figure, output_base: str | Path) -> None:
    base = Path(output_base)
    base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(base.with_suffix(".png"), dpi=180, bbox_inches="tight")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def plot_macros(timeseries: Sequence[dict], output_base: str | Path) -> None:
    if not timeseries:
        return
    step = np.asarray([int(row["step"]) for row in timeseries])
    panels = [
        ("population", "Population"),
        ("total_capital", "Capital réel total"),
        ("loan_volume", "Volume de nouveaux prêts"),
        ("failures", "Faillites par pas"),
        ("active_contracts", "Contrats actifs"),
        ("credit_hhi", "Concentration du crédit (HHI)"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True)
    for axis, (field, label) in zip(axes.flat, panels, strict=True):
        axis.plot(step, [float(row[field]) for row in timeseries], lw=1.0)
        axis.set_title(label)
        axis.grid(alpha=0.25)
    for axis in axes[-1]:
        axis.set_xlabel("Pas")
    fig.suptitle("Dynamique macroscopique M2")
    _save(fig, output_base)


def plot_distributions(rows: Sequence[dict], output_base: str | Path) -> None:
    variables = [
        ("w", "Capital $w$"),
        ("nw", "Valeur nette NW"),
        ("income_gross", "Revenu brut"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for column, (field, label) in enumerate(variables):
        values = np.asarray(
            [
                float(row[field])
                for row in rows
                if math.isfinite(float(row[field])) and float(row[field]) > 0
            ]
        )
        if not len(values):
            continue
        upper = np.quantile(values, 0.99)
        axes[0, column].hist(values[values <= upper], bins=50, density=True, alpha=0.75)
        axes[0, column].set_title(label + " (99 % inférieurs)")
        axes[0, column].set_xlabel(label)
        ordered = np.sort(values)
        ccdf = (len(ordered) - np.arange(len(ordered))) / len(ordered)
        axes[1, column].loglog(ordered, ccdf, marker=".", ls="none", ms=2)
        axes[1, column].set_xlabel(label)
        axes[1, column].set_ylabel("CCDF")
        axes[1, column].grid(alpha=0.25, which="both")
    fig.suptitle("Distributions transversales M2")
    _save(fig, output_base)


def plot_age_diagnostics(rows: Sequence[dict], output_base: str | Path) -> None:
    positive = [row for row in rows if float(row["nw"]) > 0]
    if not positive:
        return
    nw = np.asarray([float(row["nw"]) for row in positive])
    age = np.asarray([float(row["age"]) for row in positive])
    boundaries = np.quantile(nw, np.linspace(0, 1, 11))
    deciles = np.clip(np.digitize(nw, boundaries[1:-1], right=False) + 1, 1, 10)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].scatter(age, np.log(nw), s=5, alpha=0.25)
    axes[0].set_xlabel("Âge")
    axes[0].set_ylabel("log(NW)")
    axes[0].grid(alpha=0.25)
    grouped = [age[deciles == d] for d in range(1, 11)]
    axes[1].boxplot(
        grouped, tick_labels=[str(d) for d in range(1, 11)], showfliers=False
    )
    axes[1].set_xlabel("Décile de NW")
    axes[1].set_ylabel("Âge")
    axes[1].grid(alpha=0.25, axis="y")
    fig.suptitle("Garde-fou anti-cohorte")
    _save(fig, output_base)


def plot_cascade_batches(timeseries: Sequence[dict], output_base: str | Path) -> None:
    sizes = np.asarray(
        [
            int(float(row["failures"]))
            for row in timeseries
            if float(row["failures"]) > 0
        ]
    )
    if not len(sizes):
        return
    ordered = np.sort(sizes)
    ccdf = (len(ordered) - np.arange(len(ordered))) / len(ordered)
    fig, axis = plt.subplots(figsize=(6, 4.5))
    axis.loglog(ordered, ccdf, "o", ms=4)
    axis.set_xlabel("Faillites dans la phase de cascade d'un pas")
    axis.set_ylabel("CCDF")
    axis.grid(alpha=0.3, which="both")
    axis.set_title("Tailles de lots de faillites (pas des avalanches causales isolées)")
    _save(fig, output_base)


def plot_exponential_qq(
    rows: Sequence[dict],
    variable: str,
    output_base: str | Path,
    body_quantile: float = 0.95,
) -> None:
    values = np.asarray(
        [float(row[variable]) for row in rows if float(row[variable]) > 0]
    )
    fit = fit_body_distributions(values, body_quantile=body_quantile)
    if fit.get("status") != "ok":
        return
    exponential = next(item for item in fit["fits"] if item["name"] == "exponential")
    cutoff = float(fit["cutoff"])
    body = np.sort(values[values <= cutoff])
    scale = float(exponential["parameters"][-1])
    probabilities = (np.arange(1, len(body) + 1) - 0.5) / len(body)
    cdf_cutoff = 1 - math.exp(-cutoff / scale)
    theoretical = -scale * np.log(1 - probabilities * cdf_cutoff)
    fig, axis = plt.subplots(figsize=(5, 5))
    axis.scatter(theoretical, body, s=7, alpha=0.55)
    limit = max(float(theoretical[-1]), float(body[-1]))
    axis.plot([0, limit], [0, limit], color="black", lw=1)
    axis.set_xlabel("Quantiles exponentiels tronqués")
    axis.set_ylabel(f"Quantiles observés ({variable})")
    axis.grid(alpha=0.25)
    axis.set_title(f"QQ exponentiel du corps ({body_quantile:.1%})")
    _save(fig, output_base)
