# Project Radar v2 release notes

Project Radar v2 upgrades the repository-level discovery system from a useful daily directory into an auditable monitoring product.

## What changed

### Confidence-calibrated momentum

Lifetime stars divided by repository age remains available as a provisional discovery estimate, but it is no longer treated as measured recent velocity. Every project now records:

- `velocity_kind`;
- `measurement_confidence`;
- `provisional` status;
- raw and confidence-adjusted stars per day;
- one-, seven-, and thirty-day deltas when observed;
- relative growth and week-over-week acceleration when enough history exists.

Momentum, acceleration, and relative-growth contributions are multiplied by measurement confidence before entering public rankings.

### Official GitHub community-health evidence

A bounded, catalog-balanced enrichment layer reads GitHub's official community-profile endpoint and records:

- community-health percentage;
- README presence;
- code of conduct;
- contributing guide;
- issue template;
- pull-request template;
- security policy;
- whether the repository was actually sampled.

Unsampled repositories are treated as unknown rather than low quality.

### New discovery dimensions

Every catalog now publishes separate deterministic scores and leaderboards for:

- novelty;
- under-recognition;
- hidden-gem potential;
- quality;
- popularity;
- momentum;
- rising/new-project strength;
- overall interest.

Novelty combines project age with catalog-local topic, language, and project-type rarity. Under-recognition combines quality, relevance, novelty, inverse popularity, and confidence-weighted momentum.

### Monitoring and audit outputs

Each production publication now includes:

- `changes.json` and `changes.md`;
- `audit.json`;
- `review-queue.json` and `review-queue.md`;
- one Atom feed per catalog;
- `manifest.json` with SHA-256 checksums and byte sizes;
- a searchable interface with measured/provisional evidence filters.

The review queue contains evidence-based prompts for human checking. A flag is not an allegation that a project is unsafe, fraudulent, manipulated, or defective.

### Broader catalog portfolio

Project Radar now publishes one cross-domain aggregate and sixteen native technical catalogs:

1. AI Agents
2. AI Engineering
3. Developer Tools
4. Data Engineering
5. Cybersecurity
6. Robotics and Embodied AI
7. Geospatial and Mapping
8. Creative Computing
9. Self-Hosted and Local-First
10. Scientific Computing
11. Database Systems
12. Bioinformatics and Computational Biology
13. Civic Technology
14. Accessibility and Assistive Technology
15. Game Development
16. Open-Source Business Software

### Stronger reproducibility and CI

The production workflow now validates:

- publication schema 2;
- exact catalog set and minimum counts;
- stable unique IDs and repository names;
- report consistency;
- Atom XML validity;
- audit and review-queue counts;
- SHA-256 manifest integrity;
- Python 3.10, 3.11, and 3.12 compatibility.

GitHub Actions dependencies are pinned to immutable commit revisions.

## Compatibility

Path-derived project IDs remain stable for existing consumers. Numeric GitHub repository IDs and node IDs are also retained so a future alias layer can reconcile repository transfers and renames without breaking historical identity.

## Remaining boundaries

Project Radar does not execute or dynamically analyze discovered code. Community-profile evidence is sampled under a bounded API budget rather than collected for every repository. Package-download adoption, dependency counts, release downloads, OpenSSF/security signals, event-native GitHub momentum, semantic project profiles, static project pages, alerts, and analytical database exports are reserved for the v3 roadmap.
