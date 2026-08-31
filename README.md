# github-radar

[![CI](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/ci.yml)
[![Daily feed](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/daily.yml/badge.svg)](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/daily.yml)
[![Agent extensions](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/agent-extensions-daily.yml/badge.svg)](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/agent-extensions-daily.yml)
[![Project radars](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/project-radars-daily.yml/badge.svg)](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/project-radars-daily.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Runtime dependencies: none](https://img.shields.io/badge/runtime%20dependencies-none-brightgreen)](pyproject.toml)

**Find tomorrow’s important open-source projects before all-time stars bury them.**

`github-radar` is a daily, read-only discovery and publication system for:

1. fast-moving GitHub repositories;
2. Claude, Codex, MCP, Gemini CLI, OpenCode, and cross-agent extensions;
3. high-quality, novel, emerging, and under-recognized projects across technical domains.

It publishes searchable Markdown, JSON, history, change feeds, audit receipts, Atom subscriptions, and static HTML. The collectors never execute discovered code.

## Start with the live catalogs

### GitHub projects

[All project catalogs](feeds/projects/README.md) · [Interesting projects](feeds/projects/interesting-projects.md) · [What changed](feeds/projects/changes.md) · [Evidence audit](feeds/projects/audit.md) · [Review queue](feeds/projects/review-queue.md) · [Atom feed](feeds/projects/projects.atom) · [Normalized JSON](feeds/projects/latest.json)

### Agent extensions

[Claude Skills](feeds/agent-extensions/claude-skills.md) · [Claude Tools](feeds/agent-extensions/claude-tools.md) · [Claude Plugins](feeds/agent-extensions/claude-plugins.md) · [All Agent Extensions](feeds/agent-extensions/agent-extensions.md) · [Normalized JSON](feeds/agent-extensions/latest.json)

### General GitHub feed

[Today’s momentum-aware feed](feeds/latest.md)

---

## Why this is different

Most “trending repositories” products either scrape one page or sort by total stars. Both approaches repeatedly surface the same large projects and make it difficult to discover smaller ecosystems.

`github-radar` instead combines bounded discovery, rolling observations, domain-local normalization, explicit evidence confidence, quality and maintenance signals, novelty, under-recognition, provenance, and diversity constraints.

The result is not one universal popularity score. It is a set of independently useful views:

- What is gaining measured momentum?
- What only appears fast because it is new?
- Which projects have strong stewardship evidence?
- Which projects describe distinctive technical work?
- Which smaller projects look unusually mature?
- What changed since the previous publication?
- Where is the radar’s evidence incomplete?

---

# Three production systems

## 1. General GitHub Radar

The original feed combines GitHub’s Search API with the public GitHub Trending page and optional external discovery sources. It deduplicates repositories and applies a simple, inspectable score:

```text
score = popularity
      + repository freshness
      + stars reported for the Trending period
      + Trending presence
      + cross-source corroboration
```

Run it:

```bash
python -m github_radar
python -m github_radar --top 20 --format json
python -m github_radar --out-dir output --format markdown,json,atom
```

The scheduled workflow publishes at **07:13 UTC**.

## 2. Agent Extension Radar

One collector publishes four products from shared discovery, history, ranking, and safety logic:

| Catalog | Scope |
|:--|:--|
| [Claude Skills](feeds/agent-extensions/claude-skills.md) | Standalone and packaged `SKILL.md` components |
| [Claude Tools](feeds/agent-extensions/claude-tools.md) | MCP servers and evidence-backed tool integrations |
| [Claude Plugins](feeds/agent-extensions/claude-plugins.md) | Official, reviewed-community, and manifest-backed plugins |
| [Agent Extensions](feeds/agent-extensions/agent-extensions.md) | Cross-agent skills, tools, plugins, agents, and frameworks |

The workflow publishes at **08:37 UTC**. It records exact artifact paths and provenance but never installs or executes discovered skills, hooks, scripts, plugins, or MCP servers.

See [the Agent Extension Radar methodology](docs/AGENT_EXTENSION_RADAR.md).

## 3. Multi-domain Project Radar

Publication schema v2 currently produces **18 catalogs** from one engine:

| Catalog | Focus |
|:--|:--|
| [Interesting GitHub Projects](feeds/projects/interesting-projects.md) | Cross-domain shortlist balancing novelty, quality, momentum confidence, and under-recognition |
| [AI Agents](feeds/projects/ai-agents.md) | Coding agents, multi-agent systems, tool use, and orchestration |
| [AI Engineering](feeds/projects/ai-engineering.md) | RAG, inference, evaluation, observability, and model serving |
| [Developer Tools](feeds/projects/developer-tools.md) | Editors, terminals, CLIs, debuggers, testing, and build tools |
| [Data Engineering](feeds/projects/data-engineering.md) | Pipelines, ETL/ELT, orchestration, streaming, and data quality |
| [Cybersecurity](feeds/projects/cybersecurity.md) | Defensive security, AppSec, vulnerability discovery, privacy, and automation |
| [Robotics and Embodied AI](feeds/projects/robotics.md) | ROS, simulation, autonomy, control, sensing, and physical AI |
| [Geospatial and Mapping](feeds/projects/geospatial.md) | GIS, routing, Earth observation, spatial databases, and digital twins |
| [Creative Computing](feeds/projects/creative-computing.md) | Graphics, animation, video, audio, design tooling, and 3D |
| [Self-Hosted and Local-First](feeds/projects/self-hosted.md) | Personal clouds, homelabs, privacy, and independent automation |
| [Scientific Computing](feeds/projects/scientific-computing.md) | Numerical computing, simulation, solvers, and reproducible research |
| [Databases and Storage](feeds/projects/databases.md) | SQL, NoSQL, distributed storage, vector databases, search, and caches |
| [Cloud-Native Infrastructure](feeds/projects/cloud-native.md) | Kubernetes, containers, platform engineering, deployment, and observability |
| [Bioinformatics](feeds/projects/bioinformatics.md) | Genomics, sequence analysis, single-cell systems, and biomedical tooling |
| [Civic Technology](feeds/projects/civic-tech.md) | Open government, public data, participation, and public-interest technology |
| [Accessibility](feeds/projects/accessibility.md) | Assistive technology, inclusive interfaces, captions, speech, and testing |
| [Game Development](feeds/projects/game-development.md) | Engines, rendering, procedural systems, networking, and asset pipelines |
| [Business Automation](feeds/projects/business-automation.md) | Workflow automation, low-code, integrations, internal tools, and operations |

The workflow publishes at **09:17 UTC**.

---

## Project Radar leaderboards

Every catalog publishes:

- **Most Interesting**
- **High Momentum**
- **Up and Coming**
- **High Quality**
- **Hidden Gems**
- **Most Popular**
- **New Projects**
- **Latest One-Day Movers**, once prior observations exist

Scores are normalized inside the catalog. A strong geospatial, accessibility, scientific-computing, or civic-tech project is therefore not forced to compete directly with the absolute star scale of the largest AI repositories.

The cross-domain aggregate adds owner and domain diversity after scoring, then restores real score order for presentation.

---

## Evidence-aware momentum

A repository’s lifetime stars divided by age can identify an emerging candidate, but it is not a measured growth rate. Schema v2 makes that distinction visible:

| Signal | Evidence | Confidence |
|:--|:--|--:|
| Provisional lifetime estimate | No earlier observation from this radar | 25% |
| Measured short window | One or more earlier daily observations | Increases with coverage |
| Measured seven-day growth | Usable seven-day baseline | 100% |

Velocity, acceleration, and relative-growth contributions are confidence-weighted **after** catalog normalization. This prevents first-week lifetime estimates from receiving the same score contribution as measured seven-day history.

Unavailable changes remain `null`, not zero.

---

## Quality, novelty, and under-recognition

Project Radar retains separate dimensions rather than hiding everything in one number:

| Dimension | Evidence |
|:--|:--|
| Popularity | Log-scaled stars, forks, and watchers |
| Momentum | Confidence-weighted velocity, acceleration, relative growth, and freshness |
| Maintenance | Last push and repository update with time decay |
| Metadata quality | Description, license, topics, homepage, repository features, adoption, and substance |
| Community health | GitHub Community Metrics for a bounded, domain-balanced subset |
| Adoption depth | Fork and watcher depth, plus absolute forks |
| Relevance | Matched topics, configured keywords, negative terms, and discovery paths |
| Novelty | Deterministic catalog-local inverse-document-frequency over names, descriptions, and topics |
| Under-recognition | Quality and novelty relative to current popularity |
| Confidence | API completeness, corroboration, community evidence, and measurement coverage |

Community health is stewardship evidence, not a security verdict. Descriptive novelty is not a claim of scientific or patent novelty.

Read the [complete methodology](docs/PROJECT_RADARS.md).

---

## Auditability built into the publication

Each Project Radar run emits:

- [`latest.json`](feeds/projects/latest.json) — normalized full dataset;
- compact catalog JSON indexes;
- Markdown leaderboards;
- [`history.json`](feeds/projects/history.json) — rolling observations;
- [`status.json`](feeds/projects/status.json) — run and source-health receipt;
- [`changes.json`](feeds/projects/changes.json) and [`changes.md`](feeds/projects/changes.md) — run-to-run additions, removals, star changes, and rank movement;
- [`audit.json`](feeds/projects/audit.json) and [`audit.md`](feeds/projects/audit.md) — evidence coverage by catalog;
- [`review-queue.json`](feeds/projects/review-queue.json) and [`review-queue.md`](feeds/projects/review-queue.md) — unusual or incomplete high-attention evidence;
- [`projects.atom`](feeds/projects/projects.atom) — subscription feed;
- Shields-compatible badge JSON under `docs/projects/badges/`;
- [`publication-manifest.json`](feeds/projects/publication-manifest.json) — source commit, byte sizes, and SHA-256 checksums;
- searchable static files under [`docs/projects/`](docs/projects/).

The production workflow re-reads every file in the manifest and verifies its byte size and SHA-256 digest before committing.

---

## Reliability model

Production publication is blocked when:

- no projects are discovered;
- stable IDs or normalized repository names collide;
- total records fall below the configured minimum;
- the dataset collapses below the previous healthy publication ratio;
- an individual catalog collapses below its own prior ratio;
- a native catalog has no successful discovery query;
- a catalog misses its minimum size;
- schemas or expected catalogs disagree;
- required reports are missing;
- Atom parsing fails;
- any publication-manifest checksum fails.

Remote failures are isolated and recorded. Feature branches run live validation but cannot commit production data. Stale overlapping runs are canceled. Generated files are written atomically and committed only when they changed.

---

## Supply-chain posture

The runtime has no third-party Python dependencies. The CI path uses the standard library test suite and compile checks without installing arbitrary packages. GitHub Actions are pinned to immutable commit SHAs.

The collectors are metadata-only. They never clone, import, install, build, run, or evaluate discovered repositories.

This project does **not** claim that a ranked repository is secure. Future security dimensions may incorporate OpenSSF Scorecard, advisories, dependency metadata, signatures, or attestations without conflating security with popularity.

---

## Quickstart

```bash
git clone https://github.com/Amarel-Taylor-Scott/github-radar
cd github-radar

# General feed
python -m github_radar

# Agent extensions
python scripts/run_agent_extension_radar.py --config agent_extensions.json
python scripts/compact_agent_extension_outputs.py

# All project domains
python scripts/project_radar.py --config project_radars.json
```

Editable installation adds both console commands:

```bash
pip install -e .
github-radar --help
project-radar --help
```

Raise GitHub API limits with a token:

```bash
export GITHUB_TOKEN=github_pat_...
project-radar --config project_radars.json
```

The token is read from the environment and is never written to output.

---

## Add another radar

Add one object to [`project_radars.json`](project_radars.json):

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

No copied scraper is required. Custom queries are supported when GitHub topics are insufficient.

---

## Contributing

Use the [project nomination form](.github/ISSUE_TEMPLATE/nominate-project.yml) to surface a candidate. Nominations are discovery leads, not automatic ranking bonuses, and affiliations must be disclosed.

Code, catalog, methodology, and source-adapter contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the [Code of Conduct](CODE_OF_CONDUCT.md).

Standalone mirror repositories and the distribution flywheel are tracked in [Issue #5](https://github.com/Amarel-Taylor-Scott/github-radar/issues/5). The central repository remains the source of truth.

---

## License

MIT © 2026 Amarel Taylor Scott. See [LICENSE](LICENSE).
