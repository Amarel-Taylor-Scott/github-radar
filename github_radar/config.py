"""Configuration: sensible defaults plus optional file/CLI overrides.

The whole point is *zero-config*: ``python -m github_radar`` works out of the
box. A :class:`Config` carries the topic list, star/recency filters, the
rolling window, and which optional sources are enabled. It can be loaded from a
TOML file (stdlib ``tomllib`` on 3.11+) so users can pin their own niche.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

LOGGER = logging.getLogger("github_radar.config")

# The default AI-leaning topic set. Every topic is OR-ed in the search query.
DEFAULT_TOPICS = [
    "llm",
    "ai",
    "machine-learning",
    "agents",
    "rag",
    "llmops",
    "generative-ai",
]


@dataclass
class Config:
    """All knobs for a github-radar run, with AI-feed-friendly defaults."""

    topics: list[str] = field(default_factory=lambda: list(DEFAULT_TOPICS))
    min_stars: int = 100
    # Rolling-window length in days, applied to ``pushed:>`` (recent activity).
    window_days: int = 30
    # Optionally also require the repo was *created* within this many days
    # (catches brand-new breakouts). ``None`` disables the created filter.
    created_within_days: Optional[int] = None
    # How many search results to keep (paginated 100/page, capped at 1000 by GH).
    search_limit: int = 100
    # Trending languages to scrape ("" means the all-languages page).
    trending_languages: list[str] = field(default_factory=lambda: [""])
    trending_since: str = "daily"  # daily | weekly | monthly
    # Optional secondary sources, off by default.
    enable_trending: bool = True
    enable_search: bool = True
    enable_trending_rss: bool = False
    enable_huggingface: bool = False
    enable_arxiv: bool = False
    # Final feed size.
    top_n: int = 50

    def pushed_since(self, now: Optional[datetime] = None) -> str:
        """ISO date (YYYY-MM-DD) for the ``pushed:>`` recency filter."""
        now = now or datetime.now(timezone.utc)
        return (now - timedelta(days=self.window_days)).date().isoformat()

    def created_since(self, now: Optional[datetime] = None) -> Optional[str]:
        """ISO date for the optional ``created:>`` filter, or ``None``."""
        if self.created_within_days is None:
            return None
        now = now or datetime.now(timezone.utc)
        return (now - timedelta(days=self.created_within_days)).date().isoformat()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Build a Config from a parsed config file, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        unknown = set(data) - known
        if unknown:
            LOGGER.warning("Ignoring unknown config keys: %s", ", ".join(sorted(unknown)))
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_toml(cls, path: str) -> "Config":
        """Load a Config from a TOML file (requires Python 3.11+)."""
        try:
            import tomllib
        except ModuleNotFoundError as exc:  # pragma: no cover - 3.10 fallback
            raise RuntimeError(
                "TOML config requires Python 3.11+ (tomllib). "
                "Use CLI flags instead, or upgrade Python."
            ) from exc
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
        # Allow a top-level [github_radar] table or a flat file.
        if "github_radar" in data and isinstance(data["github_radar"], dict):
            data = data["github_radar"]
        return cls.from_dict(data)

    def with_overrides(self, **overrides: Any) -> "Config":
        """Return a copy with non-``None`` overrides applied (CLI > file > default)."""
        clean = {k: v for k, v in overrides.items() if v is not None}
        return replace(self, **clean)
