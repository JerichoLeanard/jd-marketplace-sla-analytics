"""
Phase 4: Comprehensive Data Understanding & Quality Assessment Script
Project: JD.com Marketplace Fulfillment SLA, Unit Economics & Retention Analytics
Purpose: Audits all 6 raw JD.com relational tables for:
         - Column headers, data types, standard NaN nulls, and coded missing values ('-', -1, 'U')
         - Exact duplicate rows vs. primary-key grain multiplicity
         - Primary key uniqueness violations in JD_sku_data and JD_delivery_data
         - Pricing, discount, and gift item distributions
         - Chronological delivery timestamp integrity (ship_out_time -> arr_station_time -> arr_time)
         - Cross-table referential integrity (Orders <-> Delivery and Orders <-> Network DCs)
"""

from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

CORE_FILES = [
    "JD_network_data.csv",
    "JD_sku_data.csv",
    "JD_user_data.csv",
    "JD_delivery_data.csv",
    "JD_order_data.csv",
    "JD_inventory_data.csv",
]


def audit_table_structure(filename: str) -> pd.DataFrame:
    file_path = RAW_DATA_DIR / filename
    df = pd.read_csv(file_path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    print("\n" + "=" * 95)
    print(f"TABLE AUDIT: {filename}  |  Rows: {df.shape[0]:,}  |  Cols: {df.shape[1]}")
    print("=" * 95)
    print(f"Exact Duplicate Rows: {df.duplicated().sum():,}")
    print("-" * 95)
    print(
        f"{'RAW COLUMN NAME':<26} | {'DTYPE':<8} | {'NaN NULLS':>10} | "
        f"{'CODED (\"-\")':>12} | {'CODED (-1/\"U\")':>14} | {'UNIQUE':>10}"
    )
    print("-" * 95)

    for col in df.columns:
        nan_count = df[col].isna().sum()
        dtype_str = str(df[col].dtype)
        if dtype_str == "object" or dtype_str.startswith("str"):
            s_clean = df[col].astype(str).str.strip()
            coded_dash = (s_clean == "-").sum()
            coded_u = (s_clean == "U").sum()
        else:
            coded_dash = 0
            coded_u = (df[col] == -1).sum() if np.issubdtype(df[col].dtype, np.number) else 0

        nunique = df[col].nunique(dropna=True)
        print(
            f"{col:<26} | {dtype_str:<8} | {nan_count:>10,} | "
            f"{coded_dash:>12,} | {coded_u:>14,} | {nunique:>10,}"
        )

    # Standardize column names to lowercase in memory for downstream relational diagnostics
    df.columns = [c.lower() for c in df.columns]
    return df


def run_business_logic_diagnostics(
    orders: pd.DataFrame,
    delivery: pd.DataFrame,
    skus: pd.DataFrame,
    net: pd.DataFrame,
):
    print("\n" + "#" * 95)
    print("DEEP-DIVE BUSINESS & RELATIONAL QUALITY DIAGNOSTICS")
    print("#" * 95)

    # 1. Grain & Primary Key Uniqueness Checks
    print("\n[1. GRAIN MULTIPLICITY & PRIMARY KEY VIOLATIONS]")
    print(f" - JD_order_data   : {len(orders):,} line rows across {orders['order_id'].nunique():,} unique order_ids")
    print(f" - JD_delivery_data: {len(delivery):,} package rows across {delivery['order_id'].nunique():,} unique order_ids")
    print(f" - Unique package_ids in delivery: {delivery['package_id'].nunique():,} (Duplicate package_id rows: {delivery['package_id'].duplicated().sum()})")
    print(f" - Unique sku_ids in JD_sku_data : {skus['sku_id'].nunique():,} (Duplicate sku_id rows: {skus['sku_id'].duplicated().sum()})")

    dup_sku = skus[skus["sku_id"].duplicated(keep=False)]
    if not dup_sku.empty:
        print("\n   -> Inspecting Duplicate sku_ID rows in JD_sku_data.csv:")
        print(dup_sku.to_string(index=False))

    dup_pkg = delivery[delivery["package_id"].duplicated(keep=False)]
    if not dup_pkg.empty:
        print("\n   -> Inspecting Duplicate package_ID rows in JD_delivery_data.csv:")
        print(dup_pkg.to_string(index=False))

    # 2. 1P vs 3P Order Split & Promised SLA ('promise') Distribution
    print("\n[2. SELLER TYPE (1P vs 3P) & PROMISE SLA VALUES]")
    print(" - Order Line Count by Type in JD_order_data (1=1P Self-Operated, 2=3P Marketplace):")
    print(orders["type"].value_counts(dropna=False).to_string())
    print("\n - Package Count by Type in JD_delivery_data (1=1P, 0=3P):")
    print(delivery["type"].value_counts(dropna=False).to_string())
    print("\n - Crosstab of 'promise' (Promised Delivery Days) vs. Seller Type (1=1P, 2=3P):")
    ct_promise = pd.crosstab(orders["promise"].astype(str).str.strip(), orders["type"], margins=True)
    print(ct_promise.to_string())

    # 3. Pricing, Discounts & Gift Item Anomalies
    print("\n[3. PRICING, DISCOUNT & GIFT ITEM CHECKS]")
    neg_orig = (orders["original_unit_price"] < 0).sum()
    zero_orig = (orders["original_unit_price"] == 0).sum()
    neg_final = (orders["final_unit_price"] < 0).sum()
    zero_final = (orders["final_unit_price"] == 0).sum()
    gift_rows = (orders["gift_item"] == 1).sum()
    paid_zero_final = ((orders["gift_item"] == 0) & (orders["final_unit_price"] <= 0)).sum()

    print(f" - Negative original_unit_price rows           : {neg_orig:,}")
    print(f" - Zero (0) original_unit_price rows           : {zero_orig:,}")
    print(f" - Negative final_unit_price rows              : {neg_final:,}")
    print(f" - Zero (0) final_unit_price rows (All)        : {zero_final:,}")
    print(f" - Promotional Gift rows (gift_item == 1)      : {gift_rows:,}")
    print(f" - Paid Item rows (gift_item == 0) with price<=0: {paid_zero_final:,}")

    print("\n - Summary Statistics for Paid Items (gift_item == 0):")
    paid = orders[orders["gift_item"] == 0]
    cols_price = [
        "quantity", "original_unit_price", "final_unit_price",
        "direct_discount_per_unit", "quantity_discount_per_unit",
        "bundle_discount_per_unit", "coupon_discount_per_unit"
    ]
    print(paid[cols_price].describe(percentiles=[0.25, 0.5, 0.75, 0.99]).round(2).to_string())

    # 4. Referential Integrity: How many Orders have Delivery Telemetry?
    print("\n[4. REFERENTIAL INTEGRITY: ORDERS <-> DELIVERY COVERAGE]")
    order_level_type = orders.groupby("order_id")["type"].first().reset_index()
    deliv_orders = set(delivery["order_id"].unique())
    order_level_type["has_delivery_record"] = order_level_type["order_id"].isin(deliv_orders)

    coverage_counts = pd.crosstab(order_level_type["type"], order_level_type["has_delivery_record"], margins=True)
    coverage_pct = pd.crosstab(order_level_type["type"], order_level_type["has_delivery_record"], normalize="index") * 100
    print(" - Unique Orders with Matching Delivery Record (Counts):")
    print(coverage_counts.to_string())
    print("\n - Unique Orders with Matching Delivery Record (Row %):")
    print(coverage_pct.round(2).to_string())

    # 5. Chronological Timestamp Check in Delivery (ship_out_time -> arr_station_time -> arr_time)
    print("\n[5. DELIVERY TIMESTAMP CHRONOLOGY CHECK]")
    for tcol in ["ship_out_time", "arr_station_time", "arr_time"]:
        delivery[tcol + "_dt"] = pd.to_datetime(delivery[tcol], errors="coerce")
        null_dt = delivery[tcol + "_dt"].isna().sum()
        print(f" - Unparseable / Missing {tcol:<18}: {null_dt:,}")

    bad_linehaul = (delivery["arr_station_time_dt"] < delivery["ship_out_time_dt"]).sum()
    bad_lastmile = (delivery["arr_time_dt"] < delivery["arr_station_time_dt"]).sum()
    bad_total = (delivery["arr_time_dt"] < delivery["ship_out_time_dt"]).sum()
    print(f" - Anomalous rows where arr_station_time < ship_out_time: {bad_linehaul:,}")
    print(f" - Anomalous rows where arr_time < arr_station_time     : {bad_lastmile:,}")
    print(f" - Anomalous rows where arr_time < ship_out_time        : {bad_total:,}")

    # 6. Cross-DC & Cross-Region Network Check
    print("\n[6. DISTRIBUTION CENTER NETWORK & UNMAPPED DC CHECK]")
    net_dc_set = set(net["dc_id"].unique())
    missing_ori = (~orders["dc_ori"].isin(net_dc_set)).sum()
    missing_des = (~orders["dc_des"].isin(net_dc_set)).sum()
    unmapped_des_ids = sorted(list(set(orders["dc_des"].unique()) - net_dc_set))
    cross_dc_rows = (orders["dc_ori"] != orders["dc_des"]).sum()

    print(f" - Order rows where dc_ori not in JD_network_data: {missing_ori:,}")
    print(f" - Order rows where dc_des not in JD_network_data: {missing_des:,} (Unmapped dc_des IDs: {unmapped_des_ids})")
    print(f" - Order rows shipped Cross-DC (dc_ori != dc_des): {cross_dc_rows:,} ({cross_dc_rows/len(orders)*100:.2f}%)")


if __name__ == "__main__":
    print("Starting Phase 4 Comprehensive Data Profiling...\n")
    loaded = {}
    for fname in CORE_FILES:
        loaded[fname] = audit_table_structure(fname)

    run_business_logic_diagnostics(
        orders=loaded["JD_order_data.csv"],
        delivery=loaded["JD_delivery_data.csv"],
        skus=loaded["JD_sku_data.csv"],
        net=loaded["JD_network_data.csv"],
    )