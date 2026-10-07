#!/usr/bin/env python3
"""Campagne reproductible pour le rapport empirique de la dyade M4.2."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import math
import os
import sys
import zlib
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
sys.path.insert(0, str(PARENT))

from verification_empirique import (  # noqa: E402
    first_step_death_probability,
    loan_terms,
    phi_gamma,
)

FIGURES = HERE / "figures"
RESULTS = HERE / "resultats"

K1 = 100.0
K2_BASE = 25.0
K2_VALUES = (5.0, 10.0, 25.0, 40.0, 50.0, 60.0)
GAMMA0 = 0.5
DELTA0 = 0.05
SIGMA0 = 0.25
RATE0 = 0.1
RATE_M4 = 0.5 * (K1 * K2_BASE) ** (-0.25)
RATES = (0.0, 0.025, 0.05, RATE_M4, 0.1, 0.25, 0.5, 1.0)
SCHEME = "arithmetic"


def stable_seed(base_seed: int, label: str) -> int:
    return (base_seed + zlib.crc32(label.encode("utf-8"))) % (2**32)


def simulate_stopped(
    *,
    k1: float,
    k2: float,
    gamma: float,
    delta: float,
    sigma: float,
    rate: float,
    scheme: str,
    paths: int,
    max_steps: int,
    seed: int,
) -> dict[str, np.ndarray | float | int | str]:
    """Simule seulement les trajectoires encore vivantes, jusqu'à absorption."""
    q, lender0, borrower0 = loan_terms(k1, k2, scheme)
    d = 1.0 - delta
    c = rate * q
    rng = np.random.default_rng(seed)

    active_ids = np.arange(paths, dtype=np.int64)
    lender = np.full(paths, lender0, dtype=np.float64)
    borrower = np.full(paths, borrower0, dtype=np.float64)
    death_time = np.zeros(paths, dtype=np.int32)
    lender_at_death = np.full(paths, np.nan, dtype=np.float64)
    borrower_terminal = np.full(paths, np.nan, dtype=np.float64)
    cause = np.zeros(paths, dtype=np.int8)

    for step in range(1, max_steps + 1):
        count = active_ids.size
        if count == 0:
            break
        xi_l = rng.normal(-0.5 * sigma**2, sigma, count)
        xi_b = rng.normal(-0.5 * sigma**2, sigma, count)
        y_l = phi_gamma(lender * np.exp(xi_l), gamma)
        y_b = phi_gamma(borrower * np.exp(xi_b), gamma)
        payment = np.minimum(c, y_b)
        new_lender = d * (y_l + payment)
        new_borrower = d * np.maximum(y_b - c, 0.0)
        survives = y_b >= c + q / d

        if np.any(~survives):
            dead_ids = active_ids[~survives]
            death_time[dead_ids] = step
            lender_at_death[dead_ids] = new_lender[~survives]
            borrower_terminal[dead_ids] = new_borrower[~survives]
            cause[dead_ids] = np.where(y_b[~survives] < c, 1, 2)

        active_ids = active_ids[survives]
        lender = new_lender[survives]
        borrower = new_borrower[survives]

    return {
        "scheme": scheme,
        "q": q,
        "lender0": lender0,
        "borrower0": borrower0,
        "death_time": death_time,
        "lender_at_death": lender_at_death,
        "borrower_terminal": borrower_terminal,
        "cause": cause,
        "censored": int(active_ids.size),
    }


def run_stopped_task(task: tuple[tuple, int, dict]) -> tuple[tuple, int, dict]:
    """Point d'entrée sérialisable pour une condition d'arrêt."""
    key, chunk_index, kwargs = task
    return key, chunk_index, simulate_stopped(**kwargs)


def combine_stopped(parts: list[dict]) -> dict:
    """Concatène les sous-échantillons indépendants d'une condition."""
    first = parts[0]
    combined = {
        "scheme": first["scheme"],
        "q": first["q"],
        "lender0": first["lender0"],
        "borrower0": first["borrower0"],
        "censored": sum(int(part["censored"]) for part in parts),
    }
    for field in ("death_time", "lender_at_death", "borrower_terminal", "cause"):
        combined[field] = np.concatenate([np.asarray(part[field]) for part in parts])
    return combined


def summarize_stopped(
    result: dict[str, np.ndarray | float | int | str],
    *,
    gamma: float,
    delta: float,
    sigma: float,
    rate: float,
    group: str,
    value: float,
    k2: float,
    paths: int,
    max_steps: int,
) -> dict[str, float | int | str]:
    t_all = np.asarray(result["death_time"])
    finite = t_all > 0
    t = t_all[finite].astype(float)
    b = np.asarray(result["borrower_terminal"])[finite]
    l = np.asarray(result["lender_at_death"])[finite]
    cause = np.asarray(result["cause"])[finite]
    q = float(result["q"])
    borrower0 = float(result["borrower0"])
    p1 = first_step_death_probability(borrower0, q, rate, gamma, delta, sigma)

    def quantile(array: np.ndarray, probability: float) -> float:
        return float(np.quantile(array, probability)) if array.size else math.nan

    def censored_time_quantile(probability: float) -> float:
        rank = int(math.ceil(probability * paths))
        ordered = np.sort(t)
        return float(ordered[rank - 1]) if rank <= ordered.size else math.inf

    return {
        "group": group,
        "value": value,
        "scheme": str(result["scheme"]),
        "k1": K1,
        "k2": k2,
        "k2_over_k1": k2 / K1,
        "gamma": gamma,
        "delta": delta,
        "sigma": sigma,
        "rate": rate,
        "paths": paths,
        "q": q,
        "lender0": float(result["lender0"]),
        "borrower0": borrower0,
        "censored": int(result["censored"]),
        "death_fraction_at_horizon": float(np.mean(finite)),
        "p_death_1_theory": p1,
        "p_death_1_empirical": float(np.mean(t_all == 1)),
        "mean_T": float(np.mean(t)) if t.size else math.nan,
        "sd_T": float(np.std(t, ddof=1)) if t.size > 1 else math.nan,
        "restricted_mean_T": float(np.mean(np.where(finite, t_all, max_steps))),
        "q10_T": censored_time_quantile(0.10),
        "q25_T": censored_time_quantile(0.25),
        "median_T": censored_time_quantile(0.50),
        "q75_T": censored_time_quantile(0.75),
        "q90_T": censored_time_quantile(0.90),
        "q95_T": censored_time_quantile(0.95),
        "q99_T": censored_time_quantile(0.99),
        "p_liquidity": float(np.mean(cause == 1)) if cause.size else math.nan,
        "p_insolvency": float(np.mean(cause == 2)) if cause.size else math.nan,
        "mean_B_terminal": float(np.mean(b)) if b.size else math.nan,
        "median_B_terminal": quantile(b, 0.50),
        "q90_B_terminal": quantile(b, 0.90),
        "mean_B_terminal_over_q": float(np.mean(b / q)) if b.size else math.nan,
        "median_B_terminal_over_q": quantile(b / q, 0.50),
        "q90_B_terminal_over_q": quantile(b / q, 0.90),
        "mean_L_at_T": float(np.mean(l)) if l.size else math.nan,
        "median_L_at_T": quantile(l, 0.50),
        "q90_L_at_T": quantile(l, 0.90),
        "q99_L_at_T": quantile(l, 0.99),
    }


def simulate_stationary(
    *,
    gamma: float,
    delta: float,
    sigma: float,
    paths: int,
    burn_steps: int,
    seed: int,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Approche la loi autarcique par particules parties de deux extrêmes."""
    d = 1.0 - delta
    if delta > 0:
        k_aut = (d / delta) ** (1.0 / (1.0 - gamma))
    else:
        k_aut = 1.0
    split = paths // 2
    capital = np.empty(paths, dtype=np.float64)
    capital[:split] = 0.01 * k_aut
    capital[split:] = 100.0 * k_aut
    rng = np.random.default_rng(seed)
    halfway = None
    for step in range(1, burn_steps + 1):
        xi = rng.normal(-0.5 * sigma**2, sigma, paths)
        capital = d * phi_gamma(capital * np.exp(xi), gamma)
        if step == burn_steps // 2:
            halfway = capital.copy()
    assert halfway is not None
    ks_time = ks_2samp(halfway, capital).statistic
    ks_initial = ks_2samp(capital[:split], capital[split:]).statistic
    lhs = delta * float(np.mean(capital))
    rhs = (
        d
        * math.exp(-gamma * (1.0 - gamma) * sigma**2 / 2.0)
        * float(np.mean(capital**gamma))
    )
    moment_residual = abs(lhs - rhs) / max(abs(lhs), abs(rhs), 1e-15)
    summary = {
        "gamma": gamma,
        "delta": delta,
        "sigma": sigma,
        "paths": paths,
        "burn_steps": burn_steps,
        "K_aut": k_aut,
        "mean": float(np.mean(capital)),
        "sd": float(np.std(capital, ddof=1)),
        "q01": float(np.quantile(capital, 0.01)),
        "q10": float(np.quantile(capital, 0.10)),
        "median": float(np.quantile(capital, 0.50)),
        "q90": float(np.quantile(capital, 0.90)),
        "q99": float(np.quantile(capital, 0.99)),
        "ks_half_vs_final": float(ks_time),
        "ks_low_vs_high_final": float(ks_initial),
        "moment_identity_relative_residual": moment_residual,
    }
    return capital, summary


def run_stationary_task(task: tuple[tuple, dict]) -> tuple[tuple, np.ndarray, dict]:
    """Point d'entrée sérialisable pour une condition stationnaire."""
    metadata, kwargs = task
    sample, summary = simulate_stationary(**kwargs)
    return metadata, sample, summary


def coupled_order_check(paths: int, max_steps: int, seed: int) -> dict[str, int]:
    """Vérifie que T(k2) croît avec k2 sous les mêmes chocs."""
    d = 1.0 - DELTA0
    rng = np.random.default_rng(seed)
    q_values = np.array([(K1 - k2) / 2.0 for k2 in K2_VALUES])
    b0_values = np.array([(K1 + k2) / 2.0 for k2 in K2_VALUES])
    capital = np.repeat(b0_values[:, None], paths, axis=1)
    alive = np.ones((len(K2_VALUES), paths), dtype=bool)
    death_times = np.zeros((len(K2_VALUES), paths), dtype=np.int32)
    for step in range(1, max_steps + 1):
        if not np.any(alive[-1]):
            break
        xi = rng.normal(-0.5 * SIGMA0**2, SIGMA0, paths)
        multiplier = np.exp(xi)
        for index, q in enumerate(q_values):
            if not np.any(alive[index]):
                continue
            c = RATE0 * q
            resources = phi_gamma(capital[index] * multiplier, GAMMA0)
            next_capital = d * np.maximum(resources - c, 0.0)
            dies = alive[index] & (resources < c + q / d)
            death_times[index, dies] = step
            alive[index, dies] = False
            capital[index, alive[index]] = next_capital[alive[index]]
    complete = np.all(death_times > 0, axis=0)
    ordered = np.all(np.diff(death_times[:, complete], axis=0) >= 0, axis=0)
    return {
        "paths": paths,
        "complete_vectors": int(np.sum(complete)),
        "violations_monotonicity": int(np.sum(~ordered)),
        "strict_from_k2_5_to_k2_60": int(
            np.sum(death_times[0, complete] < death_times[-1, complete])
        ),
        "ties_extremes": int(
            np.sum(death_times[0, complete] == death_times[-1, complete])
        ),
    }


def run_coupling_task(task: tuple[int, int, int]) -> dict[str, int]:
    paths, max_steps, seed = task
    return coupled_order_check(paths=paths, max_steps=max_steps, seed=seed)


def empirical_survival(times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.sort(times[times > 0])
    unique, counts = np.unique(values, return_counts=True)
    cumulative = np.cumsum(counts)
    survival = 1.0 - cumulative / values.size
    return unique, survival


def ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(values[np.isfinite(values)])
    return x, np.arange(1, x.size + 1) / x.size


def make_figures(
    summaries: pd.DataFrame,
    stationary: pd.DataFrame,
    baseline_raw: dict[float, dict[str, np.ndarray | float | int | str]],
    stationary_baseline: np.ndarray,
) -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (7.2, 4.5),
            "font.size": 10,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "savefig.bbox": "tight",
        }
    )
    colors = plt.cm.viridis(np.linspace(0.05, 0.95, len(K2_VALUES)))
    color_by_k2 = dict(zip(K2_VALUES, colors, strict=True))

    fig, ax = plt.subplots()
    for k2 in K2_VALUES:
        t = np.asarray(baseline_raw[k2]["death_time"])
        x, y = empirical_survival(t)
        keep = y > 0
        ax.step(x[keep], y[keep], where="post", color=color_by_k2[k2], label=rf"$k_2={k2:g}$")
    ax.set_yscale("log")
    ax.set_xlabel("temps t")
    ax.set_ylabel(r"probabilité empirique $\widehat{P}(T_B>t)$")
    ax.set_title(r"Survie de l'emprunteuse, $r=0{,}1$")
    ax.legend()
    fig.savefig(FIGURES / "survie_baseline.pdf")
    plt.close(fig)

    rate_df = summaries[summaries["group"] == "rate_k2"].sort_values("rate")
    fig, ax = plt.subplots()
    for k2 in K2_VALUES:
        sub = rate_df[rate_df["k2"] == k2]
        x = sub["rate"].to_numpy()
        ax.plot(x, sub["median_T"], "o-", color=color_by_k2[k2], label=rf"$k_2={k2:g}$")
    ax.set_xlabel("taux r")
    ax.set_ylabel(r"temps de défaut $T_B$")
    ax.set_title("Médiane et intervalle empirique 10--90 %")
    ax.legend()
    fig.savefig(FIGURES / "temps_defaut_selon_taux.pdf")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    for k2 in K2_VALUES:
        raw = baseline_raw[k2]
        b = np.asarray(raw["borrower_terminal"])
        l = np.asarray(raw["lender_at_death"])
        q = float(raw["q"])
        xb, yb = ecdf(b / q)
        xl, yl = ecdf(l)
        axes[0].plot(xb, yb, color=color_by_k2[k2], label=rf"$k_2={k2:g}$")
        axes[1].plot(xl, yl, color=color_by_k2[k2], label=rf"$k_2={k2:g}$")
    axes[0].set_xlabel(r"capital détruit relatif $B_T^\dagger/q$")
    axes[0].set_ylabel("fonction de répartition empirique")
    axes[1].set_xlabel(r"capital de la prêteuse $L_{T_B}$")
    axes[1].set_xscale("log")
    axes[0].legend()
    axes[1].legend()
    fig.suptitle(r"Lois arrêtées, $r=0{,}1$")
    fig.savefig(FIGURES / "lois_capitaux_arretes.pdf")
    plt.close(fig)

    fig, ax = plt.subplots()
    for k2 in K2_VALUES:
        sub = rate_df[rate_df["k2"] == k2]
        ax.plot(sub["rate"], sub["p_liquidity"], "o-", color=color_by_k2[k2], label=rf"$k_2={k2:g}$")
    ax.set_xlabel("taux r")
    ax.set_ylabel("part des décès par défaut de liquidité")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Composition des causes de défaut")
    ax.legend()
    fig.savefig(FIGURES / "causes_selon_taux.pdf")
    plt.close(fig)

    fig, ax = plt.subplots()
    positive = stationary_baseline[stationary_baseline > 0]
    bins = np.geomspace(np.quantile(positive, 0.001), np.quantile(positive, 0.999), 90)
    ax.hist(positive, bins=bins, density=True, alpha=0.55, color="#4c956c")
    k_aut = float(stationary.loc[stationary["label"] == "baseline", "K_aut"].iloc[0])
    ax.axvline(k_aut, color="black", linestyle="--", label=rf"$K_{{aut}}={k_aut:.0f}$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("capital autarcique stationnaire L")
    ax.set_ylabel("densité empirique")
    ax.set_title("Loi limite de la prêteuse après disparition de la dette")
    ax.legend()
    fig.savefig(FIGURES / "loi_stationnaire_preteuse.pdf")
    plt.close(fig)

    sensitivity = summaries[summaries["group"].isin(("gamma", "delta", "sigma"))]
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.7))
    for ax, parameter in zip(axes, ("gamma", "delta", "sigma"), strict=True):
        sub = sensitivity[sensitivity["group"] == parameter].sort_values("value")
        ax.plot(sub["value"], sub["median_T"], "o-", color="#b23a48")
        ax.set_xlabel(parameter)
        ax.set_ylabel(r"médiane de $T_B$")
        ax.set_title(f"Sensibilité à {parameter}")
    fig.savefig(FIGURES / "sensibilites_temps_defaut.pdf")
    plt.close(fig)

    pivot = rate_df.pivot(index="k2", columns="rate", values="median_T").sort_index()
    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    image = ax.imshow(
        pivot.to_numpy(), aspect="auto", origin="lower", cmap="magma",
        extent=[0, len(pivot.columns), 0, len(pivot.index)]
    )
    ax.set_xticks(np.arange(len(pivot.columns)) + 0.5)
    ax.set_xticklabels([format_float(value, 3) for value in pivot.columns], rotation=35)
    ax.set_yticks(np.arange(len(pivot.index)) + 0.5)
    ax.set_yticklabels([f"{value:g}" for value in pivot.index])
    ax.set_xlabel("taux r")
    ax.set_ylabel(r"capital initial $k_2$")
    ax.set_title(r"Médiane empirique de $T_B$ : interaction $(k_2,r)$")
    fig.colorbar(image, ax=ax, label=r"médiane de $T_B$")
    fig.savefig(FIGURES / "carte_mediane_k2_taux.pdf")
    plt.close(fig)


def format_float(value: float, digits: int = 3) -> str:
    if np.isposinf(value):
        return r"$>20\,000$"
    if not np.isfinite(value):
        return "--"
    return f"{value:.{digits}f}".replace(".", ",")


def write_tex_tables(summaries: pd.DataFrame, stationary: pd.DataFrame) -> None:
    rate = summaries[
        (summaries["group"] == "rate_k2") & (summaries["k2"] == K2_BASE)
    ].sort_values("rate")
    lines = [
        r"\begin{tabular}{rrrrrr}",
        r"\toprule",
        r"$r$ & médiane $T_B$ & $q_{90}$ & $q_{99}$ & liquidité & médiane $L_{T_B}$\\",
        r"\midrule",
    ]
    for _, row in rate.iterrows():
        lines.append(
            f"{format_float(row['rate'], 4)} & "
            f"{format_float(row['median_T'], 0)} & {format_float(row['q90_T'], 0)} & "
            f"{format_float(row['q99_T'], 0)} & {format_float(100*row['p_liquidity'], 1)}\\% & "
            f"{format_float(row['median_L_at_T'], 1)}\\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    (RESULTS / "table_taux.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    by_k2 = summaries[
        (summaries["group"] == "rate_k2") & (np.isclose(summaries["rate"], RATE0))
    ].sort_values("k2")
    lines = [
        r"\begin{tabular}{rrrrrrrr}",
        r"\toprule",
        r"$k_2$ & $q$ & médiane $T_B$ & $q_{90}$ & $q_{99}$ & liquidité & médiane $B_T^\dagger/q$ & médiane $L_{T_B}$\\",
        r"\midrule",
    ]
    for _, row in by_k2.iterrows():
        lines.append(
            f"{format_float(row['k2'], 0)} & {format_float(row['q'], 1)} & "
            f"{format_float(row['median_T'], 0)} & {format_float(row['q90_T'], 0)} & "
            f"{format_float(row['q99_T'], 0)} & {format_float(100*row['p_liquidity'], 1)}\\% & "
            f"{format_float(row['median_B_terminal_over_q'], 3)} & "
            f"{format_float(row['median_L_at_T'], 1)}\\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    (RESULTS / "table_k2.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    sensitivity = summaries[summaries["group"].isin(("gamma", "delta", "sigma"))]
    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"paramètre & valeur & médiane $T_B$ & $q_{90}$ & liquidité & médiane $B_T^\dagger/q$\\",
        r"\midrule",
    ]
    for _, row in sensitivity.sort_values(["group", "value"]).iterrows():
        lines.append(
            f"{row['group']} & {format_float(row['value'], 3)} & "
            f"{format_float(row['median_T'], 0)} & {format_float(row['q90_T'], 0)} & "
            f"{format_float(100*row['p_liquidity'], 1)}\\% & "
            f"{format_float(row['median_B_terminal_over_q'], 3)}\\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    (RESULTS / "table_sensibilites.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    lines = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"configuration & médiane & $q_{10}$ & $q_{90}$ & $q_{99}$ & KS init. & résidu moment\\",
        r"\midrule",
    ]
    for _, row in stationary.iterrows():
        lines.append(
            f"{row['label_tex']} & {format_float(row['median'], 1)} & "
            f"{format_float(row['q10'], 1)} & {format_float(row['q90'], 1)} & "
            f"{format_float(row['q99'], 1)} & {format_float(row['ks_low_vs_high_final'], 4)} & "
            f"{format_float(row['moment_identity_relative_residual'], 4)}\\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    (RESULTS / "table_stationnaire.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", type=int, default=100_000)
    parser.add_argument("--max-steps", type=int, default=20_000)
    parser.add_argument("--stationary-paths", type=int, default=40_000)
    parser.add_argument("--burn-steps", type=int, default=2_500)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--chunks-per-condition", type=int, default=16)
    args = parser.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    conditions: list[tuple[str, float, float, float, float, float, float]] = []
    for k2 in K2_VALUES:
        for rate in RATES:
            conditions.append(("rate_k2", rate, k2, GAMMA0, DELTA0, SIGMA0, rate))
    for value in (1.0 / 3.0, 0.5, 2.0 / 3.0):
        conditions.append(("gamma", value, K2_BASE, value, DELTA0, SIGMA0, RATE0))
    for value in (0.02, 0.05, 0.10):
        conditions.append(("delta", value, K2_BASE, GAMMA0, value, SIGMA0, RATE0))
    for value in (0.10, 0.25, 0.40):
        conditions.append(("sigma", value, K2_BASE, GAMMA0, DELTA0, value, RATE0))

    # Déduplique la baseline répétée dans les sensibilités tout en gardant
    # les lignes de chaque groupe pour les tableaux.
    task_by_key: dict[tuple[float, float, float, float, float], dict] = {}
    for _, _, k2, gamma, delta, sigma, rate in conditions:
        key = (k2, gamma, delta, sigma, rate)
        if key not in task_by_key:
            label = f"{k2:.12g}-{gamma:.12g}-{delta:.12g}-{sigma:.12g}-{rate:.12g}-{SCHEME}"
            task_by_key[key] = {
                "k1": K1,
                "k2": k2,
                "gamma": gamma,
                "delta": delta,
                "sigma": sigma,
                "rate": rate,
                "scheme": SCHEME,
                "max_steps": args.max_steps,
                "seed_label": label,
            }
    chunk_count = min(args.chunks_per_condition, args.paths)
    base_chunk, remainder = divmod(args.paths, chunk_count)
    stopped_tasks: list[tuple[tuple, int, dict]] = []
    for key, base_kwargs in task_by_key.items():
        seed_label = str(base_kwargs["seed_label"])
        for chunk_index in range(chunk_count):
            kwargs = {name: value for name, value in base_kwargs.items() if name != "seed_label"}
            kwargs["paths"] = base_chunk + int(chunk_index < remainder)
            kwargs["seed"] = stable_seed(args.seed, f"{seed_label}-chunk-{chunk_index}")
            stopped_tasks.append((key, chunk_index, kwargs))
    parts_by_key: dict[tuple[float, float, float, float, float], list[tuple[int, dict]]] = {
        key: [] for key in task_by_key
    }
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for key, chunk_index, result in executor.map(run_stopped_task, stopped_tasks, chunksize=1):
            parts_by_key[key].append((chunk_index, result))
    cache: dict[tuple[float, float, float, float, float], dict] = {}
    for key, indexed_parts in parts_by_key.items():
        ordered_parts = [part for _, part in sorted(indexed_parts, key=lambda item: item[0])]
        cache[key] = combine_stopped(ordered_parts)

    summary_rows: list[dict] = []
    baseline_raw: dict[float, dict] = {}
    for group, value, k2, gamma, delta, sigma, rate in conditions:
        key = (k2, gamma, delta, sigma, rate)
        result = cache[key]
        summary_rows.append(
            summarize_stopped(
                result,
                gamma=gamma,
                delta=delta,
                sigma=sigma,
                rate=rate,
                group=group,
                value=value,
                k2=k2,
                paths=args.paths,
                max_steps=args.max_steps,
            )
        )
        if group == "rate_k2" and abs(rate - RATE0) < 1e-12:
            baseline_raw[k2] = result
            np.savez_compressed(
                RESULTS / f"lois_arretees_r010_k2_{int(k2):03d}.npz",
                death_time=result["death_time"],
                lender_at_death=result["lender_at_death"],
                borrower_terminal=result["borrower_terminal"],
                cause=result["cause"],
                q=result["q"],
                lender0=result["lender0"],
                borrower0=result["borrower0"],
            )

    summaries = pd.DataFrame(summary_rows)
    summaries.to_csv(RESULTS / "resume_lois_arretees.csv", index=False)

    stationary_configs = [
        ("baseline", r"centrale", GAMMA0, DELTA0, SIGMA0),
        ("gamma_1_3", r"$\gamma=1/3$", 1.0 / 3.0, DELTA0, SIGMA0),
        ("gamma_2_3", r"$\gamma=2/3$", 2.0 / 3.0, DELTA0, SIGMA0),
        ("delta_002", r"$\delta=0{,}02$", GAMMA0, 0.02, SIGMA0),
        ("delta_010", r"$\delta=0{,}10$", GAMMA0, 0.10, SIGMA0),
        ("sigma_010", r"$\sigma=0{,}10$", GAMMA0, DELTA0, 0.10),
        ("sigma_040", r"$\sigma=0{,}40$", GAMMA0, DELTA0, 0.40),
    ]
    stationary_tasks: list[tuple[tuple, dict]] = []
    for label, label_tex, gamma, delta, sigma in stationary_configs:
        stationary_tasks.append(
            (
                (label, label_tex),
                {
                    "gamma": gamma,
                    "delta": delta,
                    "sigma": sigma,
                    "paths": args.stationary_paths,
                    "burn_steps": args.burn_steps,
                    "seed": stable_seed(args.seed, f"stationary-{label}"),
                },
            )
        )
    stationary_rows: list[dict] = []
    stationary_baseline = None
    with ProcessPoolExecutor(max_workers=min(args.workers, len(stationary_tasks))) as executor:
        for metadata, sample, row in executor.map(run_stationary_task, stationary_tasks):
            label, label_tex = metadata
            row.update({"label": label, "label_tex": label_tex})
            stationary_rows.append(row)
            if label == "baseline":
                stationary_baseline = sample
                np.savez_compressed(RESULTS / "loi_stationnaire_baseline.npz", capital=sample)
    assert stationary_baseline is not None
    stationary = pd.DataFrame(stationary_rows)
    stationary.to_csv(RESULTS / "resume_lois_stationnaires.csv", index=False)

    coupling_tasks: list[tuple[int, int, int]] = []
    for chunk_index in range(chunk_count):
        count = base_chunk + int(chunk_index < remainder)
        coupling_tasks.append(
            (count, args.max_steps, stable_seed(args.seed, f"coupling-{chunk_index}"))
        )
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        coupling_parts = list(executor.map(run_coupling_task, coupling_tasks))
    coupling = {
        key: sum(int(part[key]) for part in coupling_parts)
        for key in coupling_parts[0]
    }
    (RESULTS / "controle_couplage.json").write_text(
        json.dumps(coupling, indent=2), encoding="utf-8"
    )

    manifest = {
        "engine": "dyad-empirical-1",
        "seed": args.seed,
        "paths_per_condition": args.paths,
        "max_steps": args.max_steps,
        "stationary_paths": args.stationary_paths,
        "burn_steps": args.burn_steps,
        "workers": args.workers,
        "chunks_per_condition": chunk_count,
        "k1": K1,
        "k2_values": list(K2_VALUES),
        "baseline": {"gamma": GAMMA0, "delta": DELTA0, "sigma": SIGMA0, "rate": RATE0},
        "rates": list(RATES),
        "rate_m4_at_initial_capitals": RATE_M4,
        "scheme": SCHEME,
        "unique_stopped_conditions": len(cache),
        "stationary_conditions": len(stationary_configs),
        "coupling": coupling,
    }
    (RESULTS / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    make_figures(summaries, stationary, baseline_raw, stationary_baseline)
    write_tex_tables(summaries, stationary)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
