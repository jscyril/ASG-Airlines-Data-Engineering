# Data Quality Rules

These rules are agreed before transformation so the pipeline is explainable and repeatable.

| Area | Rule | Action |
|---|---|---|
| Schema | Required sheets and columns must exist | Fail the run |
| Text | Trim whitespace; normalize known categories | Standardize |
| Missing values | Convert blanks to nulls | Report and handle by field |
| Duplicate rows | Remove exact duplicates | Keep one record; log count |
| Flight ID | Match `^[A-Z]{2}[0-9]{3}$` | Flag and quarantine; never guess a replacement |
| Timestamps | Parse into typed datetimes | Flag parse failures |
| Overnight flights | Arrival earlier than departure means next day | Add one day to arrival |
| Duration | Recalculate from adjusted timestamps | Use recalculated value for KPIs |
| Duration anomalies | Null, non-positive, or implausibly high duration | Flag and quarantine/report |
| Foreign keys | Booking flight/passenger and payment booking references must resolve | Report orphan records |
| Payments | Missing amount is not zero | Keep null and exclude from amount totals |
| Booking status | Preserve cancelled bookings; exclude invalid records from business KPIs | Apply consistently |
| PII | Raw passenger and emergency-contact fields must not reach Gold/Power BI | Remove or hash before serving |

## Assumptions

- A flight arriving earlier by clock time is an overnight flight, not a negative-duration flight.
- A malformed flight identifier cannot be corrected without an approved mapping.
- Invalid records remain available in Quarantine for auditability.
- KPI definitions state their denominator explicitly.
