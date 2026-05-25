from build_database import main as build_database
from generate_data import main as generate_data
from model_demand import main as model_demand
from run_sql_analysis import main as run_sql_analysis


def main():
    print("Step 1/4: generating synthetic retail data")
    generate_data()
    print("Step 2/4: building SQLite database and feature mart")
    build_database()
    print("Step 3/4: exporting SQL analysis reports")
    run_sql_analysis()
    print("Step 4/4: training demand forecasting model")
    model_demand()
    print("Pipeline complete")


if __name__ == "__main__":
    main()

