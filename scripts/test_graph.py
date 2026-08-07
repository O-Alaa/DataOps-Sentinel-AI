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
        "Our executive Sales KPI dashboard dropped significantly today. Investigate what happened."
    )
    print(result["root_cause"])
    print(f"Confidence: {result['confidence']:.0%}")

if __name__ == "__main__":
    asyncio.run(main())
