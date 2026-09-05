"""Build analytics-ready Gold tables from Silver CSV outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SILVER = ROOT / "data/curated"
GOLD = ROOT / "data/gold"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(SILVER / f"{name}.csv")


def _flag(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].astype(str).str.lower().eq("true")


def build_gold() -> dict[str, pd.DataFrame]:
    flights = _read("flights")
    bookings = _read("bookings")
    payments = _read("payments")

    flights["departure_time"] = pd.to_datetime(flights["departure_time"], errors="coerce")
    flights["arrival_time_adjusted"] = pd.to_datetime(flights["arrival_time_adjusted"], errors="coerce")
    flights["departure_date"] = flights["departure_time"].dt.date.astype("string")
    valid_flights = flights[_flag(flights, "flight_id_valid_flag") & ~_flag(flights, "duration_anomaly_flag")].copy()
    valid_flights["route"] = valid_flights["source"] + " → " + valid_flights["destination"]
    valid_flight_ids = set(valid_flights["flight_id"])

    bookings["booking_date"] = pd.to_datetime(bookings["booking_date"], errors="coerce")
    valid_bookings = bookings[bookings["status"].isin(["CONFIRMED", "CANCELLED", "PENDING"])].copy()
    valid_bookings = valid_bookings[valid_bookings["flight_id"].isin(valid_flight_ids)]
    valid_booking_ids = set(valid_bookings["booking_id"].dropna())

    payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce")
    valid_payments = payments[payments["booking_id"].isin(valid_booking_ids)].copy()

    route = valid_flights.copy()
    route_kpis = route.groupby("route", dropna=False).agg(
        flight_count=("flight_id", "count"),
        average_duration_minutes=("duration_minutes", "mean"),
        overnight_flight_count=("overnight_flag", "sum"),
    ).reset_index()
    booking_counts = valid_bookings.groupby("flight_id").size().rename("booking_count")
    route_kpis = route_kpis.merge(
        route[["route", "flight_id"]].drop_duplicates().merge(booking_counts, on="flight_id", how="left")
        .groupby("route")["booking_count"].sum().reset_index(),
        on="route", how="left",
    ).fillna({"booking_count": 0})

    airline_kpis = valid_flights.groupby("airline", dropna=False).agg(
        flight_count=("flight_id", "count"),
        average_duration_minutes=("duration_minutes", "mean"),
        overnight_flight_count=("overnight_flag", "sum"),
    ).reset_index()
    flight_airline = valid_flights[["flight_id", "airline"]]
    airline_bookings = valid_bookings.merge(flight_airline, on="flight_id", how="left").groupby("airline").agg(
        booking_count=("booking_id", "count"),
        confirmed_booking_count=("status", lambda values: (values == "CONFIRMED").sum()),
        cancelled_booking_count=("status", lambda values: (values == "CANCELLED").sum()),
    ).reset_index()
    airline_kpis = airline_kpis.merge(airline_bookings, on="airline", how="left").fillna(0)
    airline_kpis["cancellation_rate"] = airline_kpis["cancelled_booking_count"] / airline_kpis["booking_count"].replace(0, pd.NA)

    confirmed_booking_ids = set(valid_bookings.loc[valid_bookings["status"] == "CONFIRMED", "booking_id"])
    executive = pd.DataFrame(
        [
            {"metric": "total_flights", "value": len(valid_flights)},
            {"metric": "average_duration_minutes", "value": valid_flights["duration_minutes"].mean()},
            {"metric": "median_duration_minutes", "value": valid_flights["duration_minutes"].median()},
            {"metric": "overnight_flight_count", "value": int(_flag(valid_flights, "overnight_flag").sum())},
            {"metric": "valid_booking_count", "value": len(valid_bookings)},
            {"metric": "confirmed_booking_count", "value": len(confirmed_booking_ids)},
            {"metric": "cancellation_rate", "value": (valid_bookings["status"] == "CANCELLED").mean()},
            {"metric": "payment_total_with_amount", "value": valid_payments["amount"].sum()},
        ]
    )

    dimensions = {
        "dim_airline": valid_flights[["airline"]].drop_duplicates().sort_values("airline"),
        "dim_route": valid_flights[["source", "destination"]].drop_duplicates().assign(
            route=lambda frame: frame["source"] + " → " + frame["destination"]
        ),
        "dim_date": valid_flights[["departure_date"]].drop_duplicates().sort_values("departure_date"),
    }
    return {
        "fact_flight_operations": valid_flights,
        "fact_bookings": valid_bookings,
        "fact_payments": valid_payments,
        "agg_route_kpis": route_kpis,
        "agg_airline_kpis": airline_kpis,
        "agg_executive_kpis": executive,
        **dimensions,
    }


def main() -> None:
    GOLD.mkdir(parents=True, exist_ok=True)
    tables = build_gold()
    for name, frame in tables.items():
        frame.to_csv(GOLD / f"{name}.csv", index=False)
        frame.to_parquet(GOLD / f"{name}.parquet", index=False)
    print("Gold tables written:", ", ".join(tables))


if __name__ == "__main__":
    main()
