"""Standard-library unit tests for the hand-written ridge demand model.

These tests do not touch the database: they import only the pure functions
from model_demand (split boundary, metrics, linear solver, ridge fit and
prediction clipping) so a broken model core fails here in seconds, before
anyone runs the full pipeline.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_demand import (  # noqa: E402
    TRAIN_END_DATE,
    compute_metrics,
    fit_ridge_regression,
    predict,
    solve_linear_system,
    split_rows,
)


class TestSplitRows(unittest.TestCase):
    def test_train_test_boundary(self):
        rows = [
            {"date": "2025-09-29"},
            {"date": "2025-09-30"},
            {"date": "2025-10-01"},
            {"date": "2025-10-02"},
        ]
        train, test = split_rows(rows)
        self.assertEqual(TRAIN_END_DATE, "2025-09-30")
        self.assertEqual([row["date"] for row in train], ["2025-09-29", "2025-09-30"])
        self.assertEqual([row["date"] for row in test], ["2025-10-01", "2025-10-02"])


class TestComputeMetrics(unittest.TestCase):
    def test_perfect_prediction(self):
        metrics = compute_metrics([10.0, 20.0, 30.0], [10.0, 20.0, 30.0])
        self.assertEqual(metrics["mae"], 0.0)
        self.assertEqual(metrics["rmse"], 0.0)
        self.assertEqual(metrics["wape"], 0.0)
        self.assertEqual(metrics["mape"], 0.0)
        self.assertEqual(metrics["r2"], 1.0)

    def test_known_error(self):
        metrics = compute_metrics([10.0, 20.0], [12.0, 18.0])
        self.assertEqual(metrics["mae"], 2.0)
        self.assertEqual(metrics["rmse"], 2.0)
        self.assertEqual(metrics["wape"], 0.1333)
        self.assertEqual(metrics["mape"], 0.15)
        self.assertEqual(metrics["r2"], 0.84)


class TestSolveLinearSystem(unittest.TestCase):
    def test_known_solution(self):
        solution = solve_linear_system(
            [[2.0, 1.0], [1.0, 3.0]], [5.0, 10.0]
        )
        self.assertAlmostEqual(solution[0], 1.0, places=6)
        self.assertAlmostEqual(solution[1], 3.0, places=6)


class TestFitRidgeRegression(unittest.TestCase):
    def test_recovers_known_coefficients(self):
        matrix = [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]]
        target = [1.0, 3.0, 5.0]
        coefficients = fit_ridge_regression(matrix, target, alpha=0.0)
        self.assertAlmostEqual(coefficients[0], 1.0, places=6)
        self.assertAlmostEqual(coefficients[1], 2.0, places=6)


class TestPredict(unittest.TestCase):
    def test_negative_prediction_clipped_to_zero(self):
        self.assertEqual(predict([[1.0, -5.0]], [0.0, 1.0]), [0.0])
        self.assertEqual(predict([[1.0, 2.0]], [1.0, 2.0]), [5.0])


if __name__ == "__main__":
    unittest.main()
