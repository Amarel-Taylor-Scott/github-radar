"""Catalog-local, evidence-aware, multi-dimensional ranking for Project Radar."""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime
from typing import Any

from github_radar.project_common import (
    Project,
    _percentiles,
    _valid_license,
    clamp,
    days_since,
    unique,
)
from github_radar.project_discovery import catalog_map
from github_radar.project_history import calculate_growth

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.#_-]{2,}")
STOPWORDS = {
    "about", "after", "also", "and", "are", "based", "build", "built", "can",
    "code", "data", "for", "from", "github", "into", "its", "more", "open",
    "open-source", "project", "projects", "provides", "repository", "software",
    "source", "support", "supports", "that", "the", "their", "this", "tool",
    "tools", "using", "with", "your",
}


def metadata_quality(project: Project, now: datetime) -> float:
    description = min(len(project.description.strip()) / 180.0, 1.0)
    license_score = 1.0 if _valid_license(project.license_spdx) else 0.0
    topics = min(len(project.topics) / 5.0, 1.0)
    homepage = 1.0 if project.homepage.startswith(("http://", "https://")) else 0.0
    community_features = sum(
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
        + 0.08 * community_features
        + 0.17 * maintenance
        + 0.10 * adoption
        + 0.05 * watchers
        + 0.07 * substance
        + 0.08 * provenance
    )


def community_health_score(project: Project) -> float:
    if project.community_profile_complete:
        return clamp(float(project.community_health.get("health_percentage") or 0.0) / 100.0)
    # A conservative fallback, clearly marked as unmeasured elsewhere.
    return clamp(
        0.30 * float(bool(project.description))
        + 0.25 * float(_valid_license(project.license_spdx))
        + 0.20 * float(project.has_issues)
        + 0.15 * float(bool(project.topics))
        + 0.10 * float(bool(project.homepage))
    ) * 0.65


def adoption_depth(project: Project) -> float:
    stars = max(project.stars, 1)
    fork_ratio = project.forks / stars
    watcher_ratio = project.watchers / stars
    fork_depth = min(fork_ratio / 0.08, 1.0)
    watcher_depth = min(watcher_ratio / 0.012, 1.0)
    absolute_forks = min(math.log1p(project.forks) / math.log(5001), 1.0)
    return clamp(0.50 * fork_depth + 0.25 * watcher_depth + 0.25 * absolute_forks)


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
    community_evidence = 1.0 if project.community_profile_complete else 0.0
    return clamp(
        0.36 * completeness
        + 0.22 * float(project.api_complete)
        + 0.18 * project.source_confidence
        + 0.14 * corroboration
        + 0.10 * community_evidence
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


def _document_tokens(project: Project) -> set[str]:
    text = f"{project.name.replace('-', ' ')} {project.description} {' '.join(project.topics)}"
    return {
        token.lower().strip("-_.")
        for token in TOKEN_RE.findall(text)
        if token.lower().strip("-_.") not in STOPWORDS
        and len(token.strip("-_.")) >= 3
    }


def novelty_values(projects: list[Project]) -> list[float]:
    """Estimate catalog-local descriptive novelty with deterministic IDF."""
    documents = [_document_tokens(project) for project in projects]
    if not documents:
        return []
    frequency: Counter[str] = Counter()
    for document in documents:
        frequency.update(document)
    total = len(documents)
    output: list[float] = []
    for document in documents:
        if not document:
            output.append(0.0)
            continue
        idf = sorted(
            (math.log((total + 1) / (frequency[token] + 1)) + 1.0 for token in document),
            reverse=True,
        )
        # Focus on the most discriminating terms so long descriptions do not win by length.
        strongest = idf[: min(12, len(idf))]
        output.append(sum(strongest) / len(strongest))
    return output


def review_flags(project: Project, config: dict[str, Any], now: datetime) -> list[str]:
    """Return evidence-review flags without implying wrongdoing.

    Routine incompleteness is not enough to flag every record. A gap enters the
    review queue only when the repository has meaningful adoption, unusually
    strong provisional velocity, or an exceptionally recent breakout.
    """
    flags: list[str] = []
    confidence = float(project.growth.get("signal_confidence") or 0.0)
    velocity = float(project.growth.get("stars_per_day") or 0.0)
    age = days_since(project.created_at, now, default=3650)
    attention = project.stars >= 1000 or velocity >= 5.0 or age <= 30
    if confidence < 0.999 and velocity >= 5.0:
        flags.append("provisional-high-momentum")
    if (
        project.growth.get("signal_source") == "lifetime-estimate"
        and velocity >= float(config.get("extreme_lifetime_velocity", 100.0))
    ):
        flags.append("extreme-lifetime-velocity")
    if age <= 14 and project.stars >= 1000:
        flags.append("sudden-breakout")
    if attention and not _valid_license(project.license_spdx):
        flags.append("license-unverified")
    if attention and not project.community_profile_complete:
        flags.append("community-health-unmeasured")
    if attention and len(project.provenance) <= 1:
        flags.append("single-discovery-path")
    if len(project.description.strip()) < 45:
        flags.append("thin-description")
    if project.stars >= 5000 and project.forks / max(project.stars, 1) < 0.002:
        flags.append("low-fork-depth")
    return unique(flags)


def score_projects(
    projects: list[Project], config: dict[str, Any], history: dict[str, Any], now: datetime
) -> None:
    aggregate_id = str(config["aggregate_catalog_id"])
    catalogs = catalog_map(config)
    provisional_floor = clamp(float(config.get("provisional_momentum_weight", 0.25)))

    for project in projects:
        project.growth = calculate_growth(project, history, now)
        project.risk_flags = review_flags(project, config, now)
        project.dimensions = {
            "quality": round(metadata_quality(project, now) * 100, 2),
            "community_health": round(community_health_score(project) * 100, 2),
            "adoption_depth": round(adoption_depth(project) * 100, 2),
            "confidence": round(metadata_confidence(project) * 100, 2),
            "signal_confidence": round(
                float(project.growth.get("signal_confidence") or 0.0) * 100, 2
            ),
            "maintenance": round(
                (
                    0.65 * math.exp(-days_since(project.pushed_at, now) / 45.0)
                    + 0.35 * math.exp(-days_since(project.updated_at, now) / 90.0)
                )
                * 100,
                2,
            ),
            "newness": round(math.exp(-days_since(project.created_at, now) / 180.0) * 100, 2),
            "novelty": 0.0,
            "under_recognition": 0.0,
        }

    for catalog_id, catalog in catalogs.items():
        members = [project for project in projects if catalog_id in project.catalogs]
        if not members:
            continue
        novelty_raw = novelty_values(members)
        rows: list[dict[str, float]] = []
        for index, project in enumerate(members):
            age = max(days_since(project.created_at, now, default=3650), 1)
            idle = days_since(project.pushed_at, now)
            updated = days_since(project.updated_at, now)
            relative = max(float(project.growth.get("relative_7d") or 0.0), 0.0)
            signal_confidence = clamp(
                float(project.growth.get("signal_confidence") or 0.0)
            )
            raw_quality = metadata_quality(project, now)
            raw_novelty = novelty_raw[index]
            under_recognition = (
                raw_quality
                * (0.55 + 0.45 * min(raw_novelty / 4.0, 1.0))
                * math.exp(-math.log1p(project.stars) / 14.0)
            )
            rows.append(
                {
                    "popularity": math.log1p(project.stars)
                    + 0.35 * math.log1p(project.forks)
                    + 0.12 * math.log1p(project.watchers),
                    "velocity": math.log1p(
                        max(float(project.growth.get("stars_per_day") or 0.0), 0.0)
                    ),
                    "acceleration": math.log1p(
                        max(float(project.growth.get("acceleration") or 0.0), 0.0)
                    ),
                    "relative": math.log1p(relative * 100.0),
                    "freshness": math.exp(-idle / 45.0),
                    "maintenance": 0.65 * math.exp(-idle / 45.0)
                    + 0.35 * math.exp(-updated / 90.0),
                    "quality": raw_quality,
                    "community": community_health_score(project),
                    "adoption_depth": adoption_depth(project),
                    "confidence": metadata_confidence(project),
                    "measurement": signal_confidence,
                    "newness": math.exp(-age / 180.0),
                    "novelty": raw_novelty,
                    "under_recognition": under_recognition,
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
            "community",
            "adoption_depth",
            "confidence",
            "newness",
            "novelty",
            "under_recognition",
            "relevance",
        )
        normalized: dict[str, list[float]] = {}
        for key in keys:
            values = [row[key] for row in rows]
            # Absent observed acceleration/relative-growth must not receive a
            # synthetic midpoint percentile merely because every value is zero.
            if key in {"velocity", "acceleration", "relative"} and max(values, default=0.0) <= 0:
                normalized[key] = [0.0 for _ in values]
            else:
                normalized[key] = _percentiles(values)
        for index, project in enumerate(members):
            n = {key: normalized[key][index] for key in keys}
            signal_confidence = rows[index]["measurement"]
            momentum_factor = max(provisional_floor, signal_confidence)
            velocity_evidence = n["velocity"] * momentum_factor
            acceleration_evidence = n["acceleration"] * signal_confidence
            relative_evidence = n["relative"] * signal_confidence
            popular = 100 * (
                0.66 * n["popularity"]
                + 0.06 * velocity_evidence
                + 0.09 * n["quality"]
                + 0.07 * n["community"]
                + 0.06 * n["freshness"]
                + 0.06 * n["confidence"]
            )
            momentum = 100 * (
                0.10 * n["popularity"]
                + 0.34 * velocity_evidence
                + 0.16 * acceleration_evidence
                + 0.08 * relative_evidence
                + 0.08 * n["freshness"]
                + 0.06 * n["quality"]
                + 0.05 * n["confidence"]
                + 0.13 * signal_confidence
            )
            rising = 100 * (
                0.05 * n["popularity"]
                + 0.29 * velocity_evidence
                + 0.14 * acceleration_evidence
                + 0.07 * relative_evidence
                + 0.14 * n["newness"]
                + 0.08 * n["quality"]
                + 0.07 * n["relevance"]
                + 0.05 * n["confidence"]
                + 0.07 * n["novelty"]
                + 0.04 * signal_confidence
            )
            quality = 100 * (
                0.34 * n["quality"]
                + 0.18 * n["community"]
                + 0.14 * n["maintenance"]
                + 0.10 * n["confidence"]
                + 0.08 * n["relevance"]
                + 0.08 * n["adoption_depth"]
                + 0.08 * n["popularity"]
            )
            interesting = 100 * (
                0.20 * (rising / 100.0)
                + 0.18 * (momentum / 100.0)
                + 0.19 * (quality / 100.0)
                + 0.12 * n["novelty"]
                + 0.10 * n["under_recognition"]
                + 0.08 * n["relevance"]
                + 0.07 * n["newness"]
                + 0.06 * n["popularity"]
            )
            overall = 100 * (
                0.20 * (popular / 100.0)
                + 0.20 * (momentum / 100.0)
                + 0.17 * (rising / 100.0)
                + 0.19 * (quality / 100.0)
                + 0.09 * n["relevance"]
                + 0.08 * n["novelty"]
                + 0.07 * signal_confidence
            )
            hidden_gem = 100 * (
                0.25 * (rising / 100.0)
                + 0.25 * (quality / 100.0)
                + 0.18 * n["novelty"]
                + 0.20 * n["under_recognition"]
                + 0.12 * n["relevance"]
            )

            base_penalty = 0.0
            if project.archived or project.disabled:
                base_penalty += 45.0
            if project.fork or project.is_template:
                base_penalty += 18.0
            if days_since(project.pushed_at, now) > 365:
                base_penalty += 12.0
            if not project.description:
                base_penalty += 5.0
            evidence_penalty = 0.0
            if "thin-description" in project.risk_flags:
                evidence_penalty += 2.0
            if "license-unverified" in project.risk_flags:
                evidence_penalty += 2.0
            if "low-fork-depth" in project.risk_flags:
                evidence_penalty += 1.5

            project.catalog_scores[catalog_id] = {
                "popular": round(max(popular - base_penalty, 0.0), 2),
                "momentum": round(max(momentum - base_penalty, 0.0), 2),
                "rising": round(max(rising - base_penalty, 0.0), 2),
                "quality": round(max(quality - base_penalty - evidence_penalty, 0.0), 2),
                "interesting": round(
                    max(interesting - base_penalty - 0.5 * evidence_penalty, 0.0), 2
                ),
                "overall": round(
                    max(overall - base_penalty - 0.5 * evidence_penalty, 0.0), 2
                ),
                "hidden_gem": round(
                    max(hidden_gem - base_penalty - evidence_penalty, 0.0), 2
                ),
                "relevance": round(rows[index]["relevance"] * 100, 2),
                "novelty": round(n["novelty"] * 100, 2),
                "under_recognition": round(n["under_recognition"] * 100, 2),
                "signal_confidence": round(rows[index]["measurement"] * 100, 2),
            }
            project.dimensions["novelty"] = max(
                project.dimensions.get("novelty", 0.0), round(n["novelty"] * 100, 2)
            )
            project.dimensions["under_recognition"] = max(
                project.dimensions.get("under_recognition", 0.0),
                round(n["under_recognition"] * 100, 2),
            )

    for project in projects:
        native_scores = [
            values.get("interesting", 0.0)
            for catalog_id, values in project.catalog_scores.items()
            if catalog_id != aggregate_id
        ]
        best_interesting = max(native_scores or [0.0])
        confidence_gap = 100.0 - project.dimensions.get("signal_confidence", 0.0)
        project.review_priority = round(
            clamp(
                0.56 * (best_interesting / 100.0)
                + 0.25 * (confidence_gap / 100.0)
                + 0.05 * min(len(project.risk_flags), 4)
                + 0.14 * min(
                    math.log1p(max(float(project.growth.get("stars_per_day") or 0.0), 0.0))
                    / math.log(1001),
                    1.0,
                )
            )
            * 100,
            2,
        )
        best_catalog = ""
        best_score = -1.0
        for catalog_id, values in project.catalog_scores.items():
            if catalog_id == aggregate_id:
                continue
            value = float(values.get("interesting", 0.0))
            if value > best_score:
                best_catalog, best_score = catalog_id, value
        project.insights.update(
            {
                "best_catalog": best_catalog,
                "best_interesting_score": round(max(best_score, 0.0), 2),
                "requires_review": bool(project.risk_flags and project.review_priority >= 55),
            }
        )


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


def project_rank_key(project: Project, catalog_id: str, score: str) -> tuple[Any, ...]:
    scores = project.catalog_scores.get(catalog_id, {})
    primary = (
        float(project.growth.get("delta_1d") or 0.0)
        if score == "daily_mover"
        else float(scores.get(score, 0.0))
    )
    return (
        primary,
        float(scores.get("quality", 0.0)),
        float(scores.get("signal_confidence", 0.0)),
        project.stars,
        len(project.provenance),
        project.full_name.lower(),
    )


def diverse_top(
    projects: list[Project], catalog_id: str, score: str, limit: int, max_per_owner: int
) -> list[Project]:
    owner_counts: dict[str, int] = {}
    selected: list[Project] = []
    for project in sorted(
        projects,
        key=lambda value: project_rank_key(value, catalog_id, score),
        reverse=True,
    ):
        owner = project.owner.lower()
        if owner_counts.get(owner, 0) >= max_per_owner:
            continue
        selected.append(project)
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def cross_catalog_diverse_top(
    projects: list[Project],
    catalog_id: str,
    score: str,
    limit: int,
    max_per_owner: int,
    native_catalog_ids: list[str],
    min_per_catalog: int,
    max_per_catalog: int,
) -> list[Project]:
    """Build a score-ordered aggregate board with best-effort domain coverage."""
    if limit <= 0 or not projects:
        return []
    ordered = sorted(
        projects,
        key=lambda value: project_rank_key(value, catalog_id, score),
        reverse=True,
    )
    native = [value for value in native_catalog_ids if value and value != catalog_id]
    if not native:
        return diverse_top(projects, catalog_id, score, limit, max_per_owner)

    min_per_catalog = max(int(min_per_catalog), 0)
    max_per_catalog = max(int(max_per_catalog), 1)
    if max_per_catalog < min_per_catalog:
        max_per_catalog = min_per_catalog

    owner_counts: dict[str, int] = {}
    catalog_counts = {value: 0 for value in native}
    selected: list[Project] = []
    selected_ids: set[str] = set()

    def add(project: Project, assigned_catalog: str) -> bool:
        if project.id in selected_ids:
            return False
        owner = project.owner.lower()
        if owner_counts.get(owner, 0) >= max_per_owner:
            return False
        if catalog_counts.get(assigned_catalog, 0) >= max_per_catalog:
            return False
        selected.append(project)
        selected_ids.add(project.id)
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
        catalog_counts[assigned_catalog] = catalog_counts.get(assigned_catalog, 0) + 1
        return True

    # If every domain cannot fit, rotate which domains receive reserved positions
    # using the score of their best current candidate rather than config order.
    domain_order = sorted(
        native,
        key=lambda native_id: max(
            (
                project_rank_key(project, catalog_id, score)
                for project in ordered
                if native_id in project.catalogs
            ),
            default=(-1.0,),
        ),
        reverse=True,
    )
    for _ in range(min_per_catalog):
        for native_id in domain_order:
            if len(selected) >= limit:
                break
            if catalog_counts[native_id] >= min_per_catalog:
                continue
            for project in ordered:
                if native_id not in project.catalogs:
                    continue
                if add(project, native_id):
                    break

    native_order = {value: index for index, value in enumerate(domain_order)}
    for project in ordered:
        if len(selected) >= limit:
            break
        memberships = [
            value
            for value in domain_order
            if value in project.catalogs and catalog_counts[value] < max_per_catalog
        ]
        if not memberships:
            continue
        assigned = min(
            memberships,
            key=lambda value: (catalog_counts[value], native_order[value]),
        )
        add(project, assigned)

    return sorted(
        selected,
        key=lambda value: project_rank_key(value, catalog_id, score),
        reverse=True,
    )


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

    aggregate_id = str(config["aggregate_catalog_id"])
    native_catalog_ids = [
        str(item["id"])
        for item in config["catalogs"]
        if isinstance(item, dict) and item.get("id") != aggregate_id
    ]

    def select(values: list[Project], score_key: str) -> list[Project]:
        if catalog_id != aggregate_id:
            return diverse_top(values, catalog_id, score_key, limit, diversity)
        return cross_catalog_diverse_top(
            values,
            catalog_id,
            score_key,
            limit,
            diversity,
            native_catalog_ids,
            int(config.get("aggregate_min_per_catalog", 1)),
            int(config.get("aggregate_max_per_catalog", 3)),
        )

    return {
        "interesting": select(members, "interesting"),
        "high_momentum": select(members, "momentum"),
        "up_and_coming": select(up_and_coming, "rising"),
        "high_quality": select(members, "quality"),
        "hidden_gems": select(hidden, "hidden_gem"),
        "most_popular": select(members, "popular"),
        "new_projects": select(new_projects, "rising"),
        "daily_movers": select(movers, "daily_mover"),
    }
