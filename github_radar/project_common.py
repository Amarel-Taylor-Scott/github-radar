"""Shared models and utilities for domain-specific GitHub project radars."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
PUBLICATION_SCHEMA = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def days_since(value: str | None, now: datetime, default: int = 9999) -> int:
    parsed = parse_datetime(value)
    if parsed is None:
        return default
    return max((now - parsed).days, 0)


def unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(max(value, low), high)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def normalize_repo(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^https?://(?:www\.)?github\.com/", "", text, flags=re.I)
    text = text.strip("/")
    if text.lower().endswith(".git"):
        text = text[:-4]
    parts = [part for part in text.split("/") if part]
    return f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else ""


def _valid_license(value: str) -> bool:
    return bool(value and value.upper() not in {"NOASSERTION", "OTHER"})


def _percentiles(values: list[float]) -> list[float]:
    """Return tie-aware percentile ranks in [0, 1]."""
    if not values:
        return []
    if max(values) == min(values):
        return [0.5 for _ in values]
    ordered = sorted((value, index) for index, value in enumerate(values))
    output = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[cursor][0]:
            end += 1
        rank = ((cursor + end) / 2) / max(len(ordered) - 1, 1)
        for position in range(cursor, end + 1):
            output[ordered[position][1]] = rank
        cursor = end + 1
    return output


def classify_project(project: "Project") -> str:
    name = project.name.lower()
    description = project.description.lower()
    topics = {topic.lower() for topic in project.topics}
    text = f"{name} {description} {' '.join(sorted(topics))}"
    if project.is_template or "template" in topics or name.endswith("-template"):
        return "template"
    if name.startswith("awesome-") or "awesome-list" in topics or "curated list" in text:
        return "resource-list"
    if any(term in text for term in ("course", "bootcamp", "tutorial", "roadmap", "interview questions")):
        return "education"
    if "dataset" in topics or "dataset" in name or "data set" in description:
        return "dataset"
    if "benchmark" in topics or "benchmark" in name:
        return "benchmark"
    if any(term in topics for term in ("cli", "command-line", "terminal")):
        return "cli"
    if "framework" in topics or "framework" in description:
        return "framework"
    if any(term in topics for term in ("library", "sdk", "api-client")):
        return "library"
    if any(term in topics for term in ("self-hosted", "webapp", "desktop-app", "mobile-app")):
        return "application"
    return "project"


@dataclass
class Project:
    full_name: str
    id: str = ""
    name: str = ""
    owner: str = ""
    html_url: str = ""
    description: str = ""
    homepage: str = ""
    language: str = ""
    topics: list[str] = field(default_factory=list)
    license_spdx: str = ""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    size_kb: int = 0
    created_at: str = ""
    pushed_at: str = ""
    updated_at: str = ""
    default_branch: str = "main"
    owner_type: str = ""
    archived: bool = False
    disabled: bool = False
    fork: bool = False
    is_template: bool = False
    has_issues: bool = False
    has_discussions: bool = False
    has_wiki: bool = False
    has_pages: bool = False
    api_complete: bool = False
    catalogs: list[str] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    query_modes: list[str] = field(default_factory=list)
    matched_topics: list[str] = field(default_factory=list)
    source_confidence: float = 0.0
    project_type: str = "project"
    growth: dict[str, Any] = field(default_factory=dict)
    dimensions: dict[str, float] = field(default_factory=dict)
    catalog_scores: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.full_name = normalize_repo(self.full_name)
        if not self.full_name:
            return
        owner, name = self.full_name.split("/", 1)
        self.owner = self.owner or owner
        self.name = self.name or name
        self.id = self.id or f"repo:{self.full_name.lower()}"
        self.html_url = self.html_url or f"https://github.com/{self.full_name}"
        self.topics = unique(self.topics)
        self.catalogs = unique(self.catalogs)
        self.provenance = unique(self.provenance)
        self.evidence = unique(self.evidence)
        self.query_modes = unique(self.query_modes)
        self.matched_topics = unique(self.matched_topics)

    @classmethod
    def from_api(
        cls,
        payload: dict[str, Any],
        *,
        catalog_id: str = "",
        source_id: str = "",
        mode: str = "",
        topic: str = "",
        source_confidence: float = 0.5,
    ) -> "Project":
        license_data = payload.get("license") or {}
        owner_data = payload.get("owner") or {}
        project = cls(
            full_name=str(payload.get("full_name") or ""),
            name=str(payload.get("name") or ""),
            owner=str(owner_data.get("login") or ""),
            html_url=str(payload.get("html_url") or ""),
            description=str(payload.get("description") or ""),
            homepage=str(payload.get("homepage") or ""),
            language=str(payload.get("language") or ""),
            topics=unique(payload.get("topics") or []),
            license_spdx=str(license_data.get("spdx_id") or ""),
            stars=int(payload.get("stargazers_count") or 0),
            forks=int(payload.get("forks_count") or 0),
            watchers=int(payload.get("subscribers_count") or 0),
            open_issues=int(payload.get("open_issues_count") or 0),
            size_kb=int(payload.get("size") or 0),
            created_at=str(payload.get("created_at") or ""),
            pushed_at=str(payload.get("pushed_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            default_branch=str(payload.get("default_branch") or "main"),
            owner_type=str(owner_data.get("type") or ""),
            archived=bool(payload.get("archived", False)),
            disabled=bool(payload.get("disabled", False)),
            fork=bool(payload.get("fork", False)),
            is_template=bool(payload.get("is_template", False)),
            has_issues=bool(payload.get("has_issues", False)),
            has_discussions=bool(payload.get("has_discussions", False)),
            has_wiki=bool(payload.get("has_wiki", False)),
            has_pages=bool(payload.get("has_pages", False)),
            api_complete="stargazers_count" in payload,
            catalogs=[catalog_id] if catalog_id else [],
            provenance=[source_id] if source_id else [],
            evidence=[f"topic:{topic}"] if topic else [],
            query_modes=[mode] if mode else [],
            matched_topics=[topic] if topic else [],
            source_confidence=source_confidence,
        )
        project.project_type = classify_project(project)
        return project

    def merge(self, other: "Project") -> None:
        if not self.full_name:
            self.full_name = other.full_name
        for attribute in ("stars", "forks", "watchers", "open_issues", "size_kb"):
            setattr(self, attribute, max(int(getattr(self, attribute)), int(getattr(other, attribute))))
        for attribute in (
            "html_url",
            "homepage",
            "language",
            "license_spdx",
            "created_at",
            "pushed_at",
            "updated_at",
            "default_branch",
            "owner_type",
        ):
            if not getattr(self, attribute) and getattr(other, attribute):
                setattr(self, attribute, getattr(other, attribute))
        if len(other.description) > len(self.description):
            self.description = other.description
        self.topics = unique([*self.topics, *other.topics])
        self.catalogs = unique([*self.catalogs, *other.catalogs])
        self.provenance = unique([*self.provenance, *other.provenance])
        self.evidence = unique([*self.evidence, *other.evidence])
        self.query_modes = unique([*self.query_modes, *other.query_modes])
        self.matched_topics = unique([*self.matched_topics, *other.matched_topics])
        self.source_confidence = max(self.source_confidence, other.source_confidence)
        self.archived = self.archived or other.archived
        self.disabled = self.disabled or other.disabled
        self.fork = self.fork or other.fork
        self.is_template = self.is_template or other.is_template
        self.has_issues = self.has_issues or other.has_issues
        self.has_discussions = self.has_discussions or other.has_discussions
        self.has_wiki = self.has_wiki or other.has_wiki
        self.has_pages = self.has_pages or other.has_pages
        self.api_complete = self.api_complete or other.api_complete
        self.project_type = classify_project(self)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_confidence"] = round(self.source_confidence, 3)
        return data


@dataclass(frozen=True)
class QuerySpec:
    id: str
    catalog_id: str
    mode: str
    query: str
    sort: str
    order: str
    max_results: int
    topic: str = ""
    source_confidence: float = 0.5
