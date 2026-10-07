from __future__ import annotations

import math
import warnings
from collections import defaultdict
from typing import Iterable, Sequence

import numpy as np
from scipy import optimize, stats


def _positive_finite(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=float)
    return array[np.isfinite(array) & (array > 0)]


def _information_criteria(
    log_likelihood: float, parameters: int, n: int
) -> tuple[float, float]:
    return (
        2 * parameters - 2 * log_likelihood,
        parameters * math.log(n) - 2 * log_likelihood,
    )


def _fit_right_truncated(
    body: np.ndarray,
    cutoff: float,
    name: str,
    parameter_count: int,
    initial: Sequence[float],
    unpack,
) -> dict | None:
    def objective(raw: np.ndarray) -> float:
        if not np.all(np.isfinite(raw)) or np.any(np.abs(raw) > 100):
            return 1e300
        try:
            distribution, params = unpack(raw)
        except (OverflowError, ValueError):
            return 1e300
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            log_pdf = distribution.logpdf(body, *params)
            log_normalizer = distribution.logcdf(cutoff, *params)
        if not np.all(np.isfinite(log_pdf)) or not np.isfinite(log_normalizer):
            return 1e300
        value = -(float(np.sum(log_pdf)) - len(body) * float(log_normalizer))
        return value if math.isfinite(value) else 1e300

    result = optimize.minimize(objective, np.asarray(initial), method="Nelder-Mead")
    if not result.success and not math.isfinite(float(result.fun)):
        return None
    try:
        distribution, params = unpack(result.x)
    except (OverflowError, ValueError):
        return None
    log_likelihood = -float(objective(result.x))
    if not math.isfinite(log_likelihood):
        return None
    aic, bic = _information_criteria(log_likelihood, parameter_count, len(body))
    return {
        "name": name,
        "parameters": [float(x) for x in params],
        "k": parameter_count,
        "log_likelihood": log_likelihood,
        "aic": aic,
        "bic": bic,
        "right_truncated": True,
        "cutoff": cutoff,
    }


def fit_body_distributions(
    values: Iterable[float], body_quantile: float = 0.95, min_n: int = 50
) -> dict:
    values_array = _positive_finite(values)
    if len(values_array) < min_n:
        return {"status": "insufficient_data", "n": int(len(values_array))}
    if not 0 < body_quantile < 1:
        raise ValueError("body_quantile doit appartenir à ]0,1[")
    cutoff = float(np.quantile(values_array, body_quantile))
    body = values_array[values_array <= cutoff]
    scale0 = max(float(np.mean(body)), np.finfo(float).tiny)
    median0 = max(float(np.median(body)), np.finfo(float).tiny)

    fits: list[dict] = []
    candidates = [
        (
            "exponential",
            1,
            [math.log(scale0)],
            lambda z: (stats.expon, (0.0, math.exp(float(z[0])))),
        ),
        (
            "gamma",
            2,
            [0.0, math.log(scale0)],
            lambda z: (
                stats.gamma,
                (math.exp(float(z[0])), 0.0, math.exp(float(z[1]))),
            ),
        ),
        (
            "lognormal",
            2,
            [math.log(max(float(np.std(np.log(body))), 0.1)), math.log(median0)],
            lambda z: (
                stats.lognorm,
                (math.exp(float(z[0])), 0.0, math.exp(float(z[1]))),
            ),
        ),
        (
            "fisk",
            2,
            [0.0, math.log(median0)],
            lambda z: (
                stats.fisk,
                (math.exp(float(z[0])), 0.0, math.exp(float(z[1]))),
            ),
        ),
    ]
    for name, k, initial, unpack in candidates:
        fit = _fit_right_truncated(body, cutoff, name, k, initial, unpack)
        if fit is not None:
            fits.append(fit)
    fits.sort(key=lambda item: item["aic"])
    for fit in fits:
        fit["delta_aic"] = fit["aic"] - fits[0]["aic"]
        fit["delta_bic"] = fit["bic"] - min(item["bic"] for item in fits)
    return {
        "status": "ok",
        "n_total": int(len(values_array)),
        "n_body": int(len(body)),
        "body_quantile": body_quantile,
        "cutoff": cutoff,
        "median": float(np.median(body)),
        "mean": float(np.mean(body)),
        "median_mean_ratio": float(np.median(body) / np.mean(body)),
        "fits": fits,
        "best_aic": fits[0]["name"] if fits else None,
    }


def fit_pareto_tail(
    values: Iterable[float], min_tail: int = 100, n_candidates: int = 80
) -> dict | None:
    array = np.sort(_positive_finite(values))
    if len(array) < 2 * min_tail:
        return None
    candidates = np.unique(np.quantile(array, np.linspace(0, 0.95, n_candidates)))
    best: dict | None = None
    for xmin in candidates:
        tail = array[array >= xmin]
        if len(tail) < min_tail:
            continue
        denominator = float(np.sum(np.log(tail / xmin)))
        if denominator <= 0:
            continue
        alpha = 1.0 + len(tail) / denominator
        ordered = np.sort(tail)
        empirical = np.arange(1, len(tail) + 1) / len(tail)
        fitted = 1.0 - (ordered / xmin) ** (-(alpha - 1.0))
        ks = float(np.max(np.abs(empirical - fitted)))
        candidate = {
            "xmin": float(xmin),
            "alpha": float(alpha),
            "ks": ks,
            "n_tail": int(len(tail)),
            "n_total": int(len(array)),
        }
        if best is None or candidate["ks"] < best["ks"]:
            best = candidate
    return best


def fit_pareto_at_xmin(
    values: Iterable[float], xmin: float, min_tail: int = 30
) -> dict | None:
    array = _positive_finite(values)
    tail = array[array >= xmin]
    if len(tail) < min_tail:
        return None
    denominator = float(np.sum(np.log(tail / xmin)))
    if denominator <= 0:
        return None
    alpha = 1.0 + len(tail) / denominator
    return {
        "xmin": float(xmin),
        "alpha": float(alpha),
        "n_tail": int(len(tail)),
        "n_total": int(len(array)),
    }


def compare_pareto_lognormal(
    values: Iterable[float], xmin: float, alpha: float
) -> dict | None:
    array = _positive_finite(values)
    tail = array[array >= xmin]
    if len(tail) < 30:
        return None
    log_tail = np.log(tail)
    lower = math.log(xmin)

    def lognormal_nll(raw: np.ndarray) -> float:
        mu = float(raw[0])
        sigma = math.exp(float(raw[1]))
        z = (log_tail - mu) / sigma
        lower_z = (lower - mu) / sigma
        log_survival = stats.norm.logsf(lower_z)
        ll = -log_tail - math.log(sigma) + stats.norm.logpdf(z) - log_survival
        if not np.all(np.isfinite(ll)):
            return 1e300
        return -float(np.sum(ll))

    initial = [float(np.mean(log_tail)), math.log(max(float(np.std(log_tail)), 0.1))]
    result = optimize.minimize(lognormal_nll, initial, method="Nelder-Mead")
    if not math.isfinite(float(result.fun)):
        return None
    mu = float(result.x[0])
    sigma = math.exp(float(result.x[1]))
    z = (log_tail - mu) / sigma
    log_survival = stats.norm.logsf((lower - mu) / sigma)
    ll_lognormal = -log_tail - math.log(sigma) + stats.norm.logpdf(z) - log_survival
    pareto_shape = alpha - 1.0
    ll_pareto = (
        math.log(pareto_shape) + pareto_shape * math.log(xmin) - alpha * np.log(tail)
    )
    differences = ll_pareto - ll_lognormal
    ratio = float(np.sum(differences))
    sd = float(np.std(differences, ddof=1)) if len(differences) > 1 else math.nan
    if sd > 0 and math.isfinite(sd):
        z_score = ratio / (sd * math.sqrt(len(differences)))
        p_value = float(2 * stats.norm.sf(abs(z_score)))
    else:
        z_score = math.nan
        p_value = math.nan
    return {
        "log_likelihood_ratio_pareto_minus_lognormal": ratio,
        "z": float(z_score),
        "p": p_value,
        "n_tail": int(len(tail)),
        "lognormal_mu": mu,
        "lognormal_sigma": sigma,
        "lognormal_is_left_truncated": True,
    }


def block_bootstrap_tail(
    rows: Sequence[dict],
    variable: str,
    rng: np.random.Generator,
    repetitions: int = 100,
    xmin: float | None = None,
    min_tail: int = 100,
) -> dict:
    by_step: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        value = float(row[variable])
        if math.isfinite(value) and value > 0:
            by_step[int(row["step"])].append(value)
    steps = sorted(by_step)
    estimates: list[float] = []
    if len(steps) < 2:
        return {"status": "insufficient_blocks", "blocks": len(steps)}
    for _ in range(repetitions):
        sampled_steps = rng.choice(steps, size=len(steps), replace=True)
        sample = [value for step in sampled_steps for value in by_step[int(step)]]
        fit = (
            fit_pareto_tail(sample, min_tail=min_tail)
            if xmin is None
            else fit_pareto_at_xmin(sample, xmin, min_tail=min_tail)
        )
        if fit is not None:
            estimates.append(float(fit["alpha"]))
    if not estimates:
        return {"status": "failed", "blocks": len(steps)}
    return {
        "status": "ok",
        "blocks": len(steps),
        "successful_repetitions": len(estimates),
        "alpha_median": float(np.median(estimates)),
        "alpha_ci_025": float(np.quantile(estimates, 0.025)),
        "alpha_ci_975": float(np.quantile(estimates, 0.975)),
    }


def increment_diagnostics(rows: Sequence[dict], body_quantile: float = 0.95) -> dict:
    starts: list[float] = []
    deltas: list[float] = []
    for row in rows:
        nw = float(row["nw"])
        delta = float(row["nw_delta"])
        start = nw - delta
        if math.isfinite(start) and math.isfinite(delta) and start > 0:
            starts.append(start)
            deltas.append(delta)
    if len(starts) < 30:
        return {"status": "insufficient_data", "n": len(starts)}
    starts_array = np.asarray(starts)
    deltas_array = np.asarray(deltas)
    cutoff = float(np.quantile(starts_array, body_quantile))
    selected = deltas_array[starts_array <= cutoff]
    drift = float(np.mean(selected))
    a0 = -drift
    b0 = 0.5 * float(np.var(selected, ddof=1))
    return {
        "status": "ok",
        "n": int(len(selected)),
        "body_start_cutoff": cutoff,
        "mean_increment": drift,
        "A0": a0,
        "B0": b0,
        "B0_over_A0": b0 / a0 if a0 > 0 else None,
        "survivors_only": True,
    }


def cohort_diagnostics(rows: Sequence[dict], recent_horizon: int = 100) -> dict:
    positive = [row for row in rows if float(row["nw"]) > 0]
    if len(positive) < 20:
        return {"status": "insufficient_data", "n": len(positive)}
    nw = np.asarray([float(row["nw"]) for row in positive])
    ages = np.asarray([float(row["age"]) for row in positive])
    log_nw = np.log(nw)
    pearson = (
        float(stats.pearsonr(ages, log_nw).statistic) if np.std(ages) > 0 else math.nan
    )
    spearman = (
        float(stats.spearmanr(ages, log_nw).statistic) if np.std(ages) > 0 else math.nan
    )
    boundaries = np.quantile(nw, np.linspace(0, 1, 11))
    age_by_decile = []
    for decile in range(10):
        if decile == 9:
            mask = (nw >= boundaries[decile]) & (nw <= boundaries[decile + 1])
        else:
            mask = (nw >= boundaries[decile]) & (nw < boundaries[decile + 1])
        selected = ages[mask]
        age_by_decile.append(
            {
                "decile": decile + 1,
                "n": int(len(selected)),
                "age_median": float(np.median(selected)) if len(selected) else math.nan,
                "age_q10": (
                    float(np.quantile(selected, 0.1)) if len(selected) else math.nan
                ),
                "age_q90": (
                    float(np.quantile(selected, 0.9)) if len(selected) else math.nan
                ),
            }
        )
    top_cutoff = float(np.quantile(nw, 0.9))
    top_rows = [row for row in positive if float(row["nw"]) >= top_cutoff]
    recent_fraction = float(
        np.mean([float(row["age"]) <= recent_horizon for row in top_rows])
    )
    return {
        "status": "ok",
        "n": len(positive),
        "pearson_age_log_nw": pearson,
        "spearman_age_log_nw": spearman,
        "top_decile_cutoff": top_cutoff,
        "top_recent_fraction": recent_fraction,
        "recent_horizon": recent_horizon,
        "age_by_decile": age_by_decile,
    }


def top_decile_turnover(rows_a: Sequence[dict], rows_b: Sequence[dict]) -> dict:
    def top_ids(rows: Sequence[dict]) -> set[int]:
        positive = [row for row in rows if float(row["nw"]) > 0]
        if not positive:
            return set()
        cutoff = float(np.quantile([float(row["nw"]) for row in positive], 0.9))
        return {int(row["entity_id"]) for row in positive if float(row["nw"]) >= cutoff}

    first = top_ids(rows_a)
    second = top_ids(rows_b)
    union = first | second
    intersection = first & second
    return {
        "top_a": len(first),
        "top_b": len(second),
        "survivors_from_top_a": len(intersection),
        "retention_fraction": len(intersection) / len(first) if first else None,
        "jaccard": len(intersection) / len(union) if union else None,
        "turnover": 1 - len(intersection) / len(union) if union else None,
    }
