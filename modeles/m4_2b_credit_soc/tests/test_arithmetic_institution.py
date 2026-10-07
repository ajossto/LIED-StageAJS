"""Comparaison automatique, sur grille (K_ℓ,K_b), du principal arithmétique
M4.2B au principal géométrique M4.2 (PROMPT_M4_2B.md §2, dernier
paragraphe). Produit aussi le tableau utilisé dans le rapport (§12 :
quantifier ce que l'institution arithmétique modifie à taux identique)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from m4_2b.model import _pair_principal, _pair_rate  # noqa: E402

GRID_RATIOS = (1.001, 1.01, 1.1, 1.5, 2.0, 5.0, 10.0, 100.0, 392.04)  # 392.04 ≈ K*_aut(0.5)/K0
GRID_BORROWER_K = (0.01, 1.0, 25.0, 100.0, 9801.0)
GAMMAS = (1.0 / 3.0, 0.5, 2.0 / 3.0)


def test_ratio_formula_q_arithmetic_over_q_geometric() -> None:
    """q_A/q_geo = (1+√(K_ℓ/K_b))/2 exactement, pour tout γ, A.

    Preuve : q_geo=√K_b(√K_ℓ-√K_b) (le bras de l'emprunteuse borne toujours,
    car target=√(K_ℓK_b)<K_ℓ implique K_ℓ-target>target-K_b dès que K_ℓ>K_b) ;
    q_A=(K_ℓ-K_b)/2=(√K_ℓ-√K_b)(√K_ℓ+√K_b)/2. Le rapport se simplifie en
    (√K_ℓ+√K_b)/(2√K_b) = (1+√(K_ℓ/K_b))/2, indépendant de γ et A."""
    for A in (1.0, 0.375, 2.668):
        for gamma in GAMMAS:
            for Kb in GRID_BORROWER_K:
                for ratio in GRID_RATIOS:
                    Kl = Kb * ratio
                    if Kl <= Kb:
                        continue
                    rate = _pair_rate(Kl, Kb, gamma, A)
                    q_geo = _pair_principal(Kl, Kb, rate, gamma, A, "geometric")
                    q_arith = _pair_principal(Kl, Kb, rate, gamma, A, "arithmetic")
                    assert q_geo > 0, (Kl, Kb, gamma, A)
                    observed_ratio = q_arith / q_geo
                    predicted_ratio = 0.5 * (1.0 + math.sqrt(Kl / Kb))
                    assert abs(observed_ratio - predicted_ratio) <= 1e-9 * predicted_ratio, (
                        gamma, A, Kl, Kb, observed_ratio, predicted_ratio,
                    )
                    # Fait structurel central du rapport (§2, §3) : q_A >= q_geo
                    # toujours, et sans borne quand K_ℓ/K_b croît (pas de plafond).
                    assert q_arith >= q_geo - 1e-12


def test_borrower_arm_always_binds_under_geometric_rule() -> None:
    """Sous la règle géométrique, seul le bras de l'emprunteuse atteint la
    cible (K_ℓ-target > target-K_b strictement dès que K_ℓ>K_b) : l'écart
    entre les deux institutions n'est donc pas un artefact du min(...)."""
    for gamma in GAMMAS:
        for Kb in GRID_BORROWER_K:
            for ratio in GRID_RATIOS:
                Kl = Kb * ratio
                if Kl <= Kb:
                    continue
                rate = _pair_rate(Kl, Kb, gamma, 1.0)
                target = math.sqrt(Kl * Kb)
                lender_arm = Kl - target
                borrower_arm = target - Kb
                assert borrower_arm < lender_arm, (gamma, Kl, Kb, lender_arm, borrower_arm)
                q_geo = _pair_principal(Kl, Kb, rate, gamma, 1.0, "geometric")
                assert abs(q_geo - borrower_arm) <= 1e-9 * max(1.0, borrower_arm)


def build_comparison_table() -> list[dict]:
    """Table (K_ℓ,K_b,γ) -> (r,q_geo,q_arith,ratio) pour le rapport."""
    rows = []
    for gamma in GAMMAS:
        for Kb in GRID_BORROWER_K:
            for ratio in GRID_RATIOS:
                Kl = Kb * ratio
                if Kl <= Kb:
                    continue
                rate = _pair_rate(Kl, Kb, gamma, 1.0)
                q_geo = _pair_principal(Kl, Kb, rate, gamma, 1.0, "geometric")
                q_arith = _pair_principal(Kl, Kb, rate, gamma, 1.0, "arithmetic")
                rows.append(
                    {
                        "gamma": gamma, "Kl": Kl, "Kb": Kb, "ratio_KlKb": ratio,
                        "rate": rate, "q_geometric": q_geo, "q_arithmetic": q_arith,
                        "q_ratio": q_arith / q_geo,
                    }
                )
    return rows


def test_comparison_table_is_buildable_and_monotone_in_ratio() -> None:
    rows = build_comparison_table()
    assert len(rows) > 0
    by_gamma_kb: dict[tuple[float, float], list[dict]] = {}
    for row in rows:
        by_gamma_kb.setdefault((row["gamma"], row["Kb"]), []).append(row)
    for group in by_gamma_kb.values():
        group.sort(key=lambda row: row["ratio_KlKb"])
        ratios = [row["q_ratio"] for row in group]
        assert all(b >= a - 1e-12 for a, b in zip(ratios, ratios[1:])), ratios


def main() -> None:
    tests = sorted(name for name in globals() if name.startswith("test_"))
    for name in tests:
        globals()[name]()
        print(f"OK {name}")
    print(f"{len(tests)} tests OK")


if __name__ == "__main__":
    main()
