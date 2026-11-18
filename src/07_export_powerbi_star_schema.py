"""
Phase 9: Power BI Star Schema Exporter & Date Dimension Generator
Project: JD.com Marketplace Fulfillment SLA, Unit Economics & Retention Analytics
Purpose: Exports a dedicated, VertiPaq-optimized Star Schema into data/powerbi/
         including dim_date.csv, dim_network.csv, dim_customers_pbi.csv,
         dim_brand_risk.csv, and fact_orders_pbi.csv for fast Power BI modeling.
"""

import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PBI_DIR = PROJECT_ROOT / "data" / "powerbi"
DB_PATH = PROCESSED_DIR / "jd_marketplace.db"

PBI_DIR.mkdir(parents=True, exist_ok=True)


def build_dim_date():
    print("[1/5] Generating Calendar Date Dimension (dim_date.csv)...")
    dates = pd.date_range(start="2018-03-01", end="2018-03-31", freq="D")
    promo_peak_dates = {"2018-03-01", "2018-03-02", "2018-03-07", "2018-03-08", "2018-03-09"}

    dim_date = pd.DataFrame({"order_date": dates.strftime("%Y-%m-%d")})
    dim_date["date_key"] = dates.strftime("%Y%m%d").astype(int)
    dim_date["day_of_month"] = dates.day
    dim_date["day_name"] = dates.strftime("%a")
    dim_date["day_of_week_num"] = dates.dayofweek + 1  # 1=Mon .. 7=Sun
    dim_date["week_of_month"] = ((dates.day - 1) // 7) + 1
    dim_date["is_weekend"] = np.where(dates.dayofweek >= 5, "Weekend", "Weekday")
    dim_date["promo_regime"] = np.where(
        dim_date["order_date"].isin(promo_peak_dates),
        "Promotional Peak Window",
        "Baseline Operating Day",
    )
    dim_date.to_csv(PBI_DIR / "dim_date.csv", index=False)
    print(f"   -> Saved data/powerbi/dim_date.csv ({len(dim_date)} days)")


def export_dimensions_and_facts():
    with sqlite3.connect(DB_PATH) as conn:
        # 2. Export dim_network.csv
        print("[2/5] Exporting Logistics Network Dimension (dim_network.csv)...")
        dim_net = pd.read_sql_query("SELECT * FROM dim_network;", conn)
        dim_net["dc_display_name"] = "DC " + dim_net["dc_id"].astype(str) + " (" + dim_net["region_label"] + ")"
        dim_net.to_csv(PBI_DIR / "dim_network.csv", index=False)
        print(f"   -> Saved data/powerbi/dim_network.csv ({len(dim_net)} network nodes)")

        # 3. Export dim_customers_pbi.csv (Active Buyers with Value Segment & Longitudinal Spend)
        print("[3/5] Exporting Enriched Customer Dimension (dim_customers_pbi.csv)...")
        sql_cust = """
        WITH cte_seq AS (
            SELECT
                o.user_id,
                o.order_date,
                o.promise_days,
                o.is_sla_breach,
                o.net_revenue_order,
                ROW_NUMBER() OVER (PARTITION BY o.user_id ORDER BY o.order_time) AS seq_num,
                COUNT(o.order_id) OVER (PARTITION BY o.user_id) AS march_orders,
                SUM(o.net_revenue_order) OVER (PARTITION BY o.user_id) AS total_net_rev,
                MAX(CASE WHEN o.is_sla_breach = 1.0 THEN 1 ELSE 0 END) OVER (PARTITION BY o.user_id) AS experienced_sla_breach,
                LEAD(o.net_revenue_order) OVER (PARTITION BY o.user_id ORDER BY o.order_time) AS second_order_net_rev,
                LEAD(o.order_time) OVER (PARTITION BY o.user_id ORDER BY o.order_time) AS second_order_time,
                o.order_time AS first_order_time
            FROM fact_orders_header o
            WHERE o.is_corrupted_order_id = 0
        )
        SELECT
            u.user_id,
            u.plus,
            u.plus_label,
            u.gender_clean,
            u.age_clean,
            u.marital_clean,
            u.city_level,
            u.city_tier_label,
            u.purchase_power,
            u.user_level,
            s.march_orders,
            ROUND(s.total_net_rev, 2) AS total_net_rev,
            s.experienced_sla_breach,
            s.order_date AS first_order_date,
            s.promise_days AS first_order_promise_days,
            s.is_sla_breach AS first_order_sla_breach,
            ROUND(s.net_revenue_order, 2) AS first_order_spend_rmb,
            ROUND(s.second_order_net_rev, 2) AS second_order_spend_rmb,
            ROUND((JULIANDAY(s.second_order_time) - JULIANDAY(s.first_order_time)), 2) AS days_to_second_order
        FROM dim_users u
        INNER JOIN cte_seq s ON u.user_id = s.user_id
        WHERE s.seq_num = 1;
        """
        cust = pd.read_sql_query(sql_cust, conn)
        conds = [
            (cust["plus_label"] == "JD PLUS VIP") & (cust["march_orders"] >= 2),
            (cust["plus_label"] == "JD PLUS VIP") & (cust["march_orders"] == 1),
            (cust["plus_label"] == "Regular Member") & (cust["march_orders"] >= 2),
            (cust["plus_label"] == "Regular Member") & (cust["march_orders"] == 1) & (cust["total_net_rev"] >= 100),
            (cust["plus_label"] == "Regular Member") & (cust["march_orders"] == 1) & (cust["total_net_rev"] < 100),
        ]
        segs = [
            "1. VIP Champions (JD PLUS, 2+ Orders)",
            "2. VIP Single-Order (JD PLUS, 1 Order)",
            "3. Regular Loyalists (Regular, 2+ Orders)",
            "4. High-Ticket Single Buyers (Regular, >=100 RMB)",
            "5. Baseline Single Buyers (Regular, <100 RMB)",
        ]
        cust["customer_segment"] = np.select(conds, segs, default="Other")
        cust["is_repeat_buyer"] = (cust["march_orders"] >= 2).astype(int)
        cust["first_order_sla_status"] = np.where(
            cust["first_order_sla_breach"].isna(),
            "Unpromised / 3P Courier",
            np.where(cust["first_order_sla_breach"] == 1.0, "SLA Breached (Late)", "On-Time / Early"),
        )
        cust.to_csv(PBI_DIR / "dim_customers_pbi.csv", index=False)
        print(f"   -> Saved data/powerbi/dim_customers_pbi.csv ({len(cust):,} active buyers)")

        # 4. Export dim_brand_risk.csv (Brand Unit Economics Quadrant Summary)
        print("[4/5] Exporting Brand Unit-Economics Risk Table (dim_brand_risk.csv)...")
        sql_brands = """
        SELECT
            s.brand_id,
            i.seller_type,
            COUNT(DISTINCT i.order_id) AS distinct_orders,
            SUM(i.paid_quantity) AS paid_units,
            ROUND(SUM(i.gmv_line), 2) AS gmv_rmb,
            ROUND(SUM(i.net_revenue_line), 2) AS net_rev_rmb,
            ROUND(SUM(i.total_discount_line), 2) AS discount_rmb,
            ROUND(SUM(i.total_discount_line) * 100.0 / NULLIF(SUM(i.gmv_line), 0), 2) AS disc_depth_pct,
            ROUND(AVG(i.is_cross_dc) * 100.0, 2) AS cross_dc_pct
        FROM fact_order_items i
        INNER JOIN dim_skus s ON i.sku_id = s.sku_id
        WHERE i.gift_item = 0
        GROUP BY s.brand_id, i.seller_type
        HAVING SUM(i.paid_quantity) >= 500;
        """
        brands = pd.read_sql_query(sql_brands, conn)
        b_conds = [
            (brands["disc_depth_pct"] > 31.91) & (brands["cross_dc_pct"] > 47.76),
            (brands["disc_depth_pct"] <= 31.91) & (brands["cross_dc_pct"] > 47.76),
            (brands["disc_depth_pct"] > 31.91) & (brands["cross_dc_pct"] <= 47.76),
            (brands["disc_depth_pct"] <= 31.91) & (brands["cross_dc_pct"] <= 47.76),
        ]
        b_quads = [
            "Q1: Double Bleeders (High Discount + High Cross-DC)",
            "Q2: Logistics Bottleneck (Low Discount + High Cross-DC)",
            "Q3: Promo Heavy (High Discount + Local DC)",
            "Q4: Healthy Core (Controlled Discount + Local DC)",
        ]
        brands["risk_quadrant"] = np.select(b_conds, b_quads, default="Other")
        brands.to_csv(PBI_DIR / "dim_brand_risk.csv", index=False)
        print(f"   -> Saved data/powerbi/dim_brand_risk.csv ({len(brands):,} volume brand-models)")

        # 5. Export fact_orders_pbi.csv & fact_1p_stockout_summary.csv
        print("[5/5] Exporting Order Header Fact Table (fact_orders_pbi.csv) & 1P Stockout Summary...")
        fact_orders = pd.read_sql_query(
            """
            SELECT
                o.order_id,
                o.user_id,
                o.order_date,
                o.type,
                o.seller_type,
                o.has_explicit_sla,
                o.promise_days,
                o.dc_ori,
                n_ori.region_label AS origin_region_label,
                o.dc_des,
                n_des.region_label AS dest_region_label,
                o.is_cross_dc,
                o.fulfillment_network_tier,
                o.line_item_count,
                o.paid_units,
                o.gift_units,
                o.has_gift_item,
                o.gmv_order,
                o.net_revenue_order,
                o.total_discount_order,
                o.direct_discount_order,
                o.quantity_discount_order,
                o.bundle_discount_order,
                o.coupon_discount_order,
                o.package_count,
                o.has_delivery_telemetry,
                o.is_split_shipment,
                o.warehouse_proc_hrs,
                o.linehaul_transit_hrs,
                o.lastmile_delivery_hrs,
                o.total_fulfillment_hrs,
                o.total_fulfillment_days,
                o.sla_delay_days,
                o.is_sla_breach
            FROM fact_orders_header o
            LEFT JOIN dim_network n_ori ON o.dc_ori = n_ori.dc_id
            LEFT JOIN dim_network n_des ON o.dc_des = n_des.dc_id
            WHERE o.is_corrupted_order_id = 0;
            """,
            conn,
        )
        fact_orders["sla_status_label"] = np.where(
            fact_orders["is_sla_breach"].isna(),
            "Unpromised / External 3P",
            np.where(fact_orders["is_sla_breach"] == 1.0, "SLA Breached (Late)", "On-Time / Early"),
        )
        fact_orders.to_csv(PBI_DIR / "fact_orders_pbi.csv", index=False)
        print(f"   -> Saved data/powerbi/fact_orders_pbi.csv ({len(fact_orders):,} valid orders)")

        sql_stock = """
        WITH cte_tracked_skus AS (SELECT DISTINCT sku_id FROM fact_inventory)
        SELECT
            i.fulfillment_network_tier,
            i.dc_ori,
            i.dc_des,
            CASE WHEN inv.sku_id IS NULL THEN 'Stocked Out at Destination DC' ELSE 'In Stock at Destination DC' END AS dest_stock_status,
            COUNT(*) AS order_line_count,
            ROUND(SUM(i.net_revenue_line), 2) AS net_revenue_rmb
        FROM fact_order_items i
        INNER JOIN cte_tracked_skus ts ON i.sku_id = ts.sku_id
        LEFT JOIN fact_inventory inv
            ON i.dc_des = inv.dc_id AND i.sku_id = inv.sku_id AND i.order_date = inv.date
        WHERE i.type = 1
        GROUP BY i.fulfillment_network_tier, i.dc_ori, i.dc_des, dest_stock_status;
        """
        df_stock = pd.read_sql_query(sql_stock, conn)
        df_stock.to_csv(PBI_DIR / "fact_1p_stockout_audit.csv", index=False)
        print(f"   -> Saved data/powerbi/fact_1p_stockout_audit.csv ({len(df_stock):,} aggregated route-stock rows)")


if __name__ == "__main__":
    print("=" * 90)
    print("STARTING PHASE 9 POWER BI STAR-SCHEMA EXPORT PIPELINE")
    print("=" * 90)
    build_dim_date()
    export_dimensions_and_facts()
    print("=" * 90)
    print(f"COMPLETE! All Power BI Star Schema files are ready in: {PBI_DIR}")
    print("=" * 90)