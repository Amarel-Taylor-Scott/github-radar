# Project Radar v3 source-health receipts

Every external adapter and enrichment stage emits a machine-readable receipt.

A receipt identifies source, adapter, authoritative upstream, started and completed times, freshness, request budget, requests attempted, records returned, cache hits, success, partial or failed state, error summary, and whether the source may affect production ranking. Receipts never contain access tokens.

Partial coverage is distinguished from failure. A successful request that returns no mapped packages is not converted into a negative adoption signal. Cached evidence identifies its observation time and age. Stale cache can be surfaced as degraded evidence without blocking the v2 base publication.

Source-health summaries are included in the v3 status and audit artifacts and can be used by alerts or operators to detect coverage regressions.
