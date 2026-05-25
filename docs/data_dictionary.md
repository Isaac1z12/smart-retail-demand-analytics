# Data Dictionary

## `dim_store`

| Column | Type | Description |
|---|---:|---|
| `store_id` | text | Store identifier. |
| `city` | text | Store city. |
| `region` | text | Operating region. |
| `store_format` | text | Store format such as urban, suburban, or express. |
| `floor_area_sqft` | integer | Store selling area. |
| `opening_date` | text | Store opening date. |

## `dim_product`

| Column | Type | Description |
|---|---:|---|
| `sku_id` | text | Product identifier. |
| `category` | text | Product category. |
| `brand_tier` | text | Private label, standard, or premium. |
| `unit_cost` | real | Unit cost used for gross margin analysis. |
| `list_price` | real | Base customer price before discounts. |
| `shelf_life_days` | integer | Approximate shelf life. |
| `base_daily_units` | real | Demand parameter used in synthetic generation. |

## `fact_daily_sales`

| Column | Type | Description |
|---|---:|---|
| `date` | text | Daily observation date. |
| `store_id` | text | Store identifier. |
| `sku_id` | text | Product identifier. |
| `units_sold` | integer | Observed units sold after inventory constraints. |
| `gross_revenue` | real | Unit price multiplied by units sold. |
| `discount_rate` | real | Discount applied to list price. |
| `unit_price` | real | Realized selling price after discount. |
| `stockout_flag` | integer | 1 when inventory constrained sales, else 0. |
| `on_hand_units` | integer | Inventory available at start of the day. |
| `foot_traffic` | integer | Estimated daily store visits. |
| `temperature_c` | real | Local temperature proxy. |
| `precipitation_mm` | real | Local precipitation proxy. |
| `local_event` | text | Local or seasonal event label. |
| `online_campaign` | integer | 1 if a digital campaign was active. |
| `competitor_price_index` | real | Relative competitor price index. |

## `mart_demand_features`

The feature mart joins facts to store and product dimensions, then adds SQL-created modeling variables:

- calendar variables: `day_of_week`, `month`
- lag features: `units_lag_7`
- rolling features: `units_rolling_28`, `rolling_stockout_rate`
- product/store attributes: category, brand tier, region, format
- operational signals: traffic, weather, discount, inventory, campaigns, competitor price

