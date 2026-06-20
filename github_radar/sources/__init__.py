"""Source plugins: each turns one upstream feed into a list of :class:`Repo`.

Every source is a small function/class that takes an :class:`~github_radar.http.HttpClient`
and a :class:`~github_radar.config.Config` and returns ``list[Repo]``. Sources
must never raise on remote failure — they log and return ``[]`` so the
aggregator can degrade gracefully. The orchestration lives in
:mod:`github_radar.aggregator`.
"""

from .search import SearchSource, build_search_query
from .trending import TrendingSource, parse_trending_html, parse_trending_rss

__all__ = [
    "SearchSource",
    "build_search_query",
    "TrendingSource",
    "parse_trending_html",
    "parse_trending_rss",
]
