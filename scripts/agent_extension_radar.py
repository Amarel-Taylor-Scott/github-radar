#!/usr/bin/env python3
"""Build daily, momentum-aware catalogs of AI-agent extensions.

The collector is intentionally standard-library only. It combines trusted
marketplace manifests, explicit repository seeds, GitHub repository search, and
GitHub code search; normalizes everything into one item model; stores compact
daily repository snapshots; and publishes Markdown, JSON, and a static HTML
index.

Momentum is measured at repository level because GitHub does not expose stars
for an individual SKILL.md or plugin subdirectory. Component records retain the
exact path and provenance so the limitation is visible rather than hidden.
"""

from __future__ import annotations

import argparse
import base64
import fnmatch
import html as html_lib
import json
import logging
import math
import os
import re
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from github_radar.http import FetchError, HttpClient  # noqa: E402

LOGGER = logging.getLogger("agent_extension_radar")
API_ROOT = "https://api.github.com"
SCHEMA_VERSION = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def days_since(value: str | None, now: datetime, default: int = 9999) -> int:
    parsed = parse_datetime(value)
    if parsed is None:
        return default
    return max((now - parsed).days, 0)


def unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(max(value, low), high)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def github_repo_from_url(value: str | None) -> Optional[str]:
    """Extract owner/repository from HTTPS, SSH, or git GitHub URLs."""
    if not value:
        return None
    text = str(value).strip()
    ssh = re.search(r"git@github\.com:([^/]+)/([^/#?]+)", text, re.I)
    web = re.search(r"https?://(?:www\.)?github\.com/([^/]+)/([^/#?]+)", text, re.I)
    match = ssh or web
    if not match:
        return None
    owner, repository = match.group(1), match.group(2)
    repository = re.sub(r"\.git$", "", repository, flags=re.I)
    return f"{owner}/{repository}" if owner and repository else None


def github_source_url(repo: str, ref: str | None = None, path: str | None = None) -> str:
    base = f"https://github.com/{repo}"
    if path:
        return f"{base}/tree/{ref or 'main'}/{path.strip('/')}"
    return base


def component_root(kind: str, path: str | None) -> str:
    """Normalize a manifest/file path to the component root for deduplication."""
    cleaned = (path or "").strip().strip("/")
    if not cleaned:
        return "@repository"
    parts = list(PurePosixPath(cleaned).parts)
    lowered = [part.lower() for part in parts]
    if kind == "skill" and lowered[-1] == "skill.md":
        return "/".join(parts[:-1]) or "@repository"
    if kind == "plugin":
        for marker in (".claude-plugin", ".codex-plugin"):
            if marker in lowered:
                index = lowered.index(marker)
                if index + 1 < len(parts) and lowered[index + 1] in {
                    "plugin.json",
                    "marketplace.json",
                }:
                    return "/".join(parts[:index]) or "@repository"
    return cleaned


def item_id(kind: str, repo: str, path: str | None, name: str) -> str:
    root = component_root(kind, path)
    if root == "@repository" and kind not in {"tool", "agent", "framework"}:
        root = name.strip().lower() or root
    return f"{kind}:{repo.lower()}:{root.lower()}"


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the small, top-level YAML subset used by SKILL.md frontmatter."""
    normalized = text.lstrip("\ufeff")
    lines = normalized.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return {}

    result: dict[str, str] = {}
    current_key: Optional[str] = None
    block: list[str] = []

    def flush() -> None:
        nonlocal current_key, block
        if current_key is not None and block:
            result[current_key] = " ".join(piece.strip() for piece in block if piece.strip())
        current_key, block = None, []

    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if match:
            flush()
            key = match.group(1).lower()
            raw = match.group(2).strip()
            if raw in {"|", ">"}:
                current_key = key
                continue
            result[key] = _unquote(raw)
        elif current_key is not None and (line.startswith(" ") or line.startswith("\t")):
            block.append(line)
    flush()
    return result


@dataclass
class RepoInfo:
    full_name: str
    html_url: str = ""
    description: str = ""
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    watchers: int = 0
    created_at: str = ""
    pushed_at: str = ""
    updated_at: str = ""
    language: str = ""
    topics: list[str] = field(default_factory=list)
    license_spdx: str = ""
    archived: bool = False
    default_branch: str = "main"
    owner_type: str = ""
    api_complete: bool = False

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "RepoInfo":
        license_data = payload.get("license") or {}
        owner_data = payload.get("owner") or {}
        return cls(
            full_name=str(payload.get("full_name") or ""),
            html_url=str(payload.get("html_url") or ""),
            description=str(payload.get("description") or ""),
            stars=int(payload.get("stargazers_count") or 0),
            forks=int(payload.get("forks_count") or 0),
            open_issues=int(payload.get("open_issues_count") or 0),
            watchers=int(payload.get("subscribers_count") or payload.get("watchers_count") or 0),
            created_at=str(payload.get("created_at") or ""),
            pushed_at=str(payload.get("pushed_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            language=str(payload.get("language") or ""),
            topics=unique(payload.get("topics") or []),
            license_spdx=str(license_data.get("spdx_id") or ""),
            archived=bool(payload.get("archived", False)),
            default_branch=str(payload.get("default_branch") or "main"),
            owner_type=str(owner_data.get("type") or ""),
            api_complete="stargazers_count" in payload,
        )

    def merge(self, other: "RepoInfo") -> None:
        if not self.full_name:
            self.full_name = other.full_name
        for attribute in ("stars", "forks", "open_issues", "watchers"):
            setattr(self, attribute, max(getattr(self, attribute), getattr(other, attribute)))
        for attribute in (
            "html_url",
            "created_at",
            "pushed_at",
            "updated_at",
            "language",
            "license_spdx",
            "default_branch",
            "owner_type",
        ):
            if not getattr(self, attribute) and getattr(other, attribute):
                setattr(self, attribute, getattr(other, attribute))
        if len(other.description) > len(self.description):
            self.description = other.description
        self.topics = unique([*self.topics, *other.topics])
        self.archived = self.archived or other.archived
        self.api_complete = self.api_complete or other.api_complete


@dataclass
class ExtensionItem:
    id: str
    name: str
    kind: str
    repo: RepoInfo
    path: str = ""
    source_url: str = ""
    description: str = ""
    platforms: list[str] = field(default_factory=list)
    catalogs: list[str] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    category: str = ""
    author: str = ""
    trust: float = 0.0
    manifest_valid: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    growth: dict[str, Any] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)

    def merge(self, other: "ExtensionItem") -> None:
        self.repo.merge(other.repo)
        self.platforms = unique([*self.platforms, *other.platforms])
        self.catalogs = unique([*self.catalogs, *other.catalogs])
        self.provenance = unique([*self.provenance, *other.provenance])
        self.evidence = unique([*self.evidence, *other.evidence])
        self.trust = max(self.trust, other.trust)
        self.manifest_valid = self.manifest_valid or other.manifest_valid
        if len(other.description) > len(self.description):
            self.description = other.description
        for attribute in ("source_url", "path", "category", "author"):
            if not getattr(self, attribute) and getattr(other, attribute):
                setattr(self, attribute, getattr(other, attribute))
        self.metadata.update({key: value for key, value in other.metadata.items() if value})

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
            "platforms": self.platforms,
            "catalogs": self.catalogs,
            "repo": asdict(self.repo),
            "path": self.path,
            "source_url": self.source_url,
            "provenance": self.provenance,
            "evidence": self.evidence,
            "category": self.category,
            "author": self.author,
            "trust": round(self.trust, 3),
            "manifest_valid": self.manifest_valid,
            "metadata": self.metadata,
            "growth": self.growth,
            "scores": self.scores,
        }


class GitHubAPI:
    """Small cached wrapper around the GitHub REST endpoints used here."""

    def __init__(self, client: HttpClient) -> None:
        self.client = client
        self.repo_cache: dict[str, RepoInfo] = {}
        self.tree_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self.content_cache: dict[tuple[str, str, str], str] = {}

    def json_url(self, url: str) -> Any:
        return self.client.get(url, accept="application/vnd.github+json").json()

    def repository(self, full_name: str) -> Optional[RepoInfo]:
        key = full_name.lower()
        if key in self.repo_cache:
            return self.repo_cache[key]
        try:
            payload = self.json_url(f"{API_ROOT}/repos/{urllib.parse.quote(full_name, safe='/')}")
            repo = RepoInfo.from_api(payload)
            self.repo_cache[key] = repo
            return repo
        except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
            LOGGER.warning("Repository metadata failed for %s: %s", full_name, exc)
            return None

    def tree(self, full_name: str, ref: str) -> list[dict[str, Any]]:
        key = (full_name.lower(), ref)
        if key in self.tree_cache:
            return self.tree_cache[key]
        encoded_ref = urllib.parse.quote(ref, safe="")
        url = f"{API_ROOT}/repos/{urllib.parse.quote(full_name, safe='/')}/git/trees/{encoded_ref}?recursive=1"
        try:
            payload = self.json_url(url)
            tree = payload.get("tree", []) if isinstance(payload, dict) else []
            result = [entry for entry in tree if isinstance(entry, dict)]
            self.tree_cache[key] = result
            if payload.get("truncated"):
                LOGGER.warning("Recursive tree was truncated for %s", full_name)
            return result
        except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
            LOGGER.warning("Tree scan failed for %s@%s: %s", full_name, ref, exc)
            return []

    def content(self, full_name: str, path: str, ref: str) -> str:
        key = (full_name.lower(), path, ref)
        if key in self.content_cache:
            return self.content_cache[key]
        encoded_path = urllib.parse.quote(path, safe="/")
        params = urllib.parse.urlencode({"ref": ref})
        url = f"{API_ROOT}/repos/{urllib.parse.quote(full_name, safe='/')}/contents/{encoded_path}?{params}"
        try:
            payload = self.json_url(url)
            if not isinstance(payload, dict) or payload.get("encoding") != "base64":
                return ""
            raw = base64.b64decode(str(payload.get("content") or ""), validate=False)
            text = raw.decode("utf-8", errors="replace")
            self.content_cache[key] = text
            return text
        except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
            LOGGER.debug("Content fetch failed for %s/%s: %s", full_name, path, exc)
            return ""

    def search_repositories(
        self, query: str, limit: int, *, sort: str = "stars", order: str = "desc"
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1
        while len(results) < limit:
            per_page = min(100, limit - len(results))
            params = urllib.parse.urlencode(
                {"q": query, "sort": sort, "order": order, "per_page": per_page, "page": page}
            )
            try:
                payload = self.json_url(f"{API_ROOT}/search/repositories?{params}")
            except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
                LOGGER.warning("Repository search failed for %r: %s", query, exc)
                break
            items = payload.get("items", []) if isinstance(payload, dict) else []
            page_items = [item for item in items if isinstance(item, dict) and item.get("full_name")]
            results.extend(page_items)
            if len(page_items) < per_page or payload.get("incomplete_results"):
                break
            page += 1
        return results[:limit]

    def search_code(self, query: str, limit: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1
        while len(results) < limit:
            per_page = min(100, limit - len(results))
            params = urllib.parse.urlencode({"q": query, "per_page": per_page, "page": page})
            try:
                payload = self.json_url(f"{API_ROOT}/search/code?{params}")
            except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
                LOGGER.warning("Code search failed for %r: %s", query, exc)
                break
            items = payload.get("items", []) if isinstance(payload, dict) else []
            page_items = [item for item in items if isinstance(item, dict) and item.get("repository")]
            results.extend(page_items)
            if len(page_items) < per_page or payload.get("incomplete_results"):
                break
            page += 1
        return results[:limit]


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("configuration root must be an object")
    if int(payload.get("schema_version", 0)) != SCHEMA_VERSION:
        raise ValueError(f"configuration schema_version must be {SCHEMA_VERSION}")
    catalogs = payload.get("catalogs")
    if not isinstance(catalogs, list) or not catalogs:
        raise ValueError("configuration must define at least one catalog")
    catalog_ids = [str(item.get("id") or "") for item in catalogs if isinstance(item, dict)]
    if any(not value for value in catalog_ids) or len(catalog_ids) != len(set(catalog_ids)):
        raise ValueError("catalog IDs must be non-empty and unique")
    defaults = {
        "output_dir": "feeds/agent-extensions",
        "site_dir": "docs/agent-extensions",
        "history_days": 45,
        "discovery_window_days": 120,
        "max_repository_enrichments": 240,
        "max_metadata_fetches": 120,
        "leaderboard_size": 25,
        "max_items_per_repo_per_leaderboard": 8,
        "include_all_catalog_id": "agent-extensions",
    }
    return {**defaults, **payload}


def resolve_marketplace_source(
    plugin: dict[str, Any], marketplace_repo: str
) -> tuple[str, str, str, str]:
    """Return repository, component path, ref, and source URL."""
    source = plugin.get("source")
    repo: Optional[str] = None
    path = ""
    ref = "main"
    if isinstance(source, str):
        repo = marketplace_repo
        path = source.removeprefix("./").strip("/")
    elif isinstance(source, dict):
        repo = github_repo_from_url(str(source.get("url") or source.get("repository") or ""))
        path = str(source.get("path") or "").removeprefix("./").strip("/")
        ref = str(source.get("ref") or "main")
    if repo is None:
        repo = github_repo_from_url(str(plugin.get("homepage") or ""))
    repo = repo or marketplace_repo
    return repo, path, ref, github_source_url(repo, ref, path)


class Collector:
    def __init__(self, config: dict[str, Any], github: GitHubAPI, now: datetime) -> None:
        self.config = config
        self.github = github
        self.now = now
        self.items: dict[str, ExtensionItem] = {}
        self.metadata_fetches = 0

    def _add(self, item: ExtensionItem) -> None:
        existing = self.items.get(item.id)
        if existing is None:
            self.items[item.id] = item
        else:
            existing.merge(item)

    def _content(self, repo: str, path: str, ref: str) -> str:
        if self.metadata_fetches >= int(self.config["max_metadata_fetches"]):
            return ""
        self.metadata_fetches += 1
        return self.github.content(repo, path, ref)

    def collect(self) -> list[ExtensionItem]:
        self._collect_marketplaces()
        self._collect_repository_seeds()
        self._collect_code_queries()
        self._collect_repository_queries()
        self._enrich_repositories()
        all_catalog = str(self.config.get("include_all_catalog_id") or "")
        if all_catalog:
            for item in self.items.values():
                item.catalogs = unique([*item.catalogs, all_catalog])
        return list(self.items.values())

    def _collect_marketplaces(self) -> None:
        for spec in self.config.get("marketplaces", []):
            if not isinstance(spec, dict):
                continue
            marketplace_id = str(spec.get("id") or "marketplace")
            marketplace_repo = str(spec.get("repository") or "")
            try:
                manifest = self.github.json_url(str(spec["url"]))
            except (KeyError, FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
                LOGGER.warning("Marketplace %s failed: %s", marketplace_id, exc)
                continue
            plugins = manifest.get("plugins", []) if isinstance(manifest, dict) else []
            for plugin in plugins:
                if not isinstance(plugin, dict) or not plugin.get("name"):
                    continue
                repo_name, path, ref, source_url = resolve_marketplace_source(plugin, marketplace_repo)
                repo = RepoInfo(full_name=repo_name, html_url=github_source_url(repo_name))
                author_data = plugin.get("author") or {}
                author = str(author_data.get("name") or "") if isinstance(author_data, dict) else str(author_data)
                name = str(plugin.get("displayName") or plugin.get("name"))
                kind = str(spec.get("kind") or "plugin")
                item = ExtensionItem(
                    id=item_id(kind, repo_name, path, name),
                    name=name,
                    kind=kind,
                    repo=repo,
                    path=path,
                    source_url=source_url,
                    description=str(plugin.get("description") or ""),
                    platforms=unique(spec.get("platforms") or []),
                    catalogs=unique(spec.get("catalogs") or []),
                    provenance=[f"marketplace:{marketplace_id}"],
                    evidence=["marketplace-entry", "manifest-validated"],
                    category=str(plugin.get("category") or ""),
                    author=author,
                    trust=float(spec.get("trust", 0.8)),
                    manifest_valid=True,
                    metadata={
                        "marketplace": marketplace_id,
                        "marketplace_repository": marketplace_repo,
                        "homepage": str(plugin.get("homepage") or ""),
                        "ref": ref,
                    },
                )
                self._add(item)

    def _collect_repository_seeds(self) -> None:
        for spec in self.config.get("repository_seeds", []):
            if not isinstance(spec, dict) or not spec.get("repository"):
                continue
            full_name = str(spec["repository"])
            repo = self.github.repository(full_name)
            if repo is None:
                continue
            ref = str(spec.get("ref") or repo.default_branch or "main")
            patterns = unique(spec.get("include") or ["**/SKILL.md"])
            max_artifacts = int(spec.get("max_artifacts", 100))
            matched = 0
            for entry in self.github.tree(full_name, ref):
                path = str(entry.get("path") or "")
                if entry.get("type") != "blob" or not any(fnmatch.fnmatch(path, pattern) for pattern in patterns):
                    continue
                kind = str(spec.get("kind") or "skill")
                text = self._content(full_name, path, ref)
                metadata = parse_frontmatter(text) if kind == "skill" else {}
                name = metadata.get("name") or PurePosixPath(component_root(kind, path)).name
                description = metadata.get("description") or repo.description
                item = ExtensionItem(
                    id=item_id(kind, full_name, path, name),
                    name=name,
                    kind=kind,
                    repo=RepoInfo(**asdict(repo)),
                    path=path,
                    source_url=github_source_url(full_name, ref, component_root(kind, path)),
                    description=description,
                    platforms=unique(spec.get("platforms") or []),
                    catalogs=unique(spec.get("catalogs") or []),
                    provenance=[f"seed:{spec.get('id') or full_name}"],
                    evidence=[f"path:{path}"] + (["valid-skill-frontmatter"] if metadata else []),
                    trust=float(spec.get("trust", 0.9)),
                    manifest_valid=bool(metadata.get("name") and metadata.get("description")),
                    metadata=metadata,
                )
                self._add(item)
                matched += 1
                if matched >= max_artifacts:
                    break

    def _collect_code_queries(self) -> None:
        for spec in self.config.get("code_queries", []):
            if not isinstance(spec, dict) or not spec.get("query"):
                continue
            query_id = str(spec.get("id") or "code-search")
            for result in self.github.search_code(str(spec["query"]), int(spec.get("max_results", 30))):
                repo_payload = result.get("repository") or {}
                if not isinstance(repo_payload, dict) or not repo_payload.get("full_name"):
                    continue
                path = str(result.get("path") or "")
                path_regex = str(spec.get("path_regex") or "")
                if path_regex and not re.search(path_regex, path, re.I):
                    continue
                repo = RepoInfo.from_api(repo_payload)
                kind = str(spec.get("kind") or "skill")
                text = self._content(repo.full_name, path, repo.default_branch or "main")
                metadata: dict[str, Any] = {}
                if kind == "skill":
                    metadata = parse_frontmatter(text)
                elif kind == "plugin" and text:
                    try:
                        parsed = json.loads(text)
                        metadata = parsed if isinstance(parsed, dict) else {}
                    except json.JSONDecodeError:
                        metadata = {}
                name = str(metadata.get("displayName") or metadata.get("name") or PurePosixPath(component_root(kind, path)).name or repo.full_name.split("/")[-1])
                description = str(metadata.get("description") or repo.description)
                item = ExtensionItem(
                    id=item_id(kind, repo.full_name, path, name),
                    name=name,
                    kind=kind,
                    repo=repo,
                    path=path,
                    source_url=github_source_url(repo.full_name, repo.default_branch, component_root(kind, path)),
                    description=description,
                    platforms=unique(spec.get("platforms") or []),
                    catalogs=unique(spec.get("catalogs") or []),
                    provenance=[f"code-search:{query_id}"],
                    evidence=[f"path:{path}"] + (["metadata-parsed"] if metadata else []),
                    trust=float(spec.get("trust", 0.4)),
                    manifest_valid=bool(metadata),
                    metadata=metadata,
                )
                self._add(item)

    def _collect_repository_queries(self) -> None:
        cutoff = (self.now - timedelta(days=int(self.config["discovery_window_days"]))).date().isoformat()
        for spec in self.config.get("repository_queries", []):
            if not isinstance(spec, dict) or not spec.get("query"):
                continue
            query_id = str(spec.get("id") or "repository-search")
            query = str(spec["query"]).strip()
            if "archived:" not in query:
                query += " archived:false"
            if "pushed:" not in query and not spec.get("include_inactive", False):
                query += f" pushed:>={cutoff}"
            results = self.github.search_repositories(
                query,
                int(spec.get("max_results", 30)),
                sort=str(spec.get("sort") or "stars"),
                order=str(spec.get("order") or "desc"),
            )
            for payload in results:
                repo = RepoInfo.from_api(payload)
                kind = str(spec.get("kind") or "tool")
                name = str(spec.get("name_prefix") or "") + repo.full_name.split("/")[-1]
                item = ExtensionItem(
                    id=item_id(kind, repo.full_name, "", name),
                    name=name,
                    kind=kind,
                    repo=repo,
                    source_url=repo.html_url or github_source_url(repo.full_name),
                    description=repo.description,
                    platforms=unique(spec.get("platforms") or []),
                    catalogs=unique(spec.get("catalogs") or []),
                    provenance=[f"repository-search:{query_id}"],
                    evidence=[f"query:{query}"],
                    trust=float(spec.get("trust", 0.3)),
                    manifest_valid=False,
                    metadata={"query_id": query_id},
                )
                self._add(item)

    def _enrich_repositories(self) -> None:
        priority: dict[str, tuple[float, int]] = {}
        for item in self.items.values():
            existing = priority.get(item.repo.full_name, (0.0, 0))
            priority[item.repo.full_name] = (max(existing[0], item.trust), max(existing[1], item.repo.stars))
        ordered = sorted(priority, key=lambda name: priority[name], reverse=True)
        allowed = set(ordered[: int(self.config["max_repository_enrichments"])])
        for full_name in allowed:
            needs_fetch = any(
                item.repo.full_name == full_name and not item.repo.api_complete
                for item in self.items.values()
            )
            if not needs_fetch:
                continue
            enriched = self.github.repository(full_name)
            if enriched is None:
                continue
            for item in self.items.values():
                if item.repo.full_name == full_name:
                    item.repo.merge(enriched)


def load_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "days": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("History file is unreadable; starting a new history")
        return {"schema_version": SCHEMA_VERSION, "days": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("days"), dict):
        return {"schema_version": SCHEMA_VERSION, "days": {}}
    return payload


def _history_baseline(
    history: dict[str, Any], full_name: str, target: date, today: date
) -> tuple[Optional[date], Optional[dict[str, Any]]]:
    candidates: list[tuple[date, dict[str, Any]]] = []
    for key, records in history.get("days", {}).items():
        try:
            day = date.fromisoformat(key)
        except (TypeError, ValueError):
            continue
        if day >= today or day > target or not isinstance(records, dict):
            continue
        record = records.get(full_name)
        if isinstance(record, dict):
            candidates.append((day, record))
    return max(candidates, key=lambda pair: pair[0]) if candidates else (None, None)


def calculate_growth(repo: RepoInfo, history: dict[str, Any], now: datetime) -> dict[str, Any]:
    today = now.date()
    result: dict[str, Any] = {
        "delta_1d": None,
        "delta_7d": None,
        "delta_30d": None,
        "stars_per_day": 0.0,
        "acceleration": 0.0,
        "relative_7d": None,
        "signal_source": "lifetime-estimate",
    }
    baselines: dict[int, tuple[Optional[date], Optional[dict[str, Any]]]] = {}
    for window in (1, 7, 14, 30):
        baselines[window] = _history_baseline(history, repo.full_name, today - timedelta(days=window), today)
    for window in (1, 7, 30):
        baseline_day, baseline = baselines[window]
        if baseline_day is None or baseline is None:
            continue
        elapsed = max((today - baseline_day).days, 1)
        delta = repo.stars - int(baseline.get("stars") or 0)
        result[f"delta_{window}d"] = delta
        result[f"actual_days_{window}d"] = elapsed
    seven_day, seven = baselines[7]
    fourteen_day, fourteen = baselines[14]
    if seven_day is not None and seven is not None:
        elapsed = max((today - seven_day).days, 1)
        result["stars_per_day"] = max((repo.stars - int(seven.get("stars") or 0)) / elapsed, 0.0)
        previous_stars = max(int(seven.get("stars") or 0), 1)
        result["relative_7d"] = (repo.stars - previous_stars) / previous_stars
        result["signal_source"] = "observed-history"
        if fourteen_day is not None and fourteen is not None and fourteen_day < seven_day:
            previous_elapsed = max((seven_day - fourteen_day).days, 1)
            previous_velocity = (int(seven.get("stars") or 0) - int(fourteen.get("stars") or 0)) / previous_elapsed
            result["acceleration"] = result["stars_per_day"] - previous_velocity
    elif result["delta_1d"] is not None:
        elapsed = max(int(result.get("actual_days_1d") or 1), 1)
        result["stars_per_day"] = max(float(result["delta_1d"]) / elapsed, 0.0)
        result["signal_source"] = "observed-history"
    else:
        age = max(days_since(repo.created_at, now, default=3650), 7)
        result["stars_per_day"] = repo.stars / age
    return result


def update_history(
    history: dict[str, Any], items: list[ExtensionItem], now: datetime, keep_days: int
) -> dict[str, Any]:
    days = history.setdefault("days", {})
    today = now.date()
    repository_records: dict[str, dict[str, Any]] = {}
    for item in items:
        repository_records[item.repo.full_name] = {
            "stars": item.repo.stars,
            "forks": item.repo.forks,
            "pushed_at": item.repo.pushed_at,
        }
    days[today.isoformat()] = repository_records
    cutoff = today - timedelta(days=keep_days)
    for key in list(days):
        try:
            if date.fromisoformat(key) < cutoff:
                del days[key]
        except (TypeError, ValueError):
            del days[key]
    history["schema_version"] = SCHEMA_VERSION
    history["updated_at"] = now.isoformat()
    return history


def _percentiles(values: list[float]) -> list[float]:
    if not values:
        return []
    if max(values) == min(values):
        return [0.5 for _ in values]
    ordered = sorted((value, index) for index, value in enumerate(values))
    output = [0.0] * len(values)
    position = 0
    while position < len(ordered):
        end = position
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[position][0]:
            end += 1
        rank = ((position + end) / 2) / max(len(ordered) - 1, 1)
        for cursor in range(position, end + 1):
            output[ordered[cursor][1]] = rank
        position = end + 1
    return output


def score_items(items: list[ExtensionItem], history: dict[str, Any], now: datetime) -> None:
    rows: list[dict[str, float]] = []
    for item in items:
        item.growth = calculate_growth(item.repo, history, now)
        age_days = max(days_since(item.repo.created_at, now, default=3650), 1)
        idle_days = days_since(item.repo.pushed_at, now)
        updated_days = days_since(item.repo.updated_at, now)
        quality = (
            0.18 * bool(item.description)
            + 0.12 * bool(item.repo.license_spdx and item.repo.license_spdx != "NOASSERTION")
            + 0.10 * bool(item.repo.topics)
            + 0.18 * item.manifest_valid
            + 0.12 * bool(item.path or item.source_url)
            + 0.12 * (not item.repo.archived)
            + 0.10 * min(len(item.provenance), 2) / 2
            + 0.08 * item.repo.api_complete
        )
        rows.append(
            {
                "popularity": math.log1p(item.repo.stars) + 0.35 * math.log1p(item.repo.forks),
                "velocity": math.log1p(max(float(item.growth.get("stars_per_day") or 0.0), 0.0)),
                "acceleration": math.log1p(max(float(item.growth.get("acceleration") or 0.0), 0.0)),
                "freshness": math.exp(-idle_days / 30.0),
                "maintenance": 0.65 * math.exp(-idle_days / 30.0) + 0.35 * math.exp(-updated_days / 60.0),
                "quality": quality,
                "trust": clamp(item.trust, 0.0, 1.0),
                "newness": math.exp(-age_days / 120.0),
            }
        )
    normalized: dict[str, list[float]] = {
        key: _percentiles([row[key] for row in rows])
        for key in ("popularity", "velocity", "acceleration", "freshness", "maintenance", "quality", "newness")
    }
    for index, item in enumerate(items):
        n = {key: values[index] for key, values in normalized.items()}
        trust = rows[index]["trust"]
        popular = 100 * (
            0.55 * n["popularity"]
            + 0.12 * n["velocity"]
            + 0.08 * n["freshness"]
            + 0.08 * n["maintenance"]
            + 0.09 * n["quality"]
            + 0.08 * trust
        )
        momentum = 100 * (
            0.15 * n["popularity"]
            + 0.42 * n["velocity"]
            + 0.18 * n["acceleration"]
            + 0.10 * n["freshness"]
            + 0.07 * n["quality"]
            + 0.08 * trust
        )
        rising = 100 * (
            0.08 * n["popularity"]
            + 0.38 * n["velocity"]
            + 0.20 * n["acceleration"]
            + 0.14 * n["newness"]
            + 0.08 * n["freshness"]
            + 0.05 * n["quality"]
            + 0.07 * trust
        )
        penalty = 0.0
        if item.repo.archived:
            penalty += 35.0
        if days_since(item.repo.pushed_at, now) > 365:
            penalty += 12.0
        if not item.repo.api_complete:
            penalty += 4.0
        item.scores = {
            "popular": round(clamp(popular - penalty), 2),
            "momentum": round(clamp(momentum - penalty), 2),
            "rising": round(clamp(rising - penalty), 2),
            "overall": round(clamp(0.32 * popular + 0.40 * momentum + 0.28 * rising - penalty), 2),
        }


def signal_text(item: ExtensionItem, now: datetime) -> str:
    signals: list[str] = []
    delta = item.growth.get("delta_7d")
    if delta is not None:
        signals.append(f"{int(delta):+d} stars/7d")
    else:
        velocity = float(item.growth.get("stars_per_day") or 0.0)
        if velocity > 0:
            signals.append(f"~{velocity:.1f} stars/day lifetime")
    age = days_since(item.repo.created_at, now)
    if age <= 120:
        signals.append(f"new ({age}d)")
    idle = days_since(item.repo.pushed_at, now)
    if idle <= 14:
        signals.append(f"pushed {idle}d ago")
    if item.trust >= 0.9:
        signals.append("official/reviewed source")
    if len(item.provenance) > 1:
        signals.append(f"{len(item.provenance)} sources")
    return "; ".join(signals[:3]) or "repository activity and quality"


def diverse_top(
    items: list[ExtensionItem], score: str, limit: int, max_per_repo: int
) -> list[ExtensionItem]:
    counts: dict[str, int] = {}
    selected: list[ExtensionItem] = []
    for item in sorted(items, key=lambda value: value.scores.get(score, 0.0), reverse=True):
        count = counts.get(item.repo.full_name, 0)
        if count >= max_per_repo:
            continue
        selected.append(item)
        counts[item.repo.full_name] = count + 1
        if len(selected) >= limit:
            break
    return selected


def catalog_leaderboards(
    items: list[ExtensionItem], catalog_id: str, config: dict[str, Any], now: datetime
) -> dict[str, list[ExtensionItem]]:
    eligible = [item for item in items if catalog_id in item.catalogs]
    limit = int(config["leaderboard_size"])
    diversity = int(config["max_items_per_repo_per_leaderboard"])
    new_items = [item for item in eligible if days_since(item.repo.created_at, now) <= 180]
    return {
        "high_momentum": diverse_top(eligible, "momentum", limit, diversity),
        "rising": diverse_top(eligible, "rising", limit, diversity),
        "popular": diverse_top(eligible, "popular", limit, diversity),
        "new": diverse_top(new_items, "rising", limit, diversity),
        "overall": diverse_top(eligible, "overall", max(limit * 4, 100), diversity),
    }


def render_table(items: list[ExtensionItem], score: str, now: datetime) -> str:
    lines = [
        "| # | Extension | Kind | Platforms | Stars | Δ7d | Score | Why it surfaced |",
        "|--:|:----------|:-----|:----------|------:|----:|------:|:-----------------|",
    ]
    for index, item in enumerate(items, 1):
        url = item.source_url or item.repo.html_url
        linked = f"[{markdown_escape(item.name)}]({url})" if url else markdown_escape(item.name)
        delta = item.growth.get("delta_7d")
        delta_text = "—" if delta is None else f"{int(delta):+d}"
        lines.append(
            "| {rank} | {name} | {kind} | {platforms} | {stars:,} | {delta} | {score:.1f} | {signal} |".format(
                rank=index,
                name=linked,
                kind=markdown_escape(item.kind),
                platforms=markdown_escape(", ".join(item.platforms)),
                stars=item.repo.stars,
                delta=delta_text,
                score=item.scores.get(score, 0.0),
                signal=markdown_escape(signal_text(item, now)),
            )
        )
    return "\n".join(lines)


def render_catalog_markdown(
    catalog: dict[str, Any], boards: dict[str, list[ExtensionItem]], generated_at: str, now: datetime
) -> str:
    title = str(catalog.get("title") or catalog["id"])
    description = str(catalog.get("description") or "")
    sections = [
        ("High momentum", "momentum", boards["high_momentum"]),
        ("Up and coming", "rising", boards["rising"]),
        ("Most popular", "popular", boards["popular"]),
        ("New projects", "rising", boards["new"]),
    ]
    output = [
        f"# {title}",
        "",
        description,
        "",
        f"_Generated {generated_at}. Rankings are regenerated daily._",
        "",
        "> Momentum belongs to the GitHub repository. A skill or plugin inside a monorepo inherits that repository signal; its exact path and provenance remain in the JSON record.",
        "",
    ]
    for heading, score, values in sections:
        output.extend([f"## {heading}", "", render_table(values, score, now), ""])
    output.extend(
        [
            "## Ranking model",
            "",
            "The transparent score blends log-scaled popularity, observed 1/7/30-day star growth, growth acceleration, repository freshness, maintenance, artifact quality, source trust, and an age-adjusted new-project signal. Before enough snapshots exist, velocity is explicitly labeled as a lifetime estimate.",
            "",
        ]
    )
    return "\n".join(output)


def render_html(items: list[ExtensionItem], catalogs: list[dict[str, Any]], generated_at: str, now: datetime) -> str:
    payload = json.dumps([item.to_dict() for item in items], ensure_ascii=False).replace("</", "<\\/")
    catalog_payload = json.dumps(catalogs, ensure_ascii=False).replace("</", "<\\/")
    template = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Extension Radar</title>
<style>
:root{color-scheme:dark;--bg:#090b12;--panel:#111522;--muted:#9aa6bc;--line:#25304a;--accent:#8b9cff;--text:#eef2ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#182044 0,transparent 34%),var(--bg);color:var(--text);font:15px/1.5 ui-sans-serif,system-ui,sans-serif}
main{max-width:1500px;margin:auto;padding:42px 24px 80px}h1{font-size:clamp(34px,5vw,66px);line-height:1;margin:0 0 14px}.lede{color:var(--muted);max-width:850px;font-size:18px}
.controls{display:grid;grid-template-columns:minmax(260px,2fr) repeat(3,minmax(160px,1fr));gap:12px;margin:30px 0 20px;position:sticky;top:0;padding:14px 0;background:linear-gradient(var(--bg) 70%,transparent);z-index:3}
input,select{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:12px;color:var(--text);padding:12px 14px;font:inherit}.stats{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.pill{background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:7px 12px;color:var(--muted)}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:16px;background:rgba(17,21,34,.9)}table{border-collapse:collapse;width:100%;min-width:1050px}th,td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.07em;background:#101522;position:sticky;top:76px}tr:hover td{background:#151b2c}a{color:#b8c2ff;text-decoration:none}a:hover{text-decoration:underline}.score{font-variant-numeric:tabular-nums;font-weight:700;color:#d9deff}.desc{max-width:460px;color:var(--muted)}.tag{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:2px 7px;margin:1px 3px 1px 0;font-size:12px;color:#c8d0e3}.empty{padding:50px;text-align:center;color:var(--muted)}
@media(max-width:900px){.controls{grid-template-columns:1fr 1fr}.controls input{grid-column:1/-1}}
</style></head><body><main>
<h1>Agent Extension Radar</h1><p class="lede">Daily discovery and momentum rankings for Claude skills, Claude tools, Claude plugins, Codex skills, MCP servers, and extensions for other agent ecosystems.</p>
<div class="stats"><span class="pill" id="count"></span><span class="pill">Generated __GENERATED__</span><span class="pill">Measured history replaces estimates automatically</span></div>
<div class="controls"><input id="search" placeholder="Search names, descriptions, repositories…"><select id="catalog"></select><select id="kind"><option value="">All kinds</option></select><select id="sort"><option value="overall">Overall</option><option value="momentum">Momentum</option><option value="rising">Rising</option><option value="popular">Popular</option><option value="stars">Stars</option></select></div>
<div class="table-wrap"><table><thead><tr><th>#</th><th>Extension</th><th>Kind / platform</th><th>Repository</th><th>Stars</th><th>Δ7d</th><th>Score</th><th>Description</th></tr></thead><tbody id="rows"></tbody></table><div class="empty" id="empty" hidden>No matching extensions.</div></div>
</main><script>
const items=__ITEMS__,catalogs=__CATALOGS__;
const search=document.querySelector('#search'),catalog=document.querySelector('#catalog'),kind=document.querySelector('#kind'),sort=document.querySelector('#sort'),rows=document.querySelector('#rows'),empty=document.querySelector('#empty'),count=document.querySelector('#count');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
catalog.innerHTML='<option value="">All catalogs</option>'+catalogs.map(c=>`<option value="${esc(c.id)}">${esc(c.title||c.id)}</option>`).join('');
[...new Set(items.map(i=>i.kind))].sort().forEach(v=>kind.insertAdjacentHTML('beforeend',`<option value="${esc(v)}">${esc(v)}</option>`));
function render(){const q=search.value.toLowerCase().trim(),cat=catalog.value,k=kind.value,key=sort.value;let data=items.filter(i=>(!cat||i.catalogs.includes(cat))&&(!k||i.kind===k)&&(!q||`${i.name} ${i.description} ${i.repo.full_name}`.toLowerCase().includes(q)));data.sort((a,b)=>key==='stars'?b.repo.stars-a.repo.stars:(b.scores[key]||0)-(a.scores[key]||0));count.textContent=`${data.length.toLocaleString()} extensions`;rows.innerHTML=data.slice(0,500).map((i,n)=>{const delta=i.growth.delta_7d==null?'—':`${i.growth.delta_7d>=0?'+':''}${i.growth.delta_7d}`;const score=key==='stars'?i.scores.overall:i.scores[key];return `<tr><td>${n+1}</td><td><a href="${esc(i.source_url||i.repo.html_url)}"><strong>${esc(i.name)}</strong></a><br><small>${esc(i.path)}</small></td><td><span class="tag">${esc(i.kind)}</span><br>${i.platforms.map(p=>`<span class="tag">${esc(p)}</span>`).join('')}</td><td><a href="${esc(i.repo.html_url)}">${esc(i.repo.full_name)}</a></td><td>${Number(i.repo.stars).toLocaleString()}</td><td>${delta}</td><td class="score">${Number(score||0).toFixed(1)}</td><td class="desc">${esc(i.description)}</td></tr>`}).join('');empty.hidden=data.length>0}
[search,catalog,kind,sort].forEach(el=>el.addEventListener('input',render));render();
</script></body></html>"""
    return (
        template.replace("__GENERATED__", html_lib.escape(generated_at))
        .replace("__ITEMS__", payload)
        .replace("__CATALOGS__", catalog_payload)
    )


def write_outputs(
    items: list[ExtensionItem], config: dict[str, Any], history: dict[str, Any], now: datetime,
    *, output_dir: Path, site_dir: Path
) -> dict[str, int]:
    generated_at = now.replace(microsecond=0).isoformat()
    catalogs = [item for item in config["catalogs"] if isinstance(item, dict)]
    summaries: list[dict[str, Any]] = []
    index_lines = [
        "# Agent Extension Radar",
        "",
        f"_Generated {generated_at}._",
        "",
        "One discovery engine publishes four focused catalogs. Each catalog includes high-momentum, rising, popular, and new leaderboards.",
        "",
        "| Catalog | Items | Description |",
        "|:--------|------:|:------------|",
    ]
    counts: dict[str, int] = {}
    for catalog in catalogs:
        catalog_id = str(catalog["id"])
        boards = catalog_leaderboards(items, catalog_id, config, now)
        catalog_items = [item for item in items if catalog_id in item.catalogs]
        counts[catalog_id] = len(catalog_items)
        markdown = render_catalog_markdown(catalog, boards, generated_at, now)
        atomic_write(output_dir / f"{catalog_id}.md", markdown)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "catalog": catalog,
            "count": len(catalog_items),
            "leaderboards": {
                key: [item.id for item in value] for key, value in boards.items() if key != "overall"
            },
            "items": [item.to_dict() for item in sorted(catalog_items, key=lambda value: value.scores.get("overall", 0.0), reverse=True)],
        }
        atomic_write(output_dir / f"{catalog_id}.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        summaries.append({"id": catalog_id, "title": catalog.get("title", catalog_id), "count": len(catalog_items), "description": catalog.get("description", "")})
        index_lines.append(
            f"| [{markdown_escape(catalog.get('title') or catalog_id)}]({catalog_id}.md) | {len(catalog_items):,} | {markdown_escape(catalog.get('description') or '')} |"
        )
    index_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "count": len(items),
        "catalogs": summaries,
        "items": [item.to_dict() for item in sorted(items, key=lambda value: value.scores.get("overall", 0.0), reverse=True)],
    }
    atomic_write(output_dir / "README.md", "\n".join(index_lines) + "\n")
    atomic_write(output_dir / "latest.json", json.dumps(index_payload, indent=2, ensure_ascii=False) + "\n")
    atomic_write(output_dir / "history.json", json.dumps(history, indent=2, sort_keys=True) + "\n")
    atomic_write(
        output_dir / "status.json",
        json.dumps({"ok": True, "generated_at": generated_at, "items": len(items), "catalogs": counts}, indent=2) + "\n",
    )
    atomic_write(site_dir / "index.html", render_html(items, catalogs, generated_at, now))
    atomic_write(site_dir / "latest.json", json.dumps(index_payload, indent=2, ensure_ascii=False) + "\n")
    return counts


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="agent_extensions.json", help="JSON configuration path")
    parser.add_argument("--token", default=None, help="GitHub token; defaults to GITHUB_TOKEN")
    parser.add_argument("--output-dir", default=None, help="Override generated feed directory")
    parser.add_argument("--site-dir", default=None, help="Override generated static-site directory")
    parser.add_argument("--now", default=None, help="Testing override: ISO timestamp")
    parser.add_argument("--allow-empty", action="store_true", help="Write an empty catalog instead of failing")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path
    config = load_config(config_path)
    now = parse_datetime(args.now) if args.now else utc_now()
    if now is None:
        parser.error("--now must be a valid ISO timestamp")
    output_dir = Path(args.output_dir) if args.output_dir else REPO_ROOT / str(config["output_dir"])
    site_dir = Path(args.site_dir) if args.site_dir else REPO_ROOT / str(config["site_dir"])
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    if not site_dir.is_absolute():
        site_dir = REPO_ROOT / site_dir
    history_path = output_dir / "history.json"
    history = load_history(history_path)
    token = args.token or os.environ.get("GITHUB_TOKEN")
    client = HttpClient(
        token=token,
        user_agent="github-radar-agent-extensions/0.1 (+https://github.com/Amarel-Taylor-Scott/github-radar)",
        max_retries=3,
        min_interval=float(config.get("request_interval_seconds", 0.15)),
    )
    items = Collector(config, GitHubAPI(client), now).collect()
    if not items and not args.allow_empty:
        LOGGER.error("No extension items were discovered; refusing to overwrite the published feed")
        return 2
    score_items(items, history, now)
    updated_history = update_history(history, items, now, int(config["history_days"]))
    counts = write_outputs(items, config, updated_history, now, output_dir=output_dir, site_dir=site_dir)
    LOGGER.info("Published %d unique extensions across %d catalogs", len(items), len(counts))
    for catalog_id, count in counts.items():
        LOGGER.info("  %s: %d", catalog_id, count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
