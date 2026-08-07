import sys
from pathlib import Path
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.llm import get_llm

class HealthCheck(BaseModel):
    status: str
    model_role: str

if __name__ == "__main__":
    print("Testing local Qwen3 through Ollama...")

    structured = get_llm().with_structured_output(
        HealthCheck,
        method="json_schema",
    )

    result = structured.invoke(
        "Return status='ok' and model_role='DataOps root-cause reasoning'."
    )

    print(result)
    print("\nLLM connection working.")
