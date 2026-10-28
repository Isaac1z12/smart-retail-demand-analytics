import csv
import math
import random
from datetime import date, timedelta

from config import RAW_DATA_DIR, ensure_directories


SEED = 20260525
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)


def date_range(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_stores():
    return [
        {
            "store_id": "S001",
            "city": "Seattle",
            "region": "West",
            "store_format": "Urban",
            "floor_area_sqft": 18200,
            "opening_date": "2017-04-12",
            "traffic_index": 1.18,
        },
        {
            "store_id": "S002",
            "city": "Austin",
            "region": "South",
            "store_format": "Suburban",
            "floor_area_sqft": 24600,
            "opening_date": "2015-09-08",
            "traffic_index": 1.05,
        },
        {
            "store_id": "S003",
            "city": "Chicago",
            "region": "Midwest",
            "store_format": "Flagship",
            "floor_area_sqft": 38400,
            "opening_date": "2013-02-21",
            "traffic_index": 1.32,
        },
        {
            "store_id": "S004",
            "city": "Denver",
            "region": "Mountain",
            "store_format": "Suburban",
            "floor_area_sqft": 22100,
            "opening_date": "2018-06-17",
            "traffic_index": 0.96,
        },
        {
            "store_id": "S005",
            "city": "Boston",
            "region": "Northeast",
            "store_format": "Urban",
            "floor_area_sqft": 16900,
            "opening_date": "2016-11-03",
            "traffic_index": 1.14,
        },
        {
            "store_id": "S006",
            "city": "Phoenix",
            "region": "Southwest",
            "store_format": "Express",
            "floor_area_sqft": 11800,
            "opening_date": "2020-01-15",
            "traffic_index": 0.82,
        },
        {
            "store_id": "S007",
            "city": "Atlanta",
            "region": "South",
            "store_format": "Suburban",
            "floor_area_sqft": 25500,
            "opening_date": "2014-08-24",
            "traffic_index": 1.02,
        },
        {
            "store_id": "S008",
            "city": "Portland",
            "region": "West",
            "store_format": "Express",
            "floor_area_sqft": 12600,
            "opening_date": "2019-05-05",
            "traffic_index": 0.88,
        },
    ]


def build_products():
    raw_products = [
        ("SKU001", "Beverages", "Private Label", 0.72, 1.79, 180, 24),
        ("SKU002", "Beverages", "Standard", 1.15, 2.79, 180, 18),
        ("SKU003", "Beverages", "Premium", 1.64, 3.99, 180, 12),
        ("SKU004", "Bakery", "Private Label", 0.88, 2.49, 4, 22),
        ("SKU005", "Bakery", "Standard", 1.35, 3.49, 5, 16),
        ("SKU006", "Dairy", "Private Label", 1.02, 2.99, 14, 21),
        ("SKU007", "Dairy", "Standard", 1.48, 4.49, 14, 15),
        ("SKU008", "Produce", "Standard", 0.62, 1.99, 6, 28),
        ("SKU009", "Produce", "Premium", 1.12, 3.49, 6, 18),
        ("SKU010", "Pantry", "Private Label", 0.95, 2.69, 365, 17),
        ("SKU011", "Pantry", "Standard", 1.44, 3.99, 365, 13),
        ("SKU012", "Frozen", "Standard", 1.78, 5.49, 240, 11),
        ("SKU013", "Frozen", "Premium", 2.45, 7.49, 240, 8),
        ("SKU014", "Snacks", "Private Label", 0.58, 1.89, 240, 26),
        ("SKU015", "Snacks", "Standard", 0.92, 2.99, 240, 20),
        ("SKU016", "Personal Care", "Standard", 1.96, 5.99, 720, 7),
        ("SKU017", "Personal Care", "Premium", 3.10, 9.99, 720, 5),
        ("SKU018", "Household", "Standard", 2.20, 6.99, 720, 9),
    ]
    return [
        {
            "sku_id": sku_id,
            "category": category,
            "brand_tier": brand_tier,
            "unit_cost": unit_cost,
            "list_price": list_price,
            "shelf_life_days": shelf_life_days,
            "base_daily_units": base_daily_units,
        }
        for (
            sku_id,
            category,
            brand_tier,
            unit_cost,
            list_price,
            shelf_life_days,
            base_daily_units,
        ) in raw_products
    ]


def event_for_day(current_date):
    if current_date.month == 11 and current_date.day >= 20:
        return "Holiday Build-Up"
    if current_date.month == 12 and current_date.day <= 24:
        return "Holiday Build-Up"
    if current_date.month == 8 and current_date.day >= 10:
        return "Back-to-School"
    if current_date.month == 7 and 1 <= current_date.day <= 7:
        return "Summer Celebration"
    if current_date.month == 2 and 9 <= current_date.day <= 15:
        return "Winter Promotion"
    return "None"


def weather_for(store, current_date, rng):
    day_of_year = current_date.timetuple().tm_yday
    seasonal_wave = math.sin(2 * math.pi * (day_of_year - 80) / 365.0)
    region_adjustment = {
        "West": 3.0,
        "South": 8.0,
        "Midwest": -2.0,
        "Mountain": 0.0,
        "Northeast": -1.0,
        "Southwest": 12.0,
    }[store["region"]]
    temperature = 14 + 11 * seasonal_wave + region_adjustment + rng.gauss(0, 2.7)
    rain_probability = 0.18
    if store["region"] in ("West", "Northeast"):
        rain_probability = 0.26
    if current_date.month in (6, 7, 8):
        rain_probability -= 0.06
    precipitation = 0.0
    if rng.random() < rain_probability:
        precipitation = max(0.1, rng.expovariate(0.45))
    return round(temperature, 2), round(precipitation, 2)


def seasonal_category_factor(category, current_date, temperature_c):
    month = current_date.month
    factor = 1.0
    if category == "Beverages":
        factor += max(0, temperature_c - 22) * 0.025
    elif category == "Bakery":
        factor += 0.08 if month in (11, 12, 1, 2) else 0.0
    elif category == "Produce":
        factor += 0.10 if month in (5, 6, 7, 8, 9) else -0.04
    elif category == "Frozen":
        factor += 0.10 if month in (6, 7, 8) else 0.0
    elif category == "Snacks":
        factor += 0.09 if current_date.weekday() in (4, 5, 6) else 0.0
    elif category == "Household":
        factor += 0.04 if month in (3, 9) else 0.0
    return max(0.55, factor)


def campaign_flag(product, current_date, rng):
    category = product["category"]
    event = event_for_day(current_date)
    if event != "None" and category in ("Beverages", "Snacks", "Bakery", "Household"):
        return 1
    if current_date.day in (5, 6, 7) and category in ("Personal Care", "Pantry"):
        return 1
    return 1 if rng.random() < 0.035 else 0


def discount_rate(product, local_event, online_campaign, rng):
    discount = 0.0
    if online_campaign:
        discount += rng.choice([0.05, 0.08, 0.10, 0.12])
    if local_event == "Holiday Build-Up" and product["category"] in ("Snacks", "Beverages", "Bakery"):
        discount += 0.04
    if local_event == "Back-to-School" and product["category"] in ("Household", "Pantry", "Personal Care"):
        discount += 0.06
    if rng.random() < 0.025:
        discount += rng.choice([0.03, 0.05])
    return round(min(discount, 0.28), 3)


def poisson_sample(lam, rng):
    if lam <= 0:
        return 0
    if lam < 40:
        limit = math.exp(-lam)
        count = 0
        product = 1.0
        while product > limit:
            count += 1
            product *= rng.random()
        return count - 1
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def generate_fact_rows(stores, products):
    rng = random.Random(SEED)
    rows = []
    weather_cache = {}
    for current_date in date_range(START_DATE, END_DATE):
        weekday = current_date.weekday()
        weekend_factor = 1.14 if weekday in (5, 6) else 1.0
        for store in stores:
            weather_key = (store["store_id"], current_date.isoformat())
            if weather_key not in weather_cache:
                weather_cache[weather_key] = weather_for(store, current_date, rng)
            temperature_c, precipitation_mm = weather_cache[weather_key]
            traffic_base = 850 * store["traffic_index"] * weekend_factor
            if precipitation_mm > 5:
                traffic_base *= 0.92
            foot_traffic = max(120, int(round(rng.gauss(traffic_base, traffic_base * 0.12))))
            for product in products:
                local_event = event_for_day(current_date)
                online_campaign = campaign_flag(product, current_date, rng)
                discount = discount_rate(product, local_event, online_campaign, rng)
                competitor_price_index = round(max(0.82, min(1.18, rng.gauss(1.0, 0.045))), 3)
                traffic_factor = 0.72 + (foot_traffic / 1000.0) * 0.28
                price_factor = 1.0 + discount * 1.35 + (competitor_price_index - 1.0) * 0.55
                campaign_factor = 1.08 if online_campaign else 1.0
                event_factor = 1.0
                if local_event == "Holiday Build-Up":
                    event_factor = 1.18
                elif local_event == "Back-to-School":
                    event_factor = 1.12
                elif local_event == "Summer Celebration":
                    event_factor = 1.15
                elif local_event == "Winter Promotion":
                    event_factor = 1.09
                category_factor = seasonal_category_factor(product["category"], current_date, temperature_c)
                expected_units = (
                    product["base_daily_units"]
                    * store["traffic_index"]
                    * weekend_factor
                    * traffic_factor
                    * price_factor
                    * campaign_factor
                    * event_factor
                    * category_factor
                )
                if precipitation_mm > 8 and product["category"] in ("Bakery", "Produce"):
                    expected_units *= 0.93
                demand = poisson_sample(max(0.2, expected_units), rng)
                inventory_multiplier = rng.uniform(1.05, 2.8)
                if product["shelf_life_days"] <= 7:
                    inventory_multiplier = rng.uniform(0.85, 1.85)
                on_hand = max(0, int(round(expected_units * inventory_multiplier + rng.gauss(0, 3))))
                stockout_flag = 1 if demand > on_hand else 0
                units_sold = min(demand, on_hand)
                unit_price = round(product["list_price"] * (1 - discount), 2)
                gross_revenue = round(units_sold * unit_price, 2)
                rows.append(
                    {
                        "date": current_date.isoformat(),
                        "store_id": store["store_id"],
                        "sku_id": product["sku_id"],
                        "units_sold": units_sold,
                        "gross_revenue": gross_revenue,
                        "discount_rate": discount,
                        "unit_price": unit_price,
                        "stockout_flag": stockout_flag,
                        "on_hand_units": on_hand,
                        "foot_traffic": foot_traffic,
                        "temperature_c": temperature_c,
                        "precipitation_mm": precipitation_mm,
                        "local_event": local_event,
                        "online_campaign": online_campaign,
                        "competitor_price_index": competitor_price_index,
                    }
                )
    return rows


def main():
    ensure_directories()
    stores = build_stores()
    products = build_products()
    store_rows = [
        {key: store[key] for key in ["store_id", "city", "region", "store_format", "floor_area_sqft", "opening_date"]}
        for store in stores
    ]
    write_csv(
        RAW_DATA_DIR / "dim_store.csv",
        store_rows,
        ["store_id", "city", "region", "store_format", "floor_area_sqft", "opening_date"],
    )
    write_csv(
        RAW_DATA_DIR / "dim_product.csv",
        products,
        ["sku_id", "category", "brand_tier", "unit_cost", "list_price", "shelf_life_days", "base_daily_units"],
    )
    fact_rows = generate_fact_rows(stores, products)
    write_csv(
        RAW_DATA_DIR / "fact_daily_sales.csv",
        fact_rows,
        [
            "date",
            "store_id",
            "sku_id",
            "units_sold",
            "gross_revenue",
            "discount_rate",
            "unit_price",
            "stockout_flag",
            "on_hand_units",
            "foot_traffic",
            "temperature_c",
            "precipitation_mm",
            "local_event",
            "online_campaign",
            "competitor_price_index",
        ],
    )
    print("Generated {} fact rows in {}".format(len(fact_rows), RAW_DATA_DIR))


if __name__ == "__main__":
    main()

