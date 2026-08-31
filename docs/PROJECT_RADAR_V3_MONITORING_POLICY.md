# Project Radar v3 monitoring policy

Operational monitoring should track publication success, runtime, request counts, cache hits, source failures, partial coverage, project and catalog counts, evidence coverage, profile and graph counts, alert counts, SQLite integrity, API artifact presence, benchmark coverage, shadow-rank drift, and manifest verification.

Threshold breaches produce operator-facing receipts rather than silently changing rankings. A source-health regression can degrade the v3 layer while leaving the last known-good v2 publication available. Monitoring data must not contain credentials or private subscriber information.

Ranking drift is informational until reviewed against the benchmark and promotion policy. A sudden change in shadow score overlap does not automatically trigger a production ranking update.
