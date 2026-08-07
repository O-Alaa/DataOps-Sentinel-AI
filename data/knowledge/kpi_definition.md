# Sales KPI Definition

The executive Sales KPI dashboard is refreshed from the `sales_kpi_daily`
warehouse layer after completion of the `sales_daily_etl` pipeline.

A material drop in loaded source rows can produce a misleading decline in the
reported KPI even when the underlying business performance has not changed.
