PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_daily_sales;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_store;

CREATE TABLE dim_store (
    store_id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    store_format TEXT NOT NULL,
    cluster INTEGER NOT NULL
);

CREATE TABLE dim_product (
    sku_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    perishable INTEGER NOT NULL,
    class INTEGER NOT NULL,
    base_daily_units REAL NOT NULL
);

CREATE TABLE fact_daily_sales (
    date TEXT NOT NULL,
    store_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    units_sold INTEGER NOT NULL,
    foot_traffic INTEGER NOT NULL,
    oil_price REAL NOT NULL,
    local_event TEXT NOT NULL,
    online_campaign INTEGER NOT NULL,
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
