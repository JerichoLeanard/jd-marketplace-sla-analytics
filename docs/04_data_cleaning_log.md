\# Phase 5 Deliverable: Data Cleaning \& Preprocessing Log



\## 1. Data Hygiene Architecture

\- \*\*Raw Layer (`data/raw/`):\*\* Strictly read-only original JD.com CSV exports.

\- \*\*Interim Audit Layer (`data/interim/`):\*\* Stores extracted anomalies (`audit\\\_duplicate\\\_skus.csv`, `audit\\\_duplicate\\\_packages.csv`, `audit\\\_delivery\\\_chronology\\\_anomalies.csv`, `audit\\\_duplicate\\\_order\\\_rows.csv`) for full engineering traceability.

\- \*\*Processed Layer (`data/processed/`):\*\* Standardized, validated relational tables ready for SQL ingestion, Python statistical testing, and Power BI Star Schema modeling.



\## 2. Transformation Log

1\. \*\*Schema \& Timestamp Standardization (T1):\*\* Converted all mixed-case headers (`order\\\_ID`, `sku\\\_ID`, `user\\\_ID`, `package\\\_ID`, `dc\\\_ID`, `region\\\_ID`) to lowercase `snake\\\_case`. Renamed `JD\\\_delivery\\\_data.arr\\\_time` to `dlvr\\\_time` to distinguish doorstep delivery from local station arrival (`arr\\\_station\\\_time`).

2\. \*\*Exact Row Deduplication (T2):\*\* Removed `3,928` exact duplicate line-item rows in `JD\\\_order\\\_data.csv`, reducing line count from `549,989` to `546,061` and archiving removed rows in `data/interim/audit\\\_duplicate\\\_order\\\_rows.csv`.

3\. \*\*Hexadecimal Hash Scientific-Notation Forensics (T3):\*\* Flagged records where 10-character hexadecimal hashes containing `'E'` were corrupted into scientific notation (`'4.99E+54'`) during upstream CSV export. Disambiguated the duplicate `package\\\_id` in `fact\\\_deliveries\\\_clean.csv` and prevented false cross-date joins on `'4.99E+54'`.

4\. \*\*Master SKU Deduplication (T4):\*\* Deduplicated `sku\\\_id = 'de9ed6156d'` in `dim\\\_skus\\\_clean.csv` (`31,868` -> `31,867` unique SKUs).

5\. \*\*1P vs. 3P Seller Type Unification (T5):\*\* Standardized `JD\\\_delivery\\\_data.type = 0` to `2` so that `1 = 1P Self-Operated` and `2 = 3P Marketplace` across all tables.

6\. \*\*Coded Missing Value Treatment (T6):\*\* Converted `208,583` coded `'-'` values in `promise` into a binary flag (`has\\\_explicit\\\_sla`) and nullable numeric `promise\\\_days`. Mapped `-1` and `'U'` codes in `dim\\\_users\\\_clean.csv` and `dim\\\_skus\\\_clean.csv` to explicit `"Unknown"` categories rather than dropping valid buyers.

7\. \*\*Promotional Gift Isolation \& Negative Price Clamping (T7):\*\* Isolated `94,606` free gift rows (`gift\\\_item == 1`)—including `8,537` rows where allocated order discounts pushed `final\\\_unit\\\_price < 0`—from commercial GMV and Net Revenue sums.

8\. \*\*Role-Playing Network Enrichment (T8):\*\* Added the `11` unmapped destination-only districts (`\\\[16, 17, 18, 22, 23, 29, 30, 48, 49, 60, 62]`, representing `46,282` order lines) to `dim\\\_network\\\_clean.csv` with `region\\\_id = -1` (`Virtual Destination District`) and classified every order into 4 Network Fulfillment Tiers.

9\. \*\*Chronology Anomaly Handling (T9):\*\* Flagged `521` packages with negative stage durations (`arr\\\_station\\\_time < ship\\\_out\\\_time` or `dlvr\\\_time < arr\\\_station\\\_time`) and set negative durations to `NaN` so clock-sync errors do not distort mean transit times.

10\. \*\*Granularity Reconciliation (T10):\*\* Created `fact\\\_orders\\\_header\\\_clean.csv` (`486,928` unique orders) by pre-aggregating line items and package telemetry to the `order\\\_id` grain prior to joining, preventing M:N fan-out revenue inflation. 

