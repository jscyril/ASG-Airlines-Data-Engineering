# ASG Airlines Data Engineering Case Study

An end-to-end airline operations pipeline that ingests flight, booking, payment, and passenger data; validates and cleans it; protects sensitive passenger information; produces analytics-ready Gold tables; and feeds a Power BI report.

## Architecture

```text
Source workbook → Bronze → Silver → Quarantine
                              ↓
                            Gold → Power BI
```

The cloud target architecture uses Azure Data Factory for orchestration, ADLS Gen2 for storage, Azure Databricks and Delta Lake for transformation, Key Vault and Microsoft Entra ID for security, Azure Monitor for observability, and Power BI for reporting.

## Local execution

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), place the source workbook at `data/raw/UseCase - Airlines.xlsx`, then run:

```bash
uv sync
uv run python src/profile.py
uv run python src/transform.py
uv run python src/gold.py
uv run pytest -q
```

## Outputs

- `data/quality/`: source and Silver quality reports
- `data/curated/`: cleaned Silver CSV and Parquet datasets
- `data/quarantine/`: records rejected or flagged by quality rules
- `data/gold/`: facts, dimensions, and KPI aggregates for Power BI
- `powerbi/`: report build guide and DAX measures

## Data protection

Raw passenger names, email, phone, Aadhaar, passport, and emergency-contact fields are excluded from analytical serving outputs. The original source file must remain in controlled storage and must not be committed to a public repository.

## Documentation

- [Solution approach](AIRLINES_SOLUTION_APPROACH.md)
- [Execution runbook](AIRLINES_EXECUTION_RUNBOOK.md)
- [Data quality rules](docs/data_quality_rules.md)
- [Power BI build guide](powerbi/POWER_BI_BUILD_GUIDE.md)
