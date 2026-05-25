import csv
import json
import math
import sqlite3
from collections import defaultdict

from config import DB_PATH, FIGURES_DIR, REPORTS_DIR, ensure_directories
from svg_charts import write_bar_chart, write_line_chart


TRAIN_END_DATE = "2025-09-30"
RIDGE_ALPHA = 3.5

NUMERIC_FEATURES = [
    "discount_rate",
    "unit_price",
    "on_hand_units",
    "foot_traffic",
    "temperature_c",
    "precipitation_mm",
    "competitor_price_index",
    "floor_area_sqft",
    "units_lag_7",
    "units_rolling_28",
    "rolling_stockout_rate",
]

CATEGORICAL_FEATURES = [
    "region",
    "store_format",
    "category",
    "brand_tier",
    "local_event",
    "online_campaign",
    "day_of_week",
    "month",
]


def fetch_feature_rows():
    query = """
        SELECT
            date,
            store_id,
            sku_id,
            region,
            store_format,
            floor_area_sqft,
            category,
            brand_tier,
            units_sold,
            discount_rate,
            unit_price,
            stockout_flag,
            on_hand_units,
            foot_traffic,
            temperature_c,
            precipitation_mm,
            local_event,
            online_campaign,
            competitor_price_index,
            day_of_week,
            month,
            units_lag_7,
            units_rolling_28,
            rolling_stockout_rate
        FROM mart_demand_features
        ORDER BY date, store_id, sku_id
    """
    connection = sqlite3.connect(str(DB_PATH))
    connection.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in connection.execute(query)]
    finally:
        connection.close()
    return rows


def split_rows(rows):
    train = [row for row in rows if row["date"] <= TRAIN_END_DATE]
    test = [row for row in rows if row["date"] > TRAIN_END_DATE]
    return train, test


def build_preprocessor(train_rows):
    numeric_stats = {}
    for feature in NUMERIC_FEATURES:
        values = [float(row[feature]) for row in train_rows]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 1.0
        numeric_stats[feature] = (mean, std)

    category_levels = {}
    for feature in CATEGORICAL_FEATURES:
        levels = sorted({str(row[feature]) for row in train_rows})
        if len(levels) > 1:
            levels = levels[1:]
        category_levels[feature] = levels

    feature_names = ["intercept"]
    feature_names.extend(NUMERIC_FEATURES)
    for feature in CATEGORICAL_FEATURES:
        for level in category_levels[feature]:
            feature_names.append("{}={}".format(feature, level))
    return numeric_stats, category_levels, feature_names


def transform_row(row, numeric_stats, category_levels):
    values = [1.0]
    for feature in NUMERIC_FEATURES:
        mean, std = numeric_stats[feature]
        values.append((float(row[feature]) - mean) / std)
    for feature in CATEGORICAL_FEATURES:
        current = str(row[feature])
        for level in category_levels[feature]:
            values.append(1.0 if current == level else 0.0)
    return values


def build_design_matrix(rows, numeric_stats, category_levels):
    matrix = []
    target = []
    for row in rows:
        matrix.append(transform_row(row, numeric_stats, category_levels))
        target.append(float(row["units_sold"]))
    return matrix, target


def fit_ridge_regression(matrix, target, alpha):
    feature_count = len(matrix[0])
    xtx = [[0.0 for _ in range(feature_count)] for _ in range(feature_count)]
    xty = [0.0 for _ in range(feature_count)]

    for row_values, y in zip(matrix, target):
        for i in range(feature_count):
            xty[i] += row_values[i] * y
            for j in range(i, feature_count):
                xtx[i][j] += row_values[i] * row_values[j]

    for i in range(feature_count):
        for j in range(i):
            xtx[i][j] = xtx[j][i]
        if i != 0:
            xtx[i][i] += alpha

    return solve_linear_system(xtx, xty)


def solve_linear_system(matrix, vector):
    n = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot_row][col]) < 1e-12:
            augmented[pivot_row][col] = 1e-12
        if pivot_row != col:
            augmented[col], augmented[pivot_row] = augmented[pivot_row], augmented[col]
        pivot = augmented[col][col]
        for item in range(col, n + 1):
            augmented[col][item] /= pivot
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0:
                continue
            for item in range(col, n + 1):
                augmented[row][item] -= factor * augmented[col][item]
    return [augmented[row][n] for row in range(n)]


def predict(matrix, coefficients):
    predictions = []
    for row in matrix:
        predictions.append(sum(value * coef for value, coef in zip(row, coefficients)))
    return [max(0.0, value) for value in predictions]


def compute_metrics(actual, predicted):
    n = len(actual)
    errors = [predicted_value - actual_value for actual_value, predicted_value in zip(actual, predicted)]
    abs_errors = [abs(error) for error in errors]
    squared_errors = [error ** 2 for error in errors]
    actual_mean = sum(actual) / n
    sst = sum((value - actual_mean) ** 2 for value in actual)
    sse = sum(squared_errors)
    nonzero_pairs = [(actual_value, pred_value) for actual_value, pred_value in zip(actual, predicted) if actual_value != 0]
    mape = None
    if nonzero_pairs:
        mape = sum(abs(pred_value - actual_value) / actual_value for actual_value, pred_value in nonzero_pairs) / len(nonzero_pairs)
    return {
        "mae": round(sum(abs_errors) / n, 4),
        "rmse": round(math.sqrt(sum(squared_errors) / n), 4),
        "wape": round(sum(abs_errors) / max(1.0, sum(actual)), 4),
        "mape": round(mape, 4) if mape is not None else None,
        "r2": round(1 - sse / sst, 4) if sst > 0 else None,
    }


def write_forecast_sample(rows, actual, predicted, path, limit=600):
    fieldnames = [
        "date",
        "store_id",
        "sku_id",
        "category",
        "actual_units",
        "predicted_units",
        "absolute_error",
        "rolling_28_baseline",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row, actual_value, predicted_value in list(zip(rows, actual, predicted))[:limit]:
            writer.writerow(
                {
                    "date": row["date"],
                    "store_id": row["store_id"],
                    "sku_id": row["sku_id"],
                    "category": row["category"],
                    "actual_units": int(actual_value),
                    "predicted_units": round(predicted_value, 3),
                    "absolute_error": round(abs(predicted_value - actual_value), 3),
                    "rolling_28_baseline": round(float(row["units_rolling_28"]), 3),
                }
            )


def aggregate_monthly(rows, predictions):
    monthly = defaultdict(lambda: [0.0, 0.0])
    for row, predicted in zip(rows, predictions):
        month = row["date"][:7]
        monthly[month][0] += float(row["units_sold"])
        monthly[month][1] += predicted
    months = sorted(monthly)
    return months, [monthly[month][0] for month in months], [monthly[month][1] for month in months]


def error_by_category(rows, actual, predicted):
    category_errors = defaultdict(lambda: [0.0, 0])
    for row, actual_value, predicted_value in zip(rows, actual, predicted):
        category_errors[row["category"]][0] += abs(predicted_value - actual_value)
        category_errors[row["category"]][1] += 1
    labels = []
    values = []
    for category, (total_error, count) in sorted(category_errors.items()):
        labels.append(category)
        values.append(total_error / count)
    return labels, values


def main():
    ensure_directories()
    rows = fetch_feature_rows()
    train_rows, test_rows = split_rows(rows)
    numeric_stats, category_levels, feature_names = build_preprocessor(train_rows)
    train_matrix, train_target = build_design_matrix(train_rows, numeric_stats, category_levels)
    test_matrix, test_target = build_design_matrix(test_rows, numeric_stats, category_levels)
    coefficients = fit_ridge_regression(train_matrix, train_target, RIDGE_ALPHA)
    train_predictions = predict(train_matrix, coefficients)
    test_predictions = predict(test_matrix, coefficients)
    baseline_predictions = [max(0.0, float(row["units_rolling_28"])) for row in test_rows]

    metrics = {
        "training_rows": len(train_rows),
        "test_rows": len(test_rows),
        "feature_count": len(feature_names),
        "train_end_date": TRAIN_END_DATE,
        "model": "Ridge regression implemented with Python standard library",
        "ridge_alpha": RIDGE_ALPHA,
        "train_metrics": compute_metrics(train_target, train_predictions),
        "test_metrics": compute_metrics(test_target, test_predictions),
        "rolling_28_baseline_test_metrics": compute_metrics(test_target, baseline_predictions),
    }
    metrics_path = REPORTS_DIR / "model_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    write_forecast_sample(test_rows, test_target, test_predictions, REPORTS_DIR / "forecast_sample.csv")

    months, actual_monthly, predicted_monthly = aggregate_monthly(test_rows, test_predictions)
    write_line_chart(
        FIGURES_DIR / "actual_vs_predicted.svg",
        "Actual vs Predicted Demand",
        months,
        [
            {"name": "Actual Units", "values": actual_monthly, "color": "#2563eb"},
            {"name": "Predicted Units", "values": predicted_monthly, "color": "#dc2626"},
        ],
        y_label="Monthly units in test window",
    )

    labels, values = error_by_category(test_rows, test_target, test_predictions)
    write_bar_chart(
        FIGURES_DIR / "forecast_error_by_category.svg",
        "Mean Absolute Error by Category",
        labels,
        values,
        y_label="MAE in units",
    )

    print("Trained demand model with {} features".format(len(feature_names)))
    print("Test MAE: {}".format(metrics["test_metrics"]["mae"]))
    print("Baseline MAE: {}".format(metrics["rolling_28_baseline_test_metrics"]["mae"]))


if __name__ == "__main__":
    main()

