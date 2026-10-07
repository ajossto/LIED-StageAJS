"""Auto-tests des outils d'analyse des intérêts (scripts/interest_income.py)
sur données synthétiques : masse en zéro connue, corps+queue connus,
décomposition réseau connue. Ne teste pas le modèle économique — seulement
que l'assemblage families/tail_test/pareto_convention se comporte comme
attendu avant d'être utilisé sur de vraies données de simulation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import interest_income  # noqa: E402
from scipy import stats  # noqa: E402


def _synthetic_income(n=20_000, p0=0.4, alpha_density=2.3, x_min=5.0, seed=0):
    rng = np.random.default_rng(seed)
    is_zero = rng.random(n) < p0
    n_pos = int((~is_zero).sum())
    body = rng.lognormal(mean=np.log(2.0), sigma=0.7, size=n_pos)
    is_tail = rng.random(n_pos) < 0.08
    kappa = alpha_density - 1.0
    tail_values = stats.pareto.rvs(b=kappa, scale=x_min, size=int(is_tail.sum()), random_state=rng)
    body[is_tail] = np.maximum(body[is_tail], tail_values)
    values = np.zeros(n)
    values[~is_zero] = body
    return values


def test_zero_mass_and_positive_matches_construction() -> None:
    values = _synthetic_income(n=50_000, p0=0.35, seed=1)
    p0, positive = interest_income.zero_mass_and_positive(values)
    assert abs(p0 - 0.35) <= 0.02
    assert len(positive) == int((values > 0).sum())
    assert (positive > 0).all()


def test_fit_income_distribution_reports_identifiable_with_enough_data() -> None:
    values = _synthetic_income(n=30_000, p0=0.3, alpha_density=2.4, x_min=5.0, seed=2)
    result = interest_income.fit_income_distribution(values, min_n=100)
    assert result["identifiable"]
    assert abs(result["p0"] - 0.3) <= 0.02
    assert result["tail_powerlaw"] is not None
    alpha_hat = result["tail_powerlaw"]["alpha_density"]
    # Mélange (pas un Pareto pur) : tolérance large, on vérifie juste l'ordre
    # de grandeur et que kappa=alpha-1 est bien appliqué.
    assert 1.5 <= alpha_hat <= 4.0
    assert abs(result["tail_powerlaw"]["kappa_ccdf"] - (alpha_hat - 1.0)) <= 1e-9
    assert result["tail_fraction"] > 0.0
    assert "lognorm_2p" in result["body_ladder"]
    assert "pareto_1p" in result["body_ladder"]


def test_fit_income_distribution_flags_non_identifiable_when_too_few_points() -> None:
    values = np.array([0.0, 0.0, 1.0, 2.0, 3.0])
    result = interest_income.fit_income_distribution(values, min_n=100)
    assert not result["identifiable"]
    assert result["n_positive"] == 3


def test_decompose_tail_sources_recovers_known_structure() -> None:
    """Réseau synthétique (25 prêteuses, pour dépasser le seuil n>10 de la
    décomposition) : 20 prêteuses "hub" à haut degré (10-200) et rq faible et
    homogène, 5 prêteuses concentrées à degré 1 mais rq énorme. La
    décomposition doit montrer que le revenu N'EST PAS purement expliqué par
    le degré (corrélation modérée, pas proche de 1) et que les prêteuses
    concentrées dominent le revenu malgré un degré minimal."""
    rng = np.random.default_rng(3)
    lenders: list[int] = []
    q: list[float] = []
    r: list[float] = []

    hub_degrees = rng.integers(10, 200, size=20)
    for hub, degree in enumerate(hub_degrees):
        for _ in range(int(degree)):
            lenders.append(hub)
            q.append(rng.uniform(1.0, 2.0))
            r.append(0.01)

    concentrated_ids = range(900, 905)
    for lender_id in concentrated_ids:
        lenders.append(lender_id)
        q.append(rng.uniform(3000.0, 6000.0))
        r.append(0.02)

    network = {
        "lender": np.array(lenders, dtype=np.int64),
        "borrower": np.arange(len(lenders), dtype=np.int64),
        "q": np.array(q, dtype=float),
        "r": np.array(r, dtype=float),
    }
    result = interest_income.decompose_tail_sources(network)
    assert result["n_lenders"] == 25
    assert result["n_loans"] == len(lenders)
    assert np.isfinite(result["spearman_income_vs_deg_out"])
    # Concentration du revenu bien plus forte que celle du degré : la queue
    # des intérêts contractuels n'est pas simplement la queue du degré.
    assert result["income_contractual_gini"] > result["deg_out_gini"]
    # Corrélation revenu~degré nette (les hubs à fort degré ont plus de
    # revenu QUE LES AUTRES HUBS) mais loin de 1 : les 5 prêteuses
    # concentrées (degré=1, revenu extrême) cassent la relation monotone.
    assert result["spearman_income_vs_deg_out"] < 0.85


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
