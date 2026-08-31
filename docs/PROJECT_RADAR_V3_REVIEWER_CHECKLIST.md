# Project Radar v3 reviewer checklist

## Architecture

- V3 consumes a validated v2 snapshot.
- V2 production scores and leaderboards remain unchanged.
- Optional stages can be disabled independently.

## Evidence

- Every signal has source, class, entity, unit, window, time, confidence, coverage, provenance, and missing-data semantics.
- Package identities are explicit.
- GitHub credentials are not sent to external registries.

## Safety

- Discovered code is never executed.
- Missing evidence is not zero.
- Generated interpretation is separate from facts.
- Review flags are not allegations.

## Evaluation

- Shadow rankings expose overlap, rank movement, correlation, and ablations.
- Bootstrap benchmark limitations are explicit.
- Production promotion remains blocked.

## Publication

- Schemas, XML, SQLite, profiles, API routes, sitemap, and checksums validate.
- Source commit and generation timestamp agree across artifacts.
- The feature branch and pull-request workflows pass before merge.
