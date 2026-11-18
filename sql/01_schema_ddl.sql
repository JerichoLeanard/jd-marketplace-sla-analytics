-- =============================================================================
-- PHASE 7: RELATIONAL DATABASE SCHEMA (DDL), INDEXES & ANALYTICAL VIEWS
-- Database Engine: SQLite 3 (jd_marketplace.db)
-- =============================================================================

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS vw_order_sla_economics;
DROP VIEW IF EXISTS vw_warehouse_kpi_scorecard;
DROP VIEW IF EXISTS vw_customer_order_sequence;

DROP TABLE IF EXISTS fact_inventory;
DROP TABLE IF EXISTS fact_deliveries;
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS fact_orders_header;
DROP TABLE IF EXISTS dim_users;
DROP TABLE IF EXISTS dim_skus;
DROP TABLE IF EXISTS dim_network;

CREATE TABLE dim_network (
    dc_id                 INTEGER PRIMARY KEY,
    region_id             INTEGER,
    is_physical_warehouse INTEGER,
    region_label          TEXT
);

CREATE TABLE dim_skus (
    sku_id          TEXT PRIMARY KEY,
    type            INTEGER,
    brand_id        TEXT,
    attribute1      TEXT,
    attribute2      TEXT,
    activate_date   TEXT,
    deactivate_date TEXT,
    seller_type     TEXT
);

CREATE TABLE dim_users (
    user_id           TEXT PRIMARY KEY,
    user_level        INTEGER,
    first_order_month TEXT,
    plus              INTEGER,
    gender            TEXT,
    age               TEXT,
    marital_status    TEXT,
    education         INTEGER,
    city_level        INTEGER,
    purchase_power    INTEGER,
    plus_label        TEXT,
    gender_clean      TEXT,
    age_clean         TEXT,
    marital_clean     TEXT,
    city_tier_label   TEXT
);

CREATE TABLE fact_orders_header (
    order_id                 TEXT PRIMARY KEY,
    user_id                  TEXT,
    order_date               TEXT,
    order_time               TEXT,
    type                     INTEGER,
    seller_type              TEXT,
    has_explicit_sla         INTEGER,
    promise_days             REAL,
    dc_ori                   INTEGER,
    dc_des                   INTEGER,
    ori_region_id            INTEGER,
    des_region_id            INTEGER,
    is_cross_dc              INTEGER,
    fulfillment_network_tier TEXT,
    line_item_count          INTEGER,
    unique_sku_count         INTEGER,
    paid_units               INTEGER,
    gift_units               INTEGER,
    has_gift_item            INTEGER,
    gmv_order                REAL,
    net_revenue_order        REAL,
    total_discount_order     REAL,
    direct_discount_order    REAL,
    quantity_discount_order  REAL,
    bundle_discount_order    REAL,
    coupon_discount_order    REAL,
    is_corrupted_order_id    INTEGER,
    effective_discount_rate  REAL,
    package_count            INTEGER,
    first_ship_out_time      TEXT,
    last_station_arr_time    TEXT,
    last_dlvr_time           TEXT,
    linehaul_transit_hrs     REAL,
    lastmile_delivery_hrs    REAL,
    has_chronology_anomaly   REAL,
    has_delivery_telemetry   INTEGER,
    is_split_shipment        INTEGER,
    warehouse_proc_hrs       REAL,
    total_fulfillment_hrs    REAL,
    total_fulfillment_days   REAL,
    sla_delay_days           REAL,
    is_sla_breach            REAL,
    FOREIGN KEY (dc_ori) REFERENCES dim_network(dc_id),
    FOREIGN KEY (dc_des) REFERENCES dim_network(dc_id)
);

CREATE TABLE fact_order_items (
    order_item_sk              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id                   TEXT,
    user_id                    TEXT,
    sku_id                     TEXT,
    order_date                 TEXT,
    order_time                 TEXT,
    quantity                   INTEGER,
    type                       INTEGER,
    promise                    TEXT,
    original_unit_price        REAL,
    final_unit_price           REAL,
    direct_discount_per_unit   REAL,
    quantity_discount_per_unit REAL,
    bundle_discount_per_unit   REAL,
    coupon_discount_per_unit   REAL,
    gift_item                  INTEGER,
    dc_ori                     INTEGER,
    dc_des                     INTEGER,
    is_corrupted_id            INTEGER,
    seller_type                TEXT,
    promise_raw                TEXT,
    has_explicit_sla           INTEGER,
    promise_days               REAL,
    has_negative_gift_price    INTEGER,
    final_unit_price_clean     REAL,
    paid_quantity              INTEGER,
    gift_quantity              INTEGER,
    gmv_line                   REAL,
    net_revenue_line           REAL,
    direct_discount_line       REAL,
    quantity_discount_line     REAL,
    bundle_discount_line       REAL,
    coupon_discount_line       REAL,
    total_discount_line        REAL,
    ori_region_id              INTEGER,
    des_region_id              INTEGER,
    is_cross_dc                INTEGER,
    fulfillment_network_tier   TEXT,
    FOREIGN KEY (order_id) REFERENCES fact_orders_header(order_id),
    FOREIGN KEY (dc_ori)   REFERENCES dim_network(dc_id),
    FOREIGN KEY (dc_des)   REFERENCES dim_network(dc_id)
);

CREATE TABLE fact_deliveries (
    package_id             TEXT PRIMARY KEY,
    order_id               TEXT,
    type                   INTEGER,
    ship_out_time          TEXT,
    arr_station_time       TEXT,
    dlvr_time              TEXT,
    seller_type            TEXT,
    is_corrupted_id        INTEGER,
    is_chronology_anomaly  INTEGER,
    linehaul_transit_hrs   REAL,
    lastmile_delivery_hrs  REAL,
    carrier_total_hrs      REAL
);

CREATE TABLE fact_inventory (
    dc_id  INTEGER,
    sku_id TEXT,
    date   TEXT,
    PRIMARY KEY (dc_id, sku_id, date),
    FOREIGN KEY (dc_id) REFERENCES dim_network(dc_id)
);

CREATE INDEX idx_orders_hdr_user_time ON fact_orders_header(user_id, order_time);
CREATE INDEX idx_orders_hdr_dc_ori    ON fact_orders_header(dc_ori);
CREATE INDEX idx_orders_hdr_dc_des    ON fact_orders_header(dc_des);
CREATE INDEX idx_orders_hdr_date      ON fact_orders_header(order_date);
CREATE INDEX idx_order_items_order    ON fact_order_items(order_id);
CREATE INDEX idx_order_items_sku      ON fact_order_items(sku_id);
CREATE INDEX idx_order_items_stock    ON fact_order_items(dc_des, sku_id, order_date);
CREATE INDEX idx_deliveries_order     ON fact_deliveries(order_id);

CREATE VIEW vw_order_sla_economics AS
SELECT
    o.order_id,
    o.user_id,
    o.order_date,
    o.order_time,
    o.seller_type,
    o.has_explicit_sla,
    o.promise_days,
    o.dc_ori,
    net_ori.region_label AS origin_region_name,
    o.dc_des,
    net_des.region_label AS dest_region_name,
    o.is_cross_dc,
    o.fulfillment_network_tier,
    u.plus_label,
    u.city_tier_label,
    u.user_level,
    o.paid_units,
    o.gift_units,
    o.gmv_order,
    o.net_revenue_order,
    o.total_discount_order,
    o.effective_discount_rate,
    o.package_count,
    o.is_split_shipment,
    o.warehouse_proc_hrs,
    o.linehaul_transit_hrs,
    o.lastmile_delivery_hrs,
    o.total_fulfillment_hrs,
    o.total_fulfillment_days,
    o.sla_delay_days,
    o.is_sla_breach
FROM fact_orders_header o
LEFT JOIN dim_users u     ON o.user_id = u.user_id
LEFT JOIN dim_network net_ori ON o.dc_ori = net_ori.dc_id
LEFT JOIN dim_network net_des ON o.dc_des = net_des.dc_id;

CREATE VIEW vw_warehouse_kpi_scorecard AS
SELECT
    o.dc_ori,
    n.region_label AS origin_region,
    COUNT(o.order_id) AS total_orders,
    SUM(CASE WHEN o.is_sla_breach IS NOT NULL THEN 1 ELSE 0 END) AS sla_evaluated_orders,
    SUM(CASE WHEN o.is_sla_breach = 1.0 THEN 1 ELSE 0 END) AS breached_orders,
    ROUND(AVG(o.is_sla_breach) * 100.0, 2) AS sla_breach_rate_pct,
    ROUND(AVG(o.warehouse_proc_hrs), 2) AS avg_warehouse_proc_hrs,
    ROUND(AVG(o.linehaul_transit_hrs), 2) AS avg_linehaul_hrs,
    ROUND(AVG(o.lastmile_delivery_hrs), 2) AS avg_lastmile_hrs,
    ROUND(AVG(o.is_cross_dc) * 100.0, 2) AS cross_dc_spillover_pct,
    ROUND(SUM(o.net_revenue_order), 2) AS total_net_revenue_rmb
FROM fact_orders_header o
JOIN dim_network n ON o.dc_ori = n.dc_id
GROUP BY o.dc_ori, n.region_label;