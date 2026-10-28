import csv
import re
import sqlite3

from config import DB_PATH, REPORTS_DIR, SQL_DIR, ensure_directories


QUERY_PATTERN = re.compile(r"^\s*--\s*name:\s*([A-Za-z0-9_]+)\s*$")


def parse_named_queries(sql_text):
    queries = []
    current_name = None
    current_lines = []
    for line in sql_text.splitlines():
        match = QUERY_PATTERN.match(line)
        if match:
            if current_name and current_lines:
                queries.append((current_name, "\n".join(current_lines).strip().rstrip(";")))
            current_name = match.group(1)
            current_lines = []
        else:
            current_lines.append(line)
    if current_name and current_lines:
        queries.append((current_name, "\n".join(current_lines).strip().rstrip(";")))
    return queries


def write_rows(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def main():
    ensure_directories()
    sql_path = SQL_DIR / "02_business_questions.sql"
    with sql_path.open("r", encoding="utf-8") as handle:
        named_queries = parse_named_queries(handle.read())
    connection = sqlite3.connect(str(DB_PATH))
    try:
        for name, query in named_queries:
            cursor = connection.execute(query)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            output_path = REPORTS_DIR / "{}.csv".format(name)
            write_rows(output_path, columns, rows)
            print("Exported {:>28}: {:>5} rows".format(name, len(rows)))
    finally:
        connection.close()


if __name__ == "__main__":
    main()

