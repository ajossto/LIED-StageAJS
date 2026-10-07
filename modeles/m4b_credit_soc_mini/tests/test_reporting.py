"""Contrôles rapides des statistiques et du manifeste de figures M4B."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


PATH = (
    Path(__file__).resolve().parents[2]
    / "adaptateurs/m4b_credit_soc_mini/reporting.py"
)
SPEC = importlib.util.spec_from_file_location("m4b_reporting_tests", PATH)
REPORTING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORTING)


def test_selected_manifest() -> None:
    assert len(REPORTING.SELECTED_FAMILIES) == 28
    assert len(set(REPORTING.SELECTED_FAMILIES)) == 28
    assert set(REPORTING.SELECTED_FAMILIES) == {
        "R01", "R02", "R03", "R05", "R06", "R07", "R08", "R09",
        "R10", "R11", "R12", "R14", "R15", "R17", "R18", "R19",
        "R20", "S06", "S08", "S10", "S11", "L02", "L04", "L12",
        "L13", "L14", "L15", "Y03",
    }


def test_adaptive_histogram_conserves_probability() -> None:
    values = np.repeat(np.arange(2, 50), np.arange(1, 49))
    edges, centres, counts, density, lower, upper = REPORTING.adaptive_hist(
        values, integer=True
    )
    assert np.all(np.diff(edges) > 0)
    assert counts.sum() == len(values)
    assert abs(float(np.sum(density * np.diff(edges))) - 1.0) < 1e-12
    assert np.all((lower <= density) & (density <= upper))
    assert np.all((edges[:-1] < centres) & (centres < edges[1:]))


def test_gini_and_lorenz_equal_population() -> None:
    values = np.ones(100)
    assert REPORTING.gini(values) == 0.0
    population, share, value = REPORTING.lorenz(values)
    assert value == 0.0
    assert (population[0], share[0]) == (0.0, 0.0)
    assert (population[-1], share[-1]) == (1.0, 1.0)
    assert np.all(np.diff(share) >= 0)


def test_cutoff_powerlaw_fit_is_finite() -> None:
    rng = np.random.default_rng(4)
    support = np.arange(2, 150)
    probability = support ** -1.4 * np.exp(-support / 35)
    sample = rng.choice(support, 2_000, p=probability / probability.sum())
    fit = REPORTING.fit_cutoff_powerlaw(sample)
    assert fit is not None
    assert np.isfinite(fit["alpha"]) and fit["alpha"] > 0
    assert np.isfinite(fit["cutoff"]) and fit["cutoff"] > 0


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
