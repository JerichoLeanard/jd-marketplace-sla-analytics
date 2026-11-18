\# JD.com Marketplace Fulfillment SLA Breaches, Network Spillover Economics \& VIP Retention Analytics



\*\*Role:\*\* Data Analyst / Business Intelligence Analyst Portfolio Case Study  

\*\*Dataset:\*\* Official JD.com Transaction-Level Dataset (\*INFORMS Manufacturing \& Service Operations Management\*, March 2018 Production Logs — 486,928 Unique Orders | 546,061 Line Items | 293,229 Tracked Parcels | 454,897 Active Buyers)  

\*\*Tech Stack:\*\* Python (`pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`) • SQL (`SQLite 3`) • Power BI (`Star Schema`, `DAX`) • Git/GitHub



\---



\## 1. Executive Summary \& Business Problem



\### Business Problem

JD.com operates a high-velocity hybrid marketplace combining \*\*1P Self-Operated Retail\*\* (fulfilled through JD's Regional and Front Distribution Center network) and \*\*3P Marketplace Sellers\*\*. Despite strong top-line Gross Merchandise Value (\*\*RMB 66.92M\*\* across 486,928 orders in March 2018), the platform faces three operational and commercial pressures:

1\. \*\*Unquantified Fulfillment SLA Breaches (`14.97%` breach rate):\*\* Customers experiencing missed delivery promises across specific seller models, promotional windows, and urban/rural city tiers.

2\. \*\*Cross-Region Inventory Spillover (`47.76%` of order lines) \& Discount Erosion (`31.91%` of GMV):\*\* Local warehouse stockouts force orders to ship from distant origin distribution centers (`dc\_ori != dc\_des`), compounding margin compression on heavily discounted brands.

3\. \*\*High-Value Customer Churn \& Basket Contraction:\*\* Leadership lacked an integrated data model linking warehouse-to-doorstep lead times, local stockouts, and subsequent repeat-purchase spend among paid \*\*JD PLUS VIP\*\* members.



\### Headline Analytical Impact

\* \*\*Reconciled Multi-Table Granularity:\*\* Engineered an end-to-end Python and SQLite pipeline across 6 relational tables, resolving $M:N$ fan-out traps, `208,583` coded missing SLA values (`'-'`), `8,537` negative promotional gift prices, and `808` hexadecimal-to-scientific-notation hash corruptions (`4.99E+54`).

\* \*\*Diagnosed the "Local DC SLA Paradox":\*\* Proved that Local DC orders (`dc\_ori = dc\_des`) deliver \*\*3.1x faster\*\* than cross-country orders (`20.38h` vs. `64.07h` median) yet suffer the \*\*highest SLA breach rate (`17.21%` vs. `8.88%`)\*\* because `70.52%` of local orders are assigned an unbuffered 1-Day promise that fails when promotional warehouse dispatch backlogs surge (`4.14h` $\\rightarrow$ `19.31h`, $r = 0.958$).

\* \*\*Quantified 1P Stockout Spillover \& "Double-Bleeder" Brands:\*\* Demonstrated via Chi-Square contingency testing ($\\chi^2 = 141,410.33, p < 0.0001$) that a local destination stockout increases Cross-DC shipping odds by \*\*44.49x\*\*, and isolated \*\*51 "Double-Bleeder" brands (`RMB 16.08M` GMV)\*\* combining `48.42%` discount depth with `65.91%` Cross-DC spillover.

\* \*\*Measured VIP Basket Contraction (`RMB 5.62M` Revenue at Risk):\*\* Proved via longitudinal window functions (`ROW\_NUMBER`, `LEAD`) and Welch's t-test ($p = 0.0117$) that an Order #1 SLA breach causes \*\*JD PLUS VIP\*\* repeat buyers to contract their subsequent Order #2 basket by \*\*-15.3% (`RMB 100.46` vs. `RMB 118.57`)\*\*—and by a \*\*-RMB 31.52 net swing\*\* on baseline operating days.



\---



\## 2. Interactive Power BI Executive Dashboard



\*(Full `.pbix` file available in \[`reports/jd\_marketplace\_executive\_dashboard.pbix`](reports/) and DAX measure library documented in \[`docs/05\_powerbi\_dax\_and\_design\_guide.md`](docs/05\_powerbi\_dax\_and\_design\_guide.md))\*



\### Page 1: Fulfillment SLA \& Warehouse Bottleneck Command Center

!\[Page 1: SLA Command Center](figures/pbi\_page1\_sla\_command\_center.png)



\### Page 2: Cross-DC Network Spillover \& Brand Unit Economics

!\[Page 2: Cross-DC Spillover \& Brand Economics](figures/pbi\_page2\_spillover\_and\_brand\_economics.png)



\### Page 3: VIP Loyalty \& Longitudinal Revenue at Risk

!\[Page 3: VIP Loyalty \& Revenue at Risk](figures/pbi\_page3\_vip\_loyalty\_and\_retention.png)



\---



\## 3. Data Architecture \& Methodology



```text

\[Raw JD.com CSVs (6 Tables)] 

&#x20;      │  (src/01\_download\_and\_verify\_raw\_data.py \& src/02\_data\_profiling.py)

&#x20;      ▼

\[Programmatic Cleaning \& Grain Alignment (src/03\_data\_cleaning.py)]

&#x20; • Deduplicated 3,928 exact duplicate order rows \& 1 duplicate master SKU

&#x20; • Isolated 94,606 promotional free-gift rows (clamping 8,537 negative gift prices)

&#x20; • Enriched 11 warehouse-less destination districts (46,282 rows) as Virtual Districts

&#x20; • Pre-aggregated Order Header \& Delivery tables to 1:1 order\_id grain (Zero Fan-Out)

&#x20;      │

&#x20;      ├──► \[SQLite Relational Warehouse: jd\_marketplace.db (sql/01\_schema\_ddl.sql)]

&#x20;      │      • 7 Tables, PK/FK Constraints, 8 Indexes, 2 BI Views, 6 CTE/Window Queries

&#x20;      │

&#x20;      ├──► \[Python EDA \& Statistical Testing (src/04 \& src/06)]

&#x20;      │      • Kruskal-Wallis, Mann-Whitney U, Chi-Square + Odds Ratios, Welch's t-test

&#x20;      │

&#x20;      └──► \[Power BI Star Schema (src/07\_export\_powerbi\_star\_schema.py)]

&#x20;             • Role-Playing dim\_network (USERELATIONSHIP on dc\_ori / dc\_des) + 25 DAX Measures

