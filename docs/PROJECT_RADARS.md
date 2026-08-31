# GitHub Project Radars

Project Radar turns `github-radar` into a reusable publication engine for high-quality GitHub discovery across many technical domains. It is not another all-time-star list. It measures popularity, velocity, acceleration, relative growth, freshness, maintenance, metadata quality, catalog relevance, confidence, and newness separately, then publishes several transparent leaderboards for each topic.

The implementation is deliberately centralized:

- `scripts/project_radar.py` is the stable command-line entry point.
- `github_radar/project_common.py`, `project_discovery.py`, `project_history.py`, `project_scoring.py`, `project_rendering.py`, and `project_runner.py` contain the reusable models, collection, measurement, ranking, publication, and orchestration layers.
- `project_radars.json` defines the products, topics, thresholds, exclusions, and API budget.
- `.github/workflows/project-radars-daily.yml` runs the offline suite, performs the live collection, validates the publication bundle, and commits only changed output on `main`.
- `feeds/projects/` contains Markdown, JSON, history, and a machine-readable run receipt.
- `docs/projects/` contains the searchable static interface and normalized dataset.

No domain requires a copied scraper. A new radar is normally one additional configuration object plus, when topic metadata is insufficient, a bounded custom GitHub search query.

## Initial catalogs

| Catalog | Focus |
|:--|:--|
| Interesting GitHub Projects | Cross-domain aggregate of projects that combine novelty, momentum, quality, relevance, and under-recognition |
| AI Agents | Agent runtimes, coding agents, multi-agent systems, tool use, computer use, and orchestration |
| AI Engineering | RAG, inference, evaluation, observability, model serving, LLM operations, and production ML tooling |
| Developer Tools | Editors, terminals, CLIs, debuggers, API clients, testing, build systems, and developer experience |
| Data Engineering | Pipelines, ETL/ELT, orchestration, streaming, warehouses, lakehouses, and data quality |
| Cybersecurity Tools | Defensive security, AppSec, vulnerability discovery, reverse engineering, privacy, and automation |
| Robotics and Embodied AI | Robotics frameworks, ROS, simulation, autonomy, drones, control, sensing, and embodied intelligence |
| Geospatial and Mapping | GIS, routing, spatial databases, Earth observation, mapping, analytics, and digital twins |
| Creative Computing | Graphics, animation, video, audio, creative coding, generative art, design tools, and 3D |
| Self-Hosted and Local-First | Self-hosted applications, homelabs, local-first software, privacy, personal clouds, and independent automation |

The first portfolio is intentionally broad enough to prove the engine but focused enough to remain editorially coherent. Additional candidates include scientific computing, databases, cloud-native infrastructure, bioinformatics, civic technology, accessibility, game development, and open-source business infrastructure.

## Daily collection sequence

1. Build a fair query schedule. Every native catalog receives an active-project query and a new-project query before secondary topics compete for the remaining request budget.
2. Run bounded GitHub repository searches. The collector automatically adds `archived:false` and `fork:false` unless a query explicitly states otherwise.
3. Merge duplicate repositories case-insensitively while preserving every catalog membership, matched topic, discovery path, and source-health receipt.
4. Allocate detailed repository enrichment round-robin across catalogs so the largest ecosystem cannot consume the metadata budget.
5. Apply the explicit repository blocklist and add the aggregate catalog membership.
6. Compare the current star, fork, watcher, and activity state with the rolling 90-day history.
7. Calculate scores independently inside each catalog. This prevents a healthy geospatial or robotics project from being buried merely because those ecosystems have fewer absolute stars than AI or JavaScript.
8. Build owner-diverse leaderboards, validate counts and source health, enforce the shrink guard, and atomically write the bundle.
9. Commit generated files only on `main` and only when content changed. Feature branches run the same tests and live validation without publishing over production.

## Leaderboards

Every catalog publishes:

- **Most Interesting** — a balanced blend of rising, momentum, quality, relevance, newness, and popularity.
- **High Momentum** — observed or provisional velocity, acceleration, relative growth, and freshness.
- **Up and Coming** — momentum with age and popularity ceilings so emerging projects can surface.
- **High Quality** — maintenance, metadata completeness, adoption, repository substance, confidence, and relevance.
- **Hidden Gems** — high-quality, relevant projects with strong rising signals and comparatively low popularity.
- **Most Popular** — adoption-led ranking that still includes freshness, quality, and confidence.
- **New Projects** — repositories inside the configured new-project window, ranked by rising score.
- **Latest One-Day Movers** — appears after measured daily history is available.

The aggregate cross-domain catalog adds a second diversity layer after scoring. Its 25-position boards reserve two best-effort selections for each native domain and assign no more than four positions to any one domain. Projects keep all of their true catalog memberships; the assignment is used only for quota accounting. Results are then re-sorted by their aggregate score, so diversity does not disguise the ranking order.

Resource lists, courses, and templates remain searchable in the full dataset when discovered, but the initial catalogs exclude them from project leaderboards. Archived, disabled, forked, stale, empty-description, and template repositories receive explicit exclusions or penalties rather than silently blending into the main rankings.

## Measurement behavior

Momentum belongs to a repository. Project Radar stores one snapshot per repository per day and derives:

- one-, seven-, and thirty-day star changes;
- seven-day fork and watcher changes;
- observed stars per day;
- week-over-week acceleration;
- relative seven-day growth;
- first-seen date in this radar.

On the first snapshot, no historical change exists. `delta_1d`, `delta_7d`, and `delta_30d` remain `null`; they are not fabricated as zero. The provisional velocity is clearly labeled `lifetime-estimate`. After enough daily runs, observed history automatically replaces that estimate.

## Quality is not a single opaque label

The system keeps raw evidence and separate dimensions visible:

- **Popularity:** log-scaled stars, forks, and watchers.
- **Momentum:** measured star velocity, acceleration, relative growth, and current freshness.
- **Maintenance:** recent pushes and repository updates with time decay.
- **Metadata quality:** description, license, topics, homepage, community features, adoption, repository substance, and corroboration.
- **Catalog relevance:** matched search topics, repository topics, configured keywords, negative terms, and multiple discovery paths.
- **Confidence:** API completeness, metadata completeness, source confidence, and corroboration.
- **Newness:** project age with exponential decay.

The blended public scores are deterministic and inspectable. A future semantic or LLM review layer should be additive: it may propose use cases, categories, novelty explanations, or manual-review candidates, but it must not overwrite measured repository facts.

## Reliability gates

A production run is rejected before publication when:

- no projects were collected;
- stable IDs or repository names are duplicated;
- the total count is below the configured minimum;
- the total collection shrinks below the guarded ratio of the previous healthy publication;
- an individual catalog shrinks below its own previous-publication guard;
- any native catalog lacks a successful discovery query;
- any catalog falls below its configured minimum count;
- generated JSON counts, expected catalogs, or required files fail workflow validation.

Individual source failures are retained in `source_health` and do not erase healthy results. The status receipt reports successful and failed sources and marks degraded runs.

## Safety and anti-gaming

The collector reads public metadata only. It never clones, installs, imports, builds, runs, or evaluates code from discovered repositories. Tokens are read from the environment and are never serialized.

Community nominations are accepted as leads through the issue form. They do not receive an automatic score bonus. Affiliations must be disclosed, and a nomination cannot bypass catalog relevance, history, quality, diversity, or safety rules. This makes community participation useful without turning the directory into a paid-placement or spam list.

## Adding a catalog

Add a configuration object to `project_radars.json`:

```json
{
  "id": "scientific-computing",
  "title": "Scientific Computing Radar",
  "description": "Numerical, simulation, research-computing, and reproducible-science projects.",
  "topics": ["scientific-computing", "numerical-analysis", "simulation", "reproducible-research"],
  "keywords": ["simulation", "numerical", "scientific", "research"],
  "negative_terms": ["course", "interview"],
  "min_stars": 10,
  "new_min_stars": 3,
  "minimum_items": 15,
  "source_confidence": 0.6,
  "excluded_project_types": ["resource-list", "education", "template"]
}
```

Use custom queries only when topic metadata does not cover the domain. Custom queries support `{active_since}`, `{new_since}`, `{min_stars}`, and `{new_min_stars}` placeholders and still receive safety qualifiers.

Run locally:

```bash
python scripts/project_radar.py --config project_radars.json
```

For a deterministic test date and isolated output:

```bash
python scripts/project_radar.py \
  --config project_radars.json \
  --now 2026-08-31T15:36:00Z \
  --output-dir /tmp/project-radar-feeds \
  --site-dir /tmp/project-radar-site
```

## Publication and growth strategy

The central engine should remain the source of truth. Focused public repositories can later mirror generated catalog artifacts without copying collectors. The strongest initial standalone products are likely:

- `interesting-github-projects`
- `ai-agents-radar`
- `developer-tools-radar`
- `data-engineering-radar`

Each mirror should have a memorable name, daily freshness and item-count badges, a concise README leaderboard, a searchable Pages site, a nomination issue form, Atom or JSON feeds, and links back to the methodology. Daily mover changelogs, release notes, social cards, and weekly “projects to watch” digests can turn the dataset into repeatable distribution while the transparent methodology earns backlinks and trust.

Mirrors must remain transactional outputs of this engine. Four or forty separate scrapers would drift, duplicate API use, and make ranking changes impossible to audit consistently.
