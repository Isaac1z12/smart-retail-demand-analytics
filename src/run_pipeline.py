import os

from build_database import main as build_database
from generate_data import main as generate_data
from load_favorita import main as load_favorita
from model_demand import main as model_demand
from run_sql_analysis import main as run_sql_analysis


DATA_SOURCE = os.environ.get("RETAIL_DATA_SOURCE", "favorita").strip().lower()


def main():
    if DATA_SOURCE == "synthetic":
        print("Step 1/4: generating synthetic retail data (RETAIL_DATA_SOURCE=synthetic)")
        generate_data()
    elif DATA_SOURCE == "favorita":
        print("Step 1/4: loading Favorita grocery sales subset (default; set RETAIL_DATA_SOURCE=synthetic for synthetic data)")
        load_favorita()
    else:
        raise ValueError(
            "Unknown RETAIL_DATA_SOURCE {!r}: use 'favorita' or 'synthetic'".format(DATA_SOURCE)
        )
    print("Step 2/4: building SQLite database and feature mart")
    build_database()
    print("Step 3/4: exporting SQL analysis reports")
    run_sql_analysis()
    print("Step 4/4: training demand forecasting model")
    model_demand()
    print("Pipeline complete")


if __name__ == "__main__":
    main()
