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
        "My email is analyst@example.com. "
        "Our executive Sales KPI dashboard dropped significantly today. "
        "Investigate the ETL incident and recommend what we should do."
    )

    result = await investigate(query, input_channel="text")

    print("\n=== INTENT ===")
    print(result["intent"])

    print("\n=== PII ===")
    print("Redactions:", result["pii_detected_count"])
    print("Types:", result["pii_entities"])

    print("\n=== ROOT CAUSE ===")
    print(result["root_cause"])

    print("\n=== CONFIDENCE ===")
    print(f"{result['confidence']:.0%}")
    print("Validated:", result["validation_passed"])

    print("\n=== OBSERVABILITY ===")
    print("Trace ID:", result["trace_id"])
    print("Total latency ms:", result["total_latency_ms"])
    for event in result.get("timing_trace", []):
        print(event)

    serialized = str(result)
    assert "analyst@example.com" not in serialized
    assert result["intent"] == "investigate_data_incident"
    assert result["validation_passed"] is True
    assert result["pii_detected_count"] >= 1
    assert "employee_id" in result["root_cause"]
    assert "3678" in result["root_cause"].replace(",", "")
    assert len(result.get("timing_trace", [])) >= 6

    print("\nPhase 4 end-to-end test PASSED")

if __name__ == "__main__":
    asyncio.run(main())
