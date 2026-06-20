"""Dedup + merge across sources, then orchestrate the whole pipeline.

``merge_repos`` is the pure, testable core: given repos from every source
(which heavily overlap — the same hot repo shows up in search *and* trending),
collapse duplicates by case-insensitive ``full_name`` and fold their signals
together (see :meth:`Repo.merge`).

:func:`collect` wires the sources, the merge, and the ranker into one call and
is what the CLI invokes. Each source is guarded so one failure can't sink the
run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, Optional

from .config import Config
from .http import HttpClient
from .models import Repo
from .ranking import RankingWeights, rank
from .sources.extras import ArxivSource, HuggingFaceSource
from .sources.search import SearchSource
from .sources.trending import TrendingSource

LOGGER = logging.getLogger("github_radar.aggregate")


def merge_repos(repos: Iterable[Repo]) -> list[Repo]:
    """Deduplicate repos by ``dedup_key``, merging signals across duplicates.

    First occurrence wins as the base record; later ones are folded in. Order
    of the surviving records follows first-seen order (ranking re-sorts later).
    """
    merged: dict[str, Repo] = {}
    for repo in repos:
        if not repo.full_name or "/" not in repo.full_name:
            continue
        key = repo.dedup_key
        if key in merged:
            merged[key].merge(repo)
        else:
            merged[key] = repo
    return list(merged.values())


def collect(
    config: Config,
    *,
    client: Optional[HttpClient] = None,
    weights: RankingWeights = RankingWeights(),
    now: Optional[datetime] = None,
    token: Optional[str] = None,
) -> list[Repo]:
    """Run all enabled sources, dedup/merge, rank, and return the top feed.

    Every source call is wrapped so an unexpected exception is logged and the
    run continues with whatever the other sources returned.
    """
    now = now or datetime.now(timezone.utc)
    client = client or HttpClient(token=token, min_interval=0.5)
    collected: list[Repo] = []

    def _run(label: str, fn) -> None:
        try:
            found = fn()
            LOGGER.info("Source %-14s -> %3d repos", label, len(found))
            collected.extend(found)
        except Exception as exc:  # noqa: BLE001 - graceful degradation is the point
            LOGGER.error("Source %s crashed unexpectedly: %s", label, exc)

    if config.enable_search:
        _run("search", lambda: SearchSource(client).fetch(config, now))
    if config.enable_trending:
        _run("trending", lambda: TrendingSource(client).fetch(config))
    if config.enable_trending_rss:
        _run("trending-rss", lambda: TrendingSource(client).fetch_rss(config))
    if config.enable_huggingface:
        _run("huggingface", lambda: HuggingFaceSource(client).fetch())
    if config.enable_arxiv:
        _run("arxiv", lambda: ArxivSource(client).fetch())

    merged = merge_repos(collected)
    LOGGER.info("Merged %d raw -> %d unique repos", len(collected), len(merged))
    return rank(merged, weights=weights, now=now, top_n=config.top_n)
