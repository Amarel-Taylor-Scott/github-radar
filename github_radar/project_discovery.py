"""Bounded, fair, read-only GitHub discovery and evidence enrichment."""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from github_radar.http import FetchError, HttpClient
from github_radar.project_common import (
    Project,
    QuerySpec,
    SCHEMA_VERSION,
    classify_project,
    days_since,
    normalize_repo,
    unique,
)

LOGGER = logging.getLogger("project_radar")
API_ROOT = "https://api.github.com"


class GitHubAPI:
    """Cached GitHub REST wrapper with a separate Search-API pace gate."""

    def __init__(
        self,
        client: HttpClient,
        *,
        search_interval_seconds: float = 2.1,
        sleep=time.sleep,
    ) -> None:
        self.client = client
        self.search_interval_seconds = max(search_interval_seconds, 0.0)
        self._sleep = sleep
        self._last_search = 0.0
        self.repo_cache: dict[str, Project] = {}
        self.community_cache: dict[str, dict[str, Any]] = {}

    def json_url(self, url: str) -> Any:
        return self.client.get(url, accept="application/vnd.github+json").json()

    def _pace_search(self) -> None:
        if self.search_interval_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_search
        if elapsed < self.search_interval_seconds:
            self._sleep(self.search_interval_seconds - elapsed)
        self._last_search = time.monotonic()

    def search_repositories(
        self, query: str, limit: int, *, sort: str = "stars", order: str = "desc"
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1
        limit = min(max(limit, 0), 1000)
        while len(results) < limit:
            per_page = min(100, limit - len(results))
            params = urllib.parse.urlencode(
                {"q": query, "sort": sort, "order": order, "per_page": per_page, "page": page}
            )
            self._pace_search()
            payload = self.json_url(f"{API_ROOT}/search/repositories?{params}")
            items = payload.get("items", []) if isinstance(payload, dict) else []
            page_items = [item for item in items if isinstance(item, dict) and item.get("full_name")]
            results.extend(page_items)
            if len(page_items) < per_page or payload.get("incomplete_results"):
                break
            page += 1
        return results[:limit]

    def repository(self, full_name: str) -> Optional[Project]:
        normalized = normalize_repo(full_name)
        key = normalized.lower()
        if not normalized:
            return None
        if key in self.repo_cache:
            return self.repo_cache[key]
        payload = self.json_url(f"{API_ROOT}/repos/{urllib.parse.quote(normalized, safe='/')}")
        if not isinstance(payload, dict):
            return None
        project = Project.from_api(payload)
        self.repo_cache[key] = project
        return project

    def community_profile(self, full_name: str) -> Optional[dict[str, Any]]:
        """Return GitHub's official community-profile metrics for a repository."""
        normalized = normalize_repo(full_name)
        key = normalized.lower()
        if not normalized:
            return None
        if key in self.community_cache:
            return self.community_cache[key]
        encoded = urllib.parse.quote(normalized, safe="/")
        payload = self.json_url(f"{API_ROOT}/repos/{encoded}/community/profile")
        if not isinstance(payload, dict):
            return None
        self.community_cache[key] = payload
        return payload


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("configuration root must be an object")
    if int(payload.get("schema_version", 0)) != SCHEMA_VERSION:
        raise ValueError(f"configuration schema_version must be {SCHEMA_VERSION}")
    catalogs = payload.get("catalogs")
    if not isinstance(catalogs, list) or not catalogs:
        raise ValueError("configuration must define catalogs")
    catalog_ids = [str(item.get("id") or "") for item in catalogs if isinstance(item, dict)]
    if len(catalog_ids) != len(catalogs) or any(not value for value in catalog_ids):
        raise ValueError("every catalog requires a non-empty id")
    if len(catalog_ids) != len(set(catalog_ids)):
        raise ValueError("catalog ids must be unique")

    defaults: dict[str, Any] = {
        "output_dir": "feeds/projects",
        "site_dir": "docs/projects",
        "aggregate_catalog_id": "interesting-projects",
        "history_days": 90,
        "active_window_days": 120,
        "new_project_days": 180,
        "max_search_requests": 36,
        "active_results_per_query": 45,
        "new_results_per_query": 35,
        "max_repository_enrichments": 180,
        "max_community_enrichments": 90,
        "max_projects": 2200,
        "leaderboard_size": 25,
        "max_projects_per_owner": 2,
        "aggregate_min_per_catalog": 1,
        "aggregate_max_per_catalog": 3,
        "leaderboard_min_stars": 5,
        "leaderboard_max_idle_days": 365,
        "up_and_coming_max_stars": 25000,
        "up_and_coming_max_age_days": 1095,
        "hidden_gem_max_stars": 5000,
        "minimum_total_projects": 100,
        "minimum_previous_ratio": 0.40,
        "minimum_previous_catalog_ratio": 0.40,
        "search_interval_seconds": 2.1,
        "request_interval_seconds": 0.1,
        "provisional_momentum_weight": 0.25,
        "extreme_lifetime_velocity": 100.0,
        "review_queue_size": 100,
        "changes_limit": 50,
    }
    config = {**defaults, **payload}
    aggregate_id = str(config["aggregate_catalog_id"])
    if aggregate_id not in catalog_ids:
        raise ValueError("aggregate_catalog_id must identify a configured catalog")
    native = [item for item in catalogs if isinstance(item, dict) and item.get("id") != aggregate_id]
    if not native:
        raise ValueError("at least one non-aggregate catalog is required")
    for catalog in native:
        topics = catalog.get("topics") or []
        extras = catalog.get("queries") or []
        if not topics and not extras:
            raise ValueError(f"catalog {catalog['id']} requires topics or queries")
    if int(config["max_search_requests"]) < len(native):
        raise ValueError("max_search_requests must allow at least one query per native catalog")
    if int(config["aggregate_max_per_catalog"]) < int(config["aggregate_min_per_catalog"]):
        raise ValueError("aggregate_max_per_catalog must be >= aggregate_min_per_catalog")
    return config


def catalog_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["id"]): item
        for item in config["catalogs"]
        if isinstance(item, dict) and item.get("id")
    }


def _safe_query(query: str) -> str:
    text = " ".join(query.split())
    if "archived:" not in text:
        text += " archived:false"
    if "fork:" not in text:
        text += " fork:false"
    return text.strip()


def build_query_specs(config: dict[str, Any], now: datetime) -> list[QuerySpec]:
    """Build a fair, bounded query schedule across every native catalog."""
    aggregate_id = str(config["aggregate_catalog_id"])
    native = [
        item for item in config["catalogs"]
        if isinstance(item, dict) and item.get("id") != aggregate_id
    ]
    active_since = (now - timedelta(days=int(config["active_window_days"]))).date().isoformat()
    new_since = (now - timedelta(days=int(config["new_project_days"]))).date().isoformat()

    primary_active: list[QuerySpec] = []
    primary_new: list[QuerySpec] = []
    additional: list[list[QuerySpec]] = []

    for catalog in native:
        catalog_id = str(catalog["id"])
        topics = unique(catalog.get("topics") or [])
        min_stars = int(catalog.get("min_stars", config["leaderboard_min_stars"]))
        new_min_stars = int(catalog.get("new_min_stars", max(1, min_stars // 2)))
        active_limit = int(catalog.get("active_results_per_query", config["active_results_per_query"]))
        new_limit = int(catalog.get("new_results_per_query", config["new_results_per_query"]))
        confidence = float(catalog.get("source_confidence", 0.58))
        topic_specs: list[QuerySpec] = []
        if topics:
            primary = topics[0]
            primary_active.append(
                QuerySpec(
                    id=f"{catalog_id}:active:{primary}",
                    catalog_id=catalog_id,
                    mode="active",
                    query=_safe_query(
                        f"topic:{primary} stars:>{min_stars} pushed:>={active_since}"
                    ),
                    sort="stars",
                    order="desc",
                    max_results=active_limit,
                    topic=primary,
                    source_confidence=confidence,
                )
            )
            primary_new.append(
                QuerySpec(
                    id=f"{catalog_id}:new:{primary}",
                    catalog_id=catalog_id,
                    mode="new",
                    query=_safe_query(
                        f"topic:{primary} stars:>{new_min_stars} created:>={new_since} pushed:>={active_since}"
                    ),
                    sort="updated",
                    order="desc",
                    max_results=new_limit,
                    topic=primary,
                    source_confidence=min(confidence + 0.05, 1.0),
                )
            )
            for topic in topics[1:]:
                topic_specs.append(
                    QuerySpec(
                        id=f"{catalog_id}:active:{topic}",
                        catalog_id=catalog_id,
                        mode="active",
                        query=_safe_query(
                            f"topic:{topic} stars:>{min_stars} pushed:>={active_since}"
                        ),
                        sort="stars",
                        order="desc",
                        max_results=active_limit,
                        topic=topic,
                        source_confidence=confidence,
                    )
                )
        for index, raw in enumerate(catalog.get("queries") or []):
            if not isinstance(raw, dict) or not raw.get("query"):
                continue
            query = str(raw["query"]).format(
                active_since=active_since,
                new_since=new_since,
                min_stars=min_stars,
                new_min_stars=new_min_stars,
            )
            topic_specs.append(
                QuerySpec(
                    id=str(raw.get("id") or f"{catalog_id}:custom:{index + 1}"),
                    catalog_id=catalog_id,
                    mode=str(raw.get("mode") or "custom"),
                    query=_safe_query(query),
                    sort=str(raw.get("sort") or "stars"),
                    order=str(raw.get("order") or "desc"),
                    max_results=int(raw.get("max_results") or active_limit),
                    topic=str(raw.get("topic") or ""),
                    source_confidence=float(raw.get("source_confidence", confidence)),
                )
            )
        additional.append(topic_specs)

    schedule: list[QuerySpec] = [*primary_active, *primary_new]
    depth = 0
    while any(depth < len(values) for values in additional):
        for values in additional:
            if depth < len(values):
                schedule.append(values[depth])
        depth += 1

    deduped: list[QuerySpec] = []
    seen: set[tuple[str, str]] = set()
    for spec in schedule:
        key = (spec.catalog_id, spec.query.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(spec)
    return deduped[: int(config["max_search_requests"])]


class Collector:
    def __init__(self, config: dict[str, Any], github: GitHubAPI, now: datetime) -> None:
        self.config = config
        self.github = github
        self.now = now
        self.projects: dict[str, Project] = {}
        self.source_health: list[dict[str, Any]] = []

    def _add(self, project: Project) -> None:
        if not project.full_name:
            return
        key = project.full_name.lower()
        if key in self.projects:
            self.projects[key].merge(project)
        else:
            self.projects[key] = project

    def collect(self) -> tuple[list[Project], list[dict[str, Any]]]:
        specs = build_query_specs(self.config, self.now)
        for spec in specs:
            started = time.monotonic()
            try:
                payloads = self.github.search_repositories(
                    spec.query, spec.max_results, sort=spec.sort, order=spec.order
                )
                for payload in payloads:
                    self._add(
                        Project.from_api(
                            payload,
                            catalog_id=spec.catalog_id,
                            source_id=f"github-search:{spec.id}",
                            mode=spec.mode,
                            topic=spec.topic,
                            source_confidence=spec.source_confidence,
                        )
                    )
                self.source_health.append(
                    {
                        "id": spec.id,
                        "catalog": spec.catalog_id,
                        "mode": spec.mode,
                        "ok": True,
                        "records": len(payloads),
                        "elapsed_ms": round((time.monotonic() - started) * 1000),
                        "query": spec.query,
                    }
                )
            except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
                LOGGER.warning("Query %s failed: %s", spec.id, exc)
                self.source_health.append(
                    {
                        "id": spec.id,
                        "catalog": spec.catalog_id,
                        "mode": spec.mode,
                        "ok": False,
                        "records": 0,
                        "elapsed_ms": round((time.monotonic() - started) * 1000),
                        "query": spec.query,
                        "error": str(exc),
                    }
                )

        self._collect_seeds()
        self._enrich_repositories()
        self._enrich_community_profiles()
        aggregate_id = str(self.config["aggregate_catalog_id"])
        blocked = {normalize_repo(value).lower() for value in self.config.get("blocked_repositories", [])}
        projects = []
        for project in self.projects.values():
            if project.full_name.lower() in blocked:
                continue
            project.catalogs = unique([*project.catalogs, aggregate_id])
            project.project_type = classify_project(project)
            projects.append(project)
        projects.sort(
            key=lambda value: (
                len(value.provenance),
                value.stars,
                -days_since(value.created_at, self.now),
                value.full_name.lower(),
            ),
            reverse=True,
        )
        return projects[: int(self.config["max_projects"])], self.source_health

    def _collect_seeds(self) -> None:
        for raw in self.config.get("seed_repositories", []):
            if not isinstance(raw, dict) or not raw.get("repository"):
                continue
            full_name = normalize_repo(str(raw["repository"]))
            try:
                project = self.github.repository(full_name)
            except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
                LOGGER.warning("Seed %s failed: %s", full_name, exc)
                self.source_health.append(
                    {
                        "id": f"seed:{full_name}",
                        "catalog": "",
                        "mode": "seed",
                        "ok": False,
                        "records": 0,
                        "error": str(exc),
                    }
                )
                continue
            if project is None:
                continue
            project.catalogs = unique(raw.get("catalogs") or [])
            project.provenance = [f"seed:{full_name}"]
            project.evidence = ["explicit-seed"]
            project.query_modes = ["seed"]
            project.source_confidence = float(raw.get("source_confidence", 0.95))
            self._add(project)
            self.source_health.append(
                {
                    "id": f"seed:{full_name}",
                    "catalog": ",".join(project.catalogs),
                    "mode": "seed",
                    "ok": True,
                    "records": 1,
                }
            )

    def _priority(self, project: Project) -> tuple[Any, ...]:
        return (
            len(project.provenance),
            project.source_confidence,
            float("new" in project.query_modes),
            project.stars,
            -days_since(project.created_at, self.now),
            project.full_name.lower(),
        )

    def _balanced_selection(self, budget: int) -> list[Project]:
        if budget <= 0:
            return []
        aggregate_id = str(self.config["aggregate_catalog_id"])
        native_ids = [
            str(item["id"])
            for item in self.config["catalogs"]
            if isinstance(item, dict) and item.get("id") != aggregate_id
        ]
        by_catalog = {
            catalog_id: sorted(
                [project for project in self.projects.values() if catalog_id in project.catalogs],
                key=self._priority,
                reverse=True,
            )
            for catalog_id in native_ids
        }
        selected: list[Project] = []
        selected_names: set[str] = set()
        cursors = {catalog_id: 0 for catalog_id in native_ids}
        made_progress = True
        while len(selected) < budget and made_progress:
            made_progress = False
            for catalog_id in native_ids:
                values = by_catalog[catalog_id]
                cursor = cursors[catalog_id]
                while cursor < len(values) and values[cursor].full_name.lower() in selected_names:
                    cursor += 1
                cursors[catalog_id] = cursor
                if cursor >= len(values):
                    continue
                project = values[cursor]
                cursors[catalog_id] = cursor + 1
                selected.append(project)
                selected_names.add(project.full_name.lower())
                made_progress = True
                if len(selected) >= budget:
                    break
        if len(selected) < budget:
            remaining = sorted(
                [
                    project
                    for project in self.projects.values()
                    if project.full_name.lower() not in selected_names
                ],
                key=self._priority,
                reverse=True,
            )
            selected.extend(remaining[: budget - len(selected)])
        return selected

    def _enrich_repositories(self) -> None:
        selected = self._balanced_selection(
            max(int(self.config.get("max_repository_enrichments", 0)), 0)
        )
        if not selected:
            return
        success = 0
        failures = 0
        for project in selected:
            try:
                enriched = self.github.repository(project.full_name)
            except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
                LOGGER.debug("Enrichment failed for %s: %s", project.full_name, exc)
                failures += 1
                continue
            if enriched is None:
                failures += 1
                continue
            project.merge(enriched)
            success += 1
        self.source_health.append(
            {
                "id": "repository-enrichment",
                "catalog": "all",
                "mode": "enrichment",
                "ok": success > 0 or not selected,
                "records": success,
                "attempted": len(selected),
                "failures": failures,
                "partial": failures > 0 and success > 0,
            }
        )

    def _enrich_community_profiles(self) -> None:
        selected = self._balanced_selection(
            max(int(self.config.get("max_community_enrichments", 0)), 0)
        )
        if not selected:
            return
        success = 0
        failures = 0
        for project in selected:
            try:
                payload = self.github.community_profile(project.full_name)
            except (FetchError, ValueError, TypeError, json.JSONDecodeError) as exc:
                LOGGER.debug("Community profile failed for %s: %s", project.full_name, exc)
                failures += 1
                continue
            if payload is None:
                failures += 1
                continue
            files = payload.get("files") or {}
            if not isinstance(files, dict):
                files = {}
            project.community_profile_complete = True
            project.community_health = {
                "health_percentage": int(payload.get("health_percentage") or 0),
                "has_documentation": bool(payload.get("documentation")),
                "has_readme": bool(files.get("readme")),
                "has_contributing": bool(files.get("contributing")),
                "has_code_of_conduct": bool(
                    files.get("code_of_conduct") or files.get("code_of_conduct_file")
                ),
                "has_issue_template": bool(files.get("issue_template")),
                "has_pull_request_template": bool(files.get("pull_request_template")),
                "has_detected_license": bool(files.get("license")),
                "updated_at": str(payload.get("updated_at") or ""),
            }
            project.evidence = unique([*project.evidence, "github-community-profile"])
            success += 1
        self.source_health.append(
            {
                "id": "community-profile-enrichment",
                "catalog": "all",
                "mode": "community-health",
                "ok": success > 0 or not selected,
                "records": success,
                "attempted": len(selected),
                "failures": failures,
                "partial": failures > 0 and success > 0,
            }
        )
