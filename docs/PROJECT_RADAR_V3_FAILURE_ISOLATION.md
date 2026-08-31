# Project Radar v3 failure isolation

V3 is designed so optional evidence cannot take down the validated v2 publication.

Each registry, release, security, event, profile, graph, export, alert, and benchmark stage emits a receipt. External adapters have independent request budgets and caches. A failed or partial source produces missing evidence and a degraded receipt; it does not erase healthy repository metadata or substitute a zero value.

The v3 publisher writes into staging directories, validates schemas, counts, XML, SQLite integrity, static API files, profiles, and checksums, then promotes the complete bundle. Validation-only mode rechecks an existing bundle without network access.

The v3 layer can be disabled or removed without changing v2 rankings. The last known-good v2 publication remains available when v3 enrichment fails.
