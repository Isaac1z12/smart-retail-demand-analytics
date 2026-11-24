-- name: monthly_units_growth
WITH monthly AS (
    SELECT
        strftime('%Y-%m', date) AS month,
        SUM(units_sold) AS units
    FROM fact_daily_sales
    GROUP BY strftime('%Y-%m', date)
)
SELECT
    m.month,
    m.units,
    ROUND(
        (m.units - COALESCE(prev.units, m.units)) * 1.0
        / NULLIF(prev.units, 0),
        4
    ) AS month_over_month_growth
FROM monthly m
LEFT JOIN monthly prev
    ON prev.month = strftime('%Y-%m', date(m.month || '-01', '-1 month'))
ORDER BY m.month;

-- name: category_units
SELECT
    p.category,
    SUM(f.units_sold) AS units,
    ROUND(AVG(f.units_sold), 3) AS avg_units_per_store_sku_day,
    COUNT(*) AS observation_days
FROM fact_daily_sales f
JOIN dim_product p
    ON f.sku_id = p.sku_id
GROUP BY p.category
ORDER BY units DESC;

-- name: units_per_visit
SELECT
    st.store_id,
    st.city,
    st.state,
    st.store_format,
    SUM(f.units_sold) AS units,
    SUM(f.foot_traffic) AS foot_traffic,
    ROUND(SUM(f.units_sold) * 1.0 / NULLIF(SUM(f.foot_traffic), 0), 4) AS units_per_visit
FROM fact_daily_sales f
JOIN dim_store st
    ON f.store_id = st.store_id
GROUP BY
    st.store_id,
    st.city,
    st.state,
    st.store_format
ORDER BY units_per_visit DESC;

-- name: campaign_lift
SELECT
    p.category,
    f.online_campaign,
    ROUND(AVG(f.units_sold), 3) AS avg_units_per_store_sku_day,
    COUNT(*) AS observation_days
FROM fact_daily_sales f
JOIN dim_product p
    ON f.sku_id = p.sku_id
GROUP BY
    p.category,
    f.online_campaign
ORDER BY
    p.category,
    f.online_campaign DESC;

-- name: oil_price_sensitivity
SELECT
    p.category,
    ROUND(AVG(f.oil_price), 2) AS avg_oil_price,
    ROUND(AVG(f.units_sold), 3) AS avg_units,
    ROUND(
        AVG(f.oil_price * f.units_sold)
        - AVG(f.oil_price) * AVG(f.units_sold),
        5
    ) AS oil_unit_covariance
FROM fact_daily_sales f
JOIN dim_product p
    ON f.sku_id = p.sku_id
GROUP BY p.category
ORDER BY oil_unit_covariance DESC;

-- name: event_impact
SELECT
    local_event,
    ROUND(AVG(units_sold), 3) AS avg_units,
    COUNT(*) AS observations
FROM fact_daily_sales
GROUP BY local_event
ORDER BY avg_units DESC;

-- name: demand_watchlist
-- NOTE: the Favorita source has no inventory data, so a reorder gap
-- cannot be computed. This query is a demand watchlist instead: the
-- store x item pairs with the highest recent (28-day rolling) demand
-- on the latest date, i.e. where to look first when planning stock.
WITH latest AS (
    SELECT MAX(date) AS max_date
    FROM mart_demand_features
)
SELECT
    m.date,
    m.store_id,
    m.sku_id,
    m.category,
    ROUND(m.units_rolling_28, 2) AS avg_daily_units_28d
FROM mart_demand_features m
JOIN latest l
    ON m.date = l.max_date
ORDER BY avg_daily_units_28d DESC
LIMIT 50;
