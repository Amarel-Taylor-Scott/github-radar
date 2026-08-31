# Changelog

All notable source and publication-schema changes are documented here. Daily repository movement is published separately in `feeds/projects/changes.md`.

## 0.2.0 — 2026-08-31

### Added

- Eight new project domains: scientific computing, databases, cloud-native infrastructure, bioinformatics, civic technology, accessibility, game development, and business automation.
- Official GitHub Community Metrics enrichment with balanced per-domain allocation.
- Explicit momentum evidence confidence: provisional lifetime, measured short window, and measured seven-day.
- Catalog-local descriptive novelty and under-recognition dimensions.
- Evidence review queue with non-accusatory triage flags.
- Per-catalog evidence audit.
- Run-to-run project and leaderboard change feed.
- Atom subscription feed and Shields-compatible badge JSON.
- SHA-256 publication manifest verified in the production workflow.
- `project-radar` console command.
- Python 3.13 CI coverage.
- Contribution, security, conduct, citation, ownership, pull-request, and Dependabot configuration.

### Changed

- Provisional lifetime velocity is confidence-weighted after normalization, so it cannot receive the same contribution as measured seven-day growth.
- Aggregate leaderboards use owner and domain diversity while preserving final score order.
- CI no longer installs optional test dependencies; the production test path is standard-library-only.
- Third-party GitHub Actions are pinned to immutable commit SHAs.

## 0.1.0 — 2026-08-31

- Initial general repository radar.
- Four Agent Extension Radar catalogs.
- First multi-domain Project Radar publication with ten catalogs and rolling history.
