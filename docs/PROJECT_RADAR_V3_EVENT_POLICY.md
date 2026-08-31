# Project Radar v3 event policy

V3 can derive events from consecutive validated snapshots and can optionally summarize locally supplied GH Archive event files.

Current-versus-previous events include repository discovery, disappearance from the bounded discovery surface, archival-state changes, catalog changes, star changes, package-version changes, release changes, and provider-evidence changes. “No longer discovered” is not equivalent to deletion.

The optional GH Archive importer is bounded by configured file and event limits and accepts only selected public event types. It does not download or commit raw event archives. Event counts are reconciled with current repository metadata and remain an additive signal.

An event record declares source, evidence class, entity level, window, observed time, stable identifier, and provenance. Events remain shadow-only unless a later ranking change passes the promotion gates.
