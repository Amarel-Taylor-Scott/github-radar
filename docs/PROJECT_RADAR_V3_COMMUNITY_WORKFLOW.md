# Project Radar v3 community evidence workflow

Project Radar v3 accepts community input as reviewable evidence—not as an automatic ranking bonus.

## Source proposals

Use `.github/ISSUE_TEMPLATE/project-radar-v3-source.yml` to propose a package registry, release source, security provider, event stream, or adoption dataset. A source must identify its authoritative upstream, endpoint, terms, request budget, caching design, evidence contract, missing-data behavior, and anti-gaming risks.

A proposed source remains disabled until it has:

- a bounded adapter;
- source-health receipts;
- offline fixtures;
- graceful-degradation tests;
- explicit evidence class, entity level, unit, time window, freshness, and stable identifier;
- confirmation that GitHub credentials are not leaked to third-party hosts;
- shadow evaluation showing that missing coverage does not become a penalty.

## Ranking labels

Use `.github/ISSUE_TEMPLATE/project-radar-v3-benchmark.yml` to propose evidence-backed labels for domain relevance, practical usefulness, stewardship quality, descriptive novelty, new-project recall, or catalog contamination.

Submitted labels are not inserted automatically. A reviewer verifies the repository, catalog, evidence, affiliation disclosure, and rating rationale before adding the label to the versioned benchmark corpus.

## Independence from placement

Nominations, source proposals, benchmark labels, sponsorship, and maintainer affiliation do not produce an automatic score advantage. The v2 production rankings remain unchanged by the additive v3 evidence layer until a deterministic shadow formula passes the documented ranking gates.
