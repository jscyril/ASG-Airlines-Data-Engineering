# ASG Airlines — Solution Walkthrough

## Objective

Turn inconsistent operational workbook data into trustworthy flight, booking, payment, and KPI data for Power BI while preserving audit evidence and preventing passenger PII from reaching serving tables.

## Architecture and data flow

```text
UseCase - Airlines.xlsx
        |
        v
Raw/Bronze (restricted, immutable source)
        |
        v
Profile + normalize + validate + recalculate duration
        |                         |
        v                         v
Curated/Silver (PII-safe)     Quarantine (reason-coded rejects)
        |
        v
Gold facts, dimensions, and KPI aggregates
        |
        v
Power BI semantic model and five report pages
```

The production target is ADLS Gen2, Data Factory, Databricks/Delta, Key Vault, Entra ID, Azure Monitor, and Power BI. This repository provides the equivalent local pandas implementation so the logic is reproducible without an Azure subscription.

## Data model

```text
dim_airline 1 ── * dim_flight * ── 1 fact_flight_operations
dim_route   1 ── * dim_flight * ── 1 fact_bookings * ── 1 fact_payments
```

Gold grains are one row per flight operation, valid booking, payment, airline, route, and departure date. `dim_flight` is deduplicated by `flight_id` for Power BI relationship integrity.

## Transformation and quality rules

- Column names and text are normalized; blanks become nulls.
- Flight IDs must match `^[A-Z]{2}[0-9]{3}$`; malformed IDs are never guessed or silently corrected.
- Departure and arrival are parsed as timestamps. If arrival precedes departure, one day is added before calculating duration.
- Duration is calculated from adjusted timestamps, and null, non-positive, or over-24-hour values are anomalous.
- Valid bookings retain `CONFIRMED`, `CANCELLED`, and `PENDING`; invalid statuses or missing keys are quarantined.
- Missing payment amounts remain null and are excluded from payment totals.
- Exact source profiling and quality results are written to CSV for audit.

## PII handling

Raw passenger fields remain only in restricted raw storage. `passengers_safe` contains `passenger_key_hash`, age band, and gender. Curated and Gold bookings contain only the hashed passenger key plus booking/operational attributes; passport and emergency-contact fields are removed. Power BI must load Gold and quality outputs only.

## KPI definitions

- Total flights: valid Gold flight-operation rows.
- Average/median duration: recalculated `duration_minutes` over valid Gold flights.
- Overnight flights: adjusted arrival crosses the departure date.
- Valid bookings: bookings with an allowed status and a valid Gold flight reference.
- Cancellation rate: cancelled valid bookings divided by all valid bookings.
- Payment total: sum of non-null payment amounts for valid booking references.

## Current local run results

The current source produces 747 valid flights, 679 valid bookings, average duration 164.1 minutes, 93 valid overnight Gold flights, cancellation rate 33.7%, and payment total 5,419,385.34. Quality profiling reports 273 malformed flight IDs, 125 overnight flags, 75 invalid booking/status records, 78 missing payment amounts, and 348 quarantined records.

## Report and operational handoff

The Power BI report has five pages: Executive Overview, Duration Analysis, Route Performance, Airline Trends, and Data Quality & Anomalies. Before delivery, refresh the model after the PII-safe schema change, validate slicer behavior and KPI reconciliation, capture page screenshots, and publish only the Gold/quality layer.

## Limitations and next production steps

The local implementation is batch pandas, not an Azure deployment. A production version should add ADF orchestration, immutable run metadata/checksums, managed identities, restricted ADLS permissions, monitoring/alerts, CI/CD, and a documented Power BI workspace refresh.
