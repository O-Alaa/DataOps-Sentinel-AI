import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from langgraph.graph import END
from sentinel.graph import route_after_validation

print("Failed validation, no retry yet:", route_after_validation({
    "validation_passed": False,
    "retry_count": 0,
}))

print("Passed validation:", route_after_validation({
    "validation_passed": True,
    "retry_count": 0,
}))

print("Failed after max retry:", route_after_validation({
    "validation_passed": False,
    "retry_count": 1,
}))

assert route_after_validation({"validation_passed": False, "retry_count": 0}) == "retry_context"
assert route_after_validation({"validation_passed": True, "retry_count": 0}) == END
print("\nRetry routing test PASSED")
