import pandas as pd

from transform import transform_bookings, transform_flights, transform_passengers


def test_overnight_flight_is_adjusted_to_next_day():
    flights = pd.DataFrame(
        [{"flight_id": "AI001", "airline": "Air India", "source": "BOM", "destination": "DEL",
          "departure_time": "2025-01-01 23:30", "arrival_time": "2025-01-01 01:15", "duration": 0}]
    )
    cleaned, _, _ = transform_flights(flights)
    assert cleaned.loc[0, "overnight_flag"]
    assert cleaned.loc[0, "duration_minutes"] == 105


def test_passenger_output_contains_no_raw_pii():
    passengers = pd.DataFrame(
        [{"passenger_id": "P1", "first_name": "A", "last_name": "B", "age": 25,
          "gender": "F", "email": "a@example.com", "phone": "123", "aadhaar_id": "999", "date_of_birth": "2000-01-01"}]
    )
    safe, _, _ = transform_passengers(passengers)
    assert set(safe.columns) == {"passenger_key_hash", "age_band", "gender"}
    assert "a@example.com" not in safe.astype(str).to_string()


def test_booking_output_contains_no_raw_pii():
    bookings = pd.DataFrame(
        [{"booking_id": "B1", "passenger_id": "P1", "flight_id": "AI001",
          "booking_date": "2025-01-01", "status": "confirmed", "passport_number": "X123",
          "seat_number": "12A", "emergency_contact_name": "Family",
          "emergency_contact_phone": "9999999999"}]
    )
    safe, _, _ = transform_bookings(bookings)
    assert set(safe.columns) == {
        "booking_id", "passenger_key_hash", "flight_id", "booking_date",
        "status", "seat_number", "status_valid_flag",
    }
    assert "passport_number" not in safe.columns
    assert "emergency_contact_phone" not in safe.columns
