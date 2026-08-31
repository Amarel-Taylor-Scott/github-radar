# Project Radar data dictionary

This document describes the primary fields in the normalized Project Radar publication. Field availability may vary by source and publication schema.

## Repository identity

| Field | Meaning |
|:--|:--|
| `id` | Stable public compatibility identifier derived from canonical `owner/repository` |
| `repository_id` | Numeric GitHub repository ID when observed |
| `node_id` | GitHub GraphQL node ID when observed |
| `full_name` | Canonical current GitHub `owner/repository` path |
| `owner` | Repository owner login |
| `name` | Repository name |
| `html_url` | Public repository URL |

Numeric identity fields support future rename and transfer reconciliation. They do not replace the current public compatibility ID in schema 2.

## Descriptive metadata

| Field | Meaning |
|:--|:--|
| `description` | GitHub repository description |
| `homepage` | Repository homepage URL |
| `language` | GitHub primary language |
| `topics` | GitHub repository topics |
| `license_spdx` | GitHub-reported SPDX identifier |
| `project_type` | Deterministic Project Radar classification such as project, application, framework, CLI, dataset, benchmark, education, resource-list, or template |

## Repository counters and dates

| Field | Meaning |
|:--|:--|
| `stars` | Current GitHub stargazer count |
| `forks` | Current GitHub fork count |
| `watchers` | Current GitHub subscriber count when available |
| `open_issues` | Current open issue count reported by GitHub |
| `size_kb` | GitHub repository size field |
| `created_at` | Repository creation timestamp |
| `pushed_at` | Last-push timestamp |
| `updated_at` | GitHub repository-update timestamp |

Counters are point-in-time observations, not lifetime event logs.

## Repository state

| Field | Meaning |
|:--|:--|
| `archived` | GitHub archived flag |
| `disabled` | GitHub disabled flag |
| `fork` | Whether the repository is a fork |
| `is_template` | GitHub template-repository flag |
| `has_issues` | Issues feature enabled |
| `has_discussions` | Discussions feature enabled |
| `has_wiki` | Wiki feature enabled |
| `has_pages` | GitHub Pages enabled |
| `api_complete` | Detailed repository metadata was successfully observed |

## Community-profile evidence

| Field | Meaning |
|:--|:--|
| `community_profile_complete` | GitHub community-profile endpoint was successfully sampled |
| `community_health_percentage` | GitHub-reported community-health percentage |
| `has_readme` | README observed in the official community profile |
| `has_code_of_conduct` | Code of conduct observed |
| `has_contributing` | Contributing guide observed |
| `has_issue_template` | Issue template observed |
| `has_pull_request_template` | Pull-request template observed |
| `has_security_policy` | Security policy observed |

When `community_profile_complete` is false, the other fields are unknown rather than evidence of absence.

## Discovery evidence

| Field | Meaning |
|:--|:--|
| `catalogs` | Project Radar catalogs containing the repository |
| `provenance` | Discovery sources and query identifiers |
| `evidence` | Supporting topic, seed, or enrichment evidence |
| `query_modes` | Active, new, custom, or seed discovery modes |
| `matched_topics` | Configured topics that surfaced the repository |
| `source_confidence` | Confidence assigned to the discovery source type, not to the project's quality |

## Growth and measurement

| Field | Meaning |
|:--|:--|
| `delta_1d` | Star change from the best available baseline at or before the one-day target |
| `delta_7d` | Star change from the best available baseline at or before the seven-day target |
| `delta_30d` | Star change from the best available baseline at or before the thirty-day target |
| `fork_delta_7d` | Seven-day fork change when measurable |
| `watcher_delta_7d` | Seven-day watcher change when measurable |
| `stars_per_day` | Raw observed or provisional velocity |
| `effective_stars_per_day` | Raw velocity multiplied by measurement confidence |
| `acceleration` | Current velocity minus the prior comparable velocity when enough history exists |
| `relative_7d` | Seven-day star change divided by the prior star count |
| `signal_source` | Observed-history or lifetime-estimate source class |
| `velocity_kind` | Lifetime estimate, observed short window, or observed seven-day window |
| `measurement_confidence` | Value from zero to one controlling the ranking influence of growth evidence |
| `provisional` | Whether recent growth remains an estimate |
| `history_observations` | Number of prior observation dates |
| `observed_span_days` | Span from first prior observation to current date |
| `first_seen` | Earliest date the repository appeared in retained Project Radar history |

A missing delta is `null`, not zero.

## Dimensions

The top-level `dimensions` object contains repository-oriented evidence, including:

- `quality`;
- `confidence`;
- `community_health`;
- `measurement_confidence`;
- `maintenance`;
- `newness`.

These values are generally represented on a 0–100 scale.

## Catalog scores

`catalog_scores` is keyed by catalog ID because percentiles and relevance are catalog-local. Each catalog can contain:

- `popular`;
- `momentum`;
- `rising`;
- `quality`;
- `novelty`;
- `under_recognition`;
- `interesting`;
- `overall`;
- `hidden_gem`;
- `relevance`;
- `measurement_confidence`.

A score from one catalog should not be compared as an absolute measurement against another catalog without considering each catalog's population.

## Review fields

| Field | Meaning |
|:--|:--|
| `review_flags` | Evidence-based quality-control prompts attached during report generation |

Review flags are not allegations, security verdicts, or claims about maintainer intent.

## Publication-level fields

| Field | Meaning |
|:--|:--|
| `schema_version` | Publication schema version |
| `generated_at` | UTC generation timestamp |
| `count` | Number of projects in the normalized publication |
| `history_mode` | Whether any observed history exists in the publication |
| `catalogs` | Catalog definitions and counts |
| `leaderboards` | Stable project IDs for each catalog leaderboard |
| `source_health` | Query and enrichment receipts |
| `reports` | Paths to audit, change, review, and manifest artifacts |

## Related artifacts

- `status.json` — compact run receipt;
- `audit.json` — coverage and measurement audit;
- `changes.json` — previous-publication comparison;
- `review-queue.json` — manual-review candidates;
- `manifest.json` — generated-file SHA-256 checksums;
- `<catalog>.json` — compact per-catalog index;
- `<catalog>.atom` — subscription feed;
- `<catalog>.md` — human-readable leaderboards.
