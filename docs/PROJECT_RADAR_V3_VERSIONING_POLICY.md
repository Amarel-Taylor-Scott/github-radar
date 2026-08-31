# Project Radar v3 versioning policy

V3 schemas, signal contracts, profile templates, benchmark corpora, alert rules, source mappings, API routes, and export layouts are versioned independently where practical.

Backward-compatible additions may retain the current schema version. Renamed fields, changed semantics, removed fields, or incompatible entity relationships require a new schema or explicit migration. Consumers should use `schema_version`, source commit, generation timestamp, and manifest checksums rather than relying only on file paths.

Production v2 ranking and additive v3 evidence are separate contracts. A v3 shadow formula becoming production requires a documented ranking-version change rather than silently altering existing score semantics.
