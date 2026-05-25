-- name: monthly_revenue_growth
WITH monthly AS (
    SELECT
        strftime('%Y-%m', date) AS month,
        SUM(gross_revenue) AS revenue,
        SUM(units_sold) AS units
    FROM fact_daily_sales
    GROUP BY strftime('%Y-%m', date)
)
SELECT
    m.month,
    ROUND(m.revenue, 2) AS revenue,
    m.units,
    ROUND(
        (m.revenue - COALESCE(prev.revenue, m.revenue))
        / NULLIF(prev.revenue, 0),
        4
    ) AS month_over_month_growth
FROM monthly m
LEFT JOIN monthly prev
    ON prev.month = strftime('%Y-%m', date(m.month || '-01', '-1 month'))
ORDER BY m.month;

-- name: category_margin
SELECT
    p.category,
    ROUND(SUM(f.gross_revenue), 2) AS revenue,
    ROUND(SUM((f.unit_price - p.unit_cost) * f.units_sold), 2) AS gross_margin,
    ROUND(SUM((f.unit_price - p.unit_cost) * f.units_sold) / NULLIF(SUM(f.gross_revenue), 0), 4) AS margin_rate,
    SUM(f.units_sold) AS units
FROM fact_daily_sales f
JOIN dim_product p
    ON f.sku_id = p.sku_id
GROUP BY p.category
ORDER BY gross_margin DESC;

-- name: store_efficiency
SELECT
    st.store_id,
    st.city,
    st.region,
    st.store_format,
    ROUND(SUM(f.gross_revenue), 2) AS revenue,
    ROUND(SUM(f.gross_revenue) / NULLIF(SUM(f.foot_traffic), 0), 4) AS revenue_per_visit,
    ROUND(AVG(f.stockout_flag), 4) AS stockout_rate,
    ROUND(SUM(f.gross_revenue) / st.floor_area_sqft, 2) AS revenue_per_sqft
FROM fact_daily_sales f
JOIN dim_store st
    ON f.store_id = st.store_id
GROUP BY
    st.store_id,
    st.city,
    st.region,
    st.store_format,
    st.floor_area_sqft
ORDER BY revenue_per_visit DESC;

-- name: campaign_lift
SELECT
    p.category,
    f.online_campaign,
    ROUND(AVG(f.units_sold), 3) AS avg_units_per_store_sku_day,
    ROUND(AVG(f.gross_revenue), 2) AS avg_revenue_per_store_sku_day,
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

-- name: price_sensitivity_proxy
SELECT
    p.category,
    ROUND(AVG(f.discount_rate), 4) AS avg_discount,
    ROUND(AVG(f.units_sold), 3) AS avg_units,
    ROUND(
        AVG(f.discount_rate * f.units_sold)
        - AVG(f.discount_rate) * AVG(f.units_sold),
        5
    ) AS discount_unit_covariance,
    ROUND(AVG(f.competitor_price_index), 4) AS avg_competitor_price_index
FROM fact_daily_sales f
JOIN dim_product p
    ON f.sku_id = p.sku_id
GROUP BY p.category
ORDER BY discount_unit_covariance DESC;

-- name: event_impact
SELECT
    local_event,
    ROUND(AVG(units_sold), 3) AS avg_units,
    ROUND(AVG(gross_revenue), 2) AS avg_revenue,
    ROUND(AVG(discount_rate), 4) AS avg_discount,
    COUNT(*) AS observations
FROM fact_daily_sales
GROUP BY local_event
ORDER BY avg_revenue DESC;

-- name: reorder_candidates
WITH latest AS (
    SELECT MAX(date) AS max_date
    FROM mart_demand_features
)
SELECT
    m.date,
    m.store_id,
    m.sku_id,
    m.category,
    ROUND(m.units_rolling_28, 2) AS avg_daily_units_28d,
    m.on_hand_units,
    ROUND(m.units_rolling_28 * 7, 2) AS seven_day_need,
    ROUND((m.units_rolling_28 * 7) - m.on_hand_units, 2) AS reorder_gap
FROM mart_demand_features m
JOIN latest l
    ON m.date = l.max_date
WHERE m.on_hand_units < m.units_rolling_28 * 7
ORDER BY reorder_gap DESC
LIMIT 50;

