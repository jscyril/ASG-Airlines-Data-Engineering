# ASG Airlines — Windows Setup and Power BI Guide

## 1. Get the repository

Clone the private repository:

```powershell
git clone https://github.com/jscyril/ASG-Airlines-Data-Engineering.git
cd ASG-Airlines-Data-Engineering
```

Alternatively, download the repository as a ZIP and extract it.

## 2. Install uv

Open PowerShell and install `uv` with WinGet:

```powershell
winget install --id=astral-sh.uv -e
```

Restart PowerShell, then verify:

```powershell
uv --version
```

Official guide: <https://docs.astral.sh/uv/getting-started/installation/>

## 3. Create the project environment

From the repository directory:

```powershell
uv sync
```

This reads `pyproject.toml` and `uv.lock`, installs Python 3.11 and the required dependencies, and creates the project environment.

## 4. Add the source workbook if needed

The source workbook is intentionally excluded from GitHub because it contains passenger PII.

Place it here:

```text
data\raw\UseCase - Airlines.xlsx
```

The assignment instructions document can remain local as well.

## 5. Validate the pipeline

Run the following commands from the repository root:

```powershell
uv run python src/profile.py
uv run python src/transform.py
uv run python src/gold.py
uv run pytest -q
```

Expected result:

```text
4 passed
```

The generated Power BI inputs are written to:

```text
data\gold\
```

## 6. Install Power BI Desktop

Install Power BI Desktop from Microsoft. Power BI Desktop requires Windows 10 or later.

Official download and requirements: <https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop>

## 7. Load the Gold data

Open Power BI Desktop and choose **Get data → Text/CSV**.

Load these files from `data\gold\`:

```text
fact_flight_operations.csv
fact_bookings.csv
fact_payments.csv
agg_route_kpis.csv
agg_airline_kpis.csv
agg_executive_kpis.csv
dim_airline.csv
dim_route.csv
dim_date.csv
```

Do not load the raw workbook, raw passenger data, or any file containing names, email addresses, phone numbers, Aadhaar numbers, passport numbers, or emergency contacts.

## 8. Create model relationships

In **Model view**, create these single-direction, one-to-many relationships:

```text
dim_airline[airline] → fact_flight_operations[airline]
dim_airline[airline] → agg_airline_kpis[airline]
dim_route[route] → fact_flight_operations[route]
dim_route[route] → agg_route_kpis[route]
fact_flight_operations[flight_id] → fact_bookings[flight_id]
fact_bookings[booking_id] → fact_payments[booking_id]
```

Use the relationships in the same direction shown above. Avoid many-to-many relationships.

## 9. Add DAX measures

Open **Modeling → New measure** and add the measures from `powerbi\measures.dax`.

The main measures are:

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

Valid Bookings = COUNTROWS(fact_bookings)

Cancelled Bookings =
CALCULATE(
    COUNTROWS(fact_bookings),
    fact_bookings[status] = "CANCELLED"
)

Cancellation Rate =
DIVIDE([Cancelled Bookings], [Valid Bookings])

Payment Total = SUM(fact_payments[amount])
```

Format duration as whole minutes, cancellation rate as a percentage, and payment totals as currency.

## 10. Build the report pages

Create these pages:

### Executive Overview

Add cards for total flights, average duration, valid bookings, cancellation rate, payment total, and overnight flight rate. Add airline distribution and top routes.

### Duration Analysis

Add duration distribution, average duration by airline, average duration by route, and overnight versus same-day flights.

### Route Performance

Add route traffic ranking, average route duration, source/destination matrix, and booking count by route.

### Airline Trends

Compare airlines by flights, duration, bookings, cancellation rate, and payment amount.

### Data Quality and Anomalies

Load `data\quality\source_profile.csv` and `data\quality\silver_quality_results.csv` as quality tables. Show malformed IDs, missing values, quarantined records, overnight flights, invalid statuses, and missing payment amounts.

## 11. Reconcile the report

Compare the report cards with `data\gold\agg_executive_kpis.csv`.

Expected values:

```text
Total flights: 747
Average duration: approximately 164.1 minutes
Median duration: 164 minutes
Overnight flights: 93
Valid bookings: 679
Cancellation rate: approximately 33.7%
Payment total: approximately 5,419,385
```

If a number differs, check filters and relationships before changing the source data.

## 12. Save the deliverables

Save the report as:

```text
powerbi\ASG_Airlines.pbix
```

Export report screenshots to:

```text
powerbi\dashboard_screenshot.png
```

Keep the `.pbix` and screenshots in the repository only if they contain no raw PII.

## 13. Optional Power BI Service publication

Publish the report to a dedicated Power BI workspace after validating it in Desktop. Sharing reports with others generally requires Power BI Pro/PPU or suitable Premium/Fabric capacity.

Microsoft guide: <https://learn.microsoft.com/en-us/power-bi/fundamentals/service-get-started>
