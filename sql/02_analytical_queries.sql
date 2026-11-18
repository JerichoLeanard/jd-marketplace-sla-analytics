-- =============================================================================
-- PHASE 7: PRODUCTION ANALYTICAL SQL QUERIES
-- Demonstrates: CTEs, M:N Fan-Out Prevention, Role-Playing Joins,
--               Window Functions (ROW_NUMBER, LEAD, SUM/AVG/RANK OVER),
--               Subqueries, and Conditional Aggregations.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- QUERY 1: Solving the M:N Granularity Trap from Scratch Using Pre-Aggregated CTEs
-- Business Question: How do GMV, Net Revenue, Split-Shipment Rate, and SLA Breach
--                    Rate compare across Role-Playing Network Fulfillment Tiers?
-- -----------------------------------------------------------------------------
WITH cte_order_items_agg AS (
    -- Pre-aggregate line items to order_id grain FIRST so multi-item orders do not fan out
    SELECT
        i.order_id,
        MIN(i.order_time) AS order_time,
        MAX(i.promise_days) AS promise_days,
        MIN(i.dc_ori) AS dc_ori,
        MIN(i.dc_des) AS dc_des,
        SUM(i.gmv_line) AS order_gmv,
        SUM(i.net_revenue_line) AS order_net_rev,
        SUM(i.total_discount_line) AS order_discount
    FROM fact_order_items i
    WHERE i.is_corrupted_id = 0
    GROUP BY i.order_id
),
cte_deliveries_agg AS (
    -- Pre-aggregate package records to order_id grain SECOND so split shipments do not multiply revenue
    SELECT
        d.order_id,
        COUNT(d.package_id) AS package_count,
        MIN(d.ship_out_time) AS first_ship_out_time,
        MAX(d.dlvr_time) AS last_dlvr_time,
        AVG(d.linehaul_transit_hrs) AS avg_linehaul_hrs,
        AVG(d.lastmile_delivery_hrs) AS avg_lastmile_hrs
    FROM fact_deliveries d
    WHERE d.is_corrupted_id = 0
    GROUP BY d.order_id
),
cte_reconciled_orders AS (
    -- Join the two 1:1 order-grain CTEs and role-play dim_network twice (net_ori & net_des)
    SELECT
        o.order_id,
        o.order_gmv,
        o.order_net_rev,
        o.promise_days,
        COALESCE(d.package_count, 0) AS package_count,
        CASE
            WHEN o.dc_ori = o.dc_des THEN '1. Local DC (dc_ori = dc_des)'
            WHEN net_des.region_id = -1 THEN '4. Virtual District Spillover'
            WHEN net_ori.region_id = net_des.region_id THEN '2. Intra-Region Spillover'
            ELSE '3. Inter-Region Spillover'
        END AS network_tier,
        (JULIANDAY(d.last_dlvr_time) - JULIANDAY(o.order_time)) * 24.0 AS elapsed_fulfillment_hrs
    FROM cte_order_items_agg o
    LEFT JOIN cte_deliveries_agg d ON o.order_id = d.order_id
    INNER JOIN dim_network net_ori ON o.dc_ori = net_ori.dc_id
    INNER JOIN dim_network net_des ON o.dc_des = net_des.dc_id
)
SELECT
    network_tier,
    COUNT(order_id) AS total_orders,
    ROUND(SUM(order_gmv), 2) AS total_gmv_rmb,
    ROUND(SUM(order_net_rev), 2) AS total_net_rev_rmb,
    ROUND(AVG(CASE WHEN package_count > 1 THEN 100.0 ELSE 0.0 END), 2) AS split_shipment_pct,
    ROUND(AVG(elapsed_fulfillment_hrs), 2) AS mean_fulfillment_hrs,
    ROUND(
        AVG(
            CASE
                WHEN promise_days IS NOT NULL AND elapsed_fulfillment_hrs IS NOT NULL
                THEN CASE WHEN (elapsed_fulfillment_hrs / 24.0) > promise_days THEN 100.0 ELSE 0.0 END
            END
        ), 2
    ) AS sla_breach_rate_pct
FROM cte_reconciled_orders
GROUP BY network_tier
ORDER BY network_tier;


-- -----------------------------------------------------------------------------
-- QUERY 2: Origin Warehouse (dc_ori) Pareto Bottleneck Analysis (Window Functions)
-- Business Question (AQ1.4): Which origin warehouses drive the highest cumulative
--                            share of SLA breaches and require immediate intervention?
-- -----------------------------------------------------------------------------
WITH cte_dc_breaches AS (
    SELECT
        dc_ori,
        origin_region,
        sla_evaluated_orders,
        breached_orders,
        sla_breach_rate_pct,
        avg_warehouse_proc_hrs,
        cross_dc_spillover_pct,
        total_net_revenue_rmb
    FROM vw_warehouse_kpi_scorecard
    WHERE sla_evaluated_orders >= 500
),
cte_pareto AS (
    SELECT
        dc_ori,
        origin_region,
        sla_evaluated_orders,
        breached_orders,
        sla_breach_rate_pct,
        avg_warehouse_proc_hrs,
        cross_dc_spillover_pct,
        RANK() OVER (ORDER BY breached_orders DESC) AS breach_volume_rank,
        ROUND(
            breached_orders * 100.0 / SUM(breached_orders) OVER (), 2
        ) AS share_of_total_breaches_pct,
        ROUND(
            SUM(breached_orders) OVER (
                ORDER BY breached_orders DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0 / SUM(breached_orders) OVER (), 2
        ) AS cumulative_breach_share_pct
    FROM cte_dc_breaches
)
SELECT *
FROM cte_pareto
WHERE breach_volume_rank <= 12
ORDER BY breach_volume_rank;


-- -----------------------------------------------------------------------------
-- QUERY 3: Daily Promotional Surge Stress Test with 7-Day Moving Averages
-- Business Question: How do promotional discount spikes impact daily order surges,
--                    warehouse dispatch backlogs, and SLA breaches?
-- -----------------------------------------------------------------------------
WITH cte_daily AS (
    SELECT
        order_date,
        COUNT(order_id) AS daily_orders,
        ROUND(SUM(gmv_order), 2) AS daily_gmv,
        ROUND(SUM(total_discount_order) * 100.0 / NULLIF(SUM(gmv_order), 0), 2) AS discount_rate_pct,
        ROUND(AVG(warehouse_proc_hrs), 2) AS avg_warehouse_hrs,
        ROUND(AVG(is_sla_breach) * 100.0, 2) AS sla_breach_pct
    FROM fact_orders_header
    GROUP BY order_date
)
SELECT
    order_date,
    daily_orders,
    ROUND(
        AVG(daily_orders) OVER (
            ORDER BY order_date
            ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
        ), 0
    ) AS centered_7d_avg_orders,
    discount_rate_pct,
    avg_warehouse_hrs,
    sla_breach_pct,
    RANK() OVER (ORDER BY sla_breach_pct DESC) AS worst_sla_day_rank
FROM cte_daily
ORDER BY sla_breach_pct DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- QUERY 4: 1P Inventory Stockout Attribution by Network Fulfillment Tier
-- Business Question: What percentage of 1P Cross-DC shipments were triggered
--                    because the ordered SKU was out of stock at dc_des?
-- -----------------------------------------------------------------------------
WITH cte_tracked_skus AS (
    SELECT DISTINCT sku_id FROM fact_inventory
)
SELECT
    i.fulfillment_network_tier,
    COUNT(*) AS tracked_1p_order_lines,
    SUM(CASE WHEN inv.sku_id IS NOT NULL THEN 1 ELSE 0 END) AS dest_dc_in_stock_lines,
    SUM(CASE WHEN inv.sku_id IS NULL THEN 1 ELSE 0 END) AS dest_dc_stocked_out_lines,
    ROUND(
        SUM(CASE WHEN inv.sku_id IS NULL THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2
    ) AS dest_dc_stockout_rate_pct
FROM fact_order_items i
INNER JOIN cte_tracked_skus ts ON i.sku_id = ts.sku_id
LEFT JOIN fact_inventory inv
    ON i.dc_des = inv.dc_id
   AND i.sku_id = inv.sku_id
   AND i.order_date = inv.date
WHERE i.type = 1
GROUP BY i.fulfillment_network_tier
ORDER BY i.fulfillment_network_tier;


-- -----------------------------------------------------------------------------
-- QUERY 5: Controlled Longitudinal Retention & Next-Order Lag Analysis
--          (Using ROW_NUMBER() and LEAD() Window Functions)
-- Business Question: Controlling for Promise Tier (1-2 Day Express SLA) and
--                    JD PLUS VIP Status, how does an Order #1 SLA Breach affect
--                    repeat conversion, days to Order #2, and Order #2 spend?
-- -----------------------------------------------------------------------------
WITH cte_sequenced_orders AS (
    SELECT
        o.user_id,
        u.plus_label,
        o.order_id,
        o.order_date,
        o.order_time,
        o.promise_days,
        o.is_sla_breach,
        o.net_revenue_order,
        ROW_NUMBER() OVER (PARTITION BY o.user_id ORDER BY o.order_time) AS order_seq_num,
        COUNT(o.order_id) OVER (PARTITION BY o.user_id) AS user_total_march_orders,
        LEAD(o.order_time) OVER (PARTITION BY o.user_id ORDER BY o.order_time) AS next_order_time,
        LEAD(o.net_revenue_order) OVER (PARTITION BY o.user_id ORDER BY o.order_time) AS next_order_net_rev
    FROM fact_orders_header o
    INNER JOIN dim_users u ON o.user_id = u.user_id
    WHERE o.is_corrupted_order_id = 0
)
SELECT
    plus_label,
    CASE
        WHEN is_sla_breach = 1.0 THEN 'Order #1 SLA Breached (Late)'
        ELSE 'Order #1 On-Time / Early'
    END AS first_order_sla_experience,
    COUNT(user_id) AS cohort_buyers,
    SUM(CASE WHEN user_total_march_orders >= 2 THEN 1 ELSE 0 END) AS repeat_buyers,
    ROUND(
        AVG(CASE WHEN user_total_march_orders >= 2 THEN 100.0 ELSE 0.0 END), 2
    ) AS repeat_purchase_rate_pct,
    ROUND(
        AVG((JULIANDAY(next_order_time) - JULIANDAY(order_time))), 2
    ) AS avg_days_to_second_order,
    ROUND(AVG(net_revenue_order), 2) AS avg_first_order_spend_rmb,
    ROUND(AVG(next_order_net_rev), 2) AS avg_second_order_spend_rmb
FROM cte_sequenced_orders
WHERE order_seq_num = 1
  AND order_date <= '2018-03-15'       -- Right-censoring control (min 16-day follow-up window)
  AND promise_days IN (1.0, 2.0)       -- Control for confounders: 1-2 Day Express SLA Cohort
  AND is_sla_breach IS NOT NULL
GROUP BY plus_label, first_order_sla_experience
ORDER BY plus_label, first_order_sla_experience;


-- -----------------------------------------------------------------------------
-- QUERY 6: Subquery & HAVING — High Discount-Erosion & High Spillover Brands
-- Business Question: Which high-volume brands (>= 1,000 paid units) suffer from
--                    BOTH above-average discount depth AND >50% Cross-DC spillover?
-- -----------------------------------------------------------------------------
SELECT
    s.brand_id,
    i.seller_type,
    COUNT(DISTINCT i.order_id) AS distinct_orders,
    SUM(i.paid_quantity) AS total_paid_units,
    ROUND(SUM(i.gmv_line), 2) AS total_gmv_rmb,
    ROUND(SUM(i.net_revenue_line), 2) AS total_net_rev_rmb,
    ROUND(SUM(i.total_discount_line) * 100.0 / NULLIF(SUM(i.gmv_line), 0), 2) AS brand_discount_depth_pct,
    ROUND(AVG(i.is_cross_dc) * 100.0, 2) AS cross_dc_spillover_pct
FROM fact_order_items i
INNER JOIN dim_skus s ON i.sku_id = s.sku_id
WHERE i.gift_item = 0
GROUP BY s.brand_id, i.seller_type
HAVING SUM(i.paid_quantity) >= 1000
   AND (SUM(i.total_discount_line) * 1.0 / NULLIF(SUM(i.gmv_line), 0)) > (
       SELECT SUM(total_discount_line) * 1.0 / SUM(gmv_line)
       FROM fact_order_items
       WHERE gift_item = 0
   )
   AND AVG(i.is_cross_dc) > 0.50
ORDER BY total_gmv_rmb DESC
LIMIT 12;