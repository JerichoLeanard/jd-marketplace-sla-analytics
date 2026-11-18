"""
Phase 7: SQLite Relational Database Builder & Analytical SQL Runner
Project: JD.com Marketplace Fulfillment SLA, Unit Economics & Retention Analytics
Purpose: Creates data/processed/jd_marketplace.db using sql/01_schema_ddl.sql,
         applies schema-guard backfills for coerced timestamps, loads all 7
         cleaned tables, validates row integrity, and executes all 6 production
         SQL queries from sql/02_analytical_queries.sql.
"""

import sqlite3
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SQL_DIR = PROJECT_ROOT / "sql"
DB_PATH = PROCESSED_DIR / "jd_marketplace.db"

TABLE_CSV_MAP = [
    ("dim_network", "dim_network_clean.csv"),
    ("dim_skus", "dim_skus_clean.csv"),
    ("dim_users", "dim_users_clean.csv"),
    ("fact_orders_header", "fact_orders_header_clean.csv"),
    ("fact_order_items", "fact_order_items_clean.csv"),
    ("fact_deliveries", "fact_deliveries_clean.csv"),
    ("fact_inventory", "fact_inventory_clean.csv"),
]


def build_sqlite_database():
    print("=" * 95)
    print(f"BUILDING RELATIONAL DATABASE: {DB_PATH}")
    print("=" * 95)

    ddl_sql = (SQL_DIR / "01_schema_ddl.sql").read_text(encoding="utf-8")

    with sqlite3.connect(DB_PATH) as conn:
        # 1. Execute DDL (Drops & recreates tables, PK/FK constraints, indexes, and views)
        conn.executescript(ddl_sql)
        print("[SUCCESS] Executed sql/01_schema_ddl.sql (Tables, Indexes & Views created).")

        # 2. Load cleaned CSVs into SQLite tables in chunks with Schema Guard
        for table_name, csv_name in TABLE_CSV_MAP:
            csv_path = PROCESSED_DIR / csv_name
            print(f"[LOADING] {csv_name:<30} -> SQL table '{table_name}' ...")
            coerced_time_total = 0

            for chunk in pd.read_csv(csv_path, chunksize=100_000, low_memory=False):
                # Schema Guard: Backfill any order_date or order_time coerced to NaT by Pandas 3.1
                if "order_date" in chunk.columns and chunk["order_date"].isna().any():
                    chunk["order_date"] = chunk["order_date"].ffill().bfill()

                if "order_time" in chunk.columns:
                    null_mask = chunk["order_time"].isna()
                    null_cnt = int(null_mask.sum())
                    if null_cnt > 0:
                        coerced_time_total += null_cnt
                        chunk.loc[null_mask, "order_time"] = (
                            chunk.loc[null_mask, "order_date"].astype(str) + " 00:00:00"
                        )

                chunk.to_sql(table_name, conn, if_exists="append", index=False)

            if coerced_time_total > 0:
                print(
                    f"   -> [SCHEMA GUARD] Backfilled {coerced_time_total:,} coerced NaT "
                    f"'order_time' rows in '{table_name}' using 'order_date 00:00:00'."
                )

        # 3. Validate row counts inside SQLite
        print("\n" + "-" * 65)
        print(f"{'SQL TABLE NAME':<28} | {'SQL ROW COUNT':>18}")
        print("-" * 65)
        cur = conn.cursor()
        for table_name, _ in TABLE_CSV_MAP:
            cur.execute(f"SELECT COUNT(*) FROM {table_name};")
            cnt = cur.fetchone()[0]
            print(f"{table_name:<28} | {cnt:>18,}")
        print("-" * 65)


def execute_analytical_queries():
    print("\n" + "#" * 95)
    print("EXECUTING PHASE 7 PRODUCTION ANALYTICAL SQL QUERIES (sql/02_analytical_queries.sql)")
    print("#" * 95)

    raw_sql = (SQL_DIR / "02_analytical_queries.sql").read_text(encoding="utf-8")
    # Filter out empty blocks or comment-only blocks after splitting by ';'
    statements = [
        s.strip()
        for s in raw_sql.split(";")
        if any(line.strip() and not line.strip().startswith("--") for line in s.splitlines())
    ]

    query_titles = [
        "QUERY 1: M:N Granularity Reconciliation via Pre-Aggregated CTEs & Role-Playing Joins",
        "QUERY 2: Origin Warehouse (dc_ori) Pareto Bottleneck Scorecard (Window Functions)",
        "QUERY 3: Daily Promotional Surge Stress Test with Centered 7-Day Moving Averages",
        "QUERY 4: 1P Inventory Stockout Attribution by Network Fulfillment Tier",
        "QUERY 5: Controlled Longitudinal Retention & Next-Order Lag Analysis (ROW_NUMBER & LEAD)",
        "QUERY 6: High Discount-Erosion & High Spillover Brands (Subquery & HAVING)",
    ]

    with sqlite3.connect(DB_PATH) as conn:
        for idx, stmt in enumerate(statements):
            title = query_titles[idx] if idx < len(query_titles) else f"SQL QUERY {idx + 1}"
            print("\n" + "=" * 95)
            print(title)
            print("=" * 95)
            df_res = pd.read_sql_query(stmt, conn)
            print(df_res.to_string(index=False))


if __name__ == "__main__":
    build_sqlite_database()
    execute_analytical_queries()
    print("\n" + "=" * 95)
    print("PHASE 7 SQL DATABASE & ANALYTICAL QUERIES COMPLETE!")
    print("=" * 95)