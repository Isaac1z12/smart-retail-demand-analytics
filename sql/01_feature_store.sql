DROP TABLE IF EXISTS mart_demand_features;

CREATE TABLE mart_demand_features AS
SELECT
    f.date,
    f.store_id,
    f.sku_id,
    st.city,
    st.region,
    st.store_format,
    st.floor_area_sqft,
    p.category,
    p.brand_tier,
    p.unit_cost,
    p.list_price,
    f.units_sold,
    f.gross_revenue,
    f.discount_rate,
    f.unit_price,
    f.stockout_flag,
    f.on_hand_units,
    f.foot_traffic,
    f.temperature_c,
    f.precipitation_mm,
    f.local_event,
    f.online_campaign,
    f.competitor_price_index,
    CAST(strftime('%w', f.date) AS INTEGER) AS day_of_week,
    CAST(strftime('%m', f.date) AS INTEGER) AS month,
    COALESCE(lag7.units_sold, p.base_daily_units) AS units_lag_7,
    COALESCE(AVG(hist.units_sold), p.base_daily_units) AS units_rolling_28,
    COALESCE(AVG(hist.stockout_flag), 0.0) AS rolling_stockout_rate
FROM fact_daily_sales f
JOIN dim_store st
    ON f.store_id = st.store_id
JOIN dim_product p
    ON f.sku_id = p.sku_id
LEFT JOIN fact_daily_sales lag7
    ON lag7.store_id = f.store_id
    AND lag7.sku_id = f.sku_id
    AND lag7.date = date(f.date, '-7 day')
LEFT JOIN fact_daily_sales hist
    ON hist.store_id = f.store_id
    AND hist.sku_id = f.sku_id
    AND hist.date >= date(f.date, '-28 day')
    AND hist.date < f.date
WHERE f.date >= '2024-02-01'
GROUP BY
    f.date,
    f.store_id,
    f.sku_id;

CREATE INDEX idx_mart_date
ON mart_demand_features (date);

CREATE INDEX idx_mart_store_sku_date
ON mart_demand_features (store_id, sku_id, date);

CREATE INDEX idx_mart_category_date
ON mart_demand_features (category, date);

