from pathlib import Path
from datetime import date, timedelta
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
DB_PATH = DATA_DIR / "warehouse.duckdb"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

today = date.today()
incident_date = today

days = []
for offset in range(13, -1, -1):
    d = today - timedelta(days=offset)

    if d == incident_date:
        expected = 13_521
        loaded = 9_843
        rejected = 3_678
        sales_kpi = 72.8
        reason = "employee_id is NULL after employee mapping transformation"
        status = "COMPLETED_WITH_REJECTIONS"
    else:
        expected = 13_521 if offset == 1 else 13_300 + ((offset * 41) % 350)
        loaded = expected
        rejected = 0
        sales_kpi = round(98.0 + ((offset % 5) * 0.3), 1)
        reason = "NONE"
        status = "SUCCESS"

    days.append((d, expected, loaded, rejected, sales_kpi, reason, status))

if DB_PATH.exists():
    DB_PATH.unlink()

con = duckdb.connect(str(DB_PATH))

con.execute("""
CREATE TABLE sales_kpi_daily (
    run_date DATE,
    expected_rows INTEGER,
    loaded_rows INTEGER,
    rejected_rows INTEGER,
    sales_kpi DOUBLE
)
""")

con.execute("""
CREATE TABLE pipeline_runs (
    run_date DATE,
    pipeline_name VARCHAR,
    status VARCHAR,
    extracted_rows INTEGER,
    loaded_rows INTEGER,
    rejected_rows INTEGER,
    rejected_reason VARCHAR
)
""")

for d, expected, loaded, rejected, kpi, reason, status in days:
    con.execute(
        "INSERT INTO sales_kpi_daily VALUES (?, ?, ?, ?, ?)",
        [d, expected, loaded, rejected, kpi],
    )
    con.execute(
        "INSERT INTO pipeline_runs VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, "sales_daily_etl", status, expected, loaded, rejected, reason],
    )

con.close()

log_text = f"""\
{incident_date} 08:30:00 INFO pipeline=sales_daily_etl status=STARTED
{incident_date} 08:31:24 INFO extracted_rows=13521
{incident_date} 08:33:02 INFO stage=employee_mapping status=RUNNING
{incident_date} 08:34:11 WARNING employee_id contains NULL values after employee mapping transformation
{incident_date} 08:34:15 ERROR quality_rule=employee_id_not_null failed_rows=3678
{incident_date} 08:34:16 REJECTED rows=3678 reason="employee_id is NULL"
{incident_date} 08:37:49 INFO loaded_rows=9843
{incident_date} 08:38:10 WARNING pipeline completed with rejected rows
"""
(LOG_DIR / f"pipeline_{incident_date.isoformat()}.log").write_text(
    log_text, encoding="utf-8"
)

(KNOWLEDGE_DIR / "pipeline_runbook.md").write_text(
    """# Sales Daily ETL Runbook

## Required keys

`employee_id` is a mandatory business key for all Sales KPI records.

The pre-load quality gate rejects any row where `employee_id` is NULL.
Rejected rows must not enter the analytics warehouse because they cannot be
attributed to an employee or organizational hierarchy.

## Recovery procedure

1. Inspect the employee mapping transformation.
2. Repair missing employee identifiers.
3. Reprocess the rejected batch.
4. Validate expected-versus-loaded row counts.
5. Refresh downstream KPI dashboards only after validation passes.
""",
    encoding="utf-8",
)

(KNOWLEDGE_DIR / "kpi_definition.md").write_text(
    """# Sales KPI Definition

The executive Sales KPI dashboard is refreshed from the `sales_kpi_daily`
warehouse layer after completion of the `sales_daily_etl` pipeline.

A material drop in loaded source rows can produce a misleading decline in the
reported KPI even when the underlying business performance has not changed.
""",
    encoding="utf-8",
)

(KNOWLEDGE_DIR / "historical_incident_001.md").write_text(
    """# Historical Incident INC-001

## Symptom
A Sales KPI dashboard unexpectedly declined after a morning ETL run.

## Root cause
The employee mapping source contained incomplete identifiers. Rows with missing
`employee_id` values were rejected by the warehouse quality gate.

## Resolution
The mapping table was repaired and the rejected batch was reprocessed. The
dashboard returned to the expected range after refresh.
""",
    encoding="utf-8",
)

print("Demo data generated successfully.")
print(f"Database: {DB_PATH}")
print(f"Incident date: {incident_date}")
print("Expected rows: 13,521")
print("Loaded rows:   9,843")
print("Rejected rows: 3,678")
