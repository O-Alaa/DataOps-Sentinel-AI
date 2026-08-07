from pathlib import Path
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

def get_latest_kpi_summary() -> dict:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} does not exist. Run: python scripts/generate_demo_data.py"
        )

    con = duckdb.connect(str(DB_PATH), read_only=True)

    latest = con.execute(
        """
        SELECT
            run_date,
            expected_rows,
            loaded_rows,
            rejected_rows,
            sales_kpi
        FROM sales_kpi_daily
        ORDER BY run_date DESC
        LIMIT 1
        """
    ).fetchone()

    previous = con.execute(
        """
        SELECT
            run_date,
            expected_rows,
            loaded_rows,
            rejected_rows,
            sales_kpi
        FROM sales_kpi_daily
        ORDER BY run_date DESC
        LIMIT 1 OFFSET 1
        """
    ).fetchone()

    reject = con.execute(
        """
        SELECT rejected_reason, rejected_rows
        FROM pipeline_runs
        ORDER BY run_date DESC
        LIMIT 1
        """
    ).fetchone()

    con.close()

    latest_loaded = int(latest[2])
    previous_loaded = int(previous[2])
    delta_pct = round(((latest_loaded - previous_loaded) / previous_loaded) * 100, 2)

    return {
        "latest_date": str(latest[0]),
        "latest_expected_rows": int(latest[1]),
        "latest_loaded_rows": latest_loaded,
        "latest_rejected_rows": int(latest[3]),
        "latest_sales_kpi": float(latest[4]),
        "previous_date": str(previous[0]),
        "previous_loaded_rows": previous_loaded,
        "loaded_rows_change_pct": delta_pct,
        "rejected_reason": reject[0],
        "rejected_reason_rows": int(reject[1]),
    }
