# Project Radar operator runbook

## Normal daily operation

The scheduled Project Radar workflow runs after the general and agent-extension feeds. A healthy run should:

1. check out the exact `main` commit;
2. run the complete offline test suite;
3. collect every configured native catalog;
4. enrich a bounded, catalog-balanced set of repositories and community profiles;
5. validate total and per-catalog shrink guards;
6. score projects using the prior history;
7. generate catalog, audit, change, review, Atom, site, and manifest artifacts;
8. validate schema, counts, XML, and checksums;
9. commit generated output only when files changed.

## Healthy receipt

Inspect `feeds/projects/status.json`. A healthy receipt has:

- `ok: true`;
- publication schema matching the current release;
- all configured catalogs present;
- source-health totals;
- history mode;
- measurement-mode counts;
- review-queue count;
- manifest path.

Then verify `feeds/projects/manifest.json` against both `feeds/projects/` and `docs/projects/`.

## Source degradation

A failed query or enrichment source should be visible in `source_health`. The base run may continue when healthy sources still satisfy catalog minimums and shrink guards.

Do not bypass a failure merely to publish fresh timestamps. Determine whether:

- GitHub rate limiting or availability caused the failure;
- an upstream topic or query became invalid;
- an authentication permission changed;
- a schema changed;
- a catalog genuinely became too small;
- a local history or generated file is malformed.

Use `--allow-shrink` only for a reviewed, explained structural migration. Never use it as a routine retry flag.

## Count collapse

When a total or catalog shrink guard fails:

1. preserve the existing generated publication;
2. inspect source-health records;
3. compare query construction and configured topics;
4. run the collector into temporary directories;
5. inspect `changes.json` before replacing production;
6. adjust thresholds only when the change reflects an intentional product decision;
7. document the migration in release notes.

## Invalid manifest

A checksum failure means the publication bundle is internally inconsistent.

1. Do not commit the bundle.
2. Regenerate all outputs from the same source snapshot.
3. Confirm that manifest files are written last.
4. Verify no later process modifies generated content.
5. Retain the last known-good commit until verification passes.

## History problems

If `history.json` is unreadable, the collector can start a new history, but this resets recent measurement confidence.

Before accepting a reset:

- restore the last valid history from Git;
- validate JSON structure;
- confirm date keys and repository records;
- check whether a schema migration is required;
- document any unavoidable loss of measurement continuity.

Never convert missing history into zero growth.

## Suspicious ranking result

Use the evidence chain rather than manually editing generated Markdown:

1. find the project in `latest.json`;
2. inspect raw repository facts, provenance, catalogs, and growth fields;
3. inspect catalog-local component scores;
4. check measurement confidence and provisional status;
5. inspect community-profile sampling status;
6. inspect `review-queue.json`;
7. reproduce the score with the current code and test date;
8. correct source data, configuration, classification, or methodology;
9. add a regression fixture;
10. regenerate every dependent artifact.

Never hand-edit a generated rank.

## Repository transfer or rename

Path-derived IDs remain the public compatibility key, while numeric GitHub repository IDs are retained for reconciliation.

When a transfer or rename is confirmed:

1. match old and new paths by numeric repository ID;
2. record the alias or migration in a versioned mapping;
3. preserve historical observations;
4. avoid double-counting old and new names;
5. document any public ID migration before changing the compatibility contract.

## Manual review queue

Review flags are not allegations. A reviewer should:

- verify the current repository page;
- check official registry or organization evidence where relevant;
- confirm timestamps and measurement mode;
- distinguish unsampled community evidence from an observed absence;
- disclose affiliations;
- propose the smallest reproducible correction.

## Local validation

```bash
python -m unittest discover -s tests
python scripts/project_radar.py \
  --config project_radars.json \
  --output-dir /tmp/project-radar-feeds \
  --site-dir /tmp/project-radar-site
```

Validate the temporary publication before changing production.

## Recovery principle

The last known-good publication is preferable to a new but unverifiable publication. Recovery should replay a validated snapshot or restore a known-good commit, not silently recompute from a different source state.
