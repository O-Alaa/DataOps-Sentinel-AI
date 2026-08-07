import json
import os
import statistics
import time
from pathlib import Path

import httpx

BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
CANDIDATES = ["qwen3:4b", "qwen3:1.7b"]
OUTPUT = Path("benchmarks/latest.json")


def available_models():
    response = httpx.get(BASE_URL + "/api/tags", timeout=10)
    response.raise_for_status()
    payload = response.json()
    return {
        model["name"]
        for model in payload.get("models", [])
    }


def run_once(model: str, num_ctx: int):
    prompt = (
        "You are a DataOps incident analyst. "
        "Evidence: 13,521 expected rows, 9,843 loaded rows, "
        "3,678 rejected rows, employee_id became NULL. "
        "Return a concise root cause in two sentences."
    )

    started = time.perf_counter()
    response = httpx.post(
        BASE_URL + "/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0,
                "num_ctx": num_ctx,
            },
        },
        timeout=240,
    )
    response.raise_for_status()
    elapsed_ms = (time.perf_counter() - started) * 1000

    text = response.json().get("response", "")
    factual = (
        "employee_id" in text
        and "3678" in text.replace(",", "")
    )

    return {
        "latency_ms": round(elapsed_ms, 2),
        "critical_facts_preserved": factual,
        "response": text,
    }


if __name__ == "__main__":
    models = available_models()
    results = []

    for model in CANDIDATES:
        if model not in models:
            print(f"Skipping {model}: not installed.")
            continue

        for num_ctx in [4096, 8192]:
            print(f"Benchmarking {model}, num_ctx={num_ctx}")

            # Warm-up
            run_once(model, num_ctx)

            runs = [run_once(model, num_ctx) for _ in range(2)]
            results.append({
                "model": model,
                "num_ctx": num_ctx,
                "avg_latency_ms": round(
                    statistics.mean(run["latency_ms"] for run in runs),
                    2,
                ),
                "all_critical_facts_preserved": all(
                    run["critical_facts_preserved"] for run in runs
                ),
                "runs": runs,
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nSaved benchmark to {OUTPUT}")
