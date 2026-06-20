# github-radar

**A momentum-aware feed of popular & AI-related GitHub repositories.**

`github-radar` answers one question well: **"what's actually hot on GitHub right
now, especially in AI?"** — not "what has the most all-time stars" (that list
never changes). It pulls from GitHub's official Search API and the public
Trending page, deduplicates across sources, scores each repo with a blended
**star-velocity ranking**, and emits a clean feed as **JSON**, a **Markdown
digest**, or an **Atom feed**.

It is **dependency-free** (Python standard library only), **zero-config** (runs
out of the box), and **degrades gracefully** (one rate-limited source never
sinks the run).

```bash
python -m github_radar                       # Markdown digest of the top 50, to stdout
python -m github_radar --top 20 --format json
python -m github_radar --out-dir output --format markdown,json,atom
```

---

## Why this exists (the pitch)

Discovering genuinely *new* momentum on GitHub is harder than it looks:

- **There is no official "trending API."** GitHub's Trending page is HTML-only.
- **The Search API is the only supported query path**, and it sorts by *total*
  stars — so newcomers are buried under perennial giants.
- **True star-velocity** (stars/day over a window) needs the GH Archive event
  stream + BigQuery, which is heavyweight and credential-gated.

`github-radar` stitches the *free, public* signals together and applies a
recency- and momentum-aware score, so a repo that gained 1,500 stars **today**
can out-rank a 200k-star project that's been idle for three months.

---

## Sources

Best-first. Each source normalizes into one shared `Repo` model, then everything
is deduped by `full_name` and merged.

| # | Source | How | Official? | Caveats |
|--:|--------|-----|:---------:|---------|
| 1 | **GitHub Search API** | `GET /search/repositories`, one query per topic, `stars:>N`, `pushed:>window`, sorted by stars | ✅ Yes | 10 req/min unauthenticated (30 with a token); 1,000-result hard cap; `topic:` qualifiers are **AND**, never OR — so we fan out one query per topic and merge |
| 2 | **GitHub Trending** | Scrape `github.com/trending` + `/trending/{lang}?since=…` HTML | ❌ No API | Layout can change; parser is regex-anchored on the stable `Box-row` blocks and skips unparseable rows |
| 3 | **GitHub Trending RSS** *(opt-in)* | Community feeds at `mshibanami.github.io/GitHubTrendingRSS` | ❌ Third-party | Fallback when the HTML scrape breaks; `--trending-rss` |
| 4 | **Hugging Face trending** *(opt-in)* | `huggingface.co/api/trending`, kept only when an entry links a GitHub repo | ⚠️ Undocumented | `--huggingface` |
| 5 | **arXiv cs.AI** *(opt-in)* | arXiv Atom feed; extracts `github.com/owner/name` refs from recent papers | ✅ Yes (arXiv) | `--arxiv`; papers without a repo link are ignored |

> **No token needed.** `GITHUB_TOKEN` is read from the environment (or `--token`)
> purely to raise rate limits. It is never logged, hardcoded, or committed.

---

## The ranking (headline feature)

Each repo gets a blended `score` in roughly `[0, 100]` from four signals. The
formula is deliberately simple and inspectable (`github_radar/ranking.py`):

```
score =  w_pop  · log10(stars)            # popularity, log-scaled
       + w_rec  · 0.5 ^ (days_idle / H)   # recency: exponential decay, half-life H days
       + w_mom  · log10(stars_today)      # momentum: trending stars-this-period
       + w_trend · [is on trending page]  # flat trending-presence bonus
       + w_multi · (n_sources − 1)         # cross-source corroboration bonus
```

| Term | Default weight | What it does |
|------|---------------:|--------------|
| Popularity | 18 | `log10(stars)` — an extra zero is a fixed bump, not 10×, so giants don't dominate |
| Recency | 28 | Exponential decay on days-since-last-push (half-life **14d**). The knob that lets fresh repos beat dormant ones |
| Momentum | 16 | Log-scaled stars-gained-this-period from the trending page — the lightweight star-velocity proxy |
| Trending bonus | 12 | Flat bonus for appearing on Trending at all |
| Multi-source | 6 | Per *additional* source that independently surfaced the repo |

All weights are tunable via CLI (`--w-recency`, `--half-life`, …) or in code via
`RankingWeights`.

**GH Archive note (optional, not required).** True star-velocity — `WatchEvent`
counts per repo per day — can be computed from the public
[GH Archive](https://www.gharchive.org/) stream via BigQuery. `github-radar`
deliberately avoids requiring BigQuery credentials; the trending page's
*stars-this-period* figure is the lightweight stand-in. The `momentum` term is
structured so a future GH-Archive velocity number can drop in unchanged.

---

## Quickstart

```bash
git clone https://github.com/amareltaylor/github-radar
cd github-radar
python -m github_radar                 # no install, no deps — just run it
```

Optional editable install (adds the `github-radar` console script):

```bash
pip install -e .
github-radar --help
```

Optional: raise rate limits with a token (read-only `public_repo` is plenty):

```bash
export GITHUB_TOKEN=ghp_...            # never committed; read from the env
github-radar --top 30
```

---

## CLI examples

```bash
# Top 20 as a Markdown digest (default), to stdout
python -m github_radar --top 20

# Only repos created in the last 14 days AND pushed in the last 7 — fresh breakouts
python -m github_radar --created-within-days 14 --window-days 7

# Narrow the niche and lift the star floor
python -m github_radar --topics rag,agents --min-stars 500

# Daily trending for specific languages, with the RSS fallback enabled
python -m github_radar --trending-languages python,rust --trending-since daily --trending-rss

# Turn on the optional sources
python -m github_radar --huggingface --arxiv

# Write all three formats into ./output/
python -m github_radar --out-dir output --format markdown,json,atom

# Crank recency so momentum dominates (shorter half-life = faster decay)
python -m github_radar --half-life 7 --w-recency 40 --w-momentum 24

# Pin a niche in a config file
python -m github_radar --config config.example.toml -v
```

---

## Sample output

```
# github-radar — popular & AI GitHub repositories

_Generated 2026-06-20 17:30 UTC — 12 repositories, ranked by momentum-aware score._

| # | Repo | ⭐ | Lang | Score | Description |
|--:|------|--:|:-----|------:|:------------|
| 1 | langgenius/dify         | 145,947 | TypeScript | 43.4 | Production-ready platform for agentic workflow development. |
| 2 | langchain-ai/langchain  | 139,764 | Python     | 43.0 | The agent engineering platform. |
| 3 | open-webui/open-webui   | 142,385 | Python     | 42.5 | User-friendly AI Interface (Supports Ollama, OpenAI API, ...) |
| 4 | BerriAI/litellm         |  50,976 | Python     | 42.1 | Call 100+ LLM APIs in the OpenAI format. |
...
```

JSON carries a metadata envelope (`generated_at`, `count`) and the full per-repo
record including `score`, `sources`, `stars_today`, and `topics`. The Atom feed
is valid Atom 1.0 (one `<entry>` per repo) suitable for any feed reader.

---

## Configuration

Defaults live in `github_radar/config.py` and work with zero setup. Override via
CLI flags, or a TOML file (`--config`, Python 3.11+). See
[`config.example.toml`](config.example.toml). Precedence: **CLI flag > config
file > built-in default.**

---

## Architecture

```
github_radar/
├── cli.py            # argparse CLI + python -m github_radar entry point
├── config.py         # defaults, TOML loader, rolling-window math
├── models.py         # the shared Repo dataclass (normalize, merge, serialize)
├── http.py           # stdlib HTTP client: UA, token, rate-limit back-off, typed errors
├── ranking.py        # the blended momentum-aware score
├── aggregate.py      # dedup/merge + source orchestration (graceful degradation)
├── output.py         # JSON / Markdown / Atom writers
└── sources/
    ├── search.py     # GitHub Search API (primary)
    ├── trending.py   # GitHub Trending HTML scrape + RSS fallback
    └── extras.py     # optional: Hugging Face trending, arXiv cs.AI
```

Each source is a small unit that takes an `HttpClient` + `Config` and returns
`list[Repo]`, and **never raises on remote failure** — it logs and returns `[]`
so the aggregator can carry on with the other sources.

---

## Testing

The suite is **offline and dependency-free** — it uses stdlib `unittest` and
saved fixtures (`tests/fixtures/`), so it makes **no live network calls** and is
fully deterministic (time is injected). It covers the ranking, the dedup/merge,
the trending HTML *and* RSS parsers (against a saved sample page), the
search-query builder, and the output writers.

```bash
python -m unittest discover -s tests        # 44 tests, all offline
# or, if you prefer pytest:
pip install -e ".[dev]" && pytest
```

---

## Data sources, ethics & rate limits

- **Be a good citizen.** The HTTP client sends a real User-Agent, throttles
  between requests, reads `X-RateLimit-Remaining` / `Retry-After`, and backs off
  on `403`/`429` instead of hammering.
- **Trending is scraped, not API'd.** GitHub has no official trending endpoint;
  the scrape touches only the public page, lightly, and is purely read-only. If
  the layout shifts, enable `--trending-rss` for the community feed fallback.
- **Tokens raise limits, nothing more.** `GITHUB_TOKEN` is optional and only
  ever used to authenticate read requests. It is never logged or persisted.
- **Respect the platforms.** This tool surfaces and links public repositories;
  it does not clone, mirror, or republish their contents.

---

## License

MIT © 2026 Amarel Taylor Scott. See [`LICENSE`](LICENSE).
