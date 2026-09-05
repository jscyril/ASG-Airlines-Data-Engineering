import pandas as pd

from gold import build_gold


def test_gold_executive_flight_count_reconciles():
    tables = build_gold()
    flights = tables["fact_flight_operations"]
    kpis = tables["agg_executive_kpis"].set_index("metric")["value"]
    assert int(kpis["total_flights"]) == len(flights)
    assert float(kpis["average_duration_minutes"]) == flights["duration_minutes"].mean()
