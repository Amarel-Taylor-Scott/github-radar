"""Catalog-local, multi-dimensional ranking for Project Radar."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from github_radar.project_common import (
    Project, _percentiles, _valid_license, clamp, days_since,
)
from github_radar.project_discovery import catalog_map
from github_radar.project_history import calculate_growth


def metadata_quality(project: Project, now: datetime) -> float:
    description = min(len(project.description.strip()) / 180.0, 1.0)
    license_score = 1.0 if _valid_license(project.license_spdx) else 0.0
    topics = min(len(project.topics) / 5.0, 1.0)
    homepage = 1.0 if project.homepage.startswith(("http://", "https://")) else 0.0
    community = sum(
        (project.has_issues, project.has_discussions, project.has_wiki, project.has_pages)
    ) / 4.0
    idle = days_since(project.pushed_at, now)
    updated = days_since(project.updated_at, now)
    maintenance = 0.65 * math.exp(-idle / 45.0) + 0.35 * math.exp(-updated / 90.0)
    adoption = min(math.log1p(project.forks) / max(math.log1p(project.stars), 1.0), 1.0)
    watchers = min(math.log1p(project.watchers) / math.log(101), 1.0)
    substance = min(math.log1p(project.size_kb) / math.log(100001), 1.0)
    provenance = min(len(project.provenance) / 3.0, 1.0)
    return clamp(
        0.15 * description
        + 0.13 * license_score
        + 0.10 * topics
        + 0.07 * homepage
        + 0.08 * community
        + 0.17 * maintenance
        + 0.10 * adoption
        + 0.05 * watchers
        + 0.07 * substance
        + 0.08 * provenance
    )


def metadata_confidence(project: Project) -> float:
    completeness = sum(
        (
            bool(project.full_name),
            bool(project.description),
            bool(project.created_at),
            bool(project.pushed_at),
            bool(project.updated_at),
            bool(project.language),
            bool(project.topics),
            bool(project.license_spdx),
        )
    ) / 8.0
    corroboration = min(len(project.provenance) / 3.0, 1.0)
    return clamp(
        0.42 * completeness
        + 0.23 * float(project.api_complete)
        + 0.20 * project.source_confidence
        + 0.15 * corroboration
    )


def catalog_relevance(
    project: Project, catalog: dict[str, Any], aggregate_id: str
) -> float:
    catalog_id = str(catalog["id"])
    if catalog_id == aggregate_id:
        native_memberships = [value for value in project.catalogs if value != aggregate_id]
        return clamp(
            0.55
            + 0.12 * max(len(native_memberships) - 1, 0)
            + 0.08 * min(len(project.provenance) - 1, 2)
        )
    if catalog_id not in project.catalogs:
        return 0.0
    configured_topics = {str(value).lower() for value in catalog.get("topics") or []}
    topic_overlap = len(configured_topics & {value.lower() for value in project.topics})
    matched_overlap = len(configured_topics & {value.lower() for value in project.matched_topics})
    haystack = f"{project.name} {project.description} {' '.join(project.topics)}".lower()
    keywords = [str(value).lower() for value in catalog.get("keywords") or []]
    keyword_hits = sum(1 for value in keywords if value and value in haystack)
    negatives = [str(value).lower() for value in catalog.get("negative_terms") or []]
    negative_hits = sum(1 for value in negatives if value and value in haystack)
    return clamp(
        0.54
        + 0.16 * min(matched_overlap, 2) / 2.0
        + 0.14 * min(topic_overlap, 3) / 3.0
        + 0.12 * min(keyword_hits, 3) / 3.0
        + 0.08 * min(len(project.provenance) - 1, 2) / 2.0
        - 0.18 * min(negative_hits, 2)
    )


def score_projects(
    projects: list[Project], config: dict[str, Any], history: dict[str, Any], now: datetime
) -> None:
    aggregate_id = str(config["aggregate_catalog_id"])
    catalogs = catalog_map(config)
    for project in projects:
        project.growth = calculate_growth(project, history, now)
        project.dimensions = {
            "quality": round(metadata_quality(project, now) * 100, 2),
            "confidence": round(metadata_confidence(project) * 100, 2),
            "maintenance": round(
                (
                    0.65 * math.exp(-days_since(project.pushed_at, now) / 45.0)
                    + 0.35 * math.exp(-days_since(project.updated_at, now) / 90.0)
                )
                * 100,
                2,
            ),
            "newness": round(math.exp(-days_since(project.created_at, now) / 180.0) * 100, 2),
        }

    for catalog_id, catalog in catalogs.items():
        members = [project for project in projects if catalog_id in project.catalogs]
        if not members:
            continue
        rows: list[dict[str, float]] = []
        for project in members:
            age = max(days_since(project.created_at, now, default=3650), 1)
            idle = days_since(project.pushed_at, now)
            updated = days_since(project.updated_at, now)
            relative = max(float(project.growth.get("relative_7d") or 0.0), 0.0)
            rows.append(
                {
                    "popularity": math.log1p(project.stars) + 0.35 * math.log1p(project.forks) + 0.12 * math.log1p(project.watchers),
                    "velocity": math.log1p(max(float(project.growth.get("stars_per_day") or 0.0), 0.0)),
                    "acceleration": math.log1p(max(float(project.growth.get("acceleration") or 0.0), 0.0)),
                    "relative": math.log1p(relative * 100.0),
                    "freshness": math.exp(-idle / 45.0),
                    "maintenance": 0.65 * math.exp(-idle / 45.0) + 0.35 * math.exp(-updated / 90.0),
                    "quality": metadata_quality(project, now),
                    "confidence": metadata_confidence(project),
                    "newness": math.exp(-age / 180.0),
                    "relevance": catalog_relevance(project, catalog, aggregate_id),
                }
            )
        keys = (
            "popularity",
            "velocity",
            "acceleration",
            "relative",
            "freshness",
            "maintenance",
            "quality",
            "confidence",
            "newness",
            "relevance",
        )
        normalized = {key: _percentiles([row[key] for row in rows]) for key in keys}
        for index, project in enumerate(members):
            n = {key: normalized[key][index] for key in keys}
            popular = 100 * (
                0.68 * n["popularity"]
                + 0.08 * n["velocity"]
                + 0.09 * n["quality"]
                + 0.07 * n["freshness"]
                + 0.08 * n["confidence"]
            )
            momentum = 100 * (
                0.12 * n["popularity"]
                + 0.36 * n["velocity"]
                + 0.19 * n["acceleration"]
                + 0.10 * n["relative"]
                + 0.10 * n["freshness"]
                + 0.07 * n["quality"]
                + 0.06 * n["confidence"]
            )
            rising = 100 * (
                0.07 * n["popularity"]
                + 0.32 * n["velocity"]
                + 0.17 * n["acceleration"]
                + 0.09 * n["relative"]
                + 0.15 * n["newness"]
                + 0.08 * n["quality"]
                + 0.07 * n["relevance"]
                + 0.05 * n["confidence"]
            )
            quality = 100 * (
                0.58 * n["quality"]
                + 0.14 * n["maintenance"]
                + 0.12 * n["confidence"]
                + 0.10 * n["relevance"]
                + 0.06 * n["popularity"]
            )
            interesting = (
                0.27 * rising
                + 0.23 * momentum
                + 0.22 * quality
                + 10 * n["relevance"]
                + 9 * n["newness"]
                + 9 * n["popularity"]
            )
            overall = 0.24 * popular + 0.24 * momentum + 0.20 * rising + 0.22 * quality + 10 * n["relevance"]
            hidden_gem = 0.38 * rising + 0.34 * quality + 16 * n["relevance"] + 12 * (1.0 - n["popularity"])
            penalty = 0.0
            if project.archived or project.disabled:
                penalty += 45.0
            if project.fork or project.is_template:
                penalty += 18.0
            if days_since(project.pushed_at, now) > 365:
                penalty += 12.0
            if not project.description:
                penalty += 5.0
            project.catalog_scores[catalog_id] = {
                "popular": round(max(popular - penalty, 0.0), 2),
                "momentum": round(max(momentum - penalty, 0.0), 2),
                "rising": round(max(rising - penalty, 0.0), 2),
                "quality": round(max(quality - penalty, 0.0), 2),
                "interesting": round(max(interesting - penalty, 0.0), 2),
                "overall": round(max(overall - penalty, 0.0), 2),
                "hidden_gem": round(max(hidden_gem - penalty, 0.0), 2),
                "relevance": round(rows[index]["relevance"] * 100, 2),
            }


def rankable(project: Project, catalog: dict[str, Any], config: dict[str, Any], now: datetime) -> bool:
    if str(catalog["id"]) not in project.catalogs:
        return False
    if project.archived or project.disabled or project.fork or project.is_template:
        return False
    if project.stars < int(catalog.get("leaderboard_min_stars", config["leaderboard_min_stars"])):
        return False
    if days_since(project.pushed_at, now) > int(
        catalog.get("leaderboard_max_idle_days", config["leaderboard_max_idle_days"])
    ):
        return False
    excluded = {str(value) for value in catalog.get("excluded_project_types") or []}
    if project.project_type in excluded:
        return False
    if not project.description:
        return False
    return True


def diverse_top(
    projects: list[Project], catalog_id: str, score: str, limit: int, max_per_owner: int
) -> list[Project]:
    owner_counts: dict[str, int] = {}
    selected: list[Project] = []

    def key(project: Project) -> tuple[Any, ...]:
        scores = project.catalog_scores.get(catalog_id, {})
        return (
            float(scores.get(score, 0.0)),
            float(scores.get("quality", 0.0)),
            project.stars,
            len(project.provenance),
            project.full_name.lower(),
        )

    for project in sorted(projects, key=key, reverse=True):
        owner = project.owner.lower()
        if owner_counts.get(owner, 0) >= max_per_owner:
            continue
        selected.append(project)
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def catalog_leaderboards(
    projects: list[Project], catalog: dict[str, Any], config: dict[str, Any], now: datetime
) -> dict[str, list[Project]]:
    catalog_id = str(catalog["id"])
    members = [project for project in projects if rankable(project, catalog, config, now)]
    limit = int(catalog.get("leaderboard_size", config["leaderboard_size"]))
    diversity = int(catalog.get("max_projects_per_owner", config["max_projects_per_owner"]))
    up_and_coming = [
        project
        for project in members
        if project.stars <= int(config["up_and_coming_max_stars"])
        and days_since(project.created_at, now) <= int(config["up_and_coming_max_age_days"])
    ]
    hidden = [
        project
        for project in members
        if project.stars <= int(config["hidden_gem_max_stars"])
        and project.catalog_scores.get(catalog_id, {}).get("quality", 0.0) >= 45.0
    ]
    new_projects = [
        project for project in members if days_since(project.created_at, now) <= int(config["new_project_days"])
    ]
    movers = [project for project in members if project.growth.get("delta_1d") is not None]
    movers.sort(
        key=lambda project: (
            int(project.growth.get("delta_1d") or 0),
            project.catalog_scores.get(catalog_id, {}).get("momentum", 0.0),
        ),
        reverse=True,
    )
    return {
        "interesting": diverse_top(members, catalog_id, "interesting", limit, diversity),
        "high_momentum": diverse_top(members, catalog_id, "momentum", limit, diversity),
        "up_and_coming": diverse_top(up_and_coming, catalog_id, "rising", limit, diversity),
        "high_quality": diverse_top(members, catalog_id, "quality", limit, diversity),
        "hidden_gems": diverse_top(hidden, catalog_id, "hidden_gem", limit, diversity),
        "most_popular": diverse_top(members, catalog_id, "popular", limit, diversity),
        "new_projects": diverse_top(new_projects, catalog_id, "rising", limit, diversity),
        "daily_movers": movers[:limit],
    }
