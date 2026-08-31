# Project Radar v3 signal catalog

Every v3 signal is serialized with its provider, evidence class, entity level, value, unit, time window, observation time, freshness time, confidence, coverage, stable external identifier, provenance, missing-data semantics, and ranking eligibility.

| Signal family | Entity level | Evidence class | Default ranking eligibility |
|:--|:--|:--|:--:|
| Package version and registry metadata | Package | Observed | Shadow only |
| Registry downloads or pulls | Package | Measured | Shadow only |
| GitHub releases and release assets | Release / repository | Observed or measured | Shadow only |
| OpenSSF Scorecard | Repository | Observed provider result | Shadow only |
| GH Archive event counts | Repository / event window | Measured from supplied event files | Shadow only |
| V2 stars, forks, watchers, timestamps | Repository | Observed | Controlled by v2 |
| V2 rolling growth | Repository | Measured or provisional | Controlled by v2 |
| Deterministic project profile interpretation | Profile | Generated interpretation | Never |
| Catalog/topic/package graph edge | Relationship | Observed, configured, or inferred as labeled | Never directly |
| Static alert match | Alert | Derived from versioned rule | Never |
| Shadow evidence score | Repository/catalog | Inferred experimental score | Never until promoted through gates |

Missing registry, security, release, event, or profile evidence remains absent. The shadow formula renormalizes over available evidence rather than assigning a failing zero to projects outside an adapter’s coverage.
