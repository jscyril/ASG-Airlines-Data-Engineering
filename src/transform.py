"""Create cleaned, PII-safe Silver outputs from the raw workbook."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/UseCase - Airlines.xlsx"
CURATED = ROOT / "data/curated"
QUARANTINE = ROOT / "data/quarantine"
QUALITY = ROOT / "data/quality/silver_quality_results.csv"


def _clean_text(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    for column in frame.select_dtypes(include=["object", "string"]).columns:
        frame[column] = frame[column].replace(r"^\s*$", pd.NA, regex=True)
        frame[column] = frame[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    return frame


def transform_flights(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    frame = _clean_text(frame)
    frame["flight_id_raw"] = frame["flight_id"]
    frame["flight_id"] = frame["flight_id"].astype("string").str.upper()
    frame["airline"] = frame["airline"].fillna("Unknown").replace("UNKNOWN", "Unknown")
    frame["duration_raw"] = pd.to_numeric(frame["duration"], errors="coerce")
    frame = frame.drop(columns="duration")
    frame["departure_time"] = pd.to_datetime(frame["departure_time"], errors="coerce")
    frame["arrival_time"] = pd.to_datetime(frame["arrival_time"], errors="coerce")

    frame["flight_id_valid_flag"] = frame["flight_id"].fillna("").str.fullmatch(r"[A-Z]{2}\d{3}")
    frame["arrival_time_adjusted"] = frame["arrival_time"]
    valid_times = frame["arrival_time"].notna() & frame["departure_time"].notna()
    needs_rollover = valid_times & (frame["arrival_time"] < frame["departure_time"])
    overnight = valid_times & (
        (frame["arrival_time"].dt.date > frame["departure_time"].dt.date) | needs_rollover
    )
    frame.loc[needs_rollover, "arrival_time_adjusted"] += pd.Timedelta(days=1)
    frame["overnight_flag"] = overnight
    frame["duration_minutes"] = (
        frame["arrival_time_adjusted"] - frame["departure_time"]
    ).dt.total_seconds() / 60
    frame["duration_anomaly_flag"] = frame["duration_minutes"].isna() | (frame["duration_minutes"] <= 0) | (
        frame["duration_minutes"] > 24 * 60
    )

    bad = ~frame["flight_id_valid_flag"] | frame["duration_anomaly_flag"]
    quarantine = frame.loc[bad].copy()
    quarantine.insert(0, "dataset", "flights")
    quarantine.insert(1, "quarantine_reason", "invalid flight ID or duration anomaly")
    quality = [
        {"dataset": "flights", "rule": "invalid_flight_id", "failed_records": int((~frame["flight_id_valid_flag"]).sum())},
        {"dataset": "flights", "rule": "duration_anomaly", "failed_records": int(frame["duration_anomaly_flag"].sum())},
        {"dataset": "flights", "rule": "overnight_flight", "failed_records": int(overnight.sum())},
    ]
    return frame, quarantine, quality


def transform_bookings(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    frame = _clean_text(frame)
    frame["booking_date"] = pd.to_datetime(frame["booking_date"], errors="coerce")
    frame["status"] = frame["status"].astype("string").str.upper()
    # Keep only approved analytical attributes.  Passenger identifiers are
    # retained only as a one-way hash so bookings can be joined to the safe
    # passenger dimension without exposing raw PII.
    frame["passenger_key_hash"] = frame["passenger_id"].map(
        lambda value: hashlib.sha256(str(value).encode()).hexdigest() if pd.notna(value) else pd.NA
    )
    allowed = {"CONFIRMED", "CANCELLED", "PENDING"}
    frame["status_valid_flag"] = frame["status"].isin(allowed)
    bad = ~frame["status_valid_flag"] | frame["booking_id"].isna() | frame["flight_id"].isna()
    approved_columns = [
        "booking_id", "passenger_key_hash", "flight_id", "booking_date",
        "status", "seat_number", "status_valid_flag",
    ]
    safe = frame[[column for column in approved_columns if column in frame.columns]].copy()
    quarantine = safe.loc[bad].copy()
    quarantine.insert(0, "dataset", "bookings")
    quarantine.insert(1, "quarantine_reason", "invalid status or missing booking reference")
    quality = [{"dataset": "bookings", "rule": "invalid_status_or_key", "failed_records": int(bad.sum())}]
    quality.append({"dataset": "bookings", "rule": "pii_removed", "failed_records": 0})
    return safe, quarantine, quality


def transform_payments(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    frame = _clean_text(frame)
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    bad = frame["payment_id"].isna() | frame["booking_id"].isna()
    quarantine = frame.loc[bad].copy()
    quarantine.insert(0, "dataset", "payments")
    quarantine.insert(1, "quarantine_reason", "missing payment or booking key")
    quality = [
        {"dataset": "payments", "rule": "missing_amount", "failed_records": int(frame["amount"].isna().sum())},
        {"dataset": "payments", "rule": "missing_key", "failed_records": int(bad.sum())},
    ]
    return frame, quarantine, quality


def transform_passengers(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    frame = _clean_text(frame)
    safe = pd.DataFrame(index=frame.index)
    safe["passenger_key_hash"] = frame["passenger_id"].map(
        lambda value: hashlib.sha256(str(value).encode()).hexdigest() if pd.notna(value) else pd.NA
    )
    age = pd.to_numeric(frame["age"], errors="coerce")
    safe["age_band"] = pd.cut(age, bins=[0, 17, 30, 45, 60, 200], labels=["0-17", "18-30", "31-45", "46-60", "61+"])
    safe["gender"] = frame["gender"].astype("string").str.upper()
    quality = [{"dataset": "passengers", "rule": "pii_removed", "failed_records": 0}]
    return safe, pd.DataFrame(), quality


def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(CURATED / f"{name}.csv", index=False)
    frame.to_parquet(CURATED / f"{name}.parquet", index=False)


def main() -> None:
    CURATED.mkdir(parents=True, exist_ok=True)
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    sheets = pd.read_excel(SOURCE, sheet_name=None)
    transformed = {
        "flights": transform_flights(sheets["flights"]),
        "bookings": transform_bookings(sheets["bookings"]),
        "payments": transform_payments(sheets["payments"]),
        "passengers_safe": transform_passengers(sheets["passengers"]),
    }
    quality: list[dict[str, object]] = []
    quarantine: list[pd.DataFrame] = []
    for name, (cleaned, rejected, checks) in transformed.items():
        _write(cleaned, name)
        quality.extend(checks)
        if not rejected.empty:
            quarantine.append(rejected)
    if quarantine:
        pd.concat(quarantine, ignore_index=True, sort=False).to_csv(QUARANTINE / "records.csv", index=False)
    pd.DataFrame(quality).to_csv(QUALITY, index=False)
    print(pd.DataFrame(quality).to_string(index=False))
    print(f"\nCurated data: {CURATED}")
    print(f"Quarantine data: {QUARANTINE}")


if __name__ == "__main__":
    main()
