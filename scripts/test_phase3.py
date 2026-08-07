import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.graph import investigate

async def main():
    query = (
        "Our executive Sales KPI dashboard dropped significantly today. "
        "Investigate what happened and recommend what we should do."
    )
    result = await investigate(query)

    print("\n=== ROOT CAUSE ===")
    print(result["root_cause"])

    print("\n=== IMPACT ===")
    print(result["impact"])

    print("\n=== SYNTHESIS MODE ===")
    print(result.get("synthesis_mode"))

    print("\n=== CONFIDENCE ===")
    print(f"{result['confidence']:.0%}")
    print("Validated:", result["validation_passed"])
    print("Retries:", result.get("retry_count", 0))

    print("\n=== PROTOCOL TRACE ===")
    for item in result.get("protocol_trace", []):
        print("-", item)

    print("\n=== AGENT TRACE ===")
    for item in result.get("agent_trace", []):
        print("✓", item)

    assert result["validation_passed"] is True
    assert any(x.get("protocol", "").startswith("A2A") for x in result["protocol_trace"])
    assert any(x.get("nested_protocol") == "MCP v2" for x in result["protocol_trace"])
    print("\nPhase 3 end-to-end test PASSED")

if __name__ == "__main__":
    asyncio.run(main())
