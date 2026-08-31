# Project Radar v3 mirror handoff

The central repository remains the authoritative collector, evidence processor, ranking evaluator, and snapshot publisher. Standalone repositories should be generated mirrors, not independent implementations.

A mirror handoff bundle should include the catalog README, compact JSON, applicable profiles, static API subset, feeds, source commit, generation timestamp, schema version, count, history mode, source-health state, and checksums. All mirrors in one publication cycle must identify the same central snapshot.

Repository creation, GitHub Pages enablement, social-preview administration, and cross-repository credentials require GitHub administrative capabilities outside the current connector. Issue #5 remains the operational contract for those steps.
