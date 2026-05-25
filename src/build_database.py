import csv
import sqlite3

from config import DB_PATH, RAW_DATA_DIR, SQL_DIR, ensure_directories


def read_sql(filename):
    with (SQL_DIR / filename).open("r", encoding="utf-8") as handle:
        return handle.read()


def insert_csv(connection, table_name, csv_path):
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        return 0
    columns = reader.fieldnames
    placeholders = ", ".join(["?"] * len(columns))
    column_list = ", ".join(columns)
    sql = "INSERT INTO {} ({}) VALUES ({})".format(table_name, column_list, placeholders)
    values = [[row[column] for column in columns] for row in rows]
    connection.executemany(sql, values)
    return len(rows)


def main():
    ensure_directories()
    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = sqlite3.connect(str(DB_PATH))
    try:
        connection.executescript(read_sql("00_schema.sql"))
        counts = {
            "dim_store": insert_csv(connection, "dim_store", RAW_DATA_DIR / "dim_store.csv"),
            "dim_product": insert_csv(connection, "dim_product", RAW_DATA_DIR / "dim_product.csv"),
            "fact_daily_sales": insert_csv(connection, "fact_daily_sales", RAW_DATA_DIR / "fact_daily_sales.csv"),
        }
        connection.commit()
        connection.executescript(read_sql("01_feature_store.sql"))
        connection.commit()
        mart_rows = connection.execute("SELECT COUNT(*) FROM mart_demand_features").fetchone()[0]
    finally:
        connection.close()

    print("Built SQLite database at {}".format(DB_PATH))
    for table_name, row_count in counts.items():
        print("Loaded {:>18}: {:>8} rows".format(table_name, row_count))
    print("Created {:>18}: {:>8} rows".format("mart_demand_features", mart_rows))


if __name__ == "__main__":
    main()

