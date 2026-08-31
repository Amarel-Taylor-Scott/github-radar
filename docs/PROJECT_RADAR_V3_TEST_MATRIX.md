# Project Radar v3 test matrix

| Area | Required coverage |
|:--|:--|
| Evidence contracts | Evidence classes, entity levels, units, windows, confidence, coverage, missing-data semantics, ranking eligibility |
| Registry adapters | PyPI, npm, crates.io, RubyGems, Packagist, NuGet, Maven Central, Docker Hub fixtures |
| Credential isolation | GitHub token never sent to registry hosts |
| GitHub evidence | Release and OpenSSF provider fixtures, budgets, partial failures |
| Events | Snapshot differences, package releases, GitHub releases, bounded local GH Archive import |
| Profiles | Observed facts separated from generated interpretation, source bundle retained |
| Graph | Stable node and edge IDs, typed provenance, no unsupported relationship semantics |
| Shadow ranking | Production scores unchanged, missing evidence not zero, overlap, correlation, ablations |
| Benchmark | Corpus parsing, precision at k, NDCG, coverage, bootstrap labels identified |
| Alerts | Deterministic rule matching, Atom, JSON Feed, webhook payload artifacts |
| Exports | JSONL, CSV, SQLite schema and integrity, optional Parquet capability receipt |
| Static API | Read-only routes, traversal rejection, mutating methods rejected |
| SEO | Permanent pages, canonical metadata, JSON-LD, sitemap, robots |
| Publication | Staging, validation-only mode, source commit, counts, XML, SQLite, checksums |
| Regression | Complete existing v1/v2 test suite and Python compatibility matrix |
