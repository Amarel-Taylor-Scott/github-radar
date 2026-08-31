# Project Radar v3 roadmap

Project Radar v2 establishes trustworthy daily measurement, catalog-local scoring, official GitHub community-health evidence, change tracking, audit output, review queues, subscriptions, and reproducible checksums.

The next layer should turn the dataset into a durable open-source intelligence and discovery product without weakening its evidence model.

## 1. Adoption evidence beyond stars

Add bounded, source-specific adapters for:

- package downloads from PyPI, npm, crates.io, RubyGems, Maven Central, NuGet, and Packagist;
- GitHub release cadence and release-asset downloads;
- dependent repositories and package dependents where official data is available;
- container pulls from supported registries;
- documentation traffic or installation counts only when published by an authoritative registry;
- contributor count, contributor concentration, issue responsiveness, and pull-request throughput;
- OpenSSF Scorecard, security advisories, signed releases, provenance attestations, and SBOM availability.

Popularity, adoption, maintenance, governance, security, and momentum must remain separate dimensions.

## 2. Event-native momentum

Daily snapshots are sufficient for reliable one-, seven-, and thirty-day changes. Event-native sources could add finer resolution:

- GH Archive `WatchEvent` counts;
- repository release events;
- package-version publications;
- issue and pull-request activity changes;
- sudden deletion, archival, transfer, or rename events.

Event sources must be cached, bounded, and reconciled against official current repository metadata.

## 3. Evidence-grounded editorial profiles

Generate optional project profiles containing:

- what the project does;
- the problem it solves;
- likely users;
- practical use cases;
- notable integrations;
- deployment model;
- plausible business or product opportunities;
- limitations and alternatives;
- why the project surfaced now.

Every factual statement must retain source provenance. Model-generated interpretation must be labeled separately and may never overwrite repository facts, measured history, license data, registry statistics, or security evidence.

## 4. Search and knowledge graph

Publish a queryable entity graph connecting:

- repositories;
- maintainers and organizations;
- packages;
- releases;
- dependencies;
- agent extensions;
- research papers;
- companies and commercial products;
- topics and use cases;
- forks, transfers, renames, and successor projects.

Support hybrid lexical, faceted, vector, and graph search while keeping a small static JSON experience available without infrastructure.

## 5. Static SEO and shareability

Generate indexable static pages rather than relying only on a client-side directory:

- one page per catalog;
- one evidence card per project;
- canonical URLs;
- sitemap and robots files;
- JSON-LD structured data;
- Open Graph and social-card metadata;
- Atom, RSS, and JSON Feed discovery tags;
- permanent daily and weekly snapshots;
- “projects to watch” and “new this week” landing pages.

The central engine remains authoritative; standalone repositories and sites remain generated mirrors.

## 6. Alerts and personalization

Allow users to subscribe to:

- catalogs;
- topics;
- languages;
- score thresholds;
- specific repositories;
- new-project alerts;
- high-confidence momentum changes;
- archival, transfer, or security events.

Default public products should remain useful without accounts or tracking.

## 7. Ranking evaluation and anti-gaming

Create a labeled evaluation corpus and recurring benchmark for:

- relevance;
- novelty;
- practical usefulness;
- project quality;
- ranking stability;
- new-project recall;
- false-positive rate;
- catalog contamination;
- sensitivity to star anomalies;
- owner and domain diversity.

Add shadow rankings, ablation reports, score-distribution drift checks, and reviewer agreement. Sponsored or nominated projects must never receive an automatic ranking advantage.

## 8. Data products and API

Publish compact analytical formats:

- normalized JSON;
- JSON Feed;
- Parquet;
- SQLite snapshot;
- catalog diffs;
- stable entity and observation tables;
- a documented read-only API;
- optional webhooks.

Historical observations should move to partitioned artifacts or object storage before repository size becomes a maintenance problem.

## Acceptance criteria

- New signals have authoritative source attribution and source-health receipts.
- Every signal declares whether it is observed, estimated, inferred, or model-generated.
- Ranking dimensions remain independently inspectable.
- Offline fixtures cover every upstream schema.
- A failed enrichment source cannot prevent healthy base publication.
- No discovered repository code is executed.
- Static pages, feeds, API output, and mirror repositories agree on source snapshot and checksums.
- Ranking changes are evaluated against a labeled benchmark before replacing production weights.
