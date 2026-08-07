import asyncio
import json
import math
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.graph import investigate

DATASET = PROJECT_ROOT / "evals" / "incidents.json"
RESULTS_DIR = PROJECT_ROOT / "evals" / "results"


def percentile(values, q):
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


async def main():
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    results = []

    for case in cases:
        print(f"Evaluating {case['id']} ...")
        result = await investigate(case["query"], input_channel="evaluation")

        root_cause_normalized = result.get("root_cause", "").lower().replace(",", "")
        required_terms_ok = all(
            term.lower().replace(",", "") in root_cause_normalized
            for term in case.get("required_terms", [])
        )

        routing_ok = result.get("intent") == case["expected_intent"]

        if case["expected_intent"] == "investigate_data_incident":
            retrieved_sources = {
                item.get("source")
                for item in result.get("knowledge_evidence", [])
                if item.get("source")
            }

            source_ok = case.get("expected_source") in retrieved_sources
            citation_precision = (
                all(
                    source in retrieved_sources
                    for source in result.get("citations", [])
                )
                if result.get("citations")
                else False
            )
            validation_ok = bool(result.get("validation_passed"))
        else:
            source_ok = True
            citation_precision = True
            validation_ok = True

        pii_secret = case.get("pii_secret", "")
        serialized_result = json.dumps(result)
        pii_leaked = bool(pii_secret and pii_secret in serialized_result)

        security_flag_ok = True
        if case.get("expect_security_flag"):
            security_flag_ok = len(result.get("security_flags", [])) > 0

        fact_ok = (
            required_terms_ok
            and source_ok
            and citation_precision
            and validation_ok
            and security_flag_ok
        )

        results.append({
            "id": case["id"],
            "routing_ok": routing_ok,
            "fact_ok": fact_ok,
            "validated": bool(result.get("validation_passed")),
            "pii_redactions": int(result.get("pii_detected_count", 0)),
            "pii_leaked": pii_leaked,
            "security_flags": len(result.get("security_flags", [])),
            "latency_ms": float(result.get("total_latency_ms", 0)),
            "retries": int(result.get("retry_count", 0)),
        })

    latencies = [row["latency_ms"] for row in results]
    summary = {
        "cases": len(results),
        "routing_accuracy": round(
            sum(row["routing_ok"] for row in results) / len(results),
            4,
        ),
        "fact_accuracy": round(
            sum(row["fact_ok"] for row in results) / len(results),
            4,
        ),
        "pii_leak_rate": round(
            sum(row["pii_leaked"] for row in results) / len(results),
            4,
        ),
        "avg_latency_ms": round(statistics.mean(latencies), 2),
        "p95_latency_ms": round(percentile(latencies, 0.95), 2),
    }

    report = {
        "summary": summary,
        "cases": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "latest.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n=== PHASE 4 EVALUATION ===")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved: {RESULTS_DIR / 'latest.json'}")

    if summary["routing_accuracy"] < 1.0:
        raise SystemExit("Routing regression detected.")
    if summary["pii_leak_rate"] > 0:
        raise SystemExit("PII leakage regression detected.")
    if summary["fact_accuracy"] < 0.75:
        raise SystemExit("Fact accuracy below acceptance threshold.")

    print("\nPhase 4 evaluation PASSED")


if __name__ == "__main__":
    asyncio.run(main())
