# Project Radar changelog

## 2.0.0 — 2026-08-31

### Added

- Confidence-calibrated momentum with explicit provisional and observed evidence classes.
- Raw and effective stars-per-day fields.
- Measurement confidence, observation count, and observed-history span.
- Official GitHub community-profile enrichment.
- Numeric GitHub repository IDs and node IDs for future rename reconciliation.
- Novelty and under-recognition dimensions.
- Most Novel and Under-recognized leaderboards.
- Previous-publication change reports.
- Manual evidence review queue.
- Audit receipt and evidence-coverage statistics.
- Per-catalog Atom feeds.
- SHA-256 publication manifest.
- Search interface filtering by measured versus provisional evidence.
- Scientific Computing, Database Systems, Bioinformatics, Civic Technology, Accessibility, Game Development, and Open-Source Business Software catalogs.
- Evidence policy, ranking scorecard, operator runbook, data dictionary, release notes, v3 roadmap, and v3 acceptance gates.
- Evidence-correction issue form.

### Changed

- Provisional lifetime velocity is confidence-damped before affecting momentum, acceleration, relative-growth, rising, hidden-gem, or interest scores.
- Repository quality incorporates bounded official community-health evidence when sampled.
- The aggregate catalog balances a broader set of native domains.
- Project publication schema advanced to version 2.
- GitHub Actions dependencies are pinned to immutable revisions.
- Package metadata advanced to version 0.2.0.

### Compatibility

- Existing path-derived project IDs remain stable.
- Numeric GitHub repository identity is additive.
- Missing historical changes remain `null`, never zero.

### Boundaries

- Project code is never executed.
- Community-profile enrichment is sampled under a bounded API budget.
- Inclusion is not a security, legal, quality, or maintenance endorsement.
- Review flags are quality-control prompts, not allegations.
