# Data Dictionary

Source: Corporación Favorita Grocery Sales Forecasting, a real grocery
chain dataset (Kaggle mirror
`ruiyuanfan/corporacin-favorita-grocery-sales-forecasting`). The
warehouse holds a documented subset -- 8 stores x 30 items,
2016-01-01..2017-08-15 -- loaded by `src/load_favorita.py`. See
`README.md` for the subset definition and the cleaning rules.

## `dim_store`

| Column | Type | Description |
|---|---:|---|
| `store_id` | text | Favorita store number as published (e.g. `44`). |
| `city` | text | Store city (Quito, Guayaquil, Babahoyo, Latacunga). |
| `state` | text | Store state/province (Pichincha, Guayas, Los Rios, Cotopaxi). |
| `store_format` | text | Favorita store type, A-E (A largest). |
| `cluster` | integer | Favorita store cluster id. |

## `dim_product`

| Column | Type | Description |
|---|---:|---|
| `sku_id` | text | Favorita item number as published. |
| `category` | text | Product family (GROCERY I, BEVERAGES, CLEANING, PRODUCE, DAIRY, BREAD/BAKERY). |
| `perishable` | integer | 1 if the item is perishable, else 0. |
| `class` | integer | Favorita item class code. |
| `base_daily_units` | real | Mean daily units of this item over the densified fact table. Fallback for lag/rolling features when a store x item has no history yet. It is computed over the full window (test included), so it must never be used as a model feature -- that would leak test information. |

## `fact_daily_sales`

One row per store x item x open day in the subset. Days a store was
open but an item did not sell are present with `units_sold = 0`
(densified by the loader); the 15 store x item pairs that never sold
in the window are absent entirely.

| Column | Type | Description |
|---|---:|---|
| `date` | text | Daily observation date. |
| `store_id` | text | Store identifier. |
| `sku_id` | text | Product identifier. |
| `units_sold` | integer | Units sold that day. Source values are floats (weighed goods); they are rounded to whole units, halves up. Negative values (3 return rows) are truncated to 0. |
| `foot_traffic` | integer | Daily store transactions from `transactions.csv` (used as a foot-traffic proxy). The 342 sales rows on 2016-01-02..04 have no transactions row; their value is the store's median over the window. |
| `oil_price` | real | National WTI oil price (USD/barrel). Missing days are forward-filled from the last known price. |
| `local_event` | text | `National` / `Regional` / `Local` / `None`, mapped from `holidays_events.csv` by scope (National rows apply everywhere, Regional rows match the store's state, Local rows match the store's city). |
| `online_campaign` | integer | 1 if the item was on promotion that day (`onpromotion` in the source), else 0. |

## `mart_demand_features`

The feature mart joins facts to store and product dimensions, then adds SQL-created modeling variables. It starts 2016-02-01, 31 days into the window, so every row has a full 28-day history for the rolling feature.

- calendar variables: `day_of_week`, `month`
- lag features: `units_lag_7`
- rolling features: `units_rolling_28`
- product/store attributes: category, perishable, class, state, store format, cluster
- operational signals: foot traffic, oil price, local event, promotion

`base_daily_units` is carried in the mart only as the COALESCE fallback
for `units_lag_7` / `units_rolling_28` when a store x item has no
history yet; it is not a model feature.

## What this dataset does not have

No prices, revenue, discounts, inventory, stockouts, or weather -- the
source never published them, so the old synthetic columns for those
were removed rather than invented. See the Limitations section in
`README.md`.
