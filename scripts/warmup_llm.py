import os
import time

import httpx

base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
model = os.getenv("OLLAMA_MODEL", "qwen3:4b")
num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "4096"))

payload = {
    "model": model,
    "prompt": "Return exactly: READY",
    "stream": False,
    "think": False,
    "keep_alive": "30m",
    "options": {
        "num_ctx": num_ctx,
        "temperature": 0,
    },
}

for attempt in range(30):
    try:
        started = time.perf_counter()
        response = httpx.post(
            base_url + "/api/generate",
            json=payload,
            timeout=180,
        )
        response.raise_for_status()
        print(
            f"LLM warmup complete in "
            f"{time.perf_counter() - started:.2f}s: {model}"
        )
        raise SystemExit(0)
    except Exception as exc:
        print(f"Waiting for Ollama/model ({attempt + 1}/30): {exc}")
        time.sleep(3)

raise SystemExit("LLM warmup failed.")
