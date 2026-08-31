# Project Radar v3 export contract

All v3 exports describe the same validated source snapshot.

Required shared fields include schema version, generation timestamp, source commit, project count, source-health status, evidence classes, stable identifiers, and checksums. JSONL, CSV, SQLite, static API, graph, profiles, alerts, feeds, and optional Parquet artifacts must not silently diverge.

SQLite is normalized into entity, evidence, relationship, profile, alert, and shadow-evaluation tables and is checked with `PRAGMA integrity_check`. Static API routes are read-only artifacts. The local API server rejects mutating HTTP methods. Optional Parquet output is produced only by an actual Parquet library; otherwise a capability receipt explains why the format is absent.

The SHA-256 manifest is the final publication boundary. Validation fails when a listed file is absent, has a different byte count, or has a different digest.
