import asyncio
import sys
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.protocols.mcp_client import collect_dataops_evidence

async def main():
    result = await collect_dataops_evidence()
    print("\n=== MCP V2 EVIDENCE ===")
    pprint(result)
    assert result["data_evidence"]["latest_rejected_rows"] == 3678
    assert result["log_evidence"]["contains_null_employee_id"] is True
    print("\nMCP test PASSED")

if __name__ == "__main__":
    asyncio.run(main())
