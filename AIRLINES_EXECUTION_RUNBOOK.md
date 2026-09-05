# ASG Airlines — Azure Execution Runbook

This is the build order for completing the assignment and producing a defensible submission.

## Phase 0 — Define the target and budget

Use an Azure subscription with a resource group dedicated to the project. Keep the design cost-aware: autosuspend Databricks compute, use a small development cluster, and delete the resource group after evaluation if it is no longer needed.

Target services:

- Azure Data Lake Storage Gen2
- Azure Data Factory
- Azure Databricks
- Azure Key Vault
- Microsoft Entra ID
- Azure Monitor / Log Analytics
- Power BI Service
- GitHub or Azure DevOps for source control and CI/CD

Optional polish: Microsoft Purview, Unity Catalog, private endpoints, and Bicep deployment. Add these only if they can be configured and explained correctly.

## Phase 1 — Create the repository

Create the repository with this structure and commit the original source file only where permitted by the assignment.

```text
airlines-case-study/
├── notebooks/
├── adf/
├── infra/
├── tests/
├── powerbi/
├── docs/
├── data/
└── README.md
```

Add a `.gitignore` that excludes credentials, local configuration, raw PII extracts, temporary files, and large generated artifacts. Add `README.md` immediately so later work stays documented.

### Local setup with uv

Use `uv` for fast, reproducible local development:

```bash
uv init
uv python pin 3.11
uv add pandas openpyxl pyarrow jupyter pytest
uv run jupyter lab
```

Run scripts and tests through the project environment:

```bash
uv run python src/run_pipeline.py
uv run pytest
```

Commit `pyproject.toml` and `uv.lock`. Do not commit `.venv`, credentials, raw PII extracts, or generated data.

## Phase 2 — Provision Azure

### Manual minimum

1. Create a resource group.
2. Create an ADLS Gen2 storage account with hierarchical namespace enabled.
3. Create these containers or folders:

```text
bronze/airlines/
silver/airlines/
gold/airlines/
quarantine/airlines/
audit/airlines/
```

4. Create Azure Data Factory.
5. Create Azure Databricks.
6. Create Key Vault.
7. Create Log Analytics and connect diagnostic settings.
8. Create Entra ID groups for engineers, analysts, and report consumers.

### Production-style improvement

Put resource names and environment values in Bicep. Deploy the same template to `dev`, `test`, and `prod` using parameters. This demonstrates repeatability instead of a portal-only deployment.

## Phase 3 — Configure identities and access

1. Enable a managed identity for Data Factory.
2. Grant only required ADLS permissions to Data Factory and Databricks identities.
3. Store unavoidable secrets in Key Vault.
4. Prefer Entra ID authentication over account keys.
5. Restrict raw/PII storage to the engineering group.
6. Give analysts access to Silver-safe and Gold only.
7. Give Power BI users access to the Gold serving layer.
8. Capture screenshots or exported role assignments for the documentation.

## Phase 4 — Land the source data

1. Upload the supplied workbook to a controlled staging location.
2. Use Data Factory to copy it into `bronze/airlines/<run_date>/`.
3. Add a pipeline parameter such as `source_file_path`.
4. Capture `run_id`, source file name, file size, modified time, and checksum.
5. Configure a failure path that writes an audit record and sends an alert.

Recommended ADF flow:

```text
Get Metadata
  → Validate file exists and extension
  → Copy Data to Bronze
  → Databricks: profile and transform
  → Databricks: build Gold
  → Quality Gate
  → Notify success/failure
```

Trigger it manually first, then add a daily schedule trigger. Do not claim real-time processing for a static workbook.

## Phase 5 — Profile the source in Databricks

Create `01_profile_source` and save results to `audit/airlines/<run_id>/profile`.

Profile sheet names, expected columns, record counts, nulls, duplicates, category values, ID violations, timestamp parse failures, duration outliers, and missing foreign-key references.

Expected relationships:

```text
passengers.passenger_id  ← bookings.passenger_id
flights.flight_id        ← bookings.flight_id
bookings.booking_id      ← payments.booking_id
```

Begin the notebook with markdown explaining the problem, inputs, expected schema, and quality rules. End with a compact profiling table.

## Phase 6 — Implement Silver transformations

Create `02_transform_silver` using PySpark and Delta tables.

### Required logic

1. Read every source sheet.
2. Add ingestion metadata.
3. Normalize column names.
4. Trim strings and convert blanks to null.
5. Cast numeric and timestamp fields.
6. Validate key fields.
7. Deduplicate using the correct business key.
8. Recalculate flight duration.
9. Add quality flags and reason codes.
10. Write valid data to Silver.
11. Write rejected/suspicious data to Quarantine.

### Duration algorithm

```python
arrival_adjusted = when(
    arrival_time < departure_time,
    arrival_time + expr("INTERVAL 1 DAY")
).otherwise(arrival_time)

duration_minutes = (
    unix_timestamp(arrival_adjusted) - unix_timestamp(departure_time)
) / 60
```

Use the equivalent Spark expression supported by the cluster runtime. Test same-day, overnight, missing, equal-time, and invalid-time cases.

### PII-safe passenger table

Create `silver_passengers_safe` with only approved fields, for example:

```text
passenger_key_hash
age_band
gender
```

Do not write raw email, phone, Aadhaar, passport, names, or emergency contacts into Silver-safe or Gold. Keep them only in restricted Bronze/raw storage when retention is necessary.

## Phase 7 — Build Gold tables and KPIs

Create `03_build_gold`.

Use documented grains:

- One row per flight in `fact_flight_operations`
- One row per valid booking in `fact_bookings`
- One row per payment in `fact_payments`
- One row per airline in `dim_airline`
- One row per route in `dim_route`
- One row per calendar date in `dim_date`

Create Gold aggregates for route traffic/duration, airline traffic/duration, booking status, payment totals, and anomaly summaries.

Document the grain and formula beside each table. Keep important business logic auditable in Gold rather than hiding everything inside Power BI.

## Phase 8 — Add automated quality gates

Create a quality result table with `run_id`, `rule_name`, `dataset_name`, `records_checked`, `records_failed`, `severity`, `status`, and `details`.

Suggested rules:

- Required columns exist
- Source file is not empty
- Business keys are not unexpectedly duplicated
- Required timestamps parse successfully
- Adjusted duration is positive
- No orphan booking-to-flight references
- No orphan payment-to-booking references
- PII columns are absent from serving tables
- Gold tables contain rows

Fail the ADF pipeline for critical failures. Allow warnings for known source issues when affected records are quarantined and the count is reported.

## Phase 9 — Connect Power BI

Use the Azure Databricks connector or a supported Gold serving endpoint. Prefer Import mode for this small dataset unless DirectQuery is specifically required.

Create five report pages: Executive Overview, Duration Analysis, Route Performance, Airline Trends, and Data Quality and Anomalies.

Add slicers for date, airline, source, destination, booking status, and overnight flag. Validate that KPI cards reconcile to Gold aggregates, filters work, unknown categories are clear, and no PII appears in tables, tooltips, exports, or hidden pages.

Publish to a Power BI workspace and configure scheduled refresh after validating the report locally.

## Phase 10 — CI/CD

Create a workflow with separate validation and deployment jobs:

```text
Pull request
  → lint notebooks/scripts
  → run unit tests
  → validate Bicep
  → check secrets are absent

Merge to main
  → deploy infrastructure/configuration
  → deploy ADF assets and notebooks
  → run pipeline in dev
  → publish deployment summary
```

Use GitHub repository secrets or federated credentials. Never commit storage keys, tokens, passwords, or exported raw PII.

## Phase 11 — Test end to end

Run from the original workbook and record the pipeline run ID, start/end time, input/output row counts, valid/quarantined row counts, quality results, Gold KPI totals, and Power BI refresh result.

Targeted tests:

- malformed flight ID is flagged
- missing airline becomes `Unknown` or is quarantined according to the rule
- overnight arrival receives a one-day adjustment
- negative raw duration is corrected or flagged
- cancelled booking remains available for status analysis
- missing payment amount does not become zero
- orphan references are reported
- PII does not reach Gold or Power BI

## Phase 12 — Documentation and evidence

Prepare `docs/solution_walkthrough.md` or the required Word document with the problem statement, architecture, data flow, data model, source dictionary, Bronze/Silver/Gold explanation, transformation rules, duration formula, overnight handling, quarantine strategy, PII/access control, KPIs, monitoring, CI/CD, assumptions, limitations, and screenshots.

Include this design-decision table:

| Decision | Reason |
|---|---|
| ADLS Gen2 | durable, low-cost lake storage |
| Data Factory | orchestration and parameterized ingestion |
| Databricks + Delta | scalable Spark transformations and reliable tables |
| Quarantine layer | preserves evidence instead of silently dropping data |
| PII-safe serving layer | reduces exposure in analytics tools |
| Gold aggregates | simpler and faster BI consumption |

## Phase 13 — Interview-ready explanation

Be ready to explain why you chose Bronze/Silver/Gold, why duration was recalculated, how malformed IDs were handled without guessing, what happens to invalid records, how PII was prevented from reaching Power BI, how tomorrow’s data would be processed incrementally, how the design scales, what causes failure versus warning, and how dashboard numbers were reconciled.

A strong answer is tied to an explicit rule, a logged result, or a test.

## Final acceptance checklist

- [ ] Original workbook preserved
- [ ] Azure resources deployed and documented
- [ ] ADF pipeline runs successfully
- [ ] Bronze, Silver, Gold, and Quarantine populated
- [ ] Duration and overnight logic tested
- [ ] Quality rules produce audit results
- [ ] PII absent from serving/reporting layers
- [ ] Gold KPIs reconcile with Power BI
- [ ] Power BI report published with screenshots
- [ ] CI/CD or reproducible deployment instructions committed
- [ ] README explains setup, execution, validation, and cleanup
- [ ] Repository contains no secrets or unintended PII
