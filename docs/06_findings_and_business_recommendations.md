\# Phase 10 Deliverable: Executive Findings \& Business Recommendations Report



\*\*Project:\*\* Diagnosing Delivery SLA Breaches, Network Spillover Economics, and Repeat-Purchase Basket Erosion in JD.com's Hybrid Marketplace  

\*\*Target Stakeholders:\*\* VP of Supply Chain \& Logistics, Head of Marketplace Operations (1P/3P), Director of Customer Experience \& Retention  

\*\*Data Scope:\*\* 486,928 Unique Orders | 546,061 Deduplicated Line Items | 293,229 Tracked Parcels | 454,897 Active Buyers (March 2018 Production Logs)



\---



\## 1. Executive Summary \& Synthesis



An end-to-end relational, statistical, and Business Intelligence audit of JD.com's March 2018 fulfillment and commercial logs (`RMB 66.92M` GMV; `RMB 45.57M` Net Realized Revenue) reveals that the platform's \*\*`14.97%` SLA Breach Rate (`43,485` breached orders)\*\* and \*\*`31.91%` promotional discount erosion (`RMB 21.35M`)\*\* are driven by three interconnected operational bottlenecks:



1\. \*\*Warehouse Dispatch Backlogs \& Algorithmic Over-Promising:\*\* SLA breaches are primarily caused by origin warehouse processing delays (`order\_time -> ship\_out\_time`), which surge by \*\*`+366%` (`4.14h` to `19.31h`, $p < 0.0001$)\*\* during promotional waves and correlate at \*\*$r = 0.958$\*\* with daily SLA failure. Furthermore, just \*\*3 origin warehouses (`DC 9`, `DC 5`, `DC 4`) account for `46.06%`\*\* of all late orders nationwide.

2\. \*\*Local 1P Inventory Stockouts Driving Cross-DC Spillover:\*\* Nearly half (`47.76%`) of all order lines ship Cross-DC (`dc\_ori != dc\_des`), increasing median delivery time by \*\*`+70.9%` (`20.38h` to `37.80h`, $p < 0.0001$)\*\*. Across tracked 1P SKUs, a local destination stockout increases the odds of Cross-DC spillover by \*\*`44.49x` (95% CI: `\[43.45x, 45.56x]`)\*\*, compounding margin erosion across \*\*`51` "Double-Bleeder" brands (`RMB 16.08M` GMV)\*\* that combine `48.42%` discount depth with `65.91%` Cross-DC shipping.

3\. \*\*JD PLUS VIP Exposure \& Subsequent Basket Contraction:\*\* Over \*\*`RMB 5.62M`\*\* in Net Realized Revenue (`41,619` buyers) is directly exposed to SLA breaches, including \*\*`25.09%` of multi-order JD PLUS VIP Champions\*\*. Controlling for express promise tiers and promotional periods, an Order #1 SLA breach causes JD PLUS VIPs to reduce their subsequent Order #2 basket spend by \*\*`-15.3%` (`RMB 100.46` vs. `RMB 118.57`, $p = 0.0117$)\*\*—and by \*\*`-RMB 31.52` net swing\*\* on baseline operating days.



\---



\## 2. Epistemic Separation: Facts vs. Interpretations vs. Hypotheses vs. Recommendations



| Category | Analytical Standard | Key Project Determinations |

| :--- | :--- | :--- |

| \*\*Observed Facts\*\* | Direct SQL/Python aggregations from cleaned tables (`data/processed/`). | • Platform GMV = `RMB 66,920,980.79`; Net Revenue = `RMB 45,566,800.69`; Discounts = `RMB 21,354,180.10` (`31.91%`).<br>• Local DC (`dc\_ori = dc\_des`) median delivery = `20.38h` (`17.21%` breach rate) vs. Inter-Region median delivery = `64.07h` (`8.88%` breach rate).<br>• Top 3 origin warehouses (`DC 9`, `DC 5`, `DC 4`) generate `20,030` breached orders (`46.06%` of total).<br>• Destination DC stockout rate on tracked 1P lines is `6.90%` (Local), `64.71%` (Intra-Region), `92.62%` (Inter-Region), and `100.00%` (11 Virtual Districts). |

| \*\*Statistical Hypotheses Tested\*\* | Non-parametric \& parametric inferential tests ($\\alpha = 0.05$). | • \*\*H1 (Network Spillover Lead-Time Penalty):\*\* Confirmed via Kruskal-Wallis ($H = 60,550.92, p < 0.0001$) and Mann-Whitney U ($p < 0.0001$).<br>• \*\*H2 (Warehouse \& Line-Haul Variance Share):\*\* Confirmed ($p < 0.0001$); Warehouse + Line-Haul account for `76.74%` of stage variance.<br>• \*\*Stockout-to-Spillover Contingency:\*\* Confirmed ($\\chi^2 = 141,410.33, p < 0.0001$, Cramer's $V = 0.7179$, $OR = 44.49\\text{x}$).<br>• \*\*H3 (VIP Repeat Basket Contraction):\*\* Confirmed via Welch's t-test ($t = 2.524, p = 0.0117$) and Mann-Whitney U ($p = 0.0009$). |

| \*\*Analytical Interpretations\*\* | Causal \& operational synthesis accounting for confounding variables. | • \*\*The Local DC SLA Paradox (Simpson's Paradox):\*\* Local DCs breach more often because `70.52%` of evaluated local orders carry a strict `1-Day` promise, leaving zero buffer for warehouse picking delays.<br>• \*\*Promotional Hangover Effect:\*\* Late-day promotional orders on March 1 and March 8 clog warehouse queues overnight, causing March 2 (`26.04%`) and March 9 (`21.54%`) to suffer the worst SLA breach rates.<br>• \*\*Promotional Confounding in Retention:\*\* Deal-hunters shopping during March 1–2 and 7–9 place rapid multi-orders regardless of delays, masking churn in raw repeat rates while VIP dissatisfaction manifests in smaller subsequent basket sizes. |

| \*\*Actionable Recommendations\*\* | Targeted, evidence-backed interventions tied to stakeholder KPIs. | • Dynamic Checkout SLA Buffering during warehouse queue surges.<br>• Pick-Wave Capacity \& Shift Realignment at `DC 9`, `DC 5`, `DC 4`, `DC 41`, and `DC 27`.<br>• Pre-Promotion Inventory Readiness Gate for the `51` Q1 Double-Bleeder brands.<br>• WMS VIP Priority Routing \& Automated Basket-Protected Recovery Coupons for `JD PLUS VIP` members. |



\---



\## 3. Prioritized Action Plan \& Stakeholder Roadmap



| Priority | Target Stakeholder | Recommended Intervention | Target Scope | Primary KPI Impacted | Assumptions \& Limitations |

| :---: | :--- | :--- | :--- | :--- | :--- |

| \*\*P1 (Immediate)\*\* | \*\*VP of Supply Chain \& Head of Marketplace\*\* | \*\*Dynamic Checkout SLA Buffering:\*\* Integrate real-time `dc\_ori` pick-queue backlog (`warehouse\_proc\_hrs > 6h`) into checkout EDD promises, automatically shifting 1-Day promises to 2-Day during promotional hangover windows (`Mar 2`, `Mar 9`). | Local DC \& Virtual District 1-Day Promises (`179k` orders) | Reduces \*\*Local DC SLA Breach Rate\*\* from `17.21%` toward `<10%` without added freight cost. | Assumes checkout EDD rules can query WMS queue telemetry in near-real time. |

| \*\*P2 (Short-Term)\*\* | \*\*VP of Supply Chain \& Warehouse Ops\*\* | \*\*Targeted DC Bottleneck Intervention:\*\* Reallocate pre-promo wave-picking labor to \*\*`DC 9`, `DC 5`, and `DC 4`\*\* (`46.06%` of all breaches) 12 hours before major discount events, and audit process failures at \*\*`DC 41` (`26.15h` delay)\*\* and \*\*`DC 27` (`21.55h` delay)\*\*. | Top 6 Origin DCs (`66.15%` of platform breaches) | Compresses \*\*Mean Breached Warehouse Dispatch Hrs\*\* from `19.31h` toward baseline (`<6h`). | Physical warehouse layout and labor union/shift constraints are unobserved in public logs. |

| \*\*P3 (Medium-Term)\*\* | \*\*Director of Commercial \& Inventory Planning\*\* | \*\*Pre-Promotion Inventory Gate for Q1 "Double Bleeders":\*\* Restrict the \*\*`51` Q1 Double-Bleeder brands (`RMB 16.08M` GMV)\*\* from running `>35%` direct/multi-buy markdowns unless regional destination DC stock availability exceeds `80%`. | `51` Q1 Brands (`138,562` paid units; `RMB 7.50M` discounts) | Lowers \*\*Cross-DC Spillover Rate\*\* (`65.91%`) and protects \*\*Net Realized Revenue Margin\*\*. | Wholesale COGS and vendor co-op subsidy agreements are external to the dataset. |

| \*\*P4 (Immediate CX)\*\* | \*\*Director of CX \& Retention Growth\*\* | \*\*JD PLUS VIP Priority Dispatch \& Tiered Recovery Voucher:\*\* Flag `plus = 1` orders for priority pick-wave dispatch in WMS queues (especially in Tier 1 \& Tier 5 cities) and issue an automated `RMB 15 off >= RMB 120` recovery voucher upon any VIP SLA breach. | `80,234` Active JD PLUS VIPs (`RMB 9.58M` Net Revenue) | Arrests the \*\*`-15.3%` (`-RMB 18.11`) VIP Order #2 Basket Contraction\*\* and protects \*\*`RMB 1.37M` VIP Revenue at Risk\*\*. | Voucher redemption rate and net incremental margin must be validated via A/B testing in production. |

