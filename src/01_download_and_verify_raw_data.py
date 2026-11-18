"""
Phase 3: Raw Data Acquisition & Integrity Verification Script
Purpose: Downloads and verifies the 6 core JD.com MSOM relational CSV tables
         inside data/raw/ without modifying the original source files.
"""

from pathlib import Path
import urllib.request
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://huggingface.co/datasets/a6687543/MSOM_Data_Driven_Challenge_2020/resolve/main/"
CORE_FILES = [
    "JD_network_data.csv",
    "JD_sku_data.csv",
    "JD_user_data.csv",
    "JD_delivery_data.csv",
    "JD_order_data.csv",
    "JD_inventory_data.csv",
]

def download_file_if_missing(filename: str):
    file_path = RAW_DATA_DIR / filename
    if file_path.exists() and file_path.stat().st_size > 0:
        print(f"[SKIP] {filename} already exists ({file_path.stat().st_size / (1024**2):.2f} MB)")
        return
    
    print(f"[DOWNLOADING] {filename} ...")
    try:
        req = urllib.request.Request(BASE_URL + filename, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response, open(file_path, "wb") as out_file:
            while True:
                chunk = response.read(1024 * 1024)  # 1 MB chunks
                if not chunk: break
                out_file.write(chunk)
        print(f"[SUCCESS] Saved {filename}")
    except Exception as e:
        print(f"[ERROR] Failed to download {filename}: {e}")

def verify_raw_tables():
    print("\n" + "=" * 75)
    print(f"{'FILE NAME':<24} | {'ROWS':>12} | {'COLS':>5} | {'SIZE (MB)':>10}")
    print("=" * 75)
    
    for filename in CORE_FILES:
        file_path = RAW_DATA_DIR / filename
        if file_path.exists() and file_path.stat().st_size > 0:
            df = pd.read_csv(file_path, low_memory=False)
            size_mb = file_path.stat().st_size / (1024 ** 2)
            print(f"{filename:<24} | {df.shape[0]:>12,} | {df.shape[1]:>5} | {size_mb:>10.2f}")

if __name__ == "__main__":
    print("Starting Phase 3 Raw Data Acquisition & Verification...\n")
    for fname in CORE_FILES:
        download_file_if_missing(fname)
    verify_raw_tables()