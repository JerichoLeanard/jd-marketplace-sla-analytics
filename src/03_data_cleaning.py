"""
Phase 5: Production Data Cleaning, Standardization & Grain Alignment Pipeline
Project: JD.com Marketplace Fulfillment SLA, Unit Economics & Retention Analytics
Purpose: Reads untouched raw CSVs from data/raw/, executes transformations T1-T10,
         exports audit logs to data/interim/, and saves cleaned relational & Star-Schema
         tables to data/processed/.
"""

from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INTERIM_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_raw_csv(filename: str) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / filename, low_memory=False)
    # T1: Standardize column headers to lowercase snake_case
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def clean_network_and_orders(net_raw: pd.DataFrame, orders_raw: pd.DataFrame):
    print("\n[STEP 1] Cleaning JD_network_data & Enriching Unmapped Destination DCs (T8)...")
    net = net_raw.copy()
    net["is_physical_warehouse"] = 1
    net["region_label"] = "Region " + net["region_id"].astype(str)

    # Identify unmapped dc_des IDs in orders
    known_dcs = set(net["dc_id"].unique())
    all_order_dcs = set(orders_raw["dc_ori"].unique()).union(set(orders_raw["dc_des"].unique()))
    unmapped_dcs = sorted(list(all_order_dcs - known_dcs))

    if unmapped_dcs:
        virtual_df = pd.DataFrame({
            "region_id": [-1] * len(unmapped_dcs),
            "dc_id": unmapped_dcs,
            "is_physical_warehouse": [0] * len(unmapped_dcs),
            "region_label": ["Virtual Destination District"] * len(unmapped_dcs),
        })
        net_clean = pd.concat([net, virtual_df], ignore_index=True).sort_values("dc_id").reset_index(drop=True)
    else:
        net_clean = net.copy()

    print(f" - Raw Network DCs: {len(net_raw)} | Cleaned Network DCs (with virtual districts): {len(net_clean)}")
    assert net_clean["dc_id"].is_unique, "dc_id must be unique in dim_network_clean!"
    net_clean.to_csv(PROCESSED_DIR / "dim_network_clean.csv", index=False)
    return net_clean


def clean_skus(skus_raw: pd.DataFrame) -> pd.DataFrame:
    print("\n[STEP 2] Cleaning JD_sku_data (T4, T5, T6)...")
    skus = skus_raw.copy()

    # T4: Export and resolve duplicate sku_id ('de9ed6156d')
    dup_skus = skus[skus["sku_id"].duplicated(keep=False)]
    dup_skus.to_csv(INTERIM_DIR / "audit_duplicate_skus.csv", index=False)
    skus = skus.drop_duplicates(subset=["sku_id"], keep="first").reset_index(drop=True)

    # T5 & T6: Standardize seller type and coded '-' attributes
    skus["seller_type"] = np.where(skus["type"] == 1, "1P Self-Operated", "3P Marketplace")
    for attr_col in ["attribute1", "attribute2"]:
        skus[attr_col] = skus[attr_col].astype(str).str.strip().replace({"-": "Unknown", "nan": "Unknown"})

    print(f" - Raw SKU rows: {len(skus_raw):,} | Cleaned unique SKUs: {len(skus):,}")
    assert skus["sku_id"].is_unique, "sku_id must be unique in dim_skus_clean!"
    skus.to_csv(PROCESSED_DIR / "dim_skus_clean.csv", index=False)
    return skus


def clean_users(users_raw: pd.DataFrame) -> pd.DataFrame:
    print("\n[STEP 3] Cleaning JD_user_data (T6: Coded Missing Values -1 & 'U')...")
    users = users_raw.copy()

    users["plus_label"] = np.where(users["plus"] == 1, "JD PLUS VIP", "Regular Member")
    users["gender_clean"] = users["gender"].astype(str).str.strip().replace({"U": "Unknown", "F": "Female", "M": "Male"})
    users["age_clean"] = users["age"].astype(str).str.strip().replace({"U": "Unknown"})
    users["marital_clean"] = users["marital_status"].astype(str).str.strip().replace(
        {"U": "Unknown", "M": "Married", "S": "Single"}
    )

    city_map = {
        1: "Tier 1 (Megacity)",
        2: "Tier 2 (Provincial Capital)",
        3: "Tier 3 (Prefecture City)",
        4: "Tier 4 (County City)",
        5: "Tier 5 (Township/Rural)",
        -1: "Unknown Tier",
    }
    users["city_tier_label"] = users["city_level"].map(city_map).fillna("Unknown Tier")

    print(f" - Cleaned unique users: {len(users):,}")
    assert users["user_id"].is_unique, "user_id must be unique in dim_users_clean!"
    users.to_csv(PROCESSED_DIR / "dim_users_clean.csv", index=False)
    return users


def clean_deliveries(delivery_raw: pd.DataFrame) -> pd.DataFrame:
    print("\n[STEP 4] Cleaning JD_delivery_data (T1, T3, T5, T9)...")
    deliv = delivery_raw.copy()

    # T1: Rename arr_time -> dlvr_time for unambiguous stage naming
    deliv = deliv.rename(columns={"arr_time": "dlvr_time"})

    # T5: Standardize type=0 -> type=2 (3P Marketplace)
    deliv["type"] = deliv["type"].replace({0: 2})
    deliv["seller_type"] = np.where(deliv["type"] == 1, "1P Self-Operated", "3P Marketplace")

    # T3: Detect scientific notation hash corruption ('4.99E+54')
    deliv["is_corrupted_id"] = (
        deliv["package_id"].astype(str).str.contains(r"E\+|inf", case=False, regex=True)
        | deliv["order_id"].astype(str).str.contains(r"E\+|inf", case=False, regex=True)
    ).astype(int)

    # Disambiguate duplicate package_id caused by scientific notation so PK is 100% unique
    dup_pkg_mask = deliv["package_id"].duplicated(keep=False)
    if dup_pkg_mask.any():
        deliv.loc[dup_pkg_mask].to_csv(INTERIM_DIR / "audit_duplicate_packages.csv", index=False)
        deliv.loc[dup_pkg_mask, "package_id"] = (
            deliv.loc[dup_pkg_mask, "package_id"].astype(str)
            + "_dup_"
            + deliv.loc[dup_pkg_mask].index.astype(str)
        )

    # T9: Parse timestamps & calculate stage durations in hours
    for col in ["ship_out_time", "arr_station_time", "dlvr_time"]:
        deliv[col] = pd.to_datetime(deliv[col], errors="coerce")

    raw_linehaul_hrs = (deliv["arr_station_time"] - deliv["ship_out_time"]).dt.total_seconds() / 3600.0
    raw_lastmile_hrs = (deliv["dlvr_time"] - deliv["arr_station_time"]).dt.total_seconds() / 3600.0
    raw_carrier_hrs = (deliv["dlvr_time"] - deliv["ship_out_time"]).dt.total_seconds() / 3600.0

    deliv["is_chronology_anomaly"] = ((raw_linehaul_hrs < 0) | (raw_lastmile_hrs < 0) | (raw_carrier_hrs < 0)).astype(int)
    deliv.loc[deliv["is_chronology_anomaly"] == 1].to_csv(
        INTERIM_DIR / "audit_delivery_chronology_anomalies.csv", index=False
    )

    # Nullify negative stage durations so they do not corrupt average lead-time KPIs
    deliv["linehaul_transit_hrs"] = np.where(raw_linehaul_hrs >= 0, raw_linehaul_hrs, np.nan).round(2)
    deliv["lastmile_delivery_hrs"] = np.where(raw_lastmile_hrs >= 0, raw_lastmile_hrs, np.nan).round(2)
    deliv["carrier_total_hrs"] = np.where(raw_carrier_hrs >= 0, raw_carrier_hrs, np.nan).round(2)

    print(
        f" - Cleaned Packages: {len(deliv):,} | Chronology Anomalies Flagged: "
        f"{deliv['is_chronology_anomaly'].sum():,} | Corrupted IDs Flagged: {deliv['is_corrupted_id'].sum():,}"
    )
    assert deliv["package_id"].is_unique, "package_id must be unique in fact_deliveries_clean!"
    deliv.to_csv(PROCESSED_DIR / "fact_deliveries_clean.csv", index=False)
    return deliv


def clean_orders_and_build_header(
    orders_raw: pd.DataFrame, net_clean: pd.DataFrame, deliv_clean: pd.DataFrame
):
    print("\n[STEP 5] Cleaning JD_order_data & Deriving Financial / Network Metrics (T2, T6, T7, T8)...")
    orders = orders_raw.copy()

    # T2: Export and remove 3,928 exact duplicate rows
    dup_orders = orders[orders.duplicated(keep="first")]
    dup_orders.to_csv(INTERIM_DIR / "audit_duplicate_order_rows.csv", index=False)
    orders = orders.drop_duplicates(keep="first").reset_index(drop=True)

    # T3: Flag scientific notation corrupted order_id / sku_id
    orders["is_corrupted_id"] = (
        orders["order_id"].astype(str).str.contains(r"E\+|inf", case=False, regex=True)
        | orders["sku_id"].astype(str).str.contains(r"E\+|inf", case=False, regex=True)
    ).astype(int)

    # Parse timestamps
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce").dt.date
    orders["order_time"] = pd.to_datetime(orders["order_time"], errors="coerce")

    # T5 & T6: Standardize seller_type and promise SLA
    orders["seller_type"] = np.where(orders["type"] == 1, "1P Self-Operated", "3P Marketplace")
    orders["promise_raw"] = orders["promise"].astype(str).str.strip()
    orders["has_explicit_sla"] = (orders["promise_raw"] != "-").astype(int)
    orders["promise_days"] = pd.to_numeric(orders["promise_raw"], errors="coerce")

    # T7: Separate Paid Items (gift_item == 0) from Promotional Gifts (gift_item == 1)
    orders["has_negative_gift_price"] = (orders["final_unit_price"] < 0).astype(int)
    orders["final_unit_price_clean"] = np.maximum(orders["final_unit_price"], 0.0)

    is_paid = orders["gift_item"] == 0
    orders["paid_quantity"] = np.where(is_paid, orders["quantity"], 0)
    orders["gift_quantity"] = np.where(~is_paid, orders["quantity"], 0)

    orders["gmv_line"] = np.where(is_paid, orders["original_unit_price"] * orders["quantity"], 0.0).round(2)
    orders["net_revenue_line"] = np.where(is_paid, orders["final_unit_price_clean"] * orders["quantity"], 0.0).round(2)

    orders["direct_discount_line"] = np.where(is_paid, orders["direct_discount_per_unit"] * orders["quantity"], 0.0).round(2)
    orders["quantity_discount_line"] = np.where(is_paid, orders["quantity_discount_per_unit"] * orders["quantity"], 0.0).round(2)
    orders["bundle_discount_line"] = np.where(is_paid, orders["bundle_discount_per_unit"] * orders["quantity"], 0.0).round(2)
    orders["coupon_discount_line"] = np.where(is_paid, orders["coupon_discount_per_unit"] * orders["quantity"], 0.0).round(2)
    orders["total_discount_line"] = (orders["gmv_line"] - orders["net_revenue_line"]).clip(lower=0.0).round(2)

    # T8: Role-Playing Join to dim_network_clean for Origin vs Destination Region
    dc_to_region = net_clean.set_index("dc_id")["region_id"].to_dict()
    orders["ori_region_id"] = orders["dc_ori"].map(dc_to_region)
    orders["des_region_id"] = orders["dc_des"].map(dc_to_region)
    orders["is_cross_dc"] = (orders["dc_ori"] != orders["dc_des"]).astype(int)

    conditions = [
        orders["dc_ori"] == orders["dc_des"],
        (orders["dc_ori"] != orders["dc_des"]) & (orders["des_region_id"] == -1),
        (orders["dc_ori"] != orders["dc_des"]) & (orders["ori_region_id"] == orders["des_region_id"]),
        (orders["dc_ori"] != orders["dc_des"]) & (orders["ori_region_id"] != orders["des_region_id"]),
    ]
    choices = [
        "1. Local DC (dc_ori = dc_des)",
        "4. Virtual District Spillover (No Local DC)",
        "2. Intra-Region Spillover (Same Region)",
        "3. Inter-Region Spillover (Cross-Country)",
    ]
    orders["fulfillment_network_tier"] = np.select(conditions, choices, default="Unknown")

    assert (orders["net_revenue_line"] < 0).sum() == 0, "Negative net_revenue_line found!"
    orders.to_csv(PROCESSED_DIR / "fact_order_items_clean.csv", index=False)
    print(f" - Saved fact_order_items_clean.csv ({len(orders):,} deduplicated line items)")

    # T10: Build Order-Header Grain Table (1 row per order_id) to prevent M:N Fan-Out
    print("\n[STEP 6] Building Order-Header Grain Fact Table & Reconciling Delivery SLAs (T10)...")
    order_hdr = orders.groupby("order_id", as_index=False).agg(
        user_id=("user_id", "first"),
        order_date=("order_date", "first"),
        order_time=("order_time", "min"),
        type=("type", "first"),
        seller_type=("seller_type", "first"),
        has_explicit_sla=("has_explicit_sla", "max"),
        promise_days=("promise_days", "max"),
        dc_ori=("dc_ori", "first"),
        dc_des=("dc_des", "first"),
        ori_region_id=("ori_region_id", "first"),
        des_region_id=("des_region_id", "first"),
        is_cross_dc=("is_cross_dc", "max"),
        fulfillment_network_tier=("fulfillment_network_tier", "first"),
        line_item_count=("sku_id", "count"),
        unique_sku_count=("sku_id", "nunique"),
        paid_units=("paid_quantity", "sum"),
        gift_units=("gift_quantity", "sum"),
        has_gift_item=("gift_item", "max"),
        gmv_order=("gmv_line", "sum"),
        net_revenue_order=("net_revenue_line", "sum"),
        total_discount_order=("total_discount_line", "sum"),
        direct_discount_order=("direct_discount_line", "sum"),
        quantity_discount_order=("quantity_discount_line", "sum"),
        bundle_discount_order=("bundle_discount_line", "sum"),
        coupon_discount_order=("coupon_discount_line", "sum"),
        is_corrupted_order_id=("is_corrupted_id", "max"),
    )

    order_hdr["effective_discount_rate"] = np.where(
        order_hdr["gmv_order"] > 0,
        (order_hdr["total_discount_order"] / order_hdr["gmv_order"]).round(4),
        0.0,
    )

    # Pre-aggregate delivery table to order_id grain (excluding corrupted '4.99E+54' join key)
    deliv_valid = deliv_clean[deliv_clean["is_corrupted_id"] == 0].copy()
    deliv_agg = deliv_valid.groupby("order_id", as_index=False).agg(
        package_count=("package_id", "count"),
        first_ship_out_time=("ship_out_time", "min"),
        last_station_arr_time=("arr_station_time", "max"),
        last_dlvr_time=("dlvr_time", "max"),
        linehaul_transit_hrs=("linehaul_transit_hrs", "mean"),
        lastmile_delivery_hrs=("lastmile_delivery_hrs", "mean"),
        has_chronology_anomaly=("is_chronology_anomaly", "max"),
    )

    order_hdr = order_hdr.merge(deliv_agg, on="order_id", how="left")
    order_hdr["has_delivery_telemetry"] = order_hdr["package_count"].notna().astype(int)
    order_hdr["package_count"] = order_hdr["package_count"].fillna(0).astype(int)
    order_hdr["is_split_shipment"] = (order_hdr["package_count"] > 1).astype(int)

    # Calculate Warehouse Processing Hours & End-to-End Fulfillment Hours/Days
    raw_wh_hrs = (order_hdr["first_ship_out_time"] - order_hdr["order_time"]).dt.total_seconds() / 3600.0
    raw_total_hrs = (order_hdr["last_dlvr_time"] - order_hdr["order_time"]).dt.total_seconds() / 3600.0

    order_hdr["warehouse_proc_hrs"] = np.where(raw_wh_hrs >= 0, raw_wh_hrs, np.nan).round(2)
    order_hdr["total_fulfillment_hrs"] = np.where(raw_total_hrs >= 0, raw_total_hrs, np.nan).round(2)
    order_hdr["total_fulfillment_days"] = (order_hdr["total_fulfillment_hrs"] / 24.0).round(2)

    # Calendar-day and elapsed-day SLA breach evaluation (only where promise_days and total_fulfillment_days exist)
    can_eval_sla = (
        (order_hdr["has_explicit_sla"] == 1)
        & order_hdr["promise_days"].notna()
        & order_hdr["total_fulfillment_days"].notna()
    )
    order_hdr["sla_delay_days"] = np.where(
        can_eval_sla,
        (order_hdr["total_fulfillment_days"] - order_hdr["promise_days"]).round(2),
        np.nan,
    )
    order_hdr["is_sla_breach"] = np.where(
        can_eval_sla,
        (order_hdr["total_fulfillment_days"] > order_hdr["promise_days"]).astype(float),
        np.nan,
    )

    assert order_hdr["order_id"].is_unique, "order_id must be unique in fact_orders_header_clean!"
    order_hdr.to_csv(PROCESSED_DIR / "fact_orders_header_clean.csv", index=False)
    print(f" - Saved fact_orders_header_clean.csv ({len(order_hdr):,} unique orders)")
    return order_hdr


def clean_inventory(inv_raw: pd.DataFrame) -> pd.DataFrame:
    print("\n[STEP 7] Cleaning JD_inventory_data...")
    inv = inv_raw.copy()
    inv["date"] = pd.to_datetime(inv["date"], errors="coerce").dt.date
    inv = inv.drop_duplicates().reset_index(drop=True)
    inv.to_csv(PROCESSED_DIR / "fact_inventory_clean.csv", index=False)
    print(f" - Saved fact_inventory_clean.csv ({len(inv):,} stock availability records)")
    return inv


def print_validation_summary(order_hdr: pd.DataFrame):
    print("\n" + "=" * 85)
    print("PHASE 5 POST-CLEANING VALIDATION & KPI PREVIEW SUMMARY")
    print("=" * 85)
    print(f"Total Unique Orders (Header Grain)       : {len(order_hdr):,}")
    print(f"Total Gross Merchandise Value (GMV)      : RMB {order_hdr['gmv_order'].sum():,.2f}")
    print(f"Total Net Realized Product Revenue       : RMB {order_hdr['net_revenue_order'].sum():,.2f}")
    print(f"Total Promotional Discounts Granted      : RMB {order_hdr['total_discount_order'].sum():,.2f}")
    overall_disc = order_hdr['total_discount_order'].sum() / order_hdr['gmv_order'].sum() * 100
    print(f"Platform Effective Discount Rate (%)     : {overall_disc:.2f}%")

    print("\nOrder Split by Network Fulfillment Tier:")
    tier_summary = order_hdr.groupby("fulfillment_network_tier").agg(
        orders=("order_id", "count"),
        net_rev=("net_revenue_order", "sum"),
        sla_breach_rate=("is_sla_breach", lambda s: s.mean() * 100),
        median_fulfillment_hrs=("total_fulfillment_hrs", "median"),
    )
    tier_summary["order_share_%"] = (tier_summary["orders"] / len(order_hdr) * 100).round(2)
    tier_summary["sla_breach_rate"] = tier_summary["sla_breach_rate"].round(2)
    print(tier_summary[["orders", "order_share_%", "net_rev", "sla_breach_rate", "median_fulfillment_hrs"]].to_string())
    print("=" * 85)


if __name__ == "__main__":
    print("Starting Phase 5 Data Cleaning & Preprocessing Pipeline...")
    net_raw = load_raw_csv("JD_network_data.csv")
    skus_raw = load_raw_csv("JD_sku_data.csv")
    users_raw = load_raw_csv("JD_user_data.csv")
    deliv_raw = load_raw_csv("JD_delivery_data.csv")
    orders_raw = load_raw_csv("JD_order_data.csv")
    inv_raw = load_raw_csv("JD_inventory_data.csv")

    net_clean = clean_network_and_orders(net_raw, orders_raw)
    skus_clean = clean_skus(skus_raw)
    users_clean = clean_users(users_raw)
    deliv_clean = clean_deliveries(deliv_raw)
    order_hdr = clean_orders_and_build_header(orders_raw, net_clean, deliv_clean)
    inv_clean = clean_inventory(inv_raw)

    print_validation_summary(order_hdr)