# Project Radar ranking scorecard

This scorecard makes the production ranking contract inspectable. Exact weights live in `github_radar/project_scoring.py`; this document explains the intent and evidence boundaries.

## Popularity

Purpose: reflect established adoption without letting very large repositories dominate every list.

Inputs:

- log-scaled stars;
- log-scaled forks;
- log-scaled watchers;
- small freshness, quality, and confidence contributions.

Popularity does not imply current momentum, code quality, safety, or domain relevance.

## Momentum

Purpose: identify repositories gaining attention now.

Inputs:

- observed or provisional velocity;
- acceleration;
- relative growth;
- freshness;
- quality and metadata confidence;
- a limited popularity contribution.

Critical constraint: velocity, acceleration, and relative-growth inputs are multiplied by `measurement_confidence`. A lifetime estimate with 15% confidence contributes only 15% of its percentile signal.

## Rising / up and coming

Purpose: surface younger or smaller projects with credible recent progress.

Inputs:

- confidence-weighted momentum;
- newness;
- novelty;
- relevance;
- quality;
- limited popularity.

Public up-and-coming boards also apply age and total-star ceilings.

## Quality

Purpose: estimate repository maturity and stewardship from public evidence.

Inputs:

- description quality;
- declared license;
- topics and homepage;
- maintenance recency;
- forks, watchers, and repository substance;
- multiple discovery paths;
- GitHub community-health percentage;
- README, code of conduct, contributing guide, templates, and security policy when officially sampled;
- source and metadata confidence.

Quality is not a code audit, security verdict, legal opinion, or guarantee of maintenance.

## Novelty

Purpose: surface genuinely different projects, not only newly created ones.

Inputs:

- repository age;
- topic rarity inside the catalog;
- project-type rarity;
- programming-language rarity;
- relevance, quality, and confidence.

## Under-recognition

Purpose: identify projects whose evidence appears stronger than their current popularity.

Inputs:

- quality;
- relevance;
- novelty;
- inverse catalog-local popularity;
- confidence-weighted momentum.

Under-recognition is a relative catalog score, not a claim about media attention, funding, or market value.

## Interesting

Purpose: provide a balanced editorial-style default without hiding its components.

Inputs:

- rising score;
- momentum;
- quality;
- novelty;
- under-recognition;
- popularity.

The normalized dataset exposes all component scores so users can substitute their own weights.

## Penalties and exclusions

Production ranking may penalize or exclude:

- archived or disabled repositories;
- forks and templates;
- long-stale projects;
- missing descriptions;
- incomplete repository metadata;
- resource lists, courses, or templates in catalogs configured for runnable projects.

These rules are deterministic and catalog-configurable.

## Diversity controls

Native catalogs enforce a configurable maximum number of projects per repository owner.

The cross-domain aggregate additionally reserves best-effort representation across native domains and caps quota-assigned positions from any single domain. After selection, entries are re-sorted by their true aggregate score.

## Evaluation requirements for future changes

Before replacing production weights, a proposed ranking change should include:

- affected dimensions and exact formula change;
- examples of expected winners and losers;
- first-snapshot and mature-history behavior;
- sensitivity to project size and age;
- sensitivity to missing community-profile evidence;
- catalog contamination checks;
- owner and domain diversity effects;
- an offline regression fixture;
- a shadow-ranking comparison against the current release.
