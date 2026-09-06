# ASG Airlines — End-to-End Data Engineering Case Study

This repository implements a reproducible local Python version of the ASG Airlines pipeline. It profiles the supplied workbook, applies quality rules, recalculates overnight flight durations, creates PII-safe curated data, quarantines invalid records, and builds Gold facts, dimensions, and KPI aggregates for Power BI.

## Run locally

The project uses Python 3.11 and `uv`.

```bash
uv sync
uv run pytest
uv run python src/profile.py
uv run python src/transform.py
uv run python src/gold.py
```

The source workbook must be available at `data/raw/UseCase - Airlines.xlsx`. Generated files are written to `data/curated/`, `data/quarantine/`, `data/quality/`, and `data/gold/`.

## Pipeline layers

- **Raw/Bronze:** immutable source workbook, kept outside the reporting model.
- **Curated/Silver:** normalized flights, bookings, payments, and `passengers_safe`; booking/passenger PII is removed or SHA-256 hashed.
- **Quarantine:** rejected records with reason codes for audit and remediation.
- **Gold:** `fact_flight_operations`, `fact_bookings`, `fact_payments`, dimensions, and route/airline/executive KPI aggregates.

See [docs/solution_walkthrough.md](docs/solution_walkthrough.md) and the formatted [Word walkthrough](docs/solution_walkthrough.docx) for architecture, data flow, rules, KPI definitions, security, and limitations.

## Power BI

Load the CSV files from `data/gold/` plus the quality CSVs. Use the star/snowflake model described in [powerbi/POWER_BI_BUILD_GUIDE.md](powerbi/POWER_BI_BUILD_GUIDE.md), create measures from [powerbi/measures.dax](powerbi/measures.dax), and keep raw/curated passenger data out of the report. Save the completed report as `powerbi/ASG_Airlines.pbix` locally; PBIX files are intentionally ignored by Git.

## Security note

Raw workbook, generated raw extracts, quarantine outputs, and PBIX files may contain sensitive or local-only data and are excluded by `.gitignore`. In Azure, store raw PII in a restricted container and publish only Gold/PII-safe tables to Power BI.
