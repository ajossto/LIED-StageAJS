import unittest

import numpy as np

from m2.analysis import (
    cohort_diagnostics,
    compare_pareto_lognormal,
    fit_body_distributions,
    fit_pareto_tail,
    increment_diagnostics,
    top_decile_turnover,
)


class AnalysisTests(unittest.TestCase):
    def test_exponential_synthetic_body_is_identified(self):
        rng = np.random.default_rng(1)
        values = rng.exponential(4.0, size=4_000)
        result = fit_body_distributions(values, body_quantile=0.95)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["best_aic"], "exponential")
        self.assertAlmostEqual(result["median_mean_ratio"], np.log(2), delta=0.08)

    def test_pareto_synthetic_tail_recovers_pdf_exponent(self):
        rng = np.random.default_rng(2)
        values = 5.0 * (1 + rng.pareto(2.0, size=5_000))
        result = fit_pareto_tail(values)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["alpha"], 3.0, delta=0.2)
        comparison = compare_pareto_lognormal(values, result["xmin"], result["alpha"])
        self.assertIsNotNone(comparison)

    def test_small_tail_is_not_fitted(self):
        self.assertIsNone(fit_pareto_tail([1, 2, 3]))

    def test_increment_convention(self):
        rows = [
            {"nw": 10.0 + delta, "nw_delta": delta}
            for delta in np.linspace(-2.0, 1.0, 100)
        ]
        result = increment_diagnostics(rows)
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["A0"], 0)
        self.assertGreater(result["B0"], 0)

    def test_cohort_and_turnover_diagnostics(self):
        rows_a = [
            {"entity_id": i, "nw": float(i + 1), "age": float(i % 20), "step": 100}
            for i in range(100)
        ]
        rows_b = [
            {
                "entity_id": i,
                "nw": float(101 - i),
                "age": float(i % 20 + 10),
                "step": 200,
            }
            for i in range(50, 150)
        ]
        cohort = cohort_diagnostics(rows_a)
        turnover = top_decile_turnover(rows_a, rows_b)
        self.assertEqual(cohort["status"], "ok")
        self.assertEqual(len(cohort["age_by_decile"]), 10)
        self.assertGreater(turnover["turnover"], 0)


if __name__ == "__main__":
    unittest.main()
