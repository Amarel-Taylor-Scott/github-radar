"""Offline tests for the configurable, repository-level Project Radar."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "project_radar.py"
SPEC = importlib.util.spec_from_file_location("project_radar_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
radar = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = radar
SPEC.loader.exec_module(radar)

NOW = datetime(2026, 8, 31, 15, 36, tzinfo=timezone.utc)


def config() -> dict:
    return {
        "schema_version": 1,
        "aggregate_catalog_id": "all",
        "history_days": 90,
        "active_window_days": 120,
        "new_project_days": 180,
        "max_search_requests": 8,
        "active_results_per_query": 20,
        "new_results_per_query": 10,
        "max_repository_enrichments": 0,
        "max_projects": 100,
        "leaderboard_size": 10,
        "max_projects_per_owner": 1,
        "aggregate_min_per_catalog": 1,
        "aggregate_max_per_catalog": 3,
        "leaderboard_min_stars": 1,
        "leaderboard_max_idle_days": 365,
        "up_and_coming_max_stars": 25000,
        "up_and_coming_max_age_days": 1095,
        "hidden_gem_max_stars": 5000,
        "minimum_total_projects": 2,
        "minimum_previous_ratio": 0.5,
        "minimum_previous_catalog_ratio": 0.5,
        "search_interval_seconds": 0,
        "request_interval_seconds": 0,
        "catalogs": [
            {
                "id": "all",
                "title": "All",
                "description": "Everything",
                "minimum_items": 2,
                "excluded_project_types": ["resource-list", "education", "template"],
            },
            {
                "id": "alpha",
                "title": "Alpha",
                "description": "Alpha projects",
                "topics": ["alpha", "alpha-tools", "alpha-runtime"],
                "keywords": ["alpha"],
                "minimum_items": 1,
                "excluded_project_types": ["resource-list", "education", "template"],
                "queries": [
                    {
                        "id": "alpha:text",
                        "query": "alpha in:name,description stars:>{min_stars} pushed:>={active_since}",
                    }
                ],
            },
            {
                "id": "beta",
                "title": "Beta",
                "description": "Beta projects",
                "topics": ["beta"],
                "keywords": ["beta"],
                "minimum_items": 1,
                "excluded_project_types": ["resource-list", "education", "template"],
                "queries": [
                    {
                        "id": "beta:text",
                        "query": "beta in:name,description stars:>{min_stars} pushed:>={active_since}",
                    }
                ],
            },
        ],
    }


def project(
    full_name: str,
    *,
    catalogs: list[str],
    stars: int = 100,
    forks: int = 20,
    watchers: int = 4,
    created_at: str = "2026-06-01T00:00:00Z",
    pushed_at: str = "2026-08-30T00:00:00Z",
    description: str = "A well documented alpha project for production use.",
) -> object:
    item = radar.Project(
        full_name=full_name,
        description=description,
        language="Python",
        topics=[catalogs[0] if catalogs else "project", "open-source"],
        license_spdx="MIT",
        stars=stars,
        forks=forks,
        watchers=watchers,
        size_kb=2000,
        created_at=created_at,
        pushed_at=pushed_at,
        updated_at=pushed_at,
        has_issues=True,
        has_discussions=True,
        api_complete=True,
        catalogs=catalogs,
        provenance=["github-search:test"],
        matched_topics=[catalogs[0] if catalogs else ""],
        source_confidence=0.7,
    )
    item.project_type = radar.classify_project(item)
    return item


class QueryScheduleTests(unittest.TestCase):
    def test_schedule_is_bounded_safe_and_fair(self) -> None:
        specs = radar.build_query_specs(config(), NOW)
        self.assertEqual(8, len(specs))
        self.assertTrue(all("archived:false" in spec.query for spec in specs))
        self.assertTrue(all("fork:false" in spec.query for spec in specs))
        self.assertEqual({"alpha", "beta"}, {spec.catalog_id for spec in specs})
        self.assertIn("beta:text", {spec.id for spec in specs})
        self.assertGreaterEqual(sum(spec.catalog_id == "alpha" for spec in specs), 3)
        self.assertGreaterEqual(sum(spec.catalog_id == "beta" for spec in specs), 3)


class CollectorIntegrationTests(unittest.TestCase):
    def test_fake_collection_runs_end_to_end(self) -> None:
        payload = {
            "full_name": "acme/alpha-runtime",
            "name": "alpha-runtime",
            "html_url": "https://github.com/acme/alpha-runtime",
            "description": "A production alpha runtime and developer tool.",
            "homepage": "https://example.test",
            "language": "Python",
            "topics": ["alpha", "developer-tools"],
            "license": {"spdx_id": "MIT"},
            "stargazers_count": 125,
            "forks_count": 20,
            "subscribers_count": 4,
            "open_issues_count": 3,
            "size": 2500,
            "created_at": "2026-07-01T00:00:00Z",
            "pushed_at": "2026-08-30T00:00:00Z",
            "updated_at": "2026-08-30T00:00:00Z",
            "default_branch": "main",
            "owner": {"login": "acme", "type": "Organization"},
            "archived": False,
            "disabled": False,
            "fork": False,
            "is_template": False,
            "has_issues": True,
            "has_discussions": True,
            "has_wiki": False,
            "has_pages": False,
        }

        class FakeGitHub:
            def search_repositories(self, query, limit, *, sort="stars", order="desc"):
                return [payload] if "alpha" in query else []

            def repository(self, full_name):
                return radar.Project.from_api(payload)

        cfg = config()
        cfg["max_search_requests"] = 4
        collector = radar.Collector(cfg, FakeGitHub(), NOW)
        projects, health = collector.collect()
        self.assertEqual(1, len(projects))
        self.assertEqual("repo:acme/alpha-runtime", projects[0].id)
        self.assertEqual("project", projects[0].project_type)
        self.assertEqual(["alpha", "all"], projects[0].catalogs)
        self.assertEqual(4, len(health))
        self.assertTrue(any(entry["ok"] for entry in health if entry["catalog"] == "alpha"))


class ProjectModelTests(unittest.TestCase):
    def test_merge_preserves_strongest_metadata_and_evidence(self) -> None:
        left = project("Owner/Repo", catalogs=["alpha"], stars=10, description="short")
        right = project(
            "owner/repo",
            catalogs=["beta"],
            stars=25,
            description="A substantially longer and more useful project description.",
        )
        right.provenance = ["github-search:other"]
        right.matched_topics = ["beta"]
        left.merge(right)
        self.assertEqual(25, left.stars)
        self.assertEqual(["alpha", "beta"], left.catalogs)
        self.assertEqual(2, len(left.provenance))
        self.assertIn("substantially", left.description)
        self.assertEqual("repo:owner/repo", left.id)

    def test_first_snapshot_does_not_fabricate_zero_deltas(self) -> None:
        item = project("acme/alpha", catalogs=["alpha", "all"], stars=120)
        growth = radar.calculate_growth(item, {"schema_version": 1, "days": {}}, NOW)
        self.assertIsNone(growth["delta_1d"])
        self.assertIsNone(growth["delta_7d"])
        self.assertEqual("lifetime-estimate", growth["signal_source"])
        self.assertGreater(growth["stars_per_day"], 0)

    def test_observed_history_calculates_growth_and_acceleration(self) -> None:
        item = project("acme/alpha", catalogs=["alpha", "all"], stars=150, forks=30, watchers=8)
        history = {
            "schema_version": 1,
            "days": {
                "2026-08-17": {"acme/alpha": {"stars": 100, "forks": 18, "watchers": 3}},
                "2026-08-24": {"acme/alpha": {"stars": 120, "forks": 22, "watchers": 5}},
                "2026-08-30": {"acme/alpha": {"stars": 145, "forks": 28, "watchers": 7}},
            },
        }
        growth = radar.calculate_growth(item, history, NOW)
        self.assertEqual(5, growth["delta_1d"])
        self.assertEqual(30, growth["delta_7d"])
        self.assertEqual(8, growth["fork_delta_7d"])
        self.assertEqual(3, growth["watcher_delta_7d"])
        self.assertEqual("observed-history", growth["signal_source"])
        self.assertGreater(growth["acceleration"], 0)


class RankingAndOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = config()
        self.projects = [
            project("one/fast", catalogs=["alpha", "all"], stars=800, forks=80),
            project(
                "two/new",
                catalogs=["alpha", "beta", "all"],
                stars=120,
                forks=25,
                created_at="2026-08-01T00:00:00Z",
            ),
            project("three/stable", catalogs=["beta", "all"], stars=4000, forks=500),
        ]
        history = {
            "schema_version": 1,
            "days": {
                "2026-08-24": {
                    "one/fast": {"stars": 500, "forks": 60, "watchers": 3},
                    "two/new": {"stars": 20, "forks": 4, "watchers": 1},
                    "three/stable": {"stars": 3995, "forks": 499, "watchers": 4},
                }
            },
        }
        radar.score_projects(self.projects, self.cfg, history, NOW)

    def test_scores_are_separate_catalog_local_dimensions(self) -> None:
        for item in self.projects:
            for catalog_id in item.catalogs:
                scores = item.catalog_scores[catalog_id]
                for key in (
                    "popular",
                    "momentum",
                    "rising",
                    "quality",
                    "interesting",
                    "overall",
                    "hidden_gem",
                    "relevance",
                ):
                    self.assertGreaterEqual(scores[key], 0)
                    self.assertLessEqual(scores[key], 100)
        self.assertNotEqual(
            self.projects[1].catalog_scores["alpha"]["interesting"],
            self.projects[1].catalog_scores["beta"]["interesting"],
        )

    def test_owner_diversity_is_enforced(self) -> None:
        duplicate_owner = project("one/second", catalogs=["alpha", "all"], stars=700)
        radar.score_projects([*self.projects, duplicate_owner], self.cfg, {"days": {}}, NOW)
        selected = radar.diverse_top(
            [self.projects[0], duplicate_owner, self.projects[1]],
            "alpha",
            "interesting",
            3,
            1,
        )
        self.assertEqual(2, len(selected))
        self.assertEqual(2, len({item.owner.lower() for item in selected}))

    def test_cross_domain_board_reserves_native_catalog_coverage(self) -> None:
        cfg = config()
        cfg["leaderboard_size"] = 2
        cfg["aggregate_min_per_catalog"] = 1
        cfg["aggregate_max_per_catalog"] = 1
        projects = [
            project("alpha-owner/alpha-one", catalogs=["alpha", "all"], stars=900),
            project("alpha-two/alpha-two", catalogs=["alpha", "all"], stars=800),
            project("beta-owner/beta-one", catalogs=["beta", "all"], stars=20),
        ]
        radar.score_projects(projects, cfg, {"days": {}}, NOW)
        aggregate = next(item for item in cfg["catalogs"] if item["id"] == "all")
        boards = radar.catalog_leaderboards(projects, aggregate, cfg, NOW)
        selected = boards["interesting"]
        self.assertEqual(2, len(selected))
        self.assertTrue(any("alpha" in item.catalogs for item in selected))
        self.assertTrue(any("beta" in item.catalogs for item in selected))
        self.assertGreaterEqual(
            selected[0].catalog_scores["all"]["interesting"],
            selected[1].catalog_scores["all"]["interesting"],
        )

    def test_validation_and_output_bundle(self) -> None:
        health = [
            {"catalog": "alpha", "mode": "active", "ok": True},
            {"catalog": "beta", "mode": "active", "ok": True},
        ]
        radar.validate_collection(self.projects, self.cfg, health)
        history = radar.update_history({"schema_version": 1, "days": {}}, self.projects, NOW, 90)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            counts = radar.write_outputs(
                self.projects,
                self.cfg,
                history,
                health,
                NOW,
                output_dir=base / "feeds",
                site_dir=base / "site",
            )
            self.assertEqual(3, counts["all"])
            latest = json.loads((base / "feeds" / "latest.json").read_text(encoding="utf-8"))
            status = json.loads((base / "feeds" / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(3, latest["count"])
            self.assertTrue(status["ok"])
            self.assertTrue((base / "feeds" / "alpha.md").exists())
            self.assertTrue((base / "site" / "index.html").exists())

    def test_per_catalog_shrink_guard_rejects_partial_collapse(self) -> None:
        health = [
            {"catalog": "alpha", "mode": "active", "ok": True},
            {"catalog": "beta", "mode": "active", "ok": True},
        ]
        with self.assertRaisesRegex(ValueError, "catalog shrink guards"):
            radar.validate_collection(
                self.projects,
                self.cfg,
                health,
                previous=3,
                previous_catalogs={"alpha": 100, "beta": 1},
                allow_shrink=False,
            )

    def test_shrink_guard_rejects_suspicious_collection(self) -> None:
        health = [
            {"catalog": "alpha", "mode": "active", "ok": True},
            {"catalog": "beta", "mode": "active", "ok": True},
        ]
        with self.assertRaisesRegex(ValueError, "shrank"):
            radar.validate_collection(
                self.projects,
                self.cfg,
                health,
                previous=100,
                allow_shrink=False,
            )


if __name__ == "__main__":
    unittest.main()
