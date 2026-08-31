# Agent Extension Radar

`github-radar` can now generate four daily extension catalogs from one shared discovery and ranking engine:

1. **Claude Skills Radar** — `SKILL.md` components for Claude and compatible Agent Skills implementations.
2. **Claude Tools Radar** — MCP servers, hooks, integrations, and supporting utilities.
3. **Claude Plugins Radar** — Claude Code and Claude Cowork plugins.
4. **Agent Extensions Radar** — the cross-ecosystem superset for Claude, Codex, and other agents.

The implementation deliberately keeps collection logic centralized. Four independent scrapers would drift, duplicate API traffic, disagree about ranking, and require four separate repair cycles whenever an upstream file layout changes.

## Run it

```bash
export GITHUB_TOKEN=github_token_here   # optional but strongly recommended
python scripts/agent_extension_radar.py --config agent_extensions.json
```

Generated files are written to:

```text
feeds/agent-extensions/
├── README.md
├── latest.json
├── status.json
├── history.json
├── claude-skills.md
├── claude-skills.json
├── claude-tools.md
├── claude-tools.json
├── claude-plugins.md
├── claude-plugins.json
├── agent-extensions.md
└── agent-extensions.json

docs/agent-extensions/
├── index.html
└── latest.json
```

The HTML page is fully static and searchable. It can be served with GitHub Pages, copied to another static host, or embedded in a larger directory site.

## Daily operation

`.github/workflows/agent-extensions-daily.yml` runs at **08:37 UTC** and can also be started manually. It:

1. checks out the repository;
2. runs the offline unit-test suite;
3. collects and normalizes current extension data;
4. reads the retained 45-day history;
5. computes current popularity, momentum, acceleration, freshness, and quality scores;
6. renders Markdown, JSON, and HTML;
7. commits only the generated directories.

The unusual minute reduces top-of-hour GitHub Actions congestion. A concurrency group prevents overlapping daily runs.

## Sources

Sources are declared in `agent_extensions.json`, not hardcoded into the ranking engine.

### Trusted seeds

- Anthropic's official Claude plugin marketplace.
- Anthropic's security-reviewed community marketplace mirror.
- Anthropic's knowledge-work plugin marketplace.
- Anthropic's official skills repository and skills marketplace.
- OpenAI's official Codex skills repository.

### Open discovery

- GitHub repository search for explicit topics and README/name/description matches.
- GitHub code search for concrete extension evidence such as:
  - `.claude/skills/**/SKILL.md`
  - `.agents/skills/**/SKILL.md`
  - `.codex/skills/**/SKILL.md`
  - `.claude-plugin/plugin.json`
  - `.claude-plugin/marketplace.json`
  - `.mcp.json`
  - `mcp.json`

Every item records its provenance and evidence. Marketplace inclusion increases source trust; it does **not** automatically make an item high-momentum.

## Item-level versus repository-level signals

GitHub stars, forks, creation dates, and push activity belong to repositories. They do not belong to an individual skill directory or plugin subdirectory. The system therefore:

- identifies and publishes components at item/path level;
- measures momentum at repository level;
- retains exact component paths, source URLs, manifests, and provenance;
- limits the number of items from one repository in each leaderboard so a large monorepo cannot consume every position.

This limitation is displayed in every generated catalog rather than hidden.

## Momentum model

Each artifact receives four scores from transparent features.

### Popular

Weighted toward log-scaled stars and forks, then adjusted for velocity, recent maintenance, artifact quality, and source trust.

### High momentum

Weighted toward observed stars per day and week-over-week acceleration, with smaller popularity, freshness, quality, and trust terms.

### Rising

Weights velocity and acceleration most heavily and adds an age-decay term so genuinely new projects can outrank mature projects with much larger all-time star counts.

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
- code-search queries and path validation regexes;
- platform and catalog assignments;
- trust weights;
- discovery windows;
- API and metadata budgets;
- history retention;
- leaderboard size and per-repository diversity caps;
- output paths.

Adding Gemini CLI extensions, Goose recipes, OpenCode plugins, Cursor rules, or another agent ecosystem is therefore a configuration extension plus, only when necessary, a new generic artifact parser.

## Recommended public repository layout

The current implementation publishes all four catalogs from `github-radar`, which is the safest source of truth. Once the catalog quality is established, create thin public mirrors:

```text
Amarel-Taylor-Scott/claude-skills-radar
Amarel-Taylor-Scott/claude-tools-radar
Amarel-Taylor-Scott/claude-plugins-radar
Amarel-Taylor-Scott/agent-extensions-radar
```

Each mirror should contain only its generated `README.md`, `latest.json`, optional history/changelog files, and the static HTML page. Keep collection, scoring, tests, and upstream adapters in `github-radar`; otherwise the four products will diverge.

Cross-repository publication requires either a fine-grained token restricted to those four repositories or a GitHub App installation. The built-in workflow token is intentionally scoped to `github-radar` and should not be broadened merely for convenience.

## Operational safeguards

- Read-only collection only; the crawler never executes discovered scripts.
- Standard-library JSON and frontmatter parsing; no installation of third-party extensions.
- API budgets and per-source failure isolation.
- Refusal to overwrite a healthy feed with an empty run unless `--allow-empty` is explicitly provided.
- Exact provenance and evidence retained in JSON.
- Archived and stale penalties.
- Offline deterministic tests before every scheduled publication.
- No stargazer identity collection; only aggregate repository counts and daily deltas are retained.

## Near-term improvements

The next useful increments are component-level change velocity, duplicate/typosquat detection, manifest security linting, license compatibility flags, signed publisher attestations, GH Archive `WatchEvent` ingestion for higher-resolution star velocity, and a review queue for disputed classifications.
