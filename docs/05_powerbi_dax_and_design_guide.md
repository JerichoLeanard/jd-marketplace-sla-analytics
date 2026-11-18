\# Phase 9 Deliverable: Power BI Star Schema, DAX Library \& Dashboard Specification



\## 1. Star Schema Data Model Architecture

\- \*\*Fact Tables:\*\* `fact\_orders\_pbi` (Order Header grain), `fact\_1p\_stockout\_audit` (1P SKU-DC stockout attribution), `dim\_brand\_risk` (Brand unit-economics quadrant summary).

\- \*\*Dimension Tables:\*\* `dim\_date` (Calendar date table), `dim\_customers\_pbi` (Customer loyalty \& longitudinal repeat behavior), `dim\_network` (Role-playing logistics warehouse network).

\- \*\*Role-Playing Relationship Pattern:\*\*

&#x20; - Active (`1:\*`): `dim\_network\[dc\_id]` -> `fact\_orders\_pbi\[dc\_ori]`

&#x20; - Inactive (`1:\*`): `dim\_network\[dc\_id]` -> `fact\_orders\_pbi\[dc\_des]` (invoked via `USERELATIONSHIP`)



\---



\## 2. Production DAX Measure Library (Table: `\_Measures`)



\### Folder 01: Commercial \& Unit Economics KPIs

```dax

Total Orders = DISTINCTCOUNT(fact\_orders\_pbi\[order\_id])



Total Paid Units = SUM(fact\_orders\_pbi\[paid\_units])



Total Gift Units = SUM(fact\_orders\_pbi\[gift\_units])



Gross Merchandise Value (GMV) = SUM(fact\_orders\_pbi\[gmv\_order])



Net Realized Revenue = SUM(fact\_orders\_pbi\[net\_revenue\_order])



Total Promotional Discounts = SUM(fact\_orders\_pbi\[total\_discount\_order])



Effective Discount Rate % = 

DIVIDE(\[Total Promotional Discounts], \[Gross Merchandise Value (GMV)], 0)



Net Average Order Value (AOV) = 

DIVIDE(\[Net Realized Revenue], \[Total Orders], 0)



SLA Evaluated Orders = 

CALCULATE(

&#x20;   \[Total Orders],

&#x20;   NOT(ISBLANK(fact\_orders\_pbi\[is\_sla\_breach]))

)



SLA Breached Orders = 

CALCULATE(

&#x20;   \[Total Orders],

&#x20;   fact\_orders\_pbi\[is\_sla\_breach] = 1

)



On-Time Delivery Rate (OTDR %) = 

1 - DIVIDE(\[SLA Breached Orders], \[SLA Evaluated Orders], 0)



SLA Breach Rate % = 

DIVIDE(\[SLA Breached Orders], \[SLA Evaluated Orders], 0)



Share of Platform SLA Breaches % = 

DIVIDE(

&#x20;   \[SLA Breached Orders],

&#x20;   CALCULATE(\[SLA Breached Orders], ALL(fact\_orders\_pbi), ALL(dim\_network)),

&#x20;   0

)



Avg Warehouse Processing Hrs = AVERAGE(fact\_orders\_pbi\[warehouse\_proc\_hrs])



Median Warehouse Processing Hrs = MEDIAN(fact\_orders\_pbi\[warehouse\_proc\_hrs])



Avg Line-Haul Transit Hrs = AVERAGE(fact\_orders\_pbi\[linehaul\_transit\_hrs])



Avg Last-Mile Delivery Hrs = AVERAGE(fact\_orders\_pbi\[lastmile\_delivery\_hrs])



Median Total Fulfillment Hrs = MEDIAN(fact\_orders\_pbi\[total\_fulfillment\_hrs])



1-Day Express Promise % = 

DIVIDE(

&#x20;   CALCULATE(\[Total Orders], fact\_orders\_pbi\[promise\_days] = 1),

&#x20;   \[SLA Evaluated Orders],

&#x20;   0

)

Cross-DC Spillover Orders = 

CALCULATE(\[Total Orders], fact\_orders\_pbi\[is\_cross\_dc] = 1)



Cross-DC Spillover Rate % = 

DIVIDE(\[Cross-DC Spillover Orders], \[Total Orders], 0)



Orders by Destination DC (Role-Playing) = 

CALCULATE(

&#x20;   \[Total Orders],

&#x20;   USERELATIONSHIP(dim\_network\[dc\_id], fact\_orders\_pbi\[dc\_des])

)



1P Destination Stockout Rate % = 

VAR StockedOutLines = 

&#x20;   CALCULATE(

&#x20;       SUM(fact\_1p\_stockout\_audit\[order\_line\_count]),

&#x20;       fact\_1p\_stockout\_audit\[dest\_stock\_status] = "Stocked Out at Destination DC"

&#x20;   )

VAR TotalTrackedLines = SUM(fact\_1p\_stockout\_audit\[order\_line\_count])

RETURN

&#x20;   DIVIDE(StockedOutLines, TotalTrackedLines, 0)

Active Buyers = DISTINCTCOUNT(dim\_customers\_pbi\[user\_id])



Repeat Buyers (2+ Orders) = 

CALCULATE(

&#x20;   DISTINCTCOUNT(dim\_customers\_pbi\[user\_id]),

&#x20;   dim\_customers\_pbi\[is\_repeat\_buyer] = 1

)



Repeat Purchase Rate % = 

DIVIDE(\[Repeat Buyers (2+ Orders)], \[Active Buyers], 0)



Revenue Exposed to SLA Breach = 

CALCULATE(

&#x20;   SUM(dim\_customers\_pbi\[total\_net\_rev]),

&#x20;   dim\_customers\_pbi\[experienced\_sla\_breach] = 1

)



Avg Order #1 Net Spend = AVERAGE(dim\_customers\_pbi\[first\_order\_spend\_rmb])



Avg Order #2 Net Spend (Repeat Buyers) = AVERAGE(dim\_customers\_pbi\[second\_order\_spend\_rmb])



Repeat Basket Spend Change (RMB) = 

\[Avg Order #2 Net Spend (Repeat Buyers)] - \[Avg Order #1 Net Spend]

