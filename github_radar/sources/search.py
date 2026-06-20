"""Primary source: the official GitHub Search API.

``GET /search/repositories`` is the only *officially supported* way to query
GitHub for "popular AI repos pushed recently". We build a query string from the
config (topics OR-ed, ``stars:>N``, ``pushed:>DATE``, optional ``created:>``),
sort by stars, and paginate to the requested limit while respecting the
``incomplete_results`` flag and the 1000-result hard cap GitHub enforces.
"""

from __future__ import annotations

import logging
import urllib.parse
from datetime import datetime
from typing import Optional

from ..config import Config
from ..http import FetchError, HttpClient
from ..models import Repo

LOGGER = logging.getLogger("github_radar.sources.search")

SEARCH_ENDPOINT = "https://api.github.com/search/repositories"
# GitHub caps Search results at 1000 regardless of total_count.
MAX_SEARCH_RESULTS = 1000
PER_PAGE = 100


def build_search_query(
    config: Config, *, topic: Optional[str] = None, now: Optional[datetime] = None
) -> str:
    """Build the ``q=`` qualifier string for a single Search API request.

    The GitHub Search API treats space-separated qualifiers as **AND** and does
    *not* support ``OR`` between ``topic:`` qualifiers (it returns 0 results or
    a 422). So to get an *OR across our topic set* we issue one query per topic
    (see :meth:`SearchSource.fetch`) and merge. This function builds the query
    for a *single* topic::

        topic:llm stars:>100 pushed:>2026-05-21

    When ``topic`` is ``None`` and the config has topics, the first topic is
    used; pass an explicit ``topic`` to target a specific one. With no topics at
    all, the query is just the stars/recency qualifiers. Returns the *unencoded*
    query; the caller URL-encodes it.
    """
    parts: list[str] = []
    topics = [t.strip() for t in config.topics if t.strip()]
    chosen = topic if topic is not None else (topics[0] if topics else None)
    if chosen:
        parts.append(f"topic:{chosen}")
    if config.min_stars > 0:
        parts.append(f"stars:>{config.min_stars}")
    parts.append(f"pushed:>{config.pushed_since(now)}")
    created = config.created_since(now)
    if created:
        parts.append(f"created:>{created}")
    return " ".join(parts)


class SearchSource:
    """Fetch and normalize repositories from the GitHub Search API."""

    name = "search"

    def __init__(self, client: HttpClient) -> None:
        self.client = client

    def fetch(self, config: Config, now: Optional[datetime] = None) -> list[Repo]:
        """Return up to ``config.search_limit`` repos across all topics (OR-ed).

        We issue one query per configured topic (GitHub can't OR ``topic:``
        qualifiers in a single query) and concatenate. Per-topic failures are
        logged and skipped so a rate-limit on one query never aborts the run —
        other topics and other sources still contribute. The final dedup happens
        in the aggregator; here we just gather.
        """
        limit = min(config.search_limit, MAX_SEARCH_RESULTS)
        topics = [t.strip() for t in config.topics if t.strip()] or [None]
        # Spread the limit across topics so no single topic dominates the page
        # budget; round up so small limits still return something per topic.
        per_topic = max(limit // len(topics), 1) if topics else limit
        all_repos: list[Repo] = []
        for topic in topics:
            query = build_search_query(config, topic=topic, now=now)
            all_repos.extend(self._fetch_query(query, per_topic))
            if len(all_repos) >= limit:
                break
        return all_repos[:limit]

    def _fetch_query(self, query: str, limit: int) -> list[Repo]:
        """Paginate one query up to ``limit`` results; degrade on failure."""
        repos: list[Repo] = []
        page = 1
        try:
            while len(repos) < limit:
                page_repos, has_more = self._fetch_page(query, page)
                repos.extend(page_repos)
                if not has_more or not page_repos:
                    break
                page += 1
        except FetchError as exc:
            LOGGER.error("Search query %r failed: %s (continuing with %d repos)",
                         query, exc, len(repos))
        return repos[:limit]

    def _fetch_page(self, query: str, page: int) -> tuple[list[Repo], bool]:
        params = urllib.parse.urlencode(
            {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": PER_PAGE,
                "page": page,
            }
        )
        url = f"{SEARCH_ENDPOINT}?{params}"
        LOGGER.debug("Search page %d: %s", page, url)
        response = self.client.get(url)
        payload = response.json()
        items = payload.get("items", [])
        repos = [Repo.from_search_item(item) for item in items if item.get("full_name")]
        # Stop paginating past the 1000-result cap or when GitHub returns a
        # short page. ``incomplete_results`` means GitHub timed out; we keep
        # what we got and stop to avoid hammering.
        has_more = (
            len(items) == PER_PAGE
            and page * PER_PAGE < MAX_SEARCH_RESULTS
            and not payload.get("incomplete_results", False)
        )
        return repos, has_more
