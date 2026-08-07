import sys
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.rag.ingest import build_index

if __name__ == "__main__":
    result = build_index(recreate=True)
    print("\n=== KNOWLEDGE INDEX READY ===")
    pprint(result)
