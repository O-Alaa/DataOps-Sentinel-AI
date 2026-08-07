# Historical Incident INC-001

## Symptom
A Sales KPI dashboard unexpectedly declined after a morning ETL run.

## Root cause
The employee mapping source contained incomplete identifiers. Rows with missing
`employee_id` values were rejected by the warehouse quality gate.

## Resolution
The mapping table was repaired and the rejected batch was reprocessed. The
dashboard returned to the expected range after refresh.
