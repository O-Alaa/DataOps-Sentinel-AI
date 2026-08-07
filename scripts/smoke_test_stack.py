import json
import sys

import httpx

API = "http://localhost:8000"

health = httpx.get(API + "/health/dependencies", timeout=10)
health.raise_for_status()
health_payload = health.json()

print("=== DEPENDENCY HEALTH ===")
print(json.dumps(health_payload, indent=2))

if not health_payload.get("ready"):
    raise SystemExit("Stack is not ready.")

response = httpx.post(
    API + "/investigate",
    json={
        "query": (
            "Our executive Sales KPI dashboard dropped significantly today. "
            "Investigate what happened."
        )
    },
    timeout=360,
)
response.raise_for_status()
result = response.json()

print("\n=== INVESTIGATION ===")
print(result["root_cause"])
print("Confidence:", result["confidence"])
print("Validated:", result["validation_passed"])

assert result["validation_passed"] is True
assert "employee_id" in result["root_cause"]
assert "3678" in result["root_cause"].replace(",", "")

print("\nProduction stack smoke test PASSED")
