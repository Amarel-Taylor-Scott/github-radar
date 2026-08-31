# Agent Extension Radar

`github-radar` generates four daily extension catalogs from one shared discovery, measurement, and publishing system:

1. **Claude Skills Radar** — `SKILL.md` components for Claude and compatible Agent Skills implementations.
2. **Claude Tools Radar** — MCP servers and evidence-backed tool integrations.
3. **Claude Plugins Radar** — Claude Code and Claude Cowork plugins.
4. **Agent Extensions Radar** — the cross-ecosystem superset for Claude, Codex, Gemini CLI, OpenCode, and other agents.

The implementation deliberately keeps collection logic centralized. Four independent scrapers would drift, duplicate API traffic, disagree about ranking, and require four separate repair cycles whenever an upstream file layout changes. The four public products can later be thin mirrors of this source of truth.

## Run it

```bash
export GITHUB_TOKEN=github_token_here   # optional but strongly recommended

python scripts/run_agent_extension_radar.py \
  --config agent_extensions.json \
  --output-dir feeds/agent-extensions \
  --site-dir docs/agent-extensions

python scripts/compact_agent_extension_outputs.py \
  --feed-dir feeds/agent-extensions \
  --site-dir docs/agent-extensions
```

`run_agent_extension_radar.py` loads the generic collector and installs the production policies for balanced enrichment, measured-only leaderboards, and repository diversity. The compacting pass converts the collector's convenient expanded records into an efficient normalized publication bundle.

Generated files are written to:

```text
feeds/agent-extensions/
├── README.md
├── latest.json              # normalized repositories + item records
├── status.json
├── history.json
├── claude-skills.md
├── claude-skills.json       # catalog metadata + leaderboard item IDs
├── claude-tools.md
├── claude-tools.json
├── claude-plugins.md
├── claude-plugins.json
├── agent-extensions.md
└── agent-extensions.json

docs/agent-extensions/
├── index.html               # searchable static interface
└── latest.json
```

Repository metadata is stored once in `latest.json`; item records reference it by full repository name. Catalog JSON files point to the shared dataset instead of duplicating thousands of records. The HTML page loads its adjacent JSON file rather than embedding a multi-megabyte copy.

## Daily operation

`.github/workflows/agent-extensions-daily.yml` runs at **08:37 UTC** and can also be started manually. It:

1. checks out the repository;
2. runs the complete offline test suite;
3. discovers and normalizes current extension data;
4. reads the retained 45-day history;
5. computes popularity, momentum, acceleration, freshness, and quality scores;
6. renders Markdown, JSON, status, history, and HTML outputs;
7. normalizes and deduplicates the publication bundle;
8. commits only the generated directories when content changes.

The unusual minute reduces top-of-hour GitHub Actions congestion. A per-branch concurrency group prevents overlapping daily runs.

## Sources

Sources are declared in `agent_extensions.json`, not embedded in ranking logic.

### Trusted seeds

- Anthropic's official Claude plugin marketplace.
- Anthropic's security-reviewed community marketplace mirror.
- Anthropic's knowledge-work plugin marketplace.
- Anthropic's official skills repository and skills marketplace.
- OpenAI's official Codex skills repository.
- Vercel's cross-agent skills repository.

### Evidence-backed open discovery

- GitHub repository search for explicit ecosystem topics and narrow name/description matches.
- GitHub code search for concrete extension artifacts:
  - `.claude/skills/**/SKILL.md`
  - `.agents/skills/**/SKILL.md`
  - `.codex/skills/**/SKILL.md`
  - `.claude-plugin/plugin.json`
  - `gemini-extension.json`
- Repository topics for MCP servers, Claude Code plugins, Gemini CLI extensions, OpenCode plugins, coding agents, and agent frameworks.

Broad README-only matches are intentionally excluded from the focused Claude Tools catalog. A repository that merely mentions MCP is not automatically treated as an MCP tool.

Every item records its provenance and evidence. Marketplace inclusion increases source confidence; it does **not** automatically confer popularity or momentum.

## Balanced metadata enrichment

GitHub code-search results and marketplace entries do not always include star, fork, license, creation, and push metadata. A naïve collector can spend its entire API budget enriching the first large marketplace and leave smaller catalogs with misleading zero-star records.

The production entrypoint fixes this by:

- grouping missing repository records by native catalog;
- allocating metadata requests in round-robin passes across Claude skills, tools, plugins, and cross-agent extensions;
- prioritizing explicit seeds and exact artifact paths over keyword-only candidates;
- allowing unused quota from a small catalog to flow to larger catalogs;
- retaining incomplete records in the searchable directory while excluding them from public leaderboards when enough fully measured records exist.

## Item-level versus repository-level signals

GitHub stars, forks, creation dates, and push activity belong to repositories. They do not belong to an individual skill directory or plugin subdirectory. The system therefore:

- identifies and publishes components at item/path level;
- measures GitHub momentum at repository level;
- retains exact component paths, source URLs, manifests, and provenance;
- permits only one representative from a repository in each default leaderboard;
- uses deterministic quality-aware tie breaking when several components inherit the same repository score.

This prevents a large monorepo from occupying most of a leaderboard while making the measurement limitation explicit. Component-level install and usage signals are tracked as the next ingestion layer in issue #2.

## Momentum model

Each artifact receives four transparent scores.

### Popular

Weighted toward log-scaled stars and forks, then adjusted for velocity, recent maintenance, artifact quality, and source confidence.

### High momentum

Weighted toward observed stars per day and week-over-week acceleration, with smaller popularity, freshness, quality, and confidence terms.

### Rising

Weights velocity and acceleration most heavily and adds an age-decay term so genuinely new projects can surface without needing mature-project star totals.

### Overall

A blend of popular, momentum, and rising scores.

Archived repositories, repositories stale for more than a year, and records that could not be fully enriched receive explicit penalties.

## First-run behavior

A new installation has no historical snapshots. The first run labels its velocity source as `lifetime-estimate` and uses stars divided by repository age as a provisional signal. As snapshots accumulate, the system automatically switches to measured 1-day, 7-day, and 30-day star deltas. With 14 days of retained history it also computes week-over-week acceleration.

The feed never represents an unavailable seven-day delta as a measured zero.

## Configuration model

The JSON configuration controls:

- catalogs and descriptions;
- official marketplace manifests;
- explicit repository seeds and path globs;
- repository-search queries;
- code-search queries and path validation regular expressions;
- platform and catalog assignments;
- source confidence weights;
- discovery windows;
- API and metadata budgets;
- history retention;
- leaderboard size and per-repository diversity caps;
- output paths.

Adding another agent ecosystem is normally a configuration extension. A new generic parser is required only when that ecosystem introduces a genuinely different manifest format.

## Recommended public repository layout

The current implementation publishes all four catalogs from `github-radar`, which is the safest source of truth. Once the rankings have accumulated measured history, create thin public mirrors:

```text
Amarel-Taylor-Scott/claude-skills-radar
Amarel-Taylor-Scott/claude-tools-radar
Amarel-Taylor-Scott/claude-plugins-radar
Amarel-Taylor-Scott/agent-extensions-radar
```

Each mirror should contain only its generated `README.md`, compact catalog index, shared or scoped dataset, optional changelog, and static interface. Keep collection, scoring, tests, and upstream adapters in `github-radar`; otherwise the products will diverge.

Cross-repository publication requires either a fine-grained token restricted to those repositories or a GitHub App installation. The built-in workflow token is intentionally scoped to `github-radar` and should not be broadened merely for convenience.

## Operational safeguards

- Read-only collection; discovered scripts, hooks, plugins, and MCP servers are never executed.
- Standard-library JSON and frontmatter parsing; no installation of third-party extensions.
- API budgets, request pacing, caching, and per-source failure isolation.
- Refusal to overwrite a healthy feed with an empty run unless `--allow-empty` is explicitly supplied.
- Exact provenance and evidence retained in JSON.
- Archived and stale penalties.
- Incomplete records withheld from leaderboards when measured alternatives exist.
- Offline deterministic tests before every scheduled publication.
- No stargazer identity collection; only aggregate repository counts and daily deltas are retained.

## Planned registry-native signals

Issue #2 tracks the next measurement layer: skills.sh install/trending/hot data and audits, the official MCP Registry, Gemini CLI's public extension registry, OpenCode package metadata, component-level deltas, duplicate detection, and source-health warnings. These signals will supplement—not hide—the repository-level GitHub measurements.
