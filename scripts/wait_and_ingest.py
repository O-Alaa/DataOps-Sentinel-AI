import sys
import time
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.config import settings
from sentinel.rag.ingest import build_index


def wait_for_qdrant(timeout_seconds: int = 90):
    if not settings.qdrant_url:
        return

    url = settings.qdrant_url.rstrip("/") + "/readyz"
    started = time.time()

    while time.time() - started < timeout_seconds:
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code == 200:
                return
        except Exception:
            pass

        print("Waiting for Qdrant...")
        time.sleep(2)

    raise RuntimeError(f"Qdrant did not become ready: {url}")


if __name__ == "__main__":
    wait_for_qdrant()
    result = build_index(recreate=True)
    print("RAG index ready:", result)
