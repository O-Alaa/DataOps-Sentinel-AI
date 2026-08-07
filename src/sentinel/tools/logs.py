from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = PROJECT_ROOT / "data" / "logs"

def inspect_latest_pipeline_log() -> dict:
    logs = sorted(LOG_DIR.glob("pipeline_*.log"))
    if not logs:
        raise FileNotFoundError(
            f"No logs found under {LOG_DIR}. Run: python scripts/generate_demo_data.py"
        )

    latest = logs[-1]
    lines = latest.read_text(encoding="utf-8").splitlines()

    warnings = [
        line for line in lines
        if "WARNING" in line or "ERROR" in line or "REJECTED" in line
    ]

    return {
        "log_file": latest.name,
        "warnings_and_errors": warnings,
        "contains_null_employee_id": any(
            "employee_id" in x and "NULL" in x for x in lines
        ),
        "contains_rejected_rows": any(
            "3678" in x and "REJECTED" in x for x in lines
        ),
    }
