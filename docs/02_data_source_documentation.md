\# Data Source Documentation: JD.com MSOM Relational Dataset



\## 1. Dataset Overview \& Provenance

\- \*\*Dataset Title:\*\* JD.com Transaction-Level Data for the MSOM Data-Driven Research Challenge

\- \*\*Publisher:\*\* JD.com \& INFORMS Manufacturing \& Service Operations Management

\- \*\*Collection Period:\*\* March 1, 2018 – March 31, 2018

\- \*\*Primary Mirror:\*\* https://huggingface.co/datasets/a6687543/MSOM\_Data\_Driven\_Challenge\_2020/tree/main



\## 2. Table-by-Table Specification

| Table File Name | Role in Project | Approx. Rows | Columns | Primary Grain |

| :--- | :--- | :---: | :---: | :--- |

| `JD\_order\_data.csv` | Fact Table (Transactions \& Pricing) | \~549,989 | 17 | `order\_id` + `sku\_id` |

| `JD\_delivery\_data.csv` | Fact Table (Logistics \& Lead Times) | \~293,229 | 6 | `package\_id` + `order\_id` |

| `JD\_user\_data.csv` | Customer Dimension | \~457,298 | 10 | `user\_id` |

| `JD\_sku\_data.csv` | Product Dimension | \~31,868 | 7 | `sku\_id` |

| `JD\_network\_data.csv` | Logistics Network Dimension | \~56 | 2 | `dc\_id` |

| `JD\_inventory\_data.csv` | Daily Stock Snapshot | \~1,360,795 | 3 | `dc\_id` + `sku\_id` + `date` |

