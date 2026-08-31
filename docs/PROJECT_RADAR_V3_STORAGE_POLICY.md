# Project Radar v3 storage policy

V3 treats the repository as a public snapshot and methodology source, not an unlimited event warehouse.

- The normalized v2 dataset remains the authoritative current repository snapshot.
- V3 emits compact current evidence, graph, profile, alert, shadow, and relational exports.
- SQLite is intended for reproducible local analysis and read-only API serving.
- JSONL and CSV are interchange formats; Parquet is optional when the required capability exists.
- Raw GH Archive files are never committed by the v3 publisher.
- Large registry responses are cached locally or in workflow cache and are not committed unless they are part of a bounded, normalized evidence artifact.
- Historical observations should move to partitioned releases or object storage before repository growth becomes operationally harmful.
- Every committed artifact is covered by the v3 SHA-256 manifest.
- A source can be disabled independently without making prior snapshots unreadable.
