"""Optional comparison of the hand-written ridge model against scikit-learn.

This script is intentionally separate from the core pipeline: the pipeline
itself (``run_pipeline.py`` / ``model_demand.py``) runs with the Python
standard library only. This script is a benchmark that answers one question:
is the hand-written ridge regression actually good, or does it only look good
next to the rolling-28 baseline?

It reuses the core pipeline's data loading, time-based split, feature
engineering and metric functions, so every model is scored on the same
features and the same test window:

- Training window: observations up to 2025-09-30
- Test window: observations after 2025-09-30
- Features: the same 52 columns the hand-written model uses
- Metrics: MAE, RMSE, WAPE, MAPE and R2 from ``model_demand.compute_metrics``

Models compared:

- ``handwritten_ridge``: the standard-library ridge regression from
  ``model_demand.py`` (alpha 3.5, intercept not penalised).
- ``sklearn_ridge``: ``sklearn.linear_model.Ridge`` with the same alpha
  (3.5). The intercept column is dropped before fitting because sklearn
  fits its own intercept; everything else is identical.
- ``sklearn_random_forest``: ``sklearn.ensemble.RandomForestRegressor``
  (100 trees, ``max_features="sqrt"``, fixed seed) as a non-linear reference.
- ``rolling_28_baseline``: the previous 28-day rolling demand, the baseline
  the pipeline already reports.

All predictions are clipped at zero before scoring, the same rule the
hand-written ``predict`` applies (demand cannot be negative).

Requires scikit-learn (optional dependency)::

    pip install scikit-learn
    python src/compare_sklearn.py

Results are written to ``outputs/reports/sklearn_comparison.json`` and a
comparison table is printed to stdout.
"""

import json
import sys

from config import REPORTS_DIR, ensure_directories
from model_demand import (
    RIDGE_ALPHA,
    TRAIN_END_DATE,
    build_design_matrix,
    build_preprocessor,
    compute_metrics,
    fetch_feature_rows,
    fit_ridge_regression,
    predict,
    split_rows,
)

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge
except ImportError:
    print("scikit-learn is required for this optional comparison.")
    print("Install it with: pip install scikit-learn")
    sys.exit(1)

RANDOM_FOREST_TREES = 100
RANDOM_FOREST_SEED = 42


def clip_non_negative(values):
    return [max(0.0, float(value)) for value in values]


def main():
    ensure_directories()
    rows = fetch_feature_rows()
    train_rows, test_rows = split_rows(rows)
    numeric_stats, category_levels, feature_names = build_preprocessor(train_rows)
    train_matrix, train_target = build_design_matrix(train_rows, numeric_stats, category_levels)
    test_matrix, test_target = build_design_matrix(test_rows, numeric_stats, category_levels)

    # The design matrix's first column is the intercept (all ones). The
    # hand-written model keeps it and does not penalise it; sklearn fits its
    # own intercept, so the column is dropped for the sklearn models.
    sklearn_train = [row[1:] for row in train_matrix]
    sklearn_test = [row[1:] for row in test_matrix]

    results = {}

    coefficients = fit_ridge_regression(train_matrix, train_target, RIDGE_ALPHA)
    results["handwritten_ridge"] = compute_metrics(
        test_target, predict(test_matrix, coefficients)
    )

    ridge = Ridge(alpha=RIDGE_ALPHA)
    ridge.fit(sklearn_train, train_target)
    results["sklearn_ridge"] = compute_metrics(
        test_target, clip_non_negative(ridge.predict(sklearn_test))
    )

    forest = RandomForestRegressor(
        n_estimators=RANDOM_FOREST_TREES,
        max_features="sqrt",
        random_state=RANDOM_FOREST_SEED,
        n_jobs=-1,
    )
    forest.fit(sklearn_train, train_target)
    results["sklearn_random_forest"] = compute_metrics(
        test_target, clip_non_negative(forest.predict(sklearn_test))
    )

    baseline_predictions = [
        max(0.0, float(row["units_rolling_28"])) for row in test_rows
    ]
    results["rolling_28_baseline"] = compute_metrics(
        test_target, baseline_predictions
    )

    report = {
        "train_end_date": TRAIN_END_DATE,
        "training_rows": len(train_rows),
        "test_rows": len(test_rows),
        "feature_count": len(feature_names),
        "ridge_alpha": RIDGE_ALPHA,
        "random_forest": {
            "n_estimators": RANDOM_FOREST_TREES,
            "max_features": "sqrt",
            "random_state": RANDOM_FOREST_SEED,
        },
        "test_metrics": results,
    }
    report_path = REPORTS_DIR / "sklearn_comparison.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )

    print("Test rows: {}".format(len(test_rows)))
    print("Features: {}".format(len(feature_names)))
    print()
    print("{:<24} {:>8} {:>8} {:>8} {:>8}".format("Model", "MAE", "RMSE", "WAPE", "R2"))
    for name in (
        "handwritten_ridge",
        "sklearn_ridge",
        "sklearn_random_forest",
        "rolling_28_baseline",
    ):
        metrics = results[name]
        print(
            "{:<24} {:>8} {:>8} {:>8} {:>8}".format(
                name,
                metrics["mae"],
                metrics["rmse"],
                metrics["wape"],
                metrics["r2"],
            )
        )
    print()
    print("Wrote {}".format(report_path))


if __name__ == "__main__":
    main()
