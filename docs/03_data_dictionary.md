\# Phase 4 Deliverable: Relational Data Dictionary \& Quality Assessment



\## 1. `JD\_order\_data.csv` (Transactions \& Pricing Fact Table)

\*\*Primary Grain:\*\* Order Line Item (`order\_id` + `sku\_id` + `gift\_item`)



| Column | Data Type | Description | Example | Data Quality Concerns \& Analytical Implications |

| :--- | :--- | :--- | :--- | :--- |

| `order\_id` | `string` / `object` | Anonymized unique identifier for a customer checkout order. | `d0cf5cc6db` | Non-unique per row because a single order can contain multiple SKUs or promotional gifts. Must pre-aggregate before joining to `JD\_delivery\_data`. |

| `sku\_id` | `string` / `object` | Anonymized unique identifier for the purchased product. | `a0e49f9966` | Some SKUs ordered in `JD\_order\_data` (especially 3P items) may not exist in `JD\_sku\_data` master table; requires left join audit. |

| `user\_id` | `string` / `object` | Unique identifier linking to the buyer in `JD\_user\_data`. | `000089d6a6` | Foreign key to `JD\_user\_data.csv`. |

| `order\_date` | `string` (`YYYY-MM-DD`) | Calendar date when the customer placed the order. | `2018-03-01` | Stored as string in raw CSV; must cast to `DATE`. |

| `order\_time` | `string` (`datetime`) | Exact timestamp when the order was submitted. | `2018-03-01 14:22:10.0` | Contains fractional seconds (`.0`); must parse as `DATETIME` and validate against `ship\_time`. |

| `quantity` | `int64` | Number of units of `sku\_id` purchased on this line item. | `1`, `2` | Right-skewed distribution (bulk/wholesale orders exist); unit prices and per-unit discounts must be multiplied by `quantity` for order totals. |

| `type` | `int64` | Fulfillment/Seller business model: `1` = 1P (JD Self-Operated), `2` = 3P (Third-Party Marketplace Seller). | `1`, `2` | Critical segmentation variable: 3P orders frequently use external couriers and have missing `promise` values (`'-'`). |

| `promise` | `string` / `object` | Promised delivery SLA in calendar days (`1` to `8`), or `'-'` if no standard SLA promise was displayed. | `'1'`, `'2'`, `'-'` | \*\*Major Quality Issue:\*\* Coded missing value `'-'` (primarily on `type = 2` 3P orders). Cannot cast directly to integer without separating `'-'` into an `"Unpromised / Standard 3P"` category. |

| `original\_unit\_price` | `float64` | List price per single unit before any promotional discounts (in RMB). | `89.0`, `0.0` | Can be `0.0` for promotional free gifts (`gift\_item = 1`). Never divide by `original\_unit\_price` without filtering `original\_unit\_price > 0`. |

| `final\_unit\_price` | `float64` | Net price paid per unit after all discounts are subtracted (in RMB). | `69.0`, `0.0` | Can be `0.0` for `gift\_item = 1` or 100%-coupon redemptions; some rounding discrepancies exist between `original - sum(discounts)` and `final\_unit\_price`. |

| `direct\_discount\_per\_unit` | `float64` | Instant price markdown per unit applied directly to the SKU. | `10.0` | Must multiply by `quantity` to compute total direct discount per line. |

| `quantity\_discount\_per\_unit` | `float64` | Multi-buy / tiered volume discount per unit (e.g., "Buy 2 save 20%"). | `5.0` | Must multiply by `quantity` to compute total quantity discount. |

| `bundle\_discount\_per\_unit` | `float64` | Cross-product bundle promotion discount per unit. | `0.0` | Often `0.0`; must multiply by `quantity`. |

| `coupon\_discount\_per\_unit` | `float64` | Voucher/coupon discount allocated per unit. | `5.0` | Must multiply by `quantity`. |

| `gift\_item` | `int64` | Binary flag: `1` = Free promotional gift item included with purchase; `0` = Regular paid item. | `0`, `1` | \*\*Critical Rule:\*\* Including `gift\_item = 1` rows in average price or discount depth calculations artificially inflates discount rates to 100%. Must separate paid items (`gift\_item = 0`) from gift attachments. |

| `dc\_ori` | `int64` | Origin Distribution Center ID that physically shipped the item. | `9` | Foreign key to `JD\_network\_data.dc\_id`. When `dc\_ori != dc\_des`, indicates inventory spillover / cross-shipping. |

| `dc\_des` | `int64` | Destination Distribution Center ID assigned to the customer's delivery address. | `9`, `24` | Foreign key to `JD\_network\_data.dc\_id`. |



\---



\## 2. `JD\_delivery\_data.csv` (Logistics \& Package Telemetry Fact Table)

\*\*Primary Grain:\*\* Shipment Parcel (`package\_id` + `order\_id`)



| Column | Data Type | Description | Example | Data Quality Concerns \& Analytical Implications |

| :--- | :--- | :--- | :--- | :--- |

| `package\_id` | `string` / `object` | Unique tracking identifier for an individual physical parcel. | `dc321f09b2` | A single `order\_id` can be split into multiple `package\_id`s (split shipments), or multiple items can be consolidated into one `package\_id`. |

| `order\_id` | `string` / `object` | Foreign key linking the parcel back to `JD\_order\_data`. | `d0cf5cc6db` | \*\*1:M Relationship:\*\* Joining directly to `JD\_order\_data` without pre-aggregation causes fan-out duplication. |

| `type` | `int64` | Logistics carrier indicator (`1` = 1P JD Logistics, `0` = 3P Merchant / JD-tracked 3P). | `1`, `0` | Note coding difference: In `JD\_order\_data`, 3P is coded as `2`, whereas in `JD\_delivery\_data`, 3P is coded as `0`! Must standardize in Phase 5. |

| `ship\_time` | `string` (`datetime`) | Timestamp when the parcel exited the origin warehouse (`dc\_ori`). | `2018-03-01 16:00:00` | Must verify `ship\_time >= order\_time`. Negative differences indicate timezone/system clock sync issues or pre-allocated batch timestamps. |

| `arr\_time` | `string` (`datetime`) | Timestamp when the parcel arrived at the local last-mile delivery station. | `2018-03-02 07:00:00` | Must verify `arr\_time >= ship\_time` (Line-Haul Transit Time). |

| `dlvr\_time` | `string` (`datetime`) | Timestamp when the parcel was delivered to the customer's doorstep. | `2018-03-02 13:00:00` | Must verify `dlvr\_time >= arr\_time` (Last-Mile Delivery Time). |



\---



\## 3. `JD\_user\_data.csv` (Customer Master Dimension)

\*\*Primary Grain:\*\* Unique Customer (`user\_id`)



| Column | Data Type | Description | Example | Data Quality Concerns \& Analytical Implications |

| :--- | :--- | :--- | :--- | :--- |

| `user\_id` | `string` / `object` | Primary key uniquely identifying a customer. | `000089d6a6` | Must verify 100% uniqueness. |

| `first\_order\_month` | `string` (`YYYY-MM`) | Year and month of the customer's very first order on JD.com. | `2016-08` | Useful for calculating customer tenure prior to March 2018. |

| `plus` | `int64` | Binary indicator: `1` = Active JD PLUS paid VIP member; `0` = Regular member. | `0`, `1` | Key segmentation variable for testing whether VIP members tolerate SLA breaches differently. |

| `gender` | `string` / `object` | Customer gender (`F`, `M`, `U` = Unknown). | `'F'`, `'M'`, `'U'` | `'U'` represents unrecorded gender; treat as `"Unknown"` category rather than dropping rows. |

| `age` | `string` / `object` | Age bracket of the customer (`<=15`, `16-25`, `26-35`, `36-45`, `46-55`, `>=56`, `U`). | `'26-35'`, `'U'` | Categorical string bracket with `'U'` for Unknown. |

| `marital\_status` | `string` / `object` | Marital status (`M` = Married, `S` = Single, `U` = Unknown). | `'M'`, `'S'`, `'U'` | Contains `'U'` for Unknown. |

| `education` | `int64` | Education level code (`1` to `4`, or `-1` for Unknown). | `3`, `-1` | \*\*Coded Missing Value:\*\* `-1` represents missing/unreported education. |

| `city\_level` | `int64` | Urban tier classification of customer's residence (`1` = Tier 1 Megacity to `5` = Tier 5/Rural, `-1` = Unknown). | `1`, `2`, `-1` | \*\*Coded Missing Value:\*\* `-1` represents unknown city tier. Crucial for geographic logistics analysis. |

| `purchase\_power` | `int64` | Estimated spending power tier (`1` = Highest to `5` = Lowest, `-1` = Unknown). | `2`, `-1` | \*\*Coded Missing Value:\*\* `-1` represents unestimated purchasing power. |

| `user\_level` | `int64` | JD loyalty tier (`0` to `4`, `10` = Corporate/Enterprise VIP, `-1` = New/Unranked). | `2`, `10`, `-1` | Note that `10` represents enterprise/corporate accounts with bulk purchasing behavior. |



\---



\## 4. `JD\_sku\_data.csv`, `JD\_network\_data.csv` \& `JD\_inventory\_data.csv`



| Table | Column | Data Type | Description | Example | Data Quality Concerns \& Analytical Implications |

| :--- | :--- | :--- | :--- | :--- | :--- |

| `JD\_sku\_data` | `sku\_id` | `string` | Unique product identifier (PK). | `a0e49f9966` | Catalog covers \~31,868 SKUs; some long-tail 3P SKUs in `JD\_order\_data` are not listed here. |

| `JD\_sku\_data` | `type` | `int64` | `1` = 1P SKU, `2` = 3P SKU. | `1`, `2` | Consistent with `JD\_order\_data.type`. |

| `JD\_sku\_data` | `brand\_ID` | `string` | Anonymized brand identifier. | `b988424d57` | Useful for brand-level Pareto and discount erosion analysis. |

| `JD\_sku\_data` | `attribute1` | `string` | Anonymized key product attribute 1 (`1`–`4` or `'-'`). | `'3'`, `'-'` | Contains coded missing value `'-'`. |

| `JD\_sku\_data` | `attribute2` | `string` | Anonymized key product attribute 2 (`30`–`100` or `'-'`). | `'60'`, `'-'` | Contains coded missing value `'-'`. |

| `JD\_sku\_data` | `activate\_date` | `string` | Date SKU became active on platform. | `2017-05-10` | Contains `'-'` when unrecorded. |

| `JD\_sku\_data` | `deactivate\_date`| `string` | Date SKU was delisted/deactivated. | `'-'` | Mostly `'-'` (meaning still active during March 2018). |

| `JD\_network\_data`| `region\_id` | `int64` | Parent Regional Distribution Center (RDC) cluster ID. | `0` to `7` | 8 major geographic logistics regions across China. |

| `JD\_network\_data`| `dc\_id` | `int64` | Distribution Center ID (PK). | `1` to `67` | 56 distinct DCs mapped to the 8 regions. |

| `JD\_inventory\_data`| `dc\_id`, `sku\_id`, `date` | `int64`, `str`, `str` | Logs 1P SKUs in stock at `dc\_id` on `date`. | `9, a0e..., 2018-03-01` | Presence-only snapshot table (if a row exists, SKU was available at that DC on that date). |

