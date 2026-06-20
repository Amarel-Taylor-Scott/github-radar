"""Core data model shared across every source and output writer.

A single :class:`Repo` dataclass is the lingua franca of github-radar. Each
source normalizes its raw payload into ``Repo`` objects; the ranker scores
them; the writers serialize them. Keeping one flat model (rather than passing
source-specific dicts around) is what makes dedup, merge, and ranking trivial.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """Parse a GitHub ISO-8601 timestamp (``2026-01-18T00:51:51Z``) to UTC.

    Returns ``None`` for falsy or unparseable input rather than raising, so a
    single malformed timestamp can never crash a whole run.
    """
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class Repo:
    """A normalized GitHub repository record.

    Only ``full_name`` is required; every source populates whatever subset of
    fields it can observe. ``full_name`` is the dedup key and is normalized to a
    canonical ``owner/name`` form on construction.
    """

    full_name: str
    name: str = ""
    owner: str = ""
    description: str = ""
    url: str = ""
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    topics: list[str] = field(default_factory=list)
    created_at: Optional[str] = None
    pushed_at: Optional[str] = None
    # Trending-only signals. ``stars_today`` is the per-period gain reported on
    # the trending page; ``sources`` records which feeds surfaced this repo.
    stars_today: Optional[int] = None
    sources: set[str] = field(default_factory=set)
    # Populated by the ranker; kept on the model so writers can emit it.
    score: float = 0.0

    def __post_init__(self) -> None:
        self.full_name = self.normalize_full_name(self.full_name)
        if not self.owner or not self.name:
            owner, _, name = self.full_name.partition("/")
            self.owner = self.owner or owner
            self.name = self.name or name
        if not self.url and self.full_name:
            self.url = f"https://github.com/{self.full_name}"
        # Normalize source string into a set for uniform merge handling.
        if isinstance(self.sources, str):
            self.sources = {self.sources}
        elif not isinstance(self.sources, set):
            self.sources = set(self.sources)

    @staticmethod
    def normalize_full_name(value: str) -> str:
        """Canonicalize ``owner/name`` from a slug, path, or full URL.

        Accepts ``owner/name``, ``/owner/name``, ``https://github.com/owner/name``
        (with optional ``.git`` / trailing slash) and lowercases nothing — repo
        names are case-sensitive on GitHub, but dedup is case-insensitive (see
        :meth:`dedup_key`).
        """
        if not value:
            return ""
        text = value.strip()
        # Strip a leading scheme + host if a full URL was passed.
        text = re.sub(r"^https?://(www\.)?github\.com/", "", text)
        text = text.strip("/")
        if text.endswith(".git"):
            text = text[:-4]
        parts = [p for p in text.split("/") if p]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return text

    @property
    def dedup_key(self) -> str:
        """Case-insensitive key used to merge the same repo across sources."""
        return self.full_name.lower()

    @property
    def created_dt(self) -> Optional[datetime]:
        return _parse_iso8601(self.created_at)

    @property
    def pushed_dt(self) -> Optional[datetime]:
        return _parse_iso8601(self.pushed_at)

    def merge(self, other: "Repo") -> "Repo":
        """Fold ``other`` (the same repo from another source) into ``self``.

        Numeric fields take the maximum (sources disagree; the freshest/biggest
        wins), text fields fill blanks, and the source sets are unioned.
        """
        self.stars = max(self.stars, other.stars)
        self.forks = max(self.forks, other.forks)
        self.open_issues = max(self.open_issues, other.open_issues)
        if other.stars_today is not None:
            self.stars_today = max(self.stars_today or 0, other.stars_today)
        self.description = self.description or other.description
        self.language = self.language or other.language
        self.url = self.url or other.url
        if not self.created_at:
            self.created_at = other.created_at
        if not self.pushed_at:
            self.pushed_at = other.pushed_at
        self.topics = sorted(set(self.topics) | set(other.topics))
        self.sources |= other.sources
        return self

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable view (``sources`` as a sorted list, score rounded)."""
        data = asdict(self)
        data["sources"] = sorted(self.sources)
        data["score"] = round(self.score, 4)
        return data

    @classmethod
    def from_search_item(cls, item: dict[str, Any]) -> "Repo":
        """Build a ``Repo`` from a GitHub Search API ``items[]`` entry."""
        owner = (item.get("owner") or {}).get("login", "")
        return cls(
            full_name=item.get("full_name", ""),
            name=item.get("name", ""),
            owner=owner,
            description=item.get("description") or "",
            url=item.get("html_url", ""),
            language=item.get("language"),
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            open_issues=int(item.get("open_issues_count") or 0),
            topics=list(item.get("topics") or []),
            created_at=item.get("created_at"),
            pushed_at=item.get("pushed_at"),
            sources={"search"},
        )
