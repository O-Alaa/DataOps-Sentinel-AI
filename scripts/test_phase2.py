import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.graph import investigate

async def main():
    result = await investigate(
        "Our executive Sales KPI dashboard dropped significantly today. Investigate and recommend actions."
    )
    print("Root cause:", result["root_cause"])
    print("Synthesis:", result.get("synthesis_mode"))
    print("Validated:", result.get("validation_passed"))

if __name__ == "__main__":
    asyncio.run(main())
