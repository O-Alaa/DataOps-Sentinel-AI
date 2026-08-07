import asyncio
import sys
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.config import settings
from sentinel.protocols.a2a_client import call_a2a_json

async def main():
    payload = {
        "query": "Investigate why the Sales KPI dashboard dropped today.",
        "retry_reason": "",
    }

    print("\n=== DATA AGENT OVER A2A ===")
    data = await call_a2a_json(settings.a2a_data_agent_url, payload)
    pprint(data)

    print("\n=== KNOWLEDGE AGENT OVER A2A ===")
    knowledge = await call_a2a_json(settings.a2a_knowledge_agent_url, payload)
    pprint(knowledge)

    assert data["data_evidence"]["latest_rejected_rows"] == 3678
    assert len(knowledge["knowledge_evidence"]) > 0
    print("\nA2A tests PASSED")

if __name__ == "__main__":
    asyncio.run(main())
