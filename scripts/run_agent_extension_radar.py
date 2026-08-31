#!/usr/bin/env python3
"""Run Agent Extension Radar with balanced enrichment and conservative ranking.

The core collector intentionally stays generic. This entrypoint supplies the
production policies that are specific to the multi-catalog deployment:

* repository metadata requests are allocated across catalogs instead of being
  consumed by whichever marketplace happens to be collected first;
* exact artifact evidence is enriched before weak keyword-only candidates;
* incomplete repository records are retained in the directory but excluded
  from public leaderboards when enough fully measured records exist;
* one repository may contribute only the configured number of entries to a
  leaderboard, with deterministic quality-aware tie breaking.

Keeping these policies in a small wrapper makes them independently testable and
prevents the discovery engine from accumulating deployment-specific constants.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
CORE_PATH = SCRIPT_DIR / "agent_extension_radar.py"
SPEC = importlib.util.spec_from_file_location("agent_extension_radar_core", CORE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery guard
    raise RuntimeError(f"Unable to load {CORE_PATH}")
core = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = core
SPEC.loader.exec_module(core)


def evidence_priority(item: Any) -> tuple[float, ...]:
    """Rank records for metadata enrichment without conflating trust and fame."""
    provenance = [str(value) for value in item.provenance]
    evidence = [str(value) for value in item.evidence]
    exact_artifact = bool(item.path) or any(value.startswith("path:") for value in evidence)
    explicit_seed = any(value.startswith("seed:") for value in provenance)
    code_match = any(value.startswith("code-search:") for value in provenance)
    marketplace = any(value.startswith("marketplace:") for value in provenance)
    source_count = len(set(provenance))
    return (
        float(explicit_seed),
        float(exact_artifact),
        float(code_match),
        float(marketplace),
        float(item.manifest_valid),
        min(float(item.trust), 1.0),
        float(source_count),
        float(item.repo.stars),
    )


class BalancedCollector(core.Collector):
    """Collector with round-robin repository enrichment across native catalogs."""

    def _enrich_repositories(self) -> None:
        repo_items: dict[str, list[Any]] = defaultdict(list)
        for item in self.items.values():
            if item.repo.full_name and not item.repo.api_complete:
                repo_items[item.repo.full_name].append(item)
        if not repo_items:
            return

        budget = max(int(self.config.get("max_repository_enrichments", 0)), 0)
        if budget == 0:
            return

        configured_catalogs = [
            str(value.get("id"))
            for value in self.config.get("catalogs", [])
            if isinstance(value, dict) and value.get("id")
        ]
        aggregate_id = str(self.config.get("include_all_catalog_id") or "")
        native_catalogs = [value for value in configured_catalogs if value != aggregate_id]
        if aggregate_id and any(
            aggregate_id in item.catalogs
            for values in repo_items.values()
            for item in values
        ):
            native_catalogs.append(aggregate_id)

        def repo_priority(full_name: str) -> tuple[Any, ...]:
            best = max(evidence_priority(item) for item in repo_items[full_name])
            return (*best, full_name.lower())

        candidates_by_catalog: dict[str, list[str]] = {}
        for catalog_id in native_catalogs:
            candidates = [
                full_name
                for full_name, values in repo_items.items()
                if any(catalog_id in item.catalogs for item in values)
            ]
            candidates_by_catalog[catalog_id] = sorted(
                set(candidates), key=repo_priority, reverse=True
            )

        selected: list[str] = []
        selected_set: set[str] = set()
        cursors = {catalog_id: 0 for catalog_id in candidates_by_catalog}

        # Allocate the scarce metadata budget in rounds. Small catalogs finish
        # naturally; their unused share flows to larger catalogs.
        made_progress = True
        while len(selected) < budget and made_progress:
            made_progress = False
            for catalog_id in native_catalogs:
                values = candidates_by_catalog.get(catalog_id, [])
                cursor = cursors.get(catalog_id, 0)
                while cursor < len(values) and values[cursor] in selected_set:
                    cursor += 1
                cursors[catalog_id] = cursor
                if cursor >= len(values):
                    continue
                full_name = values[cursor]
                cursors[catalog_id] = cursor + 1
                selected.append(full_name)
                selected_set.add(full_name)
                made_progress = True
                if len(selected) >= budget:
                    break

        # Fill any residual budget with the strongest remaining exact evidence.
        if len(selected) < budget:
            remaining = sorted(
                (name for name in repo_items if name not in selected_set),
                key=repo_priority,
                reverse=True,
            )
            selected.extend(remaining[: budget - len(selected)])

        for full_name in selected:
            enriched = self.github.repository(full_name)
            if enriched is None:
                continue
            for item in repo_items[full_name]:
                item.repo.merge(enriched)


def diverse_top(
    items: list[Any], score: str, limit: int, max_per_repo: int
) -> list[Any]:
    """Select deterministic, repository-diverse representatives."""
    counts: dict[str, int] = {}
    selected: list[Any] = []

    def ranking_key(item: Any) -> tuple[Any, ...]:
        return (
            float(item.scores.get(score, 0.0)),
            float(item.manifest_valid),
            min(float(item.trust), 1.0),
            len(item.provenance),
            len(item.description or ""),
            item.name.lower(),
            item.id,
        )

    for item in sorted(items, key=ranking_key, reverse=True):
        full_name = item.repo.full_name
        count = counts.get(full_name, 0)
        if count >= max_per_repo:
            continue
        selected.append(item)
        counts[full_name] = count + 1
        if len(selected) >= limit:
            break
    return selected


def catalog_leaderboards(
    items: list[Any], catalog_id: str, config: dict[str, Any], now: datetime
) -> dict[str, list[Any]]:
    """Build leaderboards from measured records, retaining all items in JSON."""
    eligible = [item for item in items if catalog_id in item.catalogs]
    measured = [
        item for item in eligible if item.repo.api_complete and not item.repo.archived
    ]
    minimum_measured = min(int(config["leaderboard_size"]), 10)
    rankable = measured if len(measured) >= minimum_measured else eligible
    limit = int(config["leaderboard_size"])
    diversity = max(int(config["max_items_per_repo_per_leaderboard"]), 1)
    new_items = [
        item
        for item in rankable
        if core.days_since(item.repo.created_at, now) <= 180
    ]
    return {
        "high_momentum": diverse_top(rankable, "momentum", limit, diversity),
        "rising": diverse_top(rankable, "rising", limit, diversity),
        "popular": diverse_top(rankable, "popular", limit, diversity),
        "new": diverse_top(new_items, "rising", limit, diversity),
        "overall": diverse_top(
            rankable, "overall", max(limit * 4, 100), diversity
        ),
    }


def install_production_policies() -> None:
    core.Collector = BalancedCollector
    core.diverse_top = diverse_top
    core.catalog_leaderboards = catalog_leaderboards


def main(argv: Optional[list[str]] = None) -> int:
    install_production_policies()
    return int(core.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
