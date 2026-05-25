PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_daily_sales;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_store;

CREATE TABLE dim_store (
    store_id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    region TEXT NOT NULL,
    store_format TEXT NOT NULL,
    floor_area_sqft INTEGER NOT NULL,
    opening_date TEXT NOT NULL
);

CREATE TABLE dim_product (
    sku_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    brand_tier TEXT NOT NULL,
    unit_cost REAL NOT NULL,
    list_price REAL NOT NULL,
    shelf_life_days INTEGER NOT NULL,
    base_daily_units REAL NOT NULL
);

CREATE TABLE fact_daily_sales (
    date TEXT NOT NULL,
    store_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    units_sold INTEGER NOT NULL,
    gross_revenue REAL NOT NULL,
    discount_rate REAL NOT NULL,
    unit_price REAL NOT NULL,
    stockout_flag INTEGER NOT NULL,
    on_hand_units INTEGER NOT NULL,
    foot_traffic INTEGER NOT NULL,
    temperature_c REAL NOT NULL,
    precipitation_mm REAL NOT NULL,
    local_event TEXT NOT NULL,
    online_campaign INTEGER NOT NULL,
    competitor_price_index REAL NOT NULL,
    PRIMARY KEY (date, store_id, sku_id),
    FOREIGN KEY (store_id) REFERENCES dim_store(store_id),
    FOREIGN KEY (sku_id) REFERENCES dim_product(sku_id)
);

CREATE INDEX idx_fact_store_sku_date
ON fact_daily_sales (store_id, sku_id, date);

CREATE INDEX idx_fact_date
ON fact_daily_sales (date);

CREATE INDEX idx_fact_store_date
ON fact_daily_sales (store_id, date);

