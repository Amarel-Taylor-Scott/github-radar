"""Command-line interface: ``python -m github_radar`` / ``github-radar``.

Zero-config by default — running with no flags fetches search + trending,
ranks, and prints a Markdown digest to stdout. Every config knob is overridable
by a flag, and a ``--config FILE`` (TOML) can pin a custom niche. The token is
read from ``--token`` or the ``GITHUB_TOKEN`` env var, never hardcoded.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Sequence

from . import __version__
from .aggregate import collect
from .config import DEFAULT_TOPICS, Config
from .output import to_atom, to_json, to_markdown, write_outputs
from .ranking import RankingWeights

LOGGER = logging.getLogger("github_radar")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="github-radar",
        description="A feed of popular / AI-related GitHub repositories, "
        "ranked by a momentum-aware score.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"github-radar {__version__}")

    src = parser.add_argument_group("sources")
    src.add_argument("--config", metavar="FILE", help="TOML config file (overrides defaults)")
    src.add_argument(
        "--topics",
        help=f"Comma-separated topics to OR together (default: {','.join(DEFAULT_TOPICS)})",
    )
    src.add_argument("--min-stars", type=int, help="Minimum stargazers (default 100)")
    src.add_argument("--window-days", type=int, help="Recency window for pushed:> (default 30)")
    src.add_argument(
        "--created-within-days",
        type=int,
        help="Also require repo created within N days (default: off)",
    )
    src.add_argument("--search-limit", type=int, help="Max search results to keep (<=1000)")
    src.add_argument(
        "--trending-languages",
        help="Comma-separated trending languages, '' for all (default: all)",
    )
    src.add_argument(
        "--trending-since",
        choices=["daily", "weekly", "monthly"],
        help="Trending window (default daily)",
    )
    src.add_argument("--no-search", action="store_true", help="Disable the Search API source")
    src.add_argument("--no-trending", action="store_true", help="Disable the Trending source")
    src.add_argument(
        "--trending-rss", action="store_true", help="Enable the community RSS trending fallback"
    )
    src.add_argument("--huggingface", action="store_true", help="Enable Hugging Face trending")
    src.add_argument("--arxiv", action="store_true", help="Enable arXiv cs.AI feed")

    out = parser.add_argument_group("output")
    out.add_argument("--top", type=int, help="Number of repos in the final feed (default 50)")
    out.add_argument(
        "--format",
        default="markdown",
        help="Comma-separated: markdown,json,atom (default markdown to stdout)",
    )
    out.add_argument(
        "--out-dir",
        metavar="DIR",
        help="Write outputs to DIR instead of stdout (one file per format)",
    )
    out.add_argument("--basename", default="feed", help="Output filename stem")

    rnk = parser.add_argument_group("ranking")
    rnk.add_argument("--w-popularity", type=float, help="Weight: log-stars popularity")
    rnk.add_argument("--w-recency", type=float, help="Weight: push-recency freshness")
    rnk.add_argument("--w-momentum", type=float, help="Weight: trending stars-this-period")
    rnk.add_argument("--w-trending", type=float, help="Weight: trending-presence bonus")
    rnk.add_argument("--half-life", type=float, help="Recency half-life in days")

    parser.add_argument("--token", help="GitHub token (else uses $GITHUB_TOKEN)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="-v info, -vv debug")
    return parser


def config_from_args(args: argparse.Namespace) -> Config:
    """Layer CLI flags over an optional TOML config over the defaults."""
    config = Config.from_toml(args.config) if args.config else Config()
    overrides: dict = {}
    if args.topics is not None:
        overrides["topics"] = [t.strip() for t in args.topics.split(",") if t.strip()]
    if args.trending_languages is not None:
        overrides["trending_languages"] = [
            t.strip() for t in args.trending_languages.split(",")
        ]
    overrides["min_stars"] = args.min_stars
    overrides["window_days"] = args.window_days
    overrides["created_within_days"] = args.created_within_days
    overrides["search_limit"] = args.search_limit
    overrides["trending_since"] = args.trending_since
    overrides["top_n"] = args.top
    if args.no_search:
        overrides["enable_search"] = False
    if args.no_trending:
        overrides["enable_trending"] = False
    if args.trending_rss:
        overrides["enable_trending_rss"] = True
    if args.huggingface:
        overrides["enable_huggingface"] = True
    if args.arxiv:
        overrides["enable_arxiv"] = True
    return config.with_overrides(**overrides)


def weights_from_args(args: argparse.Namespace) -> RankingWeights:
    base = RankingWeights()
    return RankingWeights(
        popularity=args.w_popularity if args.w_popularity is not None else base.popularity,
        recency=args.w_recency if args.w_recency is not None else base.recency,
        momentum=args.w_momentum if args.w_momentum is not None else base.momentum,
        trending_bonus=args.w_trending if args.w_trending is not None else base.trending_bonus,
        multi_source_bonus=base.multi_source_bonus,
        recency_half_life_days=args.half_life
        if args.half_life is not None
        else base.recency_half_life_days,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    level = logging.WARNING - min(args.verbose, 2) * 10
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")

    config = config_from_args(args)
    weights = weights_from_args(args)
    token = args.token or os.environ.get("GITHUB_TOKEN")

    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    valid = {"markdown", "json", "atom"}
    bad = set(formats) - valid
    if bad:
        print(f"error: unknown format(s): {', '.join(sorted(bad))}", file=sys.stderr)
        return 2

    generated_at = datetime.now(timezone.utc)
    LOGGER.info("github-radar %s starting (topics=%s, window=%dd, token=%s)",
                __version__, config.topics, config.window_days, "yes" if token else "no")

    repos = collect(config, weights=weights, now=generated_at, token=token)

    if not repos:
        print("warning: no repositories collected (all sources empty?)", file=sys.stderr)

    if args.out_dir:
        written = write_outputs(
            repos,
            formats=formats,
            out_dir=args.out_dir,
            basename=args.basename,
            generated_at=generated_at,
        )
        for fmt, path in written.items():
            print(f"wrote {fmt}: {path}", file=sys.stderr)
    else:
        renderers = {"markdown": to_markdown, "json": to_json, "atom": to_atom}
        chunks = [renderers[f](repos, generated_at=generated_at) for f in formats]
        print("\n\n".join(chunks))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
