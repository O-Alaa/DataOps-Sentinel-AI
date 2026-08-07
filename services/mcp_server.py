import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp.server import MCPServer

from sentinel.config import settings
from sentinel.tools.database import get_latest_kpi_summary as _get_latest_kpi_summary
from sentinel.tools.logs import inspect_latest_pipeline_log as _inspect_latest_pipeline_log

mcp = MCPServer(
    "DataOps Sentinel Enterprise Tools",
    instructions=(
        "Read-only enterprise investigation tools for KPI, pipeline, and log evidence. "
        "These tools never modify production data."
    ),
)


@mcp.tool()
def get_latest_kpi_summary() -> dict[str, Any]:
    """Return latest and previous KPI/pipeline row-count evidence from DuckDB."""
    return _get_latest_kpi_summary()


@mcp.tool()
def inspect_latest_pipeline_log() -> dict[str, Any]:
    """Inspect newest ETL pipeline log for warnings, errors, and rejected rows."""
    return _inspect_latest_pipeline_log()


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=settings.service_host,
        port=8100,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
