"""Secondary source: GitHub Trending (HTML scrape) + a community RSS fallback.

GitHub has **no official trending API**, so we parse the public HTML at
``github.com/trending`` (and ``/trending/{lang}?since=...``). The parser is a
small, well-anchored set of regexes over the stable ``<article class="Box-row">``
blocks — robust enough for the handful of fields we need (repo slug, language,
total stars, stars-this-period, description) without dragging in a full HTML
library.

When the HTML layout changes or the page is unreachable, we fall back to the
community-maintained RSS feeds at ``mshibanami.github.io/GitHubTrendingRSS``,
parsed with stdlib ``xml.etree``.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Optional

from ..config import Config
from ..http import FetchError, HttpClient
from ..models import Repo

LOGGER = logging.getLogger("github_radar.sources.trending")

TRENDING_BASE = "https://github.com/trending"
RSS_BASE = "https://mshibanami.github.io/GitHubTrendingRSS"

# Each trending entry is an <article class="Box-row"> block. We split on those
# and pull fields from each block independently so a malformed block can't
# corrupt its neighbours.
_ARTICLE_RE = re.compile(r'<article class="Box-row">(.*?)</article>', re.S)
# The repo slug lives in the <h2> heading's anchor href: /owner/name.
_REPO_RE = re.compile(
    r'<h2[^>]*class="h3 lh-condensed"[^>]*>.*?<a[^>]*\shref="(/[^"]+?)"', re.S
)
_DESC_RE = re.compile(r'<p class="col-9[^"]*"[^>]*>(.*?)</p>', re.S)
_LANG_RE = re.compile(r'<span itemprop="programmingLanguage">([^<]+)</span>')
# Total stars: the anchor whose href ends in /stargazers. The visible count is
# plain text *after* the inline star <svg>, so we anchor on </svg> and grab only
# the trailing text — anchoring on the anchor open tag would swallow the SVG's
# path coordinates (full of digits) and corrupt the number.
_STARS_RE = re.compile(
    r'href="/[^"]+?/stargazers"[^>]*>.*?</svg>\s*([\d,]+)\s*</a>', re.S
)
# Stars gained this period: "904 stars today" / "stars this week" / "this month".
_PERIOD_STARS_RE = re.compile(r'([\d,]+)\s*stars\s+(?:today|this week|this month)')
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str:
    """Strip HTML tags, unescape entities, and collapse whitespace."""
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_int(raw: str) -> int:
    digits = re.sub(r"[^\d]", "", raw or "")
    return int(digits) if digits else 0


def parse_trending_html(content: str, source_label: str = "trending") -> list[Repo]:
    """Parse a GitHub Trending HTML page into :class:`Repo` objects.

    This is pure and offline — it's the function the test suite exercises
    against a saved fixture. Unparseable blocks are skipped, never fatal.
    """
    repos: list[Repo] = []
    for block in _ARTICLE_RE.findall(content):
        repo_match = _REPO_RE.search(block)
        if not repo_match:
            continue
        full_name = Repo.normalize_full_name(repo_match.group(1))
        if not full_name or "/" not in full_name:
            continue
        desc_match = _DESC_RE.search(block)
        lang_match = _LANG_RE.search(block)
        stars_match = _STARS_RE.search(block)
        period_match = _PERIOD_STARS_RE.search(block)
        repos.append(
            Repo(
                full_name=full_name,
                description=_clean_text(desc_match.group(1)) if desc_match else "",
                language=lang_match.group(1).strip() if lang_match else None,
                stars=_parse_int(stars_match.group(1)) if stars_match else 0,
                stars_today=_parse_int(period_match.group(1)) if period_match else None,
                sources={source_label},
            )
        )
    return repos


def parse_trending_rss(content: str) -> list[Repo]:
    """Parse a GitHubTrendingRSS XML feed into :class:`Repo` objects.

    Each ``<item>`` carries a ``owner/name`` title and a ``github.com`` link;
    the description is HTML, so we take only its leading text as a summary.
    """
    repos: list[Repo] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        LOGGER.warning("Could not parse trending RSS: %s", exc)
        return repos
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        full_name = Repo.normalize_full_name(link or title)
        if not full_name or "/" not in full_name:
            continue
        desc = _clean_text(item.findtext("description") or "")
        repos.append(
            Repo(
                full_name=full_name,
                description=desc[:200],
                url=link or "",
                sources={"trending-rss"},
            )
        )
    return repos


class TrendingSource:
    """Fetch GitHub Trending via HTML scrape, with optional RSS fallback."""

    name = "trending"

    def __init__(self, client: HttpClient) -> None:
        self.client = client

    def _html_url(self, language: str, since: str) -> str:
        path = TRENDING_BASE
        if language:
            path = f"{TRENDING_BASE}/{urllib.parse.quote(language)}"
        query = urllib.parse.urlencode({"since": since}) if since else ""
        return f"{path}?{query}" if query else path

    def fetch(self, config: Config) -> list[Repo]:
        """Scrape each configured trending language; degrade per-language."""
        repos: list[Repo] = []
        for language in config.trending_languages or [""]:
            label = f"trending:{language}" if language else "trending"
            url = self._html_url(language, config.trending_since)
            try:
                response = self.client.get(url, accept="text/html")
                parsed = parse_trending_html(response.body, source_label="trending")
                LOGGER.debug("Trending %s: %d repos", url, len(parsed))
                repos.extend(parsed)
            except FetchError as exc:
                LOGGER.warning("Trending HTML failed for %s: %s", url, exc)
        return repos

    def fetch_rss(self, config: Config) -> list[Repo]:
        """Fetch the community RSS fallback for each configured language."""
        repos: list[Repo] = []
        for language in config.trending_languages or [""]:
            lang = language or "all"
            url = f"{RSS_BASE}/{config.trending_since}/{lang}.xml"
            try:
                response = self.client.get(url, accept="application/xml")
                parsed = parse_trending_rss(response.body)
                LOGGER.debug("Trending RSS %s: %d repos", url, len(parsed))
                repos.extend(parsed)
            except FetchError as exc:
                LOGGER.warning("Trending RSS failed for %s: %s", url, exc)
        return repos
