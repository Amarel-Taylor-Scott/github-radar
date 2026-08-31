# GitHub Project Radar methodology

Project Radar is the repository-level discovery and publication engine inside `github-radar`. It answers a harder question than “what has the most stars?”:

> Which open-source projects are becoming important, remain unusually well maintained, solve distinctive problems, or deserve more attention inside a particular technical domain?

The engine is read-only, configuration-driven, and designed to publish trustworthy daily datasets rather than a manually edited “awesome list.” It never clones, imports, installs, builds, or executes discovered repositories.

## Production architecture

The implementation is centralized:

- `scripts/project_radar.py` is the stable command-line entry point.
- `github_radar/project_common.py` defines stable records, identifiers, normalization, classification, and atomic writes.
- `github_radar/project_discovery.py` builds a fair query schedule, performs bounded GitHub discovery, deduplicates records, and allocates enrichment across domains.
- `github_radar/project_history.py` stores observations and derives measured growth with explicit confidence.
- `github_radar/project_scoring.py` calculates catalog-local dimensions, review flags, and owner/domain-diverse leaderboards.
- `github_radar/project_rendering.py` creates Markdown, compact catalog indexes, the normalized dataset, the run receipt, and the searchable static application.
- `github_radar/project_reports.py` creates run-to-run changes, the evidence audit, review queue, Atom feed, badge endpoints, and a SHA-256 publication manifest.
- `github_radar/project_runner.py` coordinates validation, collection, scoring, publication, and failure guards.
- `project_radars.json` defines domains, topics, thresholds, budgets, exclusions, and diversity rules.
- `.github/workflows/project-radars-daily.yml` runs the offline suite, live collector, integrity checks, and commit-on-change publisher.

A new domain normally requires one configuration object. It does not require a copied crawler or independent scoring implementation.

## Current catalogs

| Catalog | Scope |
|:--|:--|
| Interesting GitHub Projects | Cross-domain shortlist balancing novelty, quality, confidence-aware momentum, relevance, and under-recognition |
| AI Agents | Coding agents, multi-agent systems, tool use, computer use, orchestration, and agent infrastructure |
| AI Engineering | RAG, inference, evaluation, observability, model serving, vector systems, and production ML |
| Developer Tools | Editors, terminals, CLIs, debuggers, testing, build systems, API clients, and developer experience |
| Data Engineering | ETL/ELT, pipelines, orchestration, streaming, warehouses, lakehouses, and data quality |
| Cybersecurity Tools | Defensive security, AppSec, vulnerability discovery, reverse engineering, privacy, and automation |
| Robotics and Embodied AI | ROS, simulation, autonomy, drones, control, sensing, robot learning, and physical AI |
| Geospatial and Mapping | GIS, routing, spatial databases, Earth observation, mapping, and digital twins |
| Creative Computing | Graphics, animation, video, audio, creative coding, design tooling, and 3D engines |
| Self-Hosted and Local-First | Personal clouds, local-first software, homelabs, privacy tools, and independent automation |
| Scientific Computing | Numerical computing, simulation, solvers, reproducible research, and scientific ML |
| Databases and Storage | SQL, NoSQL, distributed databases, vector databases, storage engines, search, and caches |
| Cloud-Native Infrastructure | Kubernetes, containers, service meshes, observability, platform engineering, and deployment |
| Bioinformatics and Computational Biology | Genomics, sequence analysis, single-cell systems, biomedical data, and research tooling |
| Civic Technology | Open government, public-interest technology, public data, participation, and mobility standards |
| Accessibility and Assistive Technology | Accessibility testing, inclusive interfaces, screen readers, captions, speech, and adaptive software |
| Game Development | Game engines, rendering, simulation, procedural generation, networking, and asset pipelines |
| Business Automation | Workflow automation, low-code systems, internal tools, integrations, and process orchestration |

## Daily collection sequence

1. Build a fair query schedule. Every native catalog receives one active-project query and one new-project query before secondary topics consume the remaining Search API budget.
2. Add `archived:false` and `fork:false` safety qualifiers unless a query explicitly specifies them.
3. Pace Search API calls below the configured request rate and isolate failures by query.
4. Normalize and merge repositories case-insensitively while retaining every matched catalog, topic, query mode, source, and evidence record.
5. Allocate detailed repository enrichment round-robin across catalogs so large ecosystems cannot consume the budget.
6. Allocate GitHub Community Metrics enrichment using the same balanced policy.
7. Apply the explicit blocklist and aggregate-catalog membership.
8. Compare current stars, forks, watchers, and activity with the rolling observation history.
9. Calculate dimensions independently inside every catalog.
10. Build owner-diverse leaderboards. The aggregate catalog also applies cross-domain quotas.
11. Validate uniqueness, source coverage, minimum sizes, and total plus per-catalog shrink guards.
12. Atomically write the publication bundle.
13. Generate change, audit, review, subscription, badge, and integrity artifacts.
14. Re-read and SHA-256-verify every file listed in the publication manifest inside GitHub Actions.
15. Commit only when the workflow is running on `main` and generated files changed.

A failed optional enrichment is visible in `status.json` and `audit.json`; it does not erase healthy discovery results. A collapsed discovery run is rejected before it can replace the last healthy feed.

## Evidence-confidence model

Repository age-adjusted lifetime velocity is useful for finding candidates, but it is not a measured seven-day growth rate. Publication schema v2 makes that distinction explicit.

| Evidence state | Meaning | Default confidence |
|:--|:--|--:|
| `provisional-lifetime` | Stars divided by repository age; no prior observation from this radar | 0.25 |
| `measured-short-window` | At least one prior daily observation, but fewer than seven days of coverage | Increases with observations and elapsed time, capped below 1.0 |
| `measured-7d` | A usable seven-day baseline exists | 1.0 |

Velocity, acceleration, and relative-growth contributions are multiplied by their evidence confidence after catalog normalization. This matters especially during the first week: if every project is provisional, a common multiplier applied before percentile ranking would not change anything. Applying confidence to the final signal contribution prevents estimated momentum from receiving the same weight as measured history.

Missing one-, seven-, or thirty-day deltas remain `null`. They are never converted to zero. Zero means an observed lack of change; `null` means the measurement does not yet exist.

## Ranking dimensions

Project Radar keeps raw evidence and component scores visible rather than publishing one unexplained number.

### Popularity

Log-scaled stars, forks, and watchers. Log scaling prevents the largest repositories from automatically occupying every position.

### Momentum

Confidence-weighted velocity, acceleration, relative growth, freshness, quality, and adoption. Seven-day observations receive full weight; lifetime estimates receive limited weight.

### Newness

Exponential decay from repository creation. Newness is useful for emerging-project boards but does not independently imply quality.

### Maintenance

Time-decayed last-push and repository-update activity.

### Metadata quality

Description depth, license declaration, topics, homepage, community features, maintenance, adoption, repository substance, and independent discovery paths.

### Official GitHub community health

A bounded subset of candidates is enriched from GitHub’s Community Metrics endpoint. The evidence includes GitHub’s health percentage and detected README, contributing guide, code of conduct, issue template, pull-request template, documentation, and license files.

Community health measures repository stewardship evidence. It is not a security audit and does not prove that code is safe.

### Adoption depth

Fork-to-star depth, watcher depth, and absolute forks. This helps distinguish repositories that attract repeat use and contribution from projects with shallow awareness signals.

### Relevance

Matched GitHub topics, configured keywords, negative terms, discovery paths, and catalog memberships. Scores are normalized inside each catalog so smaller technical communities are not judged on the star scale of the largest AI and JavaScript ecosystems.

### Descriptive novelty

A deterministic inverse-document-frequency calculation over repository names, descriptions, and topics. It rewards distinctive problem descriptions without allowing long descriptions to win merely through word count.

Novelty is descriptive evidence, not a claim of patentable or scientific novelty.

### Under-recognition

A combination of quality, novelty, and comparatively low popularity. Hidden-gem boards also impose an absolute star ceiling.

### Confidence

API completeness, metadata completeness, source confidence, corroboration, community-profile evidence, and momentum measurement confidence.

## Published leaderboards

Each catalog produces:

- **Most Interesting** — balanced novelty, quality, momentum, relevance, newness, under-recognition, and adoption.
- **High Momentum** — confidence-weighted growth and freshness.
- **Up and Coming** — rising score with project-age and popularity ceilings.
- **High Quality** — stewardship, maintenance, adoption, relevance, and evidence completeness.
- **Hidden Gems** — quality and novelty among comparatively under-recognized projects.
- **Most Popular** — adoption-led ranking that still accounts for freshness and quality.
- **New Projects** — repositories inside the configured creation window.
- **Latest One-Day Movers** — appears only when a prior daily observation exists.

### Aggregate diversity

A cross-domain board can be numerically correct while still being unhelpful if one fast-moving ecosystem occupies every position. Aggregate boards therefore reserve best-effort representation for native domains and cap quota assignments per domain. Repositories retain all real catalog memberships; the temporary assignment is used only for quota accounting. The selected set is re-sorted by its real aggregate score before publication.

Owner diversity is enforced separately, preventing one organization or monorepo family from overwhelming a leaderboard.

## Evidence review queue

`review-queue.json` and `review-queue.md` identify high-attention records whose evidence deserves inspection. Flags include:

- unusually strong provisional lifetime velocity;
- a very recent breakout;
- missing license evidence on a high-attention repository;
- unavailable Community Metrics on a high-attention repository;
- only one discovery path for a high-attention repository;
- a thin description;
- unusually low fork depth for a large repository.

These are triage signals. They are not findings of manipulation, insecurity, fraud, or misconduct.

## Evidence audit

`audit.json` and `audit.md` report, for each catalog:

- total records;
- leaderboard-eligible records;
- observed-history and full seven-day coverage;
- official Community Metrics coverage;
- detected-license coverage;
- descriptive-record coverage;
- 30-day activity coverage;
- review-flag share;
- median quality score.

This allows collection gaps to be measured instead of hidden.

## Change feed

`changes.json` and `changes.md` compare the current normalized publication with the previous one. They include:

- newly discovered repositories;
- repositories no longer discovered in the bounded search surface;
- star-count changes between publication runs;
- new leaderboard entries and exits;
- rank movement for comparable projects.

“Removed” means absent from the current bounded discovery result. It does not necessarily mean the upstream repository was deleted.

## Machine-readable and subscription outputs

The publication bundle includes:

- complete normalized JSON;
- compact per-catalog JSON indexes;
- Markdown leaderboards;
- rolling history;
- `status.json` run receipt;
- searchable static HTML;
- Atom feed;
- change feed;
- evidence audit;
- review queue;
- Shields-compatible JSON badge endpoints;
- SHA-256 publication manifest.

The manifest records the source commit, generation timestamp, byte size, and checksum of every feed and site artifact. GitHub Actions verifies the manifest before publishing.

## Reliability gates

A production run is rejected when:

- collection is empty;
- stable IDs or normalized repository names are duplicated;
- the total is below the configured minimum;
- the total falls below the previous-publication ratio;
- an individual catalog falls below its own previous-publication ratio;
- a native catalog has no successful discovery query;
- a catalog falls below its configured minimum;
- expected catalog files are missing;
- publication schemas disagree;
- an Atom document is malformed;
- a publication-manifest size or SHA-256 check fails.

Feature branches run the same live collection and validation but cannot commit production outputs. Concurrent stale runs are canceled.

## Safety and anti-gaming

- Discovery and enrichment are read-only.
- Discovered code is never cloned, installed, imported, built, or executed.
- Authentication tokens are read from the environment and never serialized.
- Community nominations are leads, not ranking bonuses.
- Affiliations must be disclosed.
- Paid placement cannot bypass scoring or quality rules.
- Exact queries, provenance, evidence state, component scores, and review flags remain machine-readable.
- Third-party GitHub Actions are pinned to full commit SHAs.

The radar does not currently claim to detect malicious code. Future security enrichment should remain a separate dimension and may incorporate OpenSSF Scorecard, GitHub advisories, dependency metadata, signed releases, or other evidence without conflating security with popularity.

## Adding a catalog

Add a catalog object to `project_radars.json`:

```json
{
  "id": "energy-systems",
  "title": "Energy Systems Radar",
  "description": "Grid modeling, power systems, storage, forecasting, and energy analytics.",
  "topics": ["energy", "power-systems", "smart-grid", "energy-storage"],
  "keywords": ["grid", "power system", "energy storage", "forecasting"],
  "negative_terms": ["course", "interview", "awesome list"],
  "min_stars": 5,
  "new_min_stars": 2,
  "minimum_items": 8,
  "source_confidence": 0.6,
  "excluded_project_types": ["resource-list", "education", "template"]
}
```

Custom queries can use `{active_since}`, `{new_since}`, `{min_stars}`, and `{new_min_stars}`. Safety qualifiers are still applied automatically.

Run locally:

```bash
python scripts/project_radar.py --config project_radars.json
```

After editable installation:

```bash
project-radar --config project_radars.json
```

For an isolated deterministic run:

```bash
python scripts/project_radar.py \
  --config project_radars.json \
  --now 2026-08-31T17:00:00Z \
  --output-dir /tmp/project-radar-feeds \
  --site-dir /tmp/project-radar-site
```

## Distribution model

`github-radar` remains the source of truth. Focused standalone repositories should be thin transactional mirrors containing generated README, JSON, status, subscription, and site artifacts. They should not contain independent collectors.

The initial mirror plan is tracked in Issue #5 for:

- `interesting-github-projects`
- `ai-agents-radar`
- `developer-tools-radar`
- `data-engineering-radar`

Repository creation and GitHub Pages administration remain separate administrative operations because the connected integration cannot perform them directly.
