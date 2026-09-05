"""Profile the source workbook before any cleaning is applied."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/UseCase - Airlines.xlsx"
OUTPUT = ROOT / "data/quality/source_profile.csv"
EXPECTED_SHEETS = {"flights", "payments", "bookings", "passengers"}


def profile_workbook(source: Path = SOURCE) -> pd.DataFrame:
    sheets = pd.read_excel(source, sheet_name=None)
    missing_sheets = EXPECTED_SHEETS - set(sheets)
    assert not missing_sheets, f"Missing expected sheets: {sorted(missing_sheets)}"

    rows: list[dict[str, object]] = []

    def add(dataset: str, metric: str, value: object, details: str = "") -> None:
        rows.append({"dataset": dataset, "metric": metric, "value": value, "details": details})

    for name, frame in sheets.items():
        add(name, "row_count", len(frame))
        add(name, "column_count", len(frame.columns))
        add(name, "duplicate_row_count", int(frame.duplicated().sum()))
        for column, count in frame.isna().sum().items():
            if count:
                add(name, "missing_value_count", int(count), column)

    flights = sheets["flights"]
    valid_id = flights["flight_id"].fillna("").astype(str).str.fullmatch(r"[A-Z]{2}\d{3}")
    add("flights", "malformed_flight_id_count", int((~valid_id).sum()))
    add("flights", "duplicate_flight_id_count", int(flights["flight_id"].duplicated().sum()))

    departure = pd.to_datetime(flights["departure_time"], errors="coerce")
    arrival = pd.to_datetime(flights["arrival_time"], errors="coerce")
    raw_duration_hours = (arrival - departure).dt.total_seconds() / 3600
    add("flights", "timestamp_parse_failure_count", int((departure.isna() | arrival.isna()).sum()))
    add("flights", "overnight_flight_count", int((arrival.dt.date > departure.dt.date).sum()))
    add("flights", "negative_raw_duration_count", int((raw_duration_hours < 0).sum()))

    flight_ids = set(flights["flight_id"].dropna())
    bookings = sheets["bookings"]
    payments = sheets["payments"]
    add("bookings", "orphan_flight_reference_count", int((~bookings["flight_id"].isin(flight_ids)).sum()))
    add("payments", "duplicate_booking_reference_count", int(payments["booking_id"].duplicated().sum()))
    add(
        "passengers",
        "pii_column_count",
        len({"email", "phone", "aadhaar_id"}.intersection(sheets["passengers"].columns)),
        "email, phone, aadhaar_id",
    )

    return pd.DataFrame(rows)


def main() -> None:
    report = profile_workbook()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(OUTPUT, index=False)
    print(report.to_string(index=False))
    print(f"\nSaved profile: {OUTPUT}")


if __name__ == "__main__":
    main()
