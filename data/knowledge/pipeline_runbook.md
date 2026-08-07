# Sales Daily ETL Runbook

## Required keys

`employee_id` is a mandatory business key for all Sales KPI records.

The pre-load quality gate rejects any row where `employee_id` is NULL.
Rejected rows must not enter the analytics warehouse because they cannot be
attributed to an employee or organizational hierarchy.

## Recovery procedure

1. Inspect the employee mapping transformation.
2. Repair missing employee identifiers.
3. Reprocess the rejected batch.
4. Validate expected-versus-loaded row counts.
5. Refresh downstream KPI dashboards only after validation passes.
