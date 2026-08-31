# Project Radar architecture decisions

## ADR-001: One central collector, many generated products

**Decision:** Keep discovery, evidence, history, scoring, and validation in `github-radar`. Focused repositories and sites are generated mirrors.

**Reason:** Separate collectors would drift in query coverage, ranking behavior, safety rules, API use, and history.

## ADR-002: Catalog-local normalization

**Decision:** Normalize ranking signals inside each catalog.

**Reason:** Absolute stars and activity differ dramatically across AI, robotics, accessibility, civic technology, bioinformatics, and other ecosystems. Catalog-local percentiles improve relevance and reduce domination by the largest communities.

## ADR-003: Preserve raw evidence

**Decision:** Publish raw facts and component scores alongside blends.

**Reason:** Consumers need to reproduce, audit, or replace rankings. A single opaque score is insufficient.

## ADR-004: Treat missing evidence as unknown

**Decision:** Missing history, community profiles, registry statistics, or optional enrichment is not interpreted as zero or failure.

**Reason:** Optional API budgets and source availability should not systematically punish smaller projects.

## ADR-005: Confidence-weight provisional momentum

**Decision:** Keep age-adjusted lifetime velocity for discovery but multiply its ranking contribution by measurement confidence.

**Reason:** Lifetime stars divided by age is not measured recent growth. It should not outrank repositories with real observed momentum evidence merely because a repository is very new.

## ADR-006: Never execute discovered code

**Decision:** Restrict discovery and enrichment to public metadata, manifests, registries, and external verdicts.

**Reason:** Execution would create unacceptable security, privacy, reproducibility, and cost risks for a broad public crawler.

## ADR-007: Review flags are prompts, not verdicts

**Decision:** Publish a manual-review queue with neutral evidence language.

**Reason:** An unusual metadata pattern may have many legitimate explanations. Automated systems should request verification rather than imply wrongdoing.

## ADR-008: Keep stable path IDs while retaining numeric identity

**Decision:** Preserve existing `repo:owner/name` IDs in publication schema 2 and add GitHub repository ID and node ID.

**Reason:** Existing consumers retain compatibility while future rename and transfer reconciliation gains a stable identity anchor.

## ADR-009: Validate the whole publication bundle

**Decision:** Validate JSON, counts, catalog set, Atom XML, audit consistency, review counts, required artifacts, and SHA-256 checksums before commit.

**Reason:** A partial or internally inconsistent publication is worse than retaining the last known-good snapshot.

## ADR-010: Separate ranking from distribution and monetization

**Decision:** Sponsorship, nomination, promotion, or commercial relationships cannot automatically affect ranking.

**Reason:** The value of Project Radar depends on evidence-backed discovery and transparent methodology.
