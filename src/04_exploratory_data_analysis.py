"""
Phase 6: Structured Exploratory Data Analysis (EDA) & Visual Diagnostic Suite
Project: JD.com Marketplace Fulfillment SLA, Unit Economics & Retention Analytics
Purpose: Executes 6 hypothesis-driven exploratory analyses on data/processed/,
         prints comprehensive statistical tables to the console, and exports
         6 publication-grade PNG charts to figures/.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for reliable Windows CLI execution
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Set consistent publication visual style
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#333333"
plt.rcParams["axes.linewidth"] = 0.8
sns.set_theme(style="whitegrid", palette="deep")


def load_processed_data():
    print("Loading cleaned datasets from data/processed/ ...")
    order_hdr = pd.read_csv(PROCESSED_DIR / "fact_orders_header_clean.csv", low_memory=False)
    order_items = pd.read_csv(PROCESSED_DIR / "fact_order_items_clean.csv", low_memory=False)
    users = pd.read_csv(PROCESSED_DIR / "dim_users_clean.csv", low_memory=False)
    inv = pd.read_csv(PROCESSED_DIR / "fact_inventory_clean.csv", low_memory=False)

    order_hdr["order_date"] = pd.to_datetime(order_hdr["order_date"])
    order_hdr["order_time"] = pd.to_datetime(order_hdr["order_time"])
    return order_hdr, order_items, users, inv


def eda_1_lead_time_and_sla_paradox(order_hdr: pd.DataFrame):
    print("\n" + "=" * 95)
    print("EDA 1: END-TO-END LEAD-TIME DECOMPOSITION & THE 'LOCAL DC SLA PARADOX'")
    print("=" * 95)

    tracked = order_hdr[order_hdr["has_delivery_telemetry"] == 1].copy()

    # 1A. Stage Decomposition by Network Fulfillment Tier
    stage_summary = tracked.groupby("fulfillment_network_tier").agg(
        tracked_orders=("order_id", "count"),
        avg_promise_days=("promise_days", "mean"),
        pct_1day_promise=("promise_days", lambda s: (s == 1).mean() * 100),
        med_warehouse_hrs=("warehouse_proc_hrs", "median"),
        med_linehaul_hrs=("linehaul_transit_hrs", "median"),
        med_lastmile_hrs=("lastmile_delivery_hrs", "median"),
        med_total_hrs=("total_fulfillment_hrs", "median"),
        p90_total_hrs=("total_fulfillment_hrs", lambda s: np.nanpercentile(s.dropna(), 90)),
        sla_breach_pct=("is_sla_breach", lambda s: s.mean() * 100),
    ).round(2)
    print("\n[1A] Lead-Time Stage Breakdown & Promise Calibration by Network Tier:")
    print(stage_summary.to_string())

    # 1B. On-Time vs. SLA Breached Orders Stage Comparison
    sla_eval = tracked[tracked["is_sla_breach"].notna()].copy()
    sla_eval["sla_status"] = np.where(sla_eval["is_sla_breach"] == 1, "SLA Breached (Late)", "On-Time / Early")
    breach_comp = sla_eval.groupby("sla_status").agg(
        orders=("order_id", "count"),
        mean_warehouse_hrs=("warehouse_proc_hrs", "mean"),
        med_warehouse_hrs=("warehouse_proc_hrs", "median"),
        mean_linehaul_hrs=("linehaul_transit_hrs", "mean"),
        med_linehaul_hrs=("linehaul_transit_hrs", "median"),
        mean_lastmile_hrs=("lastmile_delivery_hrs", "mean"),
        med_lastmile_hrs=("lastmile_delivery_hrs", "median"),
        mean_total_hrs=("total_fulfillment_hrs", "mean"),
        med_total_hrs=("total_fulfillment_hrs", "median"),
    ).round(2)
    print("\n[1B] Stage Duration Comparison: On-Time vs. SLA Breached Orders:")
    print(breach_comp.to_string())

    # Plot Chart 1
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    tiers = stage_summary.index.tolist()
    short_labels = ["1. Local DC", "2. Intra-Region", "3. Inter-Region", "4. Virtual Dist."]

    # Left panel: Stacked Median Stage Hours
    wh = stage_summary["med_warehouse_hrs"].values
    lh = stage_summary["med_linehaul_hrs"].values
    lm = stage_summary["med_lastmile_hrs"].values

    axes[0].bar(short_labels, wh, label="Warehouse Processing (Hrs)", color="#1f77b4")
    axes[0].bar(short_labels, lh, bottom=wh, label="Line-Haul Transit (Hrs)", color="#ff7f0e")
    axes[0].bar(short_labels, lm, bottom=wh + lh, label="Last-Mile Delivery (Hrs)", color="#2ca02c")
    axes[0].set_title("Median Fulfillment Lead Time by Stage & Network Tier", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Median Elapsed Hours")
    axes[0].legend(loc="upper left")
    for i, tot in enumerate(stage_summary["med_total_hrs"].values):
        axes[0].text(i, wh[i] + lh[i] + lm[i] + 1.2, f"Total: {tot:.1f}h", ha="center", fontweight="bold", fontsize=9)

    # Right panel: The SLA Paradox (% 1-Day Promise vs SLA Breach Rate)
    x = np.arange(len(short_labels))
    width = 0.36
    b1 = axes[1].bar(x - width / 2, stage_summary["pct_1day_promise"], width, label="% Assigned 1-Day SLA Promise", color="#4c72b0")
    b2 = axes[1].bar(x + width / 2, stage_summary["sla_breach_pct"], width, label="SLA Breach Rate (%)", color="#c44e52")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(short_labels)
    axes[1].set_title("The SLA Paradox: Aggressive 1-Day Promises Drive Local Breaches", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("Percentage (%)")
    axes[1].legend(loc="upper right")
    for bar in b1:
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{bar.get_height():.1f}%", ha="center", fontsize=8)
    for bar in b2:
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{bar.get_height():.1f}%", ha="center", fontsize=8, fontweight="bold")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "01_lead_time_and_sla_paradox.png", dpi=200)
    plt.close()


def eda_2_origin_warehouse_bottlenecks(order_hdr: pd.DataFrame):
    print("\n" + "=" * 95)
    print("EDA 2: ORIGIN WAREHOUSE (dc_ori) BOTTLENECK RANKING (ANSWERING AQ1.4)")
    print("=" * 95)

    sla_orders = order_hdr[order_hdr["is_sla_breach"].notna()].copy()
    dc_perf = sla_orders.groupby(["dc_ori", "ori_region_id"], as_index=False).agg(
        total_orders=("order_id", "count"),
        breached_orders=("is_sla_breach", "sum"),
        sla_breach_pct=("is_sla_breach", lambda s: s.mean() * 100),
        mean_wh_hrs=("warehouse_proc_hrs", "mean"),
        med_wh_hrs=("warehouse_proc_hrs", "median"),
        mean_linehaul_hrs=("linehaul_transit_hrs", "mean"),
        cross_dc_pct=("is_cross_dc", lambda s: s.mean() * 100),
    )
    dc_perf["breached_orders"] = dc_perf["breached_orders"].astype(int)
    dc_perf["share_of_all_breaches_%"] = (dc_perf["breached_orders"] / dc_perf["breached_orders"].sum() * 100).round(2)
    dc_perf = dc_perf.sort_values("breached_orders", ascending=False).reset_index(drop=True)
    dc_perf["cum_breach_share_%"] = dc_perf["share_of_all_breaches_%"].cumsum().round(2)

    print("\n[2A] Top 15 Origin Warehouses (dc_ori) Ranked by Total Breached Orders (Scale + Rate):")
    cols_show = [
        "dc_ori", "ori_region_id", "total_orders", "breached_orders",
        "sla_breach_pct", "share_of_all_breaches_%", "cum_breach_share_%",
        "mean_wh_hrs", "med_wh_hrs", "cross_dc_pct"
    ]
    print(dc_perf[cols_show].head(15).round(2).to_string(index=False))

    # Plot Chart 2: Warehouse Bottleneck Quadrant
    top_dcs = dc_perf[dc_perf["total_orders"] >= 1000].copy()
    fig, ax = plt.subplots(figsize=(11, 6.5))
    scatter = ax.scatter(
        top_dcs["mean_wh_hrs"],
        top_dcs["sla_breach_pct"],
        s=top_dcs["total_orders"] / 120,
        c=top_dcs["cross_dc_pct"],
        cmap="viridis",
        alpha=0.8,
        edgecolors="black",
    )
    plt.colorbar(scatter, ax=ax, label="Cross-DC Spillover Rate (%)")
    ax.axvline(top_dcs["mean_wh_hrs"].median(), color="red", linestyle="--", alpha=0.6, label="Median Warehouse Dispatch Hrs")
    ax.axhline(top_dcs["sla_breach_pct"].median(), color="blue", linestyle="--", alpha=0.6, label="Median SLA Breach Rate (%)")

    for _, row in top_dcs.head(10).iterrows():
        ax.annotate(
            f"DC {int(row['dc_ori'])} ({int(row['breached_orders']):,} late)",
            (row["mean_wh_hrs"], row["sla_breach_pct"]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8.5,
            fontweight="bold",
        )

    ax.set_title("Origin Warehouse (dc_ori) Intervention Matrix: Dispatch Delay vs. SLA Breach Rate\n(Bubble Size = Order Volume, Annotated Top 10 Breach Contributors)", fontsize=11.5, fontweight="bold")
    ax.set_xlabel("Mean Warehouse Processing Time (Hours from Order to Ship-Out)")
    ax.set_ylabel("SLA Breach Rate (%)")
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "02_warehouse_bottleneck_scatter.png", dpi=200)
    plt.close()


def eda_3_daily_timeseries_and_promo_stress(order_hdr: pd.DataFrame):
    print("\n" + "=" * 95)
    print("EDA 3: DAILY TIME-SERIES TRENDS & PROMOTIONAL SPIKE STRESS TEST (MARCH 2018)")
    print("=" * 95)

    daily = order_hdr.groupby("order_date", as_index=False).agg(
        orders=("order_id", "count"),
        gmv=("gmv_order", "sum"),
        net_rev=("net_revenue_order", "sum"),
        total_disc=("total_discount_order", "sum"),
        cross_dc_pct=("is_cross_dc", lambda s: s.mean() * 100),
        sla_breach_pct=("is_sla_breach", lambda s: s.mean() * 100),
        mean_wh_hrs=("warehouse_proc_hrs", "mean"),
        med_total_hrs=("total_fulfillment_hrs", "median"),
    )
    daily["disc_rate_%"] = (daily["total_disc"] / daily["gmv"] * 100).round(2)

    print("\n[3A] Top 5 Peak Order Volume Days in March 2018 vs. Fulfillment Performance:")
    print(daily.sort_values("orders", ascending=False).head(5).round(2).to_string(index=False))

    corr_vol_breach = daily["orders"].corr(daily["sla_breach_pct"])
    corr_disc_vol = daily["disc_rate_%"].corr(daily["orders"])
    corr_wh_breach = daily["mean_wh_hrs"].corr(daily["sla_breach_pct"])
    print(f"\n[3B] Daily Time-Series Correlations (n = 31 Days):")
    print(f" - Effective Discount Rate (%) vs. Daily Order Volume : r = {corr_disc_vol:.3f}")
    print(f" - Daily Order Volume vs. Daily SLA Breach Rate (%)   : r = {corr_vol_breach:.3f}")
    print(f" - Mean Warehouse Dispatch Hrs vs. SLA Breach Rate (%): r = {corr_wh_breach:.3f}")

    # Plot Chart 3
    fig, ax1 = plt.subplots(figsize=(13, 5.5))
    ax1.bar(daily["order_date"], daily["orders"], color="#9ecae1", alpha=0.75, label="Daily Order Volume")
    ax1.set_ylabel("Daily Order Volume", color="#1f77b4", fontweight="bold")
    ax1.set_xlabel("Order Date (March 2018)")

    ax2 = ax1.twinx()
    ax2.plot(daily["order_date"], daily["sla_breach_pct"], color="#d62728", marker="o", linewidth=2, label="SLA Breach Rate (%)")
    ax2.plot(daily["order_date"], daily["disc_rate_%"], color="#2ca02c", linestyle="--", marker="s", linewidth=1.8, label="Effective Discount Rate (%)")
    ax2.set_ylabel("Rate (%)", color="#333333", fontweight="bold")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    plt.title("March 2018 Daily Stress Test: Promotional Discount Spikes, Order Surges & SLA Breaches", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "03_daily_timeseries_promo_stress.png", dpi=200)
    plt.close()


def eda_4_unit_economics_and_discounts(order_hdr: pd.DataFrame):
    print("\n" + "=" * 95)
    print("EDA 4: UNIT ECONOMICS, SELLER MODEL (1P vs 3P) & PROMOTIONAL DISCOUNT EROSION")
    print("=" * 95)

    econ = order_hdr.groupby("seller_type").agg(
        orders=("order_id", "count"),
        paid_units=("paid_units", "sum"),
        gift_units=("gift_units", "sum"),
        gmv=("gmv_order", "sum"),
        net_rev=("net_revenue_order", "sum"),
        total_disc=("total_discount_order", "sum"),
        direct_disc=("direct_discount_order", "sum"),
        qty_disc=("quantity_discount_order", "sum"),
        bundle_disc=("bundle_discount_order", "sum"),
        coupon_disc=("coupon_discount_order", "sum"),
        cross_dc_pct=("is_cross_dc", lambda s: s.mean() * 100),
        split_pkg_pct=("is_split_shipment", lambda s: s.mean() * 100),
    )
    econ["disc_depth_%"] = (econ["total_disc"] / econ["gmv"] * 100).round(2)
    econ["aov_net_rmb"] = (econ["net_rev"] / econ["orders"]).round(2)

    print("\n[4A] Commercial & Unit Economics Breakdown by Seller Model (1P vs. 3P):")
    print(econ[["orders", "gmv", "net_rev", "total_disc", "disc_depth_%", "aov_net_rmb", "cross_dc_pct"]].round(2).to_string())

    print("\n[4B] Promotional Discount Pool Decomposition (Total = RMB 21.35M):")
    for col, label in [
        ("direct_discount_order", "Direct Price Markdown"),
        ("quantity_discount_order", "Quantity / Multi-Buy Discount"),
        ("coupon_discount_order", "Voucher / Coupon Discount"),
        ("bundle_discount_order", "Bundle Promotion Discount"),
    ]:
        val = order_hdr[col].sum()
        pct_disc = val / order_hdr["total_discount_order"].sum() * 100
        pct_gmv = val / order_hdr["gmv_order"].sum() * 100
        print(f" - {label:<30}: RMB {val:>12,.2f} ({pct_disc:>5.2f}% of discounts | {pct_gmv:>5.2f}% of GMV)")

    # Plot Chart 4
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    disc_types = ["Direct\nMarkdown", "Quantity\nMulti-Buy", "Coupon /\nVoucher", "Bundle\nPromo"]
    disc_vals = [
        order_hdr["direct_discount_order"].sum() / 1e6,
        order_hdr["quantity_discount_order"].sum() / 1e6,
        order_hdr["coupon_discount_order"].sum() / 1e6,
        order_hdr["bundle_discount_order"].sum() / 1e6,
    ]
    bars = axes[0].bar(disc_types, disc_vals, color=["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"])
    axes[0].set_title("Total Promotional Discount Pool by Mechanism (RMB Millions)", fontsize=11.5, fontweight="bold")
    axes[0].set_ylabel("Discount Value (RMB Millions)")
    for b in bars:
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.2, f"RMB {b.get_height():.2f}M", ha="center", fontweight="bold", fontsize=9)

    # Right panel: 1P vs 3P Gross vs Net Revenue
    x = np.arange(len(econ.index))
    w = 0.35
    axes[1].bar(x - w / 2, econ["gmv"] / 1e6, w, label="Gross GMV (RMB M)", color="#aec7e8")
    axes[1].bar(x + w / 2, econ["net_rev"] / 1e6, w, label="Net Realized Revenue (RMB M)", color="#1f77b4")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(econ.index)
    axes[1].set_title("1P vs. 3P Gross GMV vs. Net Realized Revenue", fontsize=11.5, fontweight="bold")
    axes[1].set_ylabel("RMB (Millions)")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "04_unit_economics_discount_breakdown.png", dpi=200)
    plt.close()


def eda_5_customer_segments_and_stockout_verification(
    order_hdr: pd.DataFrame, order_items: pd.DataFrame, users: pd.DataFrame, inv: pd.DataFrame
):
    print("\n" + "=" * 95)
    print("EDA 5: CUSTOMER SEGMENTS, CITY TIERS & 1P INVENTORY STOCKOUT VERIFICATION")
    print("=" * 95)

    merged_u = order_hdr.merge(users[["user_id", "plus_label", "city_tier_label", "user_level"]], on="user_id", how="left")

    city_perf = merged_u.groupby("city_tier_label").agg(
        orders=("order_id", "count"),
        net_rev=("net_revenue_order", "sum"),
        cross_dc_pct=("is_cross_dc", lambda s: s.mean() * 100),
        sla_breach_pct=("is_sla_breach", lambda s: s.mean() * 100),
        med_fulfillment_hrs=("total_fulfillment_hrs", "median"),
    ).round(2)
    print("\n[5A] Fulfillment & Commercial Performance by Customer City Tier:")
    print(city_perf.to_string())

    plus_perf = merged_u.groupby("plus_label").agg(
        orders=("order_id", "count"),
        unique_buyers=("user_id", "nunique"),
        net_rev=("net_revenue_order", "sum"),
        aov_net=("net_revenue_order", "mean"),
        sla_breach_pct=("is_sla_breach", lambda s: s.mean() * 100),
        med_fulfillment_hrs=("total_fulfillment_hrs", "median"),
    ).round(2)
    plus_perf["orders_per_buyer"] = (plus_perf["orders"] / plus_perf["unique_buyers"]).round(3)
    print("\n[5B] JD PLUS VIP vs. Regular Member Performance:")
    print(plus_perf.to_string())

    # 5C. Inventory Stockout Verification on Tracked 1P SKUs
    tracked_skus = set(inv["sku_id"].unique())
    items_1p_tracked = order_items[(order_items["type"] == 1) & (order_items["sku_id"].isin(tracked_skus))].copy()
    inv_keys = set(zip(inv["dc_id"], inv["sku_id"], inv["date"].astype(str)))
    items_1p_tracked["dest_dc_in_stock"] = [
        1 if (d, s, str(dt)) in inv_keys else 0
        for d, s, dt in zip(items_1p_tracked["dc_des"], items_1p_tracked["sku_id"], items_1p_tracked["order_date"])
    ]
    stockout_ct = pd.crosstab(
        items_1p_tracked["is_cross_dc"].map({0: "Local DC (dc_ori=dc_des)", 1: "Cross-DC Spillover (dc_ori!=dc_des)"}),
        items_1p_tracked["dest_dc_in_stock"].map({1: "In Stock at dc_des", 0: "Stocked Out at dc_des"}),
        normalize="index",
    ) * 100
    print(f"\n[5C] Inventory Stockout Audit on {len(items_1p_tracked):,} 1P Tracked-SKU Order Lines (Row %):")
    print(stockout_ct.round(2).to_string())

    # Plot Chart 5
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    c_order = [
        "Tier 1 (Megacity)", "Tier 2 (Provincial Capital)", "Tier 3 (Prefecture City)",
        "Tier 4 (County City)", "Tier 5 (Township/Rural)", "Unknown Tier"
    ]
    city_plot = city_perf.reindex([c for c in c_order if c in city_perf.index])
    axes[0].barh(city_plot.index, city_plot["med_fulfillment_hrs"], color="#4c72b0")
    axes[0].set_title("Median Fulfillment Lead Time (Hrs) by Urban City Tier", fontsize=11.5, fontweight="bold")
    axes[0].set_xlabel("Median Fulfillment Hours")
    axes[0].invert_yaxis()

    axes[1].barh(city_plot.index, city_plot["cross_dc_pct"], color="#dd8452")
    axes[1].set_title("Cross-DC Spillover Rate (%) by Urban City Tier", fontsize=11.5, fontweight="bold")
    axes[1].set_xlabel("Cross-DC Spillover Rate (%)")
    axes[1].invert_yaxis()

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "05_customer_tier_and_city_segmentation.png", dpi=200)
    plt.close()


def eda_6_repeat_purchase_and_delivery_experience(order_hdr: pd.DataFrame):
    print("\n" + "=" * 95)
    print("EDA 6: CUSTOMER REPEAT-PURCHASE CONVERSION BY FIRST-ORDER DELIVERY EXPERIENCE")
    print("=" * 95)

    # Sort chronologically per customer to isolate their first observed order in March
    valid_orders = order_hdr[order_hdr["is_corrupted_order_id"] == 0].sort_values(["user_id", "order_time"]).copy()
    user_totals = valid_orders.groupby("user_id", as_index=False).agg(
        total_march_orders=("order_id", "count"),
        total_march_net_rev=("net_revenue_order", "sum"),
    )
    user_totals["is_repeat_buyer"] = (user_totals["total_march_orders"] >= 2).astype(int)

    first_orders = valid_orders.drop_duplicates(subset=["user_id"], keep="first").copy()
    first_orders = first_orders.merge(user_totals, on="user_id", how="left")

    print(f" - Total Unique Active Buyers in March 2018 : {len(first_orders):,}")
    print(f" - Repeat Buyers (>= 2 Orders in March)     : {first_orders['is_repeat_buyer'].sum():,} ({first_orders['is_repeat_buyer'].mean()*100:.2f}%)")

    # Filter to buyers whose first order was in the first half of March (March 1-15)
    # so they have at least a 16-day window to place a repeat order (controlling for right-censoring!)
    early_cohort = first_orders[
        (first_orders["order_date"] <= pd.to_datetime("2018-03-15"))
        & (first_orders["total_fulfillment_hrs"].notna())
    ].copy()

    early_cohort["delivery_speed_bucket"] = pd.cut(
        early_cohort["total_fulfillment_hrs"],
        bins=[0, 18, 24, 48, 72, 9999],
        labels=["1. Ultra-Fast (<=18h)", "2. Same/Next Day (18-24h)", "3. Two-Day (24-48h)", "4. Three-Day (48-72h)", "5. Slow (>72h)"],
    )

    speed_ret = early_cohort.groupby("delivery_speed_bucket", observed=False).agg(
        buyers=("user_id", "count"),
        repeat_buyers=("is_repeat_buyer", "sum"),
        repeat_purchase_rate_pct=("is_repeat_buyer", lambda s: s.mean() * 100),
        avg_total_march_orders=("total_march_orders", "mean"),
        avg_total_march_spend=("total_march_net_rev", "mean"),
    ).round(2)
    print("\n[6A] Repeat Purchase Conversion by First-Order Delivery Speed (March 1-15 Cohort, Right-Censoring Controlled):")
    print(speed_ret.to_string())

    # Plot Chart 6
    fig, ax1 = plt.subplots(figsize=(10.5, 5.5))
    buckets = speed_ret.index.astype(str).tolist()
    bars = ax1.bar(buckets, speed_ret["repeat_purchase_rate_pct"], color="#2b5c8f", width=0.55)
    ax1.set_title("Customer Repeat-Purchase Rate (%) by First-Order Delivery Speed\n(March 1–15 Acquisition Cohort, Controlling for Observation Window)", fontsize=11.5, fontweight="bold")
    ax1.set_ylabel("Repeat Purchase Rate (% Placing >= 2 Orders)")
    ax1.set_xlabel("First-Order Doorstep Delivery Speed Tier")
    for b in bars:
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.12, f"{b.get_height():.2f}%", ha="center", fontweight="bold", fontsize=9.5)

    plt.xticks(rotation=12)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "06_repeat_purchase_by_delivery_experience.png", dpi=200)
    plt.close()


if __name__ == "__main__":
    print("Starting Phase 6 Exploratory Data Analysis (EDA) Suite...")
    order_hdr, order_items, users, inv = load_processed_data()
    eda_1_lead_time_and_sla_paradox(order_hdr)
    eda_2_origin_warehouse_bottlenecks(order_hdr)
    eda_3_daily_timeseries_and_promo_stress(order_hdr)
    eda_4_unit_economics_and_discounts(order_hdr)
    eda_5_customer_segments_and_stockout_verification(order_hdr, order_items, users, inv)
    eda_6_repeat_purchase_and_delivery_experience(order_hdr)
    print("\n" + "=" * 95)
    print(f"PHASE 6 EDA COMPLETE! All 6 diagnostic charts saved to: {FIGURES_DIR}")
    print("=" * 95)