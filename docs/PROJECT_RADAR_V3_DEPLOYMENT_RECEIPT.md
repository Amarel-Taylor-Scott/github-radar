# Project Radar v3 deployment receipt

This file records the implementation scope submitted for production integration.

## Additive architecture

Project Radar v3 consumes the validated Project Radar v2 publication and does not mutate v2 production scores. It publishes an independently removable evidence, intelligence, export, graph, profile, alert, and shadow-evaluation layer under `feeds/projects/v3/` and `docs/projects/v3/`.

## Implemented components

- authoritative, bounded package-registry adapters;
- GitHub release and OpenSSF Scorecard evidence;
- optional local GH Archive event import;
- explicit evidence classes, units, windows, entity levels, coverage, confidence, and ranking eligibility;
- deterministic evidence-grounded project profiles;
- repository, owner, catalog, topic, package, release, security, and profile graph;
- shadow rankings, ablations, top-k overlap, rank correlation, and bootstrap benchmark support;
- static alert rules, Atom alerts, JSON Feed alerts, and webhook payload artifacts;
- normalized JSONL and CSV exports;
- relational SQLite snapshot with integrity validation;
- optional real Parquet output with an explicit capability receipt when `pyarrow` is unavailable;
- static read-only API and local read-only HTTP server;
- permanent project pages, canonical metadata, JSON-LD, sitemap, and robots output;
- reproducible SHA-256 manifest;
- full offline fixtures, regression tests, validation-only mode, and a pinned GitHub Actions workflow.

## Safety and evidence boundaries

- No discovered repository code is cloned, imported, installed, built, or executed.
- GitHub credentials are sent only to GitHub API hosts and never to package registries.
- Package identities are explicitly configured; repository names are not guessed as package names.
- External signals default to shadow-only and cannot change v2 production ranking.
- Missing external evidence is represented as missing, not zero.
- Generated interpretation is stored separately from observed facts.
- Public alerts require no user account, tracking, or private data.

## Promotion gates

Production promotion requires:

1. Python compile checks;
2. TOML, JSON configuration, and schema parsing;
3. v3-specific offline tests;
4. the complete repository regression suite;
5. an end-to-end offline v3 build against the current production v2 dataset;
6. SQLite integrity, XML, static API, profile, sitemap, and checksum validation;
7. feature-branch workflow success;
8. pull-request CI success;
9. main-branch production workflow success and a committed v3 status receipt.

The implementation intentionally leaves standalone mirror-repository creation and GitHub Pages administration outside this receipt because the connected integration does not expose those administrative operations.
