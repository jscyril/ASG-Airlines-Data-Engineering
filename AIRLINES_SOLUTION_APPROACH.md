# ASG Airlines — Solution Approach

## 1. Objective

Build a production-style Azure data pipeline that ingests the supplied airline workbook, preserves raw evidence, cleans and validates operational data, protects passenger PII, publishes analytics-ready data, and serves a Power BI report.

The submission should demonstrate reliable ingestion, explainable data quality decisions, correct flight-duration/KPI logic, and secure reporting.

## 2. Azure-first architecture

```text
Source Excel workbook
        |
        v
Azure Data Factory
  - parameterized ingestion
  - schema/file checks
        |
        v
ADLS Gen2: Bronze / Raw
  - immutable source copy
  - run metadata and audit files
        |
        v
Azure Databricks
  - PySpark validation/transformation
  - Delta Lake tables
        |
        +--> Silver: cleaned, validated, PII-safe data
        +--> Quarantine: rejected/suspicious records
        |
        v
Gold: KPI and star-schema tables
        |
        v
Power BI Service
  - semantic model, reports, refresh
```

Use ADLS Gen2 for storage, Data Factory for orchestration, Databricks for Spark/Delta transformations, and Power BI for consumption. Use Microsoft Entra ID, managed identities, Key Vault, Azure Monitor, and GitHub Actions or Azure DevOps for governance and deployment.

This follows the Azure Databricks medallion pattern: Bronze retains raw data, Silver improves quality, and Gold serves business-ready data. See the [Azure Databricks medallion architecture](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion), [ADLS Gen2 connector](https://learn.microsoft.com/en-us/azure/data-factory/connector-azure-data-lake-storage), [Data Factory managed identity guidance](https://learn.microsoft.com/en-us/azure/data-factory/data-factory-service-identity), and [Power BI with Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/partners/bi/power-bi-desktop).

## 3. Dataset assessment

The workbook contains four logical entities:

| Entity | Approx. rows | Key fields | Main issues |
|---|---:|---|---|
| Flights | 1,020 | `flight_id` | malformed IDs, missing airlines, time issues, overnight flights |
| Bookings | 1,000 | `booking_id`, `flight_id`, `passenger_id` | missing statuses and incomplete records |
| Payments | 1,000 | `payment_id`, `booking_id` | missing amounts and repeated booking references |
| Passengers | 1,039 | `passenger_id` | raw PII: email, phone, Aadhaar, DOB |

Observed issues include 273 malformed flight IDs, 41 missing airline values, 78 missing payment amounts, 45 missing booking statuses, 124 source overnight flights (125 after the rollover rule), and a negative raw duration after direct timestamp subtraction. Treat these as profiling findings, not assumptions to hide.

## 4. Data-layer design

### Bronze

- Store the original workbook unchanged.
- Add `ingestion_run_id`, `ingestion_timestamp`, `source_file_name`, and `source_hash`.
- Store one immutable copy per ingestion run.
- Do not expose this layer to Power BI users.

### Silver

Create cleaned Delta tables: `silver_flights`, `silver_bookings`, `silver_payments`, `silver_passengers_safe`, and `silver_data_quality_results`.

### Gold

Create analytics-ready tables: `fact_flight_operations`, `fact_bookings`, `fact_payments`, `dim_flight`, `dim_route`, `dim_airline`, `dim_date`, `agg_route_kpis`, `agg_airline_kpis`, and `agg_data_quality`.

## 5. Transformation rules

### General cleaning

- Trim whitespace from text fields.
- Standardize text casing and known category labels.
- Convert blank strings to nulls.
- Parse Excel serial dates/times into typed timestamps.
- Remove exact duplicate rows.
- Validate required columns and data types.
- Preserve rejected rows in a quarantine table with a reason code.

### Flight IDs

Validate against `^[A-Z]{2}[0-9]{3}$`.

Do not guess that an ID such as `6F026` belongs to another airline. Preserve the raw identifier, set `flight_id_valid_flag = false`, and add a quality reason. If an approved mapping becomes available, apply it through a visible mapping table rather than hardcoding it.

### Flight duration

1. Parse departure and arrival into timestamps.
2. If arrival is earlier than departure, add one day to arrival.
3. Calculate `duration_minutes = (arrival_adjusted - departure).total_seconds() / 60`.
4. Flag null, negative, zero, or implausibly high durations.
5. Use the recalculated value for KPIs; retain the source duration only for audit comparison.

### Bookings and payments

- Validate booking, passenger, and flight references.
- Keep cancelled bookings for operational reporting.
- Exclude invalid records from business KPIs unless the KPI measures data quality.
- Treat missing payment amounts as null, not zero.
- Define whether payment totals represent captured payments or all payment rows.

### PII

Exclude raw names, email, phone, Aadhaar, passport, and emergency-contact fields from Silver-safe and Gold datasets. If passenger-level relationships are needed, hash `passenger_id` with SHA-256 and retain only approved analytical attributes such as age band or gender. Store raw PII only in a restricted container when retention is necessary.

## 6. KPI catalogue

### Operations

- Total flights
- Average and median flight duration
- Same-day versus overnight flights
- Average duration by airline and route

### Network and commercial activity

- Flights by airline and route
- Bookings by route and airline
- Confirmed booking rate
- Cancellation rate
- Pending booking count
- Total and average captured payment amount

### Data quality

- Invalid flight-ID count
- Missing-value count by field
- Quarantined-record count
- Broken-reference count
- Duration anomaly count

Document every denominator. For example, cancellation rate can be `cancelled bookings / all valid bookings`.

## 7. Power BI report design

### Page 1 — Executive overview

KPI cards for total flights, average duration, bookings, cancellation rate, payment total, and anomaly count. Add airline distribution, top routes, and date/airline/status filters.

### Page 2 — Duration analysis

Show duration distribution, average duration by airline, average duration by route, and overnight-flight share. Add drill-through to non-PII flight details.

### Page 3 — Route performance

Show route traffic, source/destination matrix, booking volume by route, and route duration. Highlight busiest and least-used routes.

### Page 4 — Airline trends

Compare airlines by flight volume, average duration, booking volume, cancellation rate, and payment amount. Clearly label missing/unknown airline values.

### Page 5 — Data quality and anomalies

Show invalid IDs, missing fields, quarantined records, broken references, overnight flights, and duration outliers. This proves the pipeline is trustworthy, not just visually attractive.

## 8. Security and governance

- Use managed identities instead of storage keys in Data Factory and Databricks.
- Store unavoidable secrets in Key Vault.
- Use Entra ID groups for engineers, analysts, and report consumers.
- Apply ADLS permissions by layer.
- Keep raw PII outside the reporting model.
- Enable diagnostic logs and failure alerts in Azure Monitor.
- Use Unity Catalog where available for catalog, permissions, and lineage.

## 9. CI/CD and scalability

Store notebooks, SQL, pipeline JSON, configuration, tests, and documentation in GitHub. Use separate `dev`, `test`, and `prod` configuration values. Deploy infrastructure through Bicep or Terraform if time allows; deploy notebooks and ADF assets through the chosen CI/CD workflow.

Parameterize storage account, source path, run date, environment, catalog/schema, and Power BI workspace.

For this dataset, batch processing is sufficient. The design can scale by replacing the workbook with partitioned files or database extracts and using incremental ingestion based on a file watermark or source modification timestamp.

## 10. What makes the submission impressive

- Raw-to-Gold lineage that can be explained in an interview
- Quarantine instead of silent deletion
- Recalculated duration with overnight logic
- PII-safe reporting layer
- Automated quality gates
- Pipeline rerun/idempotency design
- Monitoring and failure notifications
- A dashboard page showing data quality
- A README with reproducible setup and deployment instructions

## 11. Proposed repository

```text
airlines-case-study/
├── data/
│   └── README.md
├── notebooks/
│   ├── 01_profile_source.py
│   ├── 02_transform_silver.py
│   └── 03_build_gold.py
├── src/
│   ├── config.py
│   ├── quality_rules.py
│   └── logging_utils.py
├── adf/
│   ├── pipeline_ingest.json
│   └── linked_services/
├── infra/
│   └── main.bicep
├── tests/
│   └── test_quality_rules.py
├── powerbi/
│   ├── ASG_Airlines.pbix
│   └── dashboard_screenshot.png
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   └── solution_walkthrough.docx
├── .github/workflows/
│   └── deploy.yml
├── pyproject.toml
├── uv.lock
└── README.md
```
