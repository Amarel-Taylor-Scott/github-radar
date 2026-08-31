# Project Radar v3 maintenance checklist

## Daily

- Confirm v2 and v3 workflows completed.
- Verify v3 status, source receipts, and manifest.
- Review failed or partial sources.
- Inspect large shadow-rank movements and alert volume.

## Weekly

- Review evidence-coverage changes by catalog.
- Triage the highest-priority review records.
- Inspect package mappings and stale caches.
- Review new benchmark contributions.
- Check repository and artifact growth.

## Monthly

- Revalidate upstream endpoints and terms.
- Re-run shadow ablations and stability comparisons.
- Review optional dependency and pinned Action updates.
- Test staged recovery and validation-only mode.
- Review privacy, security, and retention boundaries.

## Before ranking promotion

- Complete every gate in `PROJECT_RADAR_V3_PROMOTION_POLICY.md`.
- Publish the benchmark and ablation evidence.
- Version the production ranking contract explicitly.
