# github-radar

[![CI](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/ci.yml)
[![Daily feed](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/daily.yml/badge.svg)](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/daily.yml)
[![Agent extension catalogs](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/agent-extensions-daily.yml/badge.svg)](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/agent-extensions-daily.yml)
[![Project radars](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/project-radars-daily.yml/badge.svg)](https://github.com/Amarel-Taylor-Scott/github-radar/actions/workflows/project-radars-daily.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies: none](https://img.shields.io/badge/deps-stdlib--only-brightgreen)](pyproject.toml)

**Daily, momentum-aware discovery for GitHub repositories, agent extensions, and high-quality projects across technical domains.**

📈 **General feed:** [`feeds/latest.md`](feeds/latest.md)

🧭 **Agent extensions:** [Claude Skills](feeds/agent-extensions/claude-skills.md) · [Claude Tools](feeds/agent-extensions/claude-tools.md) · [Claude Plugins](feeds/agent-extensions/claude-plugins.md) · [All Agent Extensions](feeds/agent-extensions/agent-extensions.md)

🔭 **Project radars:** [Interesting Projects](feeds/projects/interesting-projects.md) · [AI Agents](feeds/projects/ai-agents.md) · [AI Engineering](feeds/projects/ai-engineering.md) · [Developer Tools](feeds/projects/developer-tools.md) · [Data Engineering](feeds/projects/data-engineering.md) · [All Catalogs](feeds/projects/README.md)

`github-radar` answers three related questions:

1. What is hot on GitHub right now, especially in AI?
2. Which Claude, Codex, MCP, and agent extensions are gaining traction?
3. Which high-quality, fast-rising, new, or under-recognized projects deserve attention inside a particular technical domain?

The repository contains three production pipelines rather than three disconnected demos. They share the same principles: bounded public discovery, explicit provenance, honest missing-data behavior, deterministic scoring, rolling history, validation before publication, and read-only collection.

```bash
python -m github_radar
python scripts/run_agent_extension_radar.py --config agent_extensions.json
python scripts/project_radar.py --config project_radars.json
```

The core runtime uses only the Python standard library.

---

## Products

### 1. General GitHub feed

The original radar combines GitHub Search with the public Trending page, deduplicates repositories, and publishes JSON, Markdown, or Atom. Its blended score uses log-scaled popularity, repository freshness, Trending momentum, Trending presence, and cross-source corroboration.

```text
score =  w_pop  · log10(stars)
       + w_rec  · 0.5 ^ (days_idle / H)
       + w_mom  · log10(stars_today)
       + w_trend · [is on Trending]
       + w_multi · (source_count − 1)
```

The scheduled workflow runs daily at **07:13 UTC** and commits output only when it changes.

### 2. Agent Extension Radar

One collector publishes four independently consumable catalogs:

| Catalog | Scope |
|:--|:--|
| [Claude Skills Radar](feeds/agent-extensions/claude-skills.md) | Standalone and packaged `SKILL.md` components for Claude and compatible Agent Skills runtimes |
| [Claude Tools Radar](feeds/agent-extensions/claude-tools.md) | MCP servers and evidence-backed tool integrations |
| [Claude Plugins Radar](feeds/agent-extensions/claude-plugins.md) | Official, reviewed-community, and manifest-backed Claude Code/Cowork plugins |
| [Agent Extensions Radar](feeds/agent-extensions/agent-extensions.md) | Cross-agent skills, tools, plugins, agents, and frameworks for Claude, Codex, Gemini CLI, OpenCode, and others |

The normalized dataset, rolling history, run receipt, compact catalog indexes, and searchable static interface live under [`feeds/agent-extensions/`](feeds/agent-extensions/) and [`docs/agent-extensions/`](docs/agent-extensions/).

The extension workflow runs daily at **08:37 UTC**. It never installs or executes discovered skills, hooks, plugins, scripts, or MCP servers. See [`docs/AGENT_EXTENSION_RADAR.md`](docs/AGENT_EXTENSION_RADAR.md) for the source map, schemas, ranking model, and mirror design.

### 3. Multi-domain Project Radar

Project Radar generalizes the same daily-publication model to ordinary GitHub projects. One declarative configuration currently produces ten catalogs:

| Catalog | Focus |
|:--|:--|
| [Interesting GitHub Projects](feeds/projects/interesting-projects.md) | Cross-domain aggregate balancing novelty, momentum, quality, relevance, and under-recognition |
| [AI Agents](feeds/projects/ai-agents.md) | Agent runtimes, coding agents, multi-agent systems, tool use, computer use, and orchestration |
| [AI Engineering](feeds/projects/ai-engineering.md) | RAG, inference, evaluation, observability, model serving, LLM operations, and production ML tooling |
| [Developer Tools](feeds/projects/developer-tools.md) | Editors, terminals, CLIs, debuggers, API clients, testing, build systems, and developer experience |
| [Data Engineering](feeds/projects/data-engineering.md) | Pipelines, ETL/ELT, orchestration, streaming, warehouses, lakehouses, and data quality |
| [Cybersecurity Tools](feeds/projects/cybersecurity.md) | Defensive security, AppSec, vulnerability discovery, reverse engineering, privacy, and automation |
| [Robotics and Embodied AI](feeds/projects/robotics.md) | Robotics frameworks, ROS, simulation, autonomy, drones, control, sensing, and embodied intelligence |
| [Geospatial and Mapping](feeds/projects/geospatial.md) | GIS, routing, spatial databases, Earth observation, mapping, analytics, and digital twins |
| [Creative Computing](feeds/projects/creative-computing.md) | Graphics, animation, video, audio, creative coding, generative art, design tools, and 3D |
| [Self-Hosted and Local-First](feeds/projects/self-hosted.md) | Self-hosted applications, homelabs, local-first software, privacy, personal clouds, and independent automation |

Every catalog publishes:

- **Most Interesting**
- **High Momentum**
- **Up and Coming**
- **High Quality**
- **Hidden Gems**
- **Most Popular**
- **New Projects**
- **Latest One-Day Movers**, once daily history exists

Project scores are normalized **inside each catalog**. This prevents a strong robotics, geospatial, or scientific project from being buried simply because its ecosystem has fewer absolute stars than the largest AI or JavaScript projects.

The scheduled workflow runs daily at **09:17 UTC**, after the other two products. It publishes Markdown, compact catalog JSON, a normalized full dataset, 90-day history, source-health receipt, and a searchable static interface under [`feeds/projects/`](feeds/projects/) and [`docs/projects/`](docs/projects/).

See [`docs/PROJECT_RADARS.md`](docs/PROJECT_RADARS.md) for the complete architecture, scoring model, configuration contract, reliability gates, safety rules, and standalone-mirror growth strategy.

---

## Project Radar ranking model

“High quality” is not treated as an unexplainable label. The engine retains raw repository evidence and computes separate dimensions:

| Dimension | Evidence |
|:--|:--|
| Popularity | Log-scaled stars, forks, and watchers |
| Velocity | Measured stars per day; provisional lifetime estimate on the first snapshot |
| Acceleration | Current observed velocity compared with the preceding window |
| Relative growth | Growth relative to the repository's prior size |
| Freshness | Time-decayed last push |
| Maintenance | Push and repository-update recency |
| Metadata quality | Description, license, topics, homepage, community features, adoption, substance, and corroboration |
| Relevance | Catalog memberships, matched topics, configured keywords, negative terms, and discovery paths |
| Confidence | API completeness, metadata completeness, source confidence, and corroboration |
| Newness | Time decay from repository creation |

The public leaderboards blend these dimensions for distinct purposes. Raw dimensions and component scores remain in JSON so consumers can build their own ranking.

Momentum belongs to the repository, not to an arbitrary catalog. The rolling history derives one-, seven-, and thirty-day star changes, seven-day fork and watcher changes, velocity, acceleration, relative growth, and first-seen date.

On the first run, unavailable deltas remain `null`; they are never represented as zero. As observations accumulate, measured history automatically replaces the provisional lifetime estimate.

---

## Discovery and reliability

Project Radar builds a fair query schedule across every native catalog. Each domain receives an active-project query and a new-project query before secondary topics compete for the remaining API budget. Repository-detail enrichment is also allocated round-robin, so the largest ecosystem cannot consume the entire run.

Production safeguards include:

- bounded Search API requests with pacing and retry/backoff;
- automatic `archived:false` and `fork:false` qualifiers;
- case-insensitive deduplication and stable repository IDs;
- provenance, matched topics, query modes, and source-health receipts;
- owner-diverse leaderboards;
- age and popularity ceilings for emerging-project rankings;
- total and per-catalog minimum counts;
- total and per-catalog previous-publication shrink guards;
- atomic local output writes;
- feature-branch validation without production publication;
- commit-on-change behavior on `main`;
- stale overlapping workflow cancellation.

A failed query is recorded and does not terminate healthy sources. A suspiciously empty or collapsed result cannot overwrite the last healthy publication.

Resource lists, courses, and templates may remain searchable in the normalized dataset but are excluded from the initial project leaderboards. Archived, disabled, forked, stale, empty-description, and template repositories receive explicit exclusions or penalties.

Community nominations are accepted through [the project nomination issue form](.github/ISSUE_TEMPLATE/nominate-project.yml). A nomination is discovery evidence only and receives no automatic score bonus. Affiliations must be disclosed.

---

## Sources and caveats

| Source | Used by | Notes |
|:--|:--|:--|
| GitHub Search API | General feed, extensions, projects | Official; rate-limited; 1,000-result cap per query; topic metadata varies |
| GitHub repository API | Extensions, projects | Official metadata enrichment and validation |
| GitHub Trending HTML | General feed only | GitHub has no official Trending API; layout can change |
| Official/reviewed marketplaces | Agent extensions | Exact manifests, component paths, and provenance retained |
| Hugging Face trending | Optional general source | Entries without GitHub repositories are ignored |
| arXiv cs.AI | Optional general source | Recent papers are retained only when they reference a GitHub repository |

`GITHUB_TOKEN` is optional locally and supplied automatically in Actions. Tokens are used only for authenticated read requests and are never logged or serialized.

---

## Quickstart

```bash
git clone https://github.com/Amarel-Taylor-Scott/github-radar
cd github-radar

# General feed
python -m github_radar
python -m github_radar --top 20 --format json
python -m github_radar --out-dir output --format markdown,json,atom

# Agent extensions
python scripts/run_agent_extension_radar.py --config agent_extensions.json
python scripts/compact_agent_extension_outputs.py

# All configured project domains
python scripts/project_radar.py --config project_radars.json
```

Optional editable installation provides the `github-radar` console command:

```bash
pip install -e .
github-radar --help
```

For a deterministic Project Radar test run:

```bash
python scripts/project_radar.py \
  --config project_radars.json \
  --now 2026-08-31T15:36:00Z \
  --output-dir /tmp/project-radar-feeds \
  --site-dir /tmp/project-radar-site
```

---

## Adding another domain

Add one object to [`project_radars.json`](project_radars.json):

```json
{
  "id": "scientific-computing",
  "title": "Scientific Computing Radar",
  "description": "Numerical, simulation, research-computing, and reproducible-science projects.",
  "topics": ["scientific-computing", "numerical-analysis", "simulation"],
  "keywords": ["simulation", "numerical", "scientific", "research"],
  "negative_terms": ["course", "interview"],
  "min_stars": 10,
  "new_min_stars": 3,
  "minimum_items": 15,
  "source_confidence": 0.6,
  "excluded_project_types": ["resource-list", "education", "template"]
}
```

No copied scraper is required. Custom bounded search queries can be added when GitHub topics are insufficient.

Strong next catalogs include scientific computing, databases, cloud-native infrastructure, bioinformatics, civic technology, accessibility, game development, and open-source business infrastructure.

---

## Architecture

```text
github_radar/
├── cli.py                 # original feed CLI
├── config.py              # original feed configuration
├── models.py              # original repository model
├── http.py                # stdlib HTTP client, auth, pacing, retries
├── ranking.py             # original feed ranking
├── aggregate.py           # original source orchestration
├── output.py              # original JSON, Markdown, Atom writers
├── project_common.py      # project records, stable IDs, classification, utilities
├── project_discovery.py   # fair query scheduling, collection, enrichment
├── project_history.py     # rolling snapshots and measured growth
├── project_scoring.py     # catalog-local dimensions and leaderboards
├── project_rendering.py   # Markdown, JSON, status, searchable HTML
├── project_runner.py      # validation, shrink guards, CLI orchestration
└── sources/
    ├── search.py
    ├── trending.py
    └── extras.py

scripts/
├── agent_extension_radar.py
├── run_agent_extension_radar.py
├── compact_agent_extension_outputs.py
└── project_radar.py       # stable CLI shim for the modular project engine

configuration/
├── agent_extensions.json
└── project_radars.json
```

The central engines remain the source of truth. Future standalone presentation repositories should be thin transactional mirrors of generated artifacts—not separate collectors that can drift.

---

## Testing

The offline suite uses stdlib `unittest`, saved fixtures, fake API payloads, and injected time. It covers the general feed, extension parsing and history, balanced enrichment, publication normalization, Project Radar query fairness, collector integration, deduplication, first-run honesty, measured growth and acceleration, catalog-local scoring, owner diversity, output generation, and total plus per-catalog shrink protection.

```bash
python -m unittest discover -s tests
```

CI runs on Python **3.10, 3.11, and 3.12** for pushes and pull requests. Each production workflow reruns the complete offline suite before live collection.

---

## Safety and ethics

- Discovery is read-only.
- Discovered repositories, skills, hooks, scripts, plugins, and MCP servers are never cloned, installed, imported, built, or executed.
- Public metadata and links are surfaced; upstream repository contents are not republished.
- Requests use a real User-Agent, pacing, rate-limit awareness, and retry/backoff.
- Tokens are never written to generated data.
- Nominations do not bypass relevance, quality, history, diversity, or safety rules.

---

## License

MIT © 2026 Amarel Taylor Scott. See [`LICENSE`](LICENSE).
