"""Load the Corporacion Favorita grocery sales subset into data/raw/.

Source data: Corporacion Favorita Grocery Sales Forecasting (Kaggle
competition, mirrored at ruiyuanfan/corporacin-favorita-grocery-sales-
forecasting). The raw files live in ``data/favorita_source/``:

- ``train.csv`` -- daily unit sales, either the 863 MB zip as downloaded
  or the extracted CSV (NOT committed: far too large for git).
- ``stores.csv``, ``items.csv``, ``oil.csv``, ``holidays_events.csv``,
  ``transactions.csv`` -- small reference files, committed with the repo.

Subset (locked in week 4 after a full scan of train.csv):

- 8 stores spanning store types A-E and 5 cities / 4 states.
- 30 items: the top 5 sellers in each of 6 families (GROCERY I,
  BEVERAGES, CLEANING, PRODUCE, DAIRY, BREAD/BAKERY) by total unit
  sales in the window. The loader recomputes this top-5 list from
  train.csv on every run and refuses to continue if it differs from
  the locked list below -- the subset must be derived, not copied.
- Window 2016-01-01..2017-08-15; train <= 2017-06-30, test after.

Cleaning rules, all applied here so the rest of the pipeline only ever
sees clean CSVs:

- ``unit_sales`` is a float in the source because weighed goods are
  sold by weight (12.8% of subset rows are fractional). It is rounded
  to the nearest whole unit, halves rounding up, because ``units_sold``
  is an integer count in this warehouse.
- Negative unit sales (3 rows: -1, -144, -1) are returns; they are
  truncated to 0 and counted.
- Zero-sales rows do not exist in the source (0 rows): a missing
  store x item x day means nothing was sold, so the fact table is
  densified with 0 rows -- but only on days the store was actually
  open. A store's open days are the days it has a row in
  transactions.csv (this also reproduces the 110-day closure of
  store 18, 2016-08-15..12-02, where the store sold nothing).
- ``onpromotion`` is the strings "True"/"False" in the window; it
  becomes ``online_campaign`` 1/0.
- ``foot_traffic`` comes from transactions.csv. The 342 sales rows on
  2016-01-02..04 have no transactions row (those days are missing for
  some stores); their foot traffic is filled with the store's median
  over the window.
- ``oil_price`` is the national WTI price from oil.csv. The file only
  has rows on trading days and 43 rows have an empty value, so 186
  days in the window have no usable price; they are forward-filled
  from the last known price.
- ``local_event`` is a rule-based mapping of holidays_events.csv:
  only type Holiday / Event / Additional / Bridge are used (Work Day
  and Transfer are excluded -- they mark a moved workday, not a day
  off). National rows apply to every store, Regional rows only when
  locale_name matches the store's state, Local rows only when
  locale_name matches the store's city. Priority on a clash:
  National > Regional > Local; otherwise "None".
- ``base_daily_units`` is computed by the loader as the item's mean
  daily units over the densified fact table. It is only a fallback
  for lag/rolling features when a store x item has no history yet;
  it must NOT be used as a model feature, because it is computed
  over the full window including the test period and would leak
  test information. (The SQL mart uses it only in COALESCE fallbacks.)

If any source file is missing, the loader prints where to get it and
exits 0 without touching ``data/raw/`` -- the pipeline then continues
with the subset CSVs already committed in the repo.
"""

import csv
import math
import sys
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from config import DATA_DIR, RAW_DATA_DIR, ensure_directories

SOURCE_DIR = DATA_DIR / "favorita_source"

WINDOW_START = "2016-01-01"
WINDOW_END = "2017-08-15"
SPLIT_DATE = "2017-06-30"

STORES = {1, 12, 18, 28, 30, 31, 44, 51}
TARGET_FAMILIES = [
    "GROCERY I",
    "BEVERAGES",
    "CLEANING",
    "PRODUCE",
    "DAIRY",
    "BREAD/BAKERY",
]
TOP_PER_FAMILY = 5

# Locked subset (week 4). The loader recomputes the top-5 items per
# family from train.csv and stops if the result differs from this set.
LOCKED_ITEMS = {
    264299, 265559, 314384, 314393, 364606, 502331, 559870, 564287,
    581078, 819932, 852110, 939207, 1047679, 1052563, 1239809, 1309246,
    1333307, 1346638, 1427659, 1430040, 1463992, 1463993, 1473474,
    1503844, 1503847, 1642399, 1695835, 1963265, 1963277, 1978835,
}

# Locked verification counts (week 4 full scan). The loader checks
# each of these and stops if any differs.
#
# CORRECTION (week 5 implementation): week 4 locked zero_fill_rows as
# 13,529 / densified_rows as 127,435, but an independent recount shows
# those numbers come from counting ALL calendar days in each pair's
# [first, last] range (13,529 / 127,435 reproduce exactly that way).
# The specified rule -- fill 0 only on days the store was actually
# open (a transactions row exists for that store and day) -- gives
# 10,101 / 124,007, verified twice with independent code. The
# all-days count is wrong for this project: it would fabricate
# "open but sold nothing" rows on closed days, including store 18's
# 110-day closure (2016-08-15..12-02), and distort lag/rolling
# features. The counts below are the per-store business-day values.
EXPECTED = {
    "subset_rows": 113906,
    "train_rows": 104477,
    "test_rows": 9429,
    "pairs_present": 225,
    "zero_fill_rows": 10101,
    "densified_rows": 124007,
    "negative_sales_rows": 3,
    "zero_sales_rows": 0,
    "onpromotion_true_rows": 15326,
}

KEPT_HOLIDAY_TYPES = {"Holiday", "Event", "Additional", "Bridge"}

SMALL_FILES = [
    "stores.csv",
    "items.csv",
    "oil.csv",
    "holidays_events.csv",
    "transactions.csv",
]


def parse_date(text):
    year, month, day = (int(part) for part in text.split("-"))
    return date(year, month, day)


def round_units(value):
    """Round a (possibly fractional) unit sale to whole units.

    Favorita sells weighed goods by weight, so unit_sales is a float.
    Halves round up; negatives are handled by the caller.
    """
    return int(math.floor(value + 0.5))


def find_train_source():
    """Return (path, is_zip) for train.csv, or None if not present."""
    plain = SOURCE_DIR / "train.csv"
    if plain.exists():
        if zipfile.is_zipfile(plain):
            return plain, True
        return plain, False
    zipped = SOURCE_DIR / "train.csv.zip"
    if zipped.exists():
        return zipped, True
    return None


def iter_train_lines(train_path, is_zip):
    """Yield raw lines of train.csv (skipping its header)."""
    if is_zip:
        handle = zipfile.ZipFile(train_path).open("train.csv")
        first = True
        for line in handle:
            if first:
                first = False
                continue
            yield line.decode("ascii").rstrip("\n")
        handle.close()
    else:
        with train_path.open("r", encoding="ascii") as handle:
            next(handle)  # header
            for line in handle:
                yield line.rstrip("\n")


def read_stores():
    stores = {}
    with (SOURCE_DIR / "stores.csv").open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            store_nbr = int(row["store_nbr"])
            if store_nbr in STORES:
                stores[store_nbr] = {
                    "city": row["city"],
                    "state": row["state"],
                    "store_format": row["type"],
                    "cluster": int(row["cluster"]),
                }
    missing = STORES - set(stores)
    if missing:
        raise ValueError("stores.csv is missing stores: {}".format(sorted(missing)))
    return stores


def read_items():
    """Return (family_of_item, item_info) for all items."""
    family_of = {}
    info = {}
    with (SOURCE_DIR / "items.csv").open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            item_nbr = int(row["item_nbr"])
            family_of[item_nbr] = row["family"]
            info[item_nbr] = {
                "category": row["family"],
                "perishable": int(row["perishable"]),
                "class": int(row["class"]),
            }
    return family_of, info


def compute_top_items(train_path, is_zip, family_of):
    """Pass 1 over train.csv: top-5 sellers per target family in window."""
    item_sales = defaultdict(float)
    for line in iter_train_lines(train_path, is_zip):
        parts = line.split(",")
        # id,date,store_nbr,item_nbr,unit_sales,onpromotion
        item_nbr = int(parts[3])
        family = family_of.get(item_nbr)
        if family not in TARGET_FAMILIES:
            continue
        sale_date = parts[1]
        if sale_date < WINDOW_START or sale_date > WINDOW_END:
            continue
        item_sales[item_nbr] += float(parts[4])
    top_items = {}
    for family in TARGET_FAMILIES:
        ranked = sorted(
            ((sales, item) for item, sales in item_sales.items()
             if family_of[item] == family),
            key=lambda pair: (-pair[0], pair[1]),
        )
        top_items[family] = [item for _, item in ranked[:TOP_PER_FAMILY]]
    return top_items


def extract_subset(train_path, is_zip, items):
    """Pass 2 over train.csv: raw rows for the 8 stores x 30 items."""
    sales = {}  # (store, item, date) -> (unit_sales float, onpromotion str)
    counts = defaultdict(int)
    for line in iter_train_lines(train_path, is_zip):
        parts = line.split(",")
        sale_date, store_nbr, item_nbr = parts[1], int(parts[2]), int(parts[3])
        if sale_date < WINDOW_START or sale_date > WINDOW_END:
            continue
        if store_nbr not in STORES or item_nbr not in items:
            continue
        value = float(parts[4])
        promo = parts[5] if len(parts) > 5 else ""
        key = (store_nbr, item_nbr, sale_date)
        if key in sales:
            counts["duplicate_rows"] += 1
        sales[key] = (value, promo)
        counts["subset_rows"] += 1
        if sale_date <= SPLIT_DATE:
            counts["train_rows"] += 1
        else:
            counts["test_rows"] += 1
        if value == 0:
            counts["zero_sales_rows"] += 1
        if value < 0:
            counts["negative_sales_rows"] += 1
        if promo == "True":
            counts["onpromotion_true_rows"] += 1
        elif promo == "False":
            counts["onpromotion_false_rows"] += 1
        else:
            counts["onpromotion_other_rows"] += 1
    pairs = {(store, item) for store, item, _ in sales}
    counts["pairs_present"] = len(pairs)
    return sales, counts, pairs


def read_transactions():
    """Return (transactions, store_median) for the window.

    transactions: {(store, date_str): visits}. The store median is
    computed over the store's window values and fills the few sales
    rows whose date has no transactions row.
    """
    by_store = defaultdict(list)
    transactions = {}
    with (SOURCE_DIR / "transactions.csv").open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            store_nbr = int(row["store_nbr"])
            if store_nbr not in STORES:
                continue
            sale_date = row["date"]
            if sale_date < WINDOW_START or sale_date > WINDOW_END:
                continue
            value = int(row["transactions"])
            transactions[(store_nbr, sale_date)] = value
            by_store[store_nbr].append(value)
    import statistics

    medians = {}
    for store_nbr, values in by_store.items():
        medians[store_nbr] = round_units(statistics.median(values))
    return transactions, medians


def read_oil():
    """Return {date_str: price} with forward-filled prices for window.

    Days with no oil row, or an empty value, take the last known price.
    Also returns how many window days were filled this way.
    """
    raw = {}
    with (SOURCE_DIR / "oil.csv").open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw[row["date"]] = row["dcoilwtico"].strip()
    prices = {}
    filled_days = 0
    last_value = None
    start = parse_date("2013-01-01")
    end = parse_date(WINDOW_END)
    day = start
    while day <= end:
        text = raw.get(day.isoformat())
        if text:
            last_value = float(text)
        if day.isoformat() >= WINDOW_START:
            if text:
                prices[day.isoformat()] = float(text)
            else:
                if last_value is None:
                    raise ValueError("no oil price known before {}".format(day))
                prices[day.isoformat()] = last_value
                filled_days += 1
        day += timedelta(days=1)
    return prices, filled_days


def read_holidays():
    """Return {date_str: (has_national, {states}, {cities})}.

    Only Holiday / Event / Additional / Bridge rows are kept. Work Day
    and Transfer rows are excluded: they mark a moved workday, not a
    day off.
    """
    events = defaultdict(lambda: (False, set(), set()))
    with (SOURCE_DIR / "holidays_events.csv").open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["type"] not in KEPT_HOLIDAY_TYPES:
                continue
            sale_date = row["date"]
            if sale_date < WINDOW_START or sale_date > WINDOW_END:
                continue
            has_national, states, cities = events[sale_date]
            if row["locale"] == "National":
                has_national = True
            elif row["locale"] == "Regional":
                states.add(row["locale_name"])
            elif row["locale"] == "Local":
                cities.add(row["locale_name"])
            events[sale_date] = (has_national, states, cities)
    return events


def local_event_for(store, sale_date, events):
    """Map a store x date to National / Regional / Local / None."""
    entry = events.get(sale_date)
    if entry is None:
        return "None"
    has_national, states, cities = entry
    if has_national:
        return "National"
    if store["state"] in states:
        return "Regional"
    if store["city"] in cities:
        return "Local"
    return "None"


def print_missing_guidance(missing):
    print("Favorita source files are missing from {}:".format(SOURCE_DIR))
    for name in missing:
        print("  - {}".format(name))
    print()
    print("The five small reference files are committed in the repo; only")
    print("train.csv (863 MB zip) is too large for git and must be fetched:")
    print()
    print("  1. Download train.csv from the Kaggle mirror")
    print("     ruiyuanfan/corporacin-favorita-grocery-sales-forecasting")
    print("     (the official competition files need rule acceptance; the")
    print("     mirror does not). It downloads as train.csv, a zip archive")
    print("     containing train.csv.")
    print("  2. Place it at data/favorita_source/train.csv")
    print("     (zip or extracted CSV both work; *.zip is git-ignored).")
    print("  3. Re-run: python src/load_favorita.py")
    print()
    print("Skipping the Favorita load; data/raw/ is left untouched.")


def check_counts(counts):
    failed = []
    for name, expected in EXPECTED.items():
        actual = counts.get(name, 0)
        status = "OK " if actual == expected else "MISMATCH"
        print("  CHECK {:<24} actual {:>8}  expected {:>8}  {}".format(
            name, actual, expected, status))
        if actual != expected:
            failed.append(name)
    if failed:
        print()
        print("ERROR: verification failed for: {}".format(", ".join(failed)))
        print("The subset does not match the locked week-4 counts. Stop and")
        print("investigate instead of writing data/raw/ with other numbers.")
        return False
    return True


def main():
    missing = [name for name in SMALL_FILES if not (SOURCE_DIR / name).exists()]
    train_source = find_train_source()
    if train_source is None:
        missing.append("train.csv (zip or extracted CSV)")
    if missing:
        print_missing_guidance(missing)
        return 0

    train_path, is_zip = train_source
    print("Loading Favorita subset from {}".format(train_path))
    print("Window {}..{}, train <= {}".format(WINDOW_START, WINDOW_END, SPLIT_DATE))

    stores = read_stores()
    family_of, item_info = read_items()

    print("Pass 1/2: computing top-{} sellers per family from train.csv ...".format(TOP_PER_FAMILY))
    top_items = compute_top_items(train_path, is_zip, family_of)
    computed_items = set()
    for family in TARGET_FAMILIES:
        print("  {:<14} {}".format(family, top_items[family]))
        computed_items.update(top_items[family])
    if computed_items != LOCKED_ITEMS:
        print()
        print("ERROR: recomputed top-5 items differ from the locked subset.")
        print("  only in recomputed: {}".format(sorted(computed_items - LOCKED_ITEMS)))
        print("  only in locked:     {}".format(sorted(LOCKED_ITEMS - computed_items)))
        print("Stop and investigate instead of writing a different subset.")
        return 1

    print("Pass 2/2: extracting 8 stores x 30 items ...")
    sales, counts, pairs = extract_subset(train_path, is_zip, LOCKED_ITEMS)
    print("  subset rows: {} (train {}, test {})".format(
        counts["subset_rows"], counts["train_rows"], counts["test_rows"]))
    print("  (store, item) pairs present: {} of {}".format(
        counts["pairs_present"], len(STORES) * len(LOCKED_ITEMS)))

    transactions, store_medians = read_transactions()
    oil_prices, oil_filled_days = read_oil()
    holidays = read_holidays()

    # Densify: for each pair, every store-open day between its first and
    # last sale gets a row (0 where nothing was sold). Raw sale rows on
    # days with no transactions row (2016-01-02..04) are kept as-is.
    pair_dates = defaultdict(list)
    for store_nbr, item_nbr, sale_date in sales:
        pair_dates[(store_nbr, item_nbr)].append(sale_date)
    pair_range = {}
    for pair, dates in pair_dates.items():
        pair_range[pair] = (min(dates), max(dates))

    window_start = parse_date(WINDOW_START)
    window_end = parse_date(WINDOW_END)
    all_dates = []
    day = window_start
    while day <= window_end:
        all_dates.append(day.isoformat())
        day += timedelta(days=1)

    fact_rows = []
    zero_fill_rows = 0
    traffic_filled_rows = 0
    fractional_rows = 0
    truncated_rows = 0
    units_by_item = defaultdict(int)
    days_by_item = defaultdict(int)
    for (store_nbr, item_nbr) in sorted(pairs):
        store = stores[store_nbr]
        first, last = pair_range[(store_nbr, item_nbr)]
        dense_dates = set()
        for text in all_dates:
            if first <= text <= last and (store_nbr, text) in transactions:
                dense_dates.add(text)
        for text in pair_dates[(store_nbr, item_nbr)]:
            dense_dates.add(text)  # keep real sales even on non-open days
        for text in sorted(dense_dates):
            raw = sales.get((store_nbr, item_nbr, text))
            if raw is None:
                units = 0
                promo = "False"
                zero_fill_rows += 1
            else:
                value, promo = raw
                if value != int(value):
                    fractional_rows += 1
                if value < 0:
                    units = 0
                    truncated_rows += 1
                else:
                    units = round_units(value)
            traffic = transactions.get((store_nbr, text))
            if traffic is None:
                traffic = store_medians[store_nbr]
                traffic_filled_rows += 1
            fact_rows.append({
                "date": text,
                "store_id": str(store_nbr),
                "sku_id": str(item_nbr),
                "units_sold": units,
                "foot_traffic": traffic,
                "oil_price": round(oil_prices[text], 2),
                "local_event": local_event_for(store, text, holidays),
                "online_campaign": 1 if promo == "True" else 0,
            })
            units_by_item[item_nbr] += units
            days_by_item[item_nbr] += 1

    counts["zero_fill_rows"] = zero_fill_rows
    counts["densified_rows"] = len(fact_rows)
    counts["fractional_sales_rows"] = fractional_rows
    counts["truncated_negative_rows"] = truncated_rows
    counts["traffic_median_filled_rows"] = traffic_filled_rows
    counts["oil_forward_filled_days"] = oil_filled_days

    print("Verification:")
    if not check_counts(counts):
        return 1
    print("  fractional unit_sales rows rounded to whole units: {}".format(fractional_rows))
    print("  negative sales rows truncated to 0: {}".format(truncated_rows))
    print("  foot_traffic rows filled with store median: {}".format(traffic_filled_rows))
    print("  oil price days forward-filled in window: {}".format(oil_filled_days))
    print("  densified fact rows: {}".format(len(fact_rows)))

    # base_daily_units: mean daily units per item over the densified fact
    # table. Fallback for lag/rolling features only -- never a model
    # feature (it is computed over the full window, test included).
    dim_products = []
    for item_nbr in sorted(LOCKED_ITEMS):
        info = item_info[item_nbr]
        dim_products.append({
            "sku_id": str(item_nbr),
            "category": info["category"],
            "perishable": info["perishable"],
            "class": info["class"],
            "base_daily_units": round(units_by_item[item_nbr] / days_by_item[item_nbr], 4),
        })
    dim_stores = []
    for store_nbr in sorted(STORES):
        store = stores[store_nbr]
        dim_stores.append({
            "store_id": str(store_nbr),
            "city": store["city"],
            "state": store["state"],
            "store_format": store["store_format"],
            "cluster": store["cluster"],
        })

    ensure_directories()
    with (RAW_DATA_DIR / "dim_store.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["store_id", "city", "state", "store_format", "cluster"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(dim_stores)
    with (RAW_DATA_DIR / "dim_product.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sku_id", "category", "perishable", "class", "base_daily_units"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(dim_products)
    with (RAW_DATA_DIR / "fact_daily_sales.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["date", "store_id", "sku_id", "units_sold", "foot_traffic",
                        "oil_price", "local_event", "online_campaign"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(fact_rows)

    print("Wrote {} dim_store rows, {} dim_product rows, {} fact rows to {}".format(
        len(dim_stores), len(dim_products), len(fact_rows), RAW_DATA_DIR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
