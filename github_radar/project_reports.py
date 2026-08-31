"""Change feeds, review queues, Atom output, and badge endpoints for Project Radar."""

from __future__ import annotations

import hashlib
import html
import json
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from github_radar.project_common import (
    MANIFEST_SCHEMA_URL,
    PUBLICATION_SCHEMA,
    Project,
    _valid_license,
    atomic_write,
    days_since,
    markdown_escape,
)
from github_radar.project_discovery import catalog_map
from github_radar.project_scoring import catalog_leaderboards, rankable


def load_previous_dataset(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _project_summary(project: Project, aggregate_id: str) -> dict[str, Any]:
    scores = project.catalog_scores.get(aggregate_id, {})
    return {
        "id": project.id,
        "full_name": project.full_name,
        "url": project.html_url,
        "description": project.description,
        "stars": project.stars,
        "forks": project.forks,
        "language": project.language,
        "catalogs": [value for value in project.catalogs if value != aggregate_id],
        "best_catalog": project.insights.get("best_catalog", ""),
        "interesting": scores.get("interesting", 0.0),
        "momentum": scores.get("momentum", 0.0),
        "quality": scores.get("quality", 0.0),
        "signal_confidence": project.growth.get("signal_confidence", 0.0),
        "risk_flags": project.risk_flags,
        "review_priority": project.review_priority,
    }


def current_leaderboards(
    projects: list[Project], config: dict[str, Any], now: datetime
) -> dict[str, dict[str, list[str]]]:
    return {
        catalog_id: {
            key: [project.id for project in values]
            for key, values in catalog_leaderboards(projects, catalog, config, now).items()
        }
        for catalog_id, catalog in catalog_map(config).items()
    }


def build_changes(
    projects: list[Project],
    config: dict[str, Any],
    previous: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    generated_at = now.replace(microsecond=0).isoformat()
    aggregate_id = str(config["aggregate_catalog_id"])
    limit = max(int(config.get("changes_limit", 50)), 1)
    current_by_id = {project.id: project for project in projects}
    previous_projects = previous.get("projects", []) if isinstance(previous, dict) else []
    previous_by_id = {
        str(item.get("id")): item
        for item in previous_projects
        if isinstance(item, dict) and item.get("id")
    }

    added = [project for project in projects if project.id not in previous_by_id]
    added.sort(
        key=lambda project: (
            project.catalog_scores.get(aggregate_id, {}).get("interesting", 0.0),
            project.stars,
        ),
        reverse=True,
    )
    removed = [
        {
            "id": project_id,
            "full_name": str(item.get("full_name") or ""),
            "url": str(item.get("html_url") or ""),
            "stars": int(item.get("stars") or 0),
            "catalogs": item.get("catalogs") or [],
        }
        for project_id, item in previous_by_id.items()
        if project_id not in current_by_id
    ]
    removed.sort(key=lambda item: item["stars"], reverse=True)

    star_changes: list[dict[str, Any]] = []
    for project_id, project in current_by_id.items():
        old = previous_by_id.get(project_id)
        if not old:
            continue
        delta = project.stars - int(old.get("stars") or 0)
        if delta == 0:
            continue
        row = _project_summary(project, aggregate_id)
        row["star_change"] = delta
        star_changes.append(row)
    star_changes.sort(key=lambda item: (item["star_change"], item["stars"]), reverse=True)

    current_boards = current_leaderboards(projects, config, now)
    previous_boards = previous.get("leaderboards", {}) if isinstance(previous, dict) else {}
    board_changes: dict[str, dict[str, Any]] = {}
    for catalog_id, boards in current_boards.items():
        board_changes[catalog_id] = {}
        prior_catalog = previous_boards.get(catalog_id, {}) if isinstance(previous_boards, dict) else {}
        for board_name, ids in boards.items():
            prior_ids = prior_catalog.get(board_name, []) if isinstance(prior_catalog, dict) else []
            prior_positions = {value: index + 1 for index, value in enumerate(prior_ids)}
            current_positions = {value: index + 1 for index, value in enumerate(ids)}
            movements = []
            for project_id, current_rank in current_positions.items():
                if project_id not in prior_positions:
                    continue
                previous_rank = prior_positions[project_id]
                if previous_rank == current_rank:
                    continue
                project = current_by_id.get(project_id)
                if project is None:
                    continue
                movements.append(
                    {
                        "id": project_id,
                        "full_name": project.full_name,
                        "url": project.html_url,
                        "previous_rank": previous_rank,
                        "current_rank": current_rank,
                        "movement": previous_rank - current_rank,
                    }
                )
            movements.sort(key=lambda item: (item["movement"], -item["current_rank"]), reverse=True)
            board_changes[catalog_id][board_name] = {
                "new_entries": [
                    _project_summary(current_by_id[value], aggregate_id)
                    for value in ids
                    if value not in prior_positions and value in current_by_id
                ][:limit],
                "exits": [value for value in prior_ids if value not in current_positions][:limit],
                "movements": movements[:limit],
            }

    return {
        "schema_version": PUBLICATION_SCHEMA,
        "generated_at": generated_at,
        "previous_generated_at": previous.get("generated_at") if previous else None,
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "baseline": not bool(previous_by_id),
        "counts": {
            "current": len(projects),
            "previous": len(previous_by_id),
            "added": len(added),
            "removed": len(removed),
            "changed_stars": len(star_changes),
        },
        "new_discoveries": [_project_summary(project, aggregate_id) for project in added[:limit]],
        "removed_projects": removed[:limit],
        "top_star_changes": star_changes[:limit],
        "leaderboards": board_changes,
    }


def render_changes_markdown(changes: dict[str, Any], aggregate_id: str) -> str:
    generated = changes.get("generated_at", "unknown")
    previous = changes.get("previous_generated_at") or "no previous publication"
    counts = changes.get("counts", {})
    lines = [
        "# Project Radar changes",
        "",
        f"_Generated {generated}; compared with {previous}._",
        "",
        f"Current projects: **{int(counts.get('current', 0)):,}** · New discoveries: **{int(counts.get('added', 0)):,}** · Removed or no longer discovered: **{int(counts.get('removed', 0)):,}**",
        "",
    ]
    if changes.get("baseline"):
        lines.extend(
            [
                "> This is the first comparable publication. Rank movement and run-to-run star changes will appear automatically on the next successful run.",
                "",
            ]
        )

    lines.extend(["## New discoveries", ""])
    new_items = changes.get("new_discoveries", [])
    if new_items:
        lines.extend(
            [
                "| Project | Stars | Interesting | Best catalog |",
                "|:--|--:|--:|:--|",
            ]
        )
        for item in new_items:
            lines.append(
                f"| [{markdown_escape(item.get('full_name'))}]({item.get('url')}) | {int(item.get('stars') or 0):,} | {float(item.get('interesting') or 0):.1f} | {markdown_escape(item.get('best_catalog'))} |"
            )
    else:
        lines.append("No newly discovered repositories in this run.")
    lines.extend(["", "## Largest star changes since the previous publication", ""])
    gains = changes.get("top_star_changes", [])
    if gains:
        lines.extend(
            [
                "| Project | Change | Stars | Signal confidence |",
                "|:--|--:|--:|--:|",
            ]
        )
        for item in gains:
            lines.append(
                f"| [{markdown_escape(item.get('full_name'))}]({item.get('url')}) | {int(item.get('star_change') or 0):+d} | {int(item.get('stars') or 0):,} | {100 * float(item.get('signal_confidence') or 0):.0f}% |"
            )
    else:
        lines.append("No star-count changes were observed between publications.")

    aggregate = changes.get("leaderboards", {}).get(aggregate_id, {})
    interesting = aggregate.get("interesting", {}) if isinstance(aggregate, dict) else {}
    lines.extend(["", "## Aggregate Most Interesting rank movement", ""])
    movements = interesting.get("movements", []) if isinstance(interesting, dict) else []
    if movements:
        lines.extend(
            [
                "| Project | Previous | Current | Movement |",
                "|:--|--:|--:|--:|",
            ]
        )
        for item in movements:
            lines.append(
                f"| [{markdown_escape(item.get('full_name'))}]({item.get('url')}) | {int(item.get('previous_rank') or 0)} | {int(item.get('current_rank') or 0)} | {int(item.get('movement') or 0):+d} |"
            )
    else:
        lines.append("No comparable rank movement yet.")
    lines.append("")
    return "\n".join(lines)


def build_review_queue(
    projects: list[Project], config: dict[str, Any], now: datetime
) -> dict[str, Any]:
    aggregate_id = str(config["aggregate_catalog_id"])
    limit = max(int(config.get("review_queue_size", 100)), 1)
    candidates = [
        project
        for project in projects
        if project.risk_flags or project.insights.get("requires_review")
    ]
    candidates.sort(
        key=lambda project: (
            project.review_priority,
            project.catalog_scores.get(aggregate_id, {}).get("interesting", 0.0),
            project.stars,
        ),
        reverse=True,
    )
    return {
        "schema_version": PUBLICATION_SCHEMA,
        "generated_at": now.replace(microsecond=0).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "count": min(len(candidates), limit),
        "total_flagged": len(candidates),
        "note": "Flags identify evidence that deserves review; they are not findings of manipulation or misconduct.",
        "projects": [_project_summary(project, aggregate_id) for project in candidates[:limit]],
    }


def render_review_markdown(queue: dict[str, Any]) -> str:
    lines = [
        "# Project Radar review queue",
        "",
        f"_Generated {queue.get('generated_at', 'unknown')}. Showing {int(queue.get('count', 0)):,} of {int(queue.get('total_flagged', 0)):,} flagged records._",
        "",
        "> Flags identify incomplete or unusual evidence that deserves review. They are not findings of manipulation, insecurity, or misconduct.",
        "",
        "| Project | Priority | Stars | Signal confidence | Best catalog | Review flags |",
        "|:--|--:|--:|--:|:--|:--|",
    ]
    for item in queue.get("projects", []):
        flags = ", ".join(item.get("risk_flags") or [])
        lines.append(
            f"| [{markdown_escape(item.get('full_name'))}]({item.get('url')}) | {float(item.get('review_priority') or 0):.1f} | {int(item.get('stars') or 0):,} | {100 * float(item.get('signal_confidence') or 0):.0f}% | {markdown_escape(item.get('best_catalog'))} | {markdown_escape(flags)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_atom(
    projects: list[Project],
    config: dict[str, Any],
    now: datetime,
) -> str:
    aggregate_id = str(config["aggregate_catalog_id"])
    aggregate = catalog_map(config)[aggregate_id]
    top = catalog_leaderboards(projects, aggregate, config, now)["interesting"]
    updated = now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    base = "https://github.com/Amarel-Taylor-Scott/github-radar"
    entries = []
    for project in top:
        summary = html.escape(project.description or project.full_name)
        score = project.catalog_scores.get(aggregate_id, {}).get("interesting", 0.0)
        entries.append(
            "\n".join(
                [
                    "  <entry>",
                    f"    <id>urn:github-radar:{html.escape(project.id)}</id>",
                    f"    <title>{html.escape(project.full_name)} — interesting {score:.1f}</title>",
                    f"    <link href=\"{html.escape(project.html_url, quote=True)}\"/>",
                    f"    <updated>{updated}</updated>",
                    f"    <summary>{summary}</summary>",
                    "  </entry>",
                ]
            )
        )
    return "\n".join(
        [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<feed xmlns="http://www.w3.org/2005/Atom">',
            "  <id>tag:github.com,2026:Amarel-Taylor-Scott/github-radar/projects</id>",
            "  <title>Interesting GitHub Projects Radar</title>",
            f"  <updated>{updated}</updated>",
            f"  <link href=\"{base}/blob/main/feeds/projects/interesting-projects.md\"/>",
            "  <link rel=\"self\" href=\"https://raw.githubusercontent.com/Amarel-Taylor-Scott/github-radar/main/feeds/projects/projects.atom\"/>",
            *entries,
            "</feed>",
            "",
        ]
    )


def _percentage(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 1) if denominator else 0.0


def build_catalog_audit(
    projects: list[Project], config: dict[str, Any], now: datetime
) -> dict[str, Any]:
    """Summarize evidence coverage and leaderboard eligibility by catalog."""
    rows: list[dict[str, Any]] = []
    for catalog_id, catalog in catalog_map(config).items():
        members = [project for project in projects if catalog_id in project.catalogs]
        count = len(members)
        observed = sum(
            project.growth.get("signal_source") == "observed-history"
            for project in members
        )
        fully_measured = sum(
            float(project.growth.get("signal_confidence") or 0.0) >= 0.999
            for project in members
        )
        community = sum(project.community_profile_complete for project in members)
        licensed = sum(_valid_license(project.license_spdx) for project in members)
        descriptive = sum(len(project.description.strip()) >= 45 for project in members)
        active_30d = sum(days_since(project.pushed_at, now) <= 30 for project in members)
        flagged = sum(bool(project.risk_flags) for project in members)
        eligible = sum(rankable(project, catalog, config, now) for project in members)
        qualities = [
            float(project.catalog_scores.get(catalog_id, {}).get("quality", 0.0))
            for project in members
        ]
        rows.append(
            {
                "id": catalog_id,
                "title": str(catalog.get("title") or catalog_id),
                "count": count,
                "leaderboard_eligible": eligible,
                "observed_history": observed,
                "fully_measured_7d": fully_measured,
                "community_profiles": community,
                "verified_licenses": licensed,
                "descriptive_records": descriptive,
                "active_30d": active_30d,
                "flagged_for_review": flagged,
                "coverage": {
                    "leaderboard_eligible_pct": _percentage(eligible, count),
                    "observed_history_pct": _percentage(observed, count),
                    "fully_measured_7d_pct": _percentage(fully_measured, count),
                    "community_profile_pct": _percentage(community, count),
                    "verified_license_pct": _percentage(licensed, count),
                    "descriptive_pct": _percentage(descriptive, count),
                    "active_30d_pct": _percentage(active_30d, count),
                    "review_flag_pct": _percentage(flagged, count),
                },
                "median_quality": round(statistics.median(qualities), 2) if qualities else 0.0,
            }
        )
    return {
        "schema_version": PUBLICATION_SCHEMA,
        "generated_at": now.replace(microsecond=0).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "catalogs": rows,
    }


def render_catalog_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Project Radar evidence audit",
        "",
        f"_Generated {audit.get('generated_at', 'unknown')}._",
        "",
        "This report measures evidence coverage. A low percentage is a collection or verification gap, not a negative judgment about the underlying projects.",
        "",
        "| Catalog | Projects | Eligible | Observed | 7d measured | Community | License | Active 30d | Review flags | Median quality |",
        "|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for row in audit.get("catalogs", []):
        coverage = row.get("coverage", {})
        lines.append(
            "| {title} | {count:,} | {eligible:.1f}% | {observed:.1f}% | {measured:.1f}% | {community:.1f}% | {license:.1f}% | {active:.1f}% | {flags:.1f}% | {quality:.1f} |".format(
                title=markdown_escape(row.get("title")),
                count=int(row.get("count") or 0),
                eligible=float(coverage.get("leaderboard_eligible_pct") or 0.0),
                observed=float(coverage.get("observed_history_pct") or 0.0),
                measured=float(coverage.get("fully_measured_7d_pct") or 0.0),
                community=float(coverage.get("community_profile_pct") or 0.0),
                license=float(coverage.get("verified_license_pct") or 0.0),
                active=float(coverage.get("active_30d_pct") or 0.0),
                flags=float(coverage.get("review_flag_pct") or 0.0),
                quality=float(row.get("median_quality") or 0.0),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _manifest_entry(scope: str, root: Path, path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "scope": scope,
        "path": path.relative_to(root).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def write_publication_manifest(
    output_dir: Path, site_dir: Path, now: datetime
) -> dict[str, Any]:
    excluded = {"publication-manifest.json"}
    files: list[dict[str, Any]] = []
    for scope, root in (("feed", output_dir), ("site", site_dir)):
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name not in excluded:
                files.append(_manifest_entry(scope, root, path))
    manifest = {
        "schema_version": PUBLICATION_SCHEMA,
        "schema_url": MANIFEST_SCHEMA_URL,
        "generated_at": now.replace(microsecond=0).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "file_count": len(files),
        "total_bytes": sum(int(item["bytes"]) for item in files),
        "files": files,
    }
    content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    atomic_write(output_dir / "publication-manifest.json", content)
    atomic_write(site_dir / "publication-manifest.json", content)
    return manifest


def badge_payload(label: str, message: str, color: str) -> str:
    return json.dumps(
        {"schemaVersion": 1, "label": label, "message": message, "color": color},
        indent=2,
    ) + "\n"


def write_reports(
    projects: list[Project],
    config: dict[str, Any],
    previous: dict[str, Any],
    now: datetime,
    *,
    output_dir: Path,
    site_dir: Path,
) -> dict[str, int]:
    aggregate_id = str(config["aggregate_catalog_id"])
    changes = build_changes(projects, config, previous, now)
    queue = build_review_queue(projects, config, now)
    audit = build_catalog_audit(projects, config, now)
    changes_json = json.dumps(changes, indent=2, ensure_ascii=False) + "\n"
    queue_json = json.dumps(queue, indent=2, ensure_ascii=False) + "\n"
    audit_json = json.dumps(audit, indent=2, ensure_ascii=False) + "\n"
    changes_markdown = render_changes_markdown(changes, aggregate_id)
    queue_markdown = render_review_markdown(queue)
    audit_markdown = render_catalog_audit_markdown(audit)
    atom = render_atom(projects, config, now)
    atomic_write(output_dir / "changes.json", changes_json)
    atomic_write(output_dir / "changes.md", changes_markdown)
    atomic_write(output_dir / "review-queue.json", queue_json)
    atomic_write(output_dir / "review-queue.md", queue_markdown)
    atomic_write(output_dir / "audit.json", audit_json)
    atomic_write(output_dir / "audit.md", audit_markdown)
    atomic_write(output_dir / "projects.atom", atom)
    atomic_write(site_dir / "changes.json", changes_json)
    atomic_write(site_dir / "changes.md", changes_markdown)
    atomic_write(site_dir / "review-queue.json", queue_json)
    atomic_write(site_dir / "review-queue.md", queue_markdown)
    atomic_write(site_dir / "audit.json", audit_json)
    atomic_write(site_dir / "audit.md", audit_markdown)
    atomic_write(site_dir / "projects.atom", atom)

    badge_dir = site_dir / "badges"
    atomic_write(badge_dir / "count.json", badge_payload("projects", f"{len(projects):,}", "blue"))
    atomic_write(
        badge_dir / "freshness.json",
        badge_payload("updated", now.date().isoformat(), "brightgreen"),
    )
    for catalog_id, catalog in catalog_map(config).items():
        count = sum(catalog_id in project.catalogs for project in projects)
        atomic_write(
            badge_dir / f"{catalog_id}.json",
            badge_payload(str(catalog.get("title") or catalog_id), f"{count:,}", "blueviolet"),
        )
    manifest = write_publication_manifest(output_dir, site_dir, now)
    return {
        "new_discoveries": int(changes["counts"]["added"]),
        "removed": int(changes["counts"]["removed"]),
        "review_queue": int(queue["count"]),
        "audit_catalogs": len(audit.get("catalogs", [])),
        "manifest_files": int(manifest.get("file_count", 0)),
    }
