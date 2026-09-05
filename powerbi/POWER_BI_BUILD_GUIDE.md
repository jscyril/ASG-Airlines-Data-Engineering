# ASG Airlines — Power BI Build Guide

## Data connection

In Power BI Desktop, choose **Get Data → Text/CSV** and load the CSV files from `data/gold/`:

- `fact_flight_operations.csv`
- `fact_bookings.csv`
- `fact_payments.csv`
- `agg_route_kpis.csv`
- `agg_airline_kpis.csv`
- `agg_executive_kpis.csv`
- `dim_airline.csv`
- `dim_route.csv`
- `dim_date.csv`

Set date/time and numeric types explicitly. Do not load the Silver passenger file or any raw passenger data into the report.

## Recommended relationships

Use single-direction, one-to-many relationships:

```text
dim_airline[airline]       1 ─── * fact_flight_operations[airline]
dim_airline[airline]       1 ─── * agg_airline_kpis[airline]
dim_route[route]           1 ─── * fact_flight_operations[route]
dim_route[route]           1 ─── * agg_route_kpis[route]
fact_flight_operations[flight_id] 1 ─── * fact_bookings[flight_id]
fact_bookings[booking_id]  1 ─── * fact_payments[booking_id]
```

Use the aggregate tables for fast KPI visuals and the fact tables for drill-through/detail analysis. Avoid many-to-many relationships.

## Core DAX measures

Create the measures in a dedicated `Measures` table:

```DAX
Total Flights = COUNTROWS(fact_flight_operations)

Average Flight Duration (min) =
AVERAGE(fact_flight_operations[duration_minutes])

Median Flight Duration (min) =
MEDIAN(fact_flight_operations[duration_minutes])

Overnight Flights =
CALCULATE(
    COUNTROWS(fact_flight_operations),
    fact_flight_operations[overnight_flag] = TRUE()
)

Overnight Flight Rate =
DIVIDE([Overnight Flights], [Total Flights])

Valid Bookings = COUNTROWS(fact_bookings)

Confirmed Bookings =
CALCULATE(
    COUNTROWS(fact_bookings),
    fact_bookings[status] = "CONFIRMED"
)

Cancelled Bookings =
CALCULATE(
    COUNTROWS(fact_bookings),
    fact_bookings[status] = "CANCELLED"
)

Cancellation Rate =
DIVIDE([Cancelled Bookings], [Valid Bookings])

Payment Total =
SUM(fact_payments[amount])

Average Payment =
AVERAGE(fact_payments[amount])
```

Format durations as whole numbers, rates as percentages, and payments using the selected currency. Never replace missing payment amounts with zero in Power Query or DAX.

## Report pages

### 1. Executive Overview

Use cards for Total Flights, Average Flight Duration, Valid Bookings, Cancellation Rate, Payment Total, and Overnight Flight Rate.

Add:

- clustered bar: flights by airline
- bar chart: top 10 routes by flight count
- line or column chart: flights by departure date
- slicers: departure date, airline, source, destination, overnight flag

### 2. Duration Analysis

Add:

- histogram or binned column chart for duration
- average duration by airline
- average duration by route
- same-day versus overnight comparison
- detail table with flight ID, airline, route, departure, arrival, and duration

### 3. Route Performance

Add:

- route traffic ranking
- route average duration
- source/destination matrix
- booking count by route
- tooltip with average duration and overnight count

### 4. Airline Trends

Add:

- flight count by airline
- average duration by airline
- booking status by airline
- cancellation rate by airline
- payment total by airline

Keep `Unknown` visible and explain it in a tooltip or subtitle.

### 5. Data Quality and Anomalies

Load `data/quality/source_profile.csv` and `data/quality/silver_quality_results.csv` as quality tables. Show:

- malformed flight IDs
- missing-value counts
- quarantined record count
- overnight-flight count
- invalid booking/status count
- missing payment amount count

This page should be included in the submitted screenshots because it demonstrates engineering quality, not just dashboard styling.

## Visual design

- Use a dark navy header with a restrained blue accent.
- Use amber for warnings and red only for failed quality checks.
- Keep one consistent number format across pages.
- Use descriptive titles such as “Average Flight Duration by Airline”, not “Chart 1”.
- Put slicers in a consistent left or top panel.
- Add a small “Data refreshed” label using the pipeline run metadata once the Azure version is connected.
- Keep raw PII out of visual fields, filters, tooltips, and drill-through pages.

## Reconciliation checklist

Before publishing, compare Power BI values with `agg_executive_kpis.csv`:

- Total Flights = 747
- Average Flight Duration ≈ 164.1 minutes
- Median Flight Duration = 164 minutes
- Overnight Flights = 93 in the valid-flight Gold layer
- Valid Bookings = 679
- Cancellation Rate ≈ 33.7%
- Payment Total ≈ 5,419,385

If a value differs, check relationships and filters before changing the data.

## Publish and refresh

1. Save `ASG_Airlines.pbix` under `powerbi/`.
2. Publish to a dedicated Power BI workspace.
3. Configure the cloud data source after the Azure Gold layer is available.
4. Set scheduled refresh only after validating the first manual refresh.
5. Capture screenshots of every page and the successful refresh history.
