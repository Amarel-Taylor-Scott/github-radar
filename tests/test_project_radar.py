"""Offline tests for Project Radar publication schema v2."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
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
        "max_community_enrichments": 0,
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
        "provisional_momentum_weight": 0.2,
        "extreme_lifetime_velocity": 75,
        "review_queue_size": 20,
        "changes_limit": 20,
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
                "keywords": ["alpha", "runtime"],
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
    description: str = "A well documented alpha project for production runtime use.",
    topics: list[str] | None = None,
    community_health: int | None = None,
) -> object:
    item = radar.Project(
        full_name=full_name,
        description=description,
        homepage="https://example.test",
        language="Python",
        topics=topics or [catalogs[0] if catalogs else "project", "open-source"],
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
    if community_health is not None:
        item.community_profile_complete = True
        item.community_health = {
            "health_percentage": community_health,
            "has_readme": True,
            "has_contributing": community_health >= 60,
            "has_code_of_conduct": community_health >= 75,
            "has_issue_template": community_health >= 75,
            "has_pull_request_template": community_health >= 75,
            "has_detected_license": True,
        }
        item.evidence.append("github-community-profile")
    item.project_type = radar.classify_project(item)
    return item


def api_payload(full_name: str = "acme/alpha-runtime") -> dict:
    owner, name = full_name.split("/", 1)
    return {
        "full_name": full_name,
        "name": name,
        "html_url": f"https://github.com/{full_name}",
        "description": "A production alpha runtime and developer tool with complete documentation.",
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
        "owner": {"login": owner, "type": "Organization"},
        "archived": False,
        "disabled": False,
        "fork": False,
        "is_template": False,
        "has_issues": True,
        "has_discussions": True,
        "has_wiki": False,
        "has_pages": False,
    }


class ConfigAndQueryTests(unittest.TestCase):
    def test_load_config_applies_v2_defaults(self) -> None:
        cfg = config()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            loaded = radar.load_config(path)
        self.assertIn("max_community_enrichments", loaded)
        self.assertIn("provisional_momentum_weight", loaded)
        self.assertGreaterEqual(loaded["aggregate_max_per_catalog"], loaded["aggregate_min_per_catalog"])

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
    def test_fake_collection_enriches_repository_and_community_profile(self) -> None:
        payload = api_payload()

        class FakeGitHub:
            def search_repositories(self, query, limit, *, sort="stars", order="desc"):
                return [payload] if "alpha" in query else []

            def repository(self, full_name):
                return radar.Project.from_api(payload)

            def community_profile(self, full_name):
                return {
                    "health_percentage": 88,
                    "documentation": "https://example.test/docs",
                    "files": {
                        "readme": {"url": "x"},
                        "contributing": {"url": "x"},
                        "code_of_conduct": {"url": "x"},
                        "issue_template": {"url": "x"},
                        "pull_request_template": {"url": "x"},
                        "license": {"url": "x"},
                    },
                }

        cfg = config()
        cfg["max_search_requests"] = 4
        cfg["max_repository_enrichments"] = 1
        cfg["max_community_enrichments"] = 1
        collector = radar.Collector(cfg, FakeGitHub(), NOW)
        projects, health = collector.collect()
        self.assertEqual(1, len(projects))
        item = projects[0]
        self.assertEqual("repo:acme/alpha-runtime", item.id)
        self.assertEqual(["alpha", "all"], item.catalogs)
        self.assertTrue(item.community_profile_complete)
        self.assertEqual(88, item.community_health["health_percentage"])
        self.assertIn("github-community-profile", item.evidence)
        self.assertTrue(any(entry["mode"] == "community-health" for entry in health))


class ProjectModelAndHistoryTests(unittest.TestCase):
    def test_merge_preserves_strongest_metadata_and_evidence(self) -> None:
        left = project("Owner/Repo", catalogs=["alpha"], stars=10, description="short")
        right = project(
            "owner/repo",
            catalogs=["beta"],
            stars=25,
            description="A substantially longer and more useful project description.",
            community_health=91,
        )
        right.provenance = ["github-search:other"]
        right.matched_topics = ["beta"]
        left.merge(right)
        self.assertEqual(25, left.stars)
        self.assertEqual(["alpha", "beta"], left.catalogs)
        self.assertEqual(2, len(left.provenance))
        self.assertTrue(left.community_profile_complete)
        self.assertEqual(91, left.community_health["health_percentage"])
        self.assertEqual("repo:owner/repo", left.id)

    def test_first_snapshot_is_explicitly_low_confidence(self) -> None:
        item = project("acme/alpha", catalogs=["alpha", "all"], stars=120)
        growth = radar.calculate_growth(item, {"schema_version": 1, "days": {}}, NOW)
        self.assertIsNone(growth["delta_1d"])
        self.assertIsNone(growth["delta_7d"])
        self.assertEqual("lifetime-estimate", growth["signal_source"])
        self.assertEqual(0.25, growth["signal_confidence"])
        self.assertEqual("provisional-lifetime", growth["confidence_label"])
        self.assertTrue(growth["is_provisional"])

    def test_short_history_and_seven_day_history_raise_confidence(self) -> None:
        item = project("acme/alpha", catalogs=["alpha", "all"], stars=150)
        short = {
            "days": {"2026-08-30": {"acme/alpha": {"stars": 145, "forks": 18, "watchers": 3}}}
        }
        short_growth = radar.calculate_growth(item, short, NOW)
        self.assertEqual("observed-history", short_growth["signal_source"])
        self.assertGreater(short_growth["signal_confidence"], 0.25)
        self.assertLess(short_growth["signal_confidence"], 1.0)

        full = {
            "days": {
                "2026-08-17": {"acme/alpha": {"stars": 100, "forks": 15, "watchers": 2}},
                "2026-08-24": {"acme/alpha": {"stars": 120, "forks": 18, "watchers": 3}},
                "2026-08-30": {"acme/alpha": {"stars": 145, "forks": 25, "watchers": 6}},
            }
        }
        full_growth = radar.calculate_growth(item, full, NOW)
        self.assertEqual(30, full_growth["delta_7d"])
        self.assertEqual(1.0, full_growth["signal_confidence"])
        self.assertEqual("measured-7d", full_growth["confidence_label"])
        self.assertFalse(full_growth["is_provisional"])
        self.assertGreater(full_growth["acceleration"], 0)


class RankingTests(unittest.TestCase):
    def test_measured_velocity_outscores_equivalent_provisional_velocity(self) -> None:
        cfg = config()
        provisional = project(
            "new/provisional",
            catalogs=["alpha", "all"],
            stars=700,
            forks=70,
            created_at="2026-08-24T00:00:00Z",
            community_health=90,
        )
        measured = project(
            "old/measured",
            catalogs=["alpha", "all"],
            stars=700,
            forks=70,
            created_at="2025-08-24T00:00:00Z",
            community_health=90,
        )
        history = {
            "days": {
                "2026-08-24": {
                    "old/measured": {"stars": 0, "forks": 0, "watchers": 0}
                }
            }
        }
        radar.score_projects([provisional, measured], cfg, history, NOW)
        self.assertEqual(0.25, provisional.growth["signal_confidence"])
        self.assertEqual(1.0, measured.growth["signal_confidence"])
        self.assertGreater(
            measured.catalog_scores["alpha"]["momentum"],
            provisional.catalog_scores["alpha"]["momentum"],
        )

    def test_quality_uses_official_community_health_when_available(self) -> None:
        cfg = config()
        measured = project("org/measured", catalogs=["alpha", "all"], community_health=100)
        unmeasured = project("org2/unmeasured", catalogs=["alpha", "all"])
        radar.score_projects([measured, unmeasured], cfg, {"days": {}}, NOW)
        self.assertGreater(
            measured.catalog_scores["alpha"]["quality"],
            unmeasured.catalog_scores["alpha"]["quality"],
        )
        self.assertEqual(100.0, measured.dimensions["community_health"])

    def test_review_flags_focus_on_material_attention(self) -> None:
        cfg = config()
        quiet = project(
            "small/quiet",
            catalogs=["alpha", "all"],
            stars=20,
            forks=3,
            created_at="2025-01-01T00:00:00Z",
        )
        breakout = project(
            "new/breakout",
            catalogs=["alpha", "all"],
            stars=6000,
            forks=1,
            created_at="2026-08-25T00:00:00Z",
        )
        radar.score_projects([quiet, breakout], cfg, {"days": {}}, NOW)
        self.assertNotIn("community-health-unmeasured", quiet.risk_flags)
        self.assertIn("provisional-high-momentum", breakout.risk_flags)
        self.assertIn("community-health-unmeasured", breakout.risk_flags)
        self.assertIn("low-fork-depth", breakout.risk_flags)

    def test_scores_expose_novelty_under_recognition_and_confidence(self) -> None:
        cfg = config()
        common = project(
            "org/common",
            catalogs=["alpha", "all"],
            description="Alpha runtime framework for standard workflow automation and developer tools.",
            topics=["alpha", "runtime", "workflow"],
        )
        unusual = project(
            "org2/unusual",
            catalogs=["alpha", "all"],
            stars=35,
            forks=8,
            description="Alpha runtime for cryogenic spectrograph calibration and polarimetric telescope control.",
            topics=["alpha", "spectrograph", "polarimetry"],
        )
        radar.score_projects([common, unusual], cfg, {"days": {}}, NOW)
        for item in (common, unusual):
            scores = item.catalog_scores["alpha"]
            self.assertIn("novelty", scores)
            self.assertIn("under_recognition", scores)
            self.assertEqual(25.0, scores["signal_confidence"])
        self.assertGreater(
            unusual.catalog_scores["alpha"]["novelty"],
            common.catalog_scores["alpha"]["novelty"],
        )

    def test_aggregate_board_reserves_native_catalog_coverage(self) -> None:
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
        selected = radar.catalog_leaderboards(projects, aggregate, cfg, NOW)["interesting"]
        self.assertEqual(2, len(selected))
        self.assertTrue(any("alpha" in item.catalogs for item in selected))
        self.assertTrue(any("beta" in item.catalogs for item in selected))


class PublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = config()
        self.projects = [
            project("one/fast", catalogs=["alpha", "all"], stars=800, forks=80, community_health=90),
            project(
                "two/new",
                catalogs=["alpha", "beta", "all"],
                stars=120,
                forks=25,
                created_at="2026-08-01T00:00:00Z",
                topics=["alpha", "beta", "quantum-widget"],
            ),
            project("three/stable", catalogs=["beta", "all"], stars=4000, forks=500, community_health=80),
        ]
        self.history = {
            "schema_version": 1,
            "days": {
                "2026-08-24": {
                    "one/fast": {"stars": 500, "forks": 60, "watchers": 3},
                    "two/new": {"stars": 20, "forks": 4, "watchers": 1},
                    "three/stable": {"stars": 3995, "forks": 499, "watchers": 4},
                }
            },
        }
        radar.score_projects(self.projects, self.cfg, self.history, NOW)

    def test_validation_and_schema_v2_output_bundle(self) -> None:
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
            self.assertEqual(2, latest["schema_version"])
            self.assertEqual(3, latest["count"])
            self.assertIn("observed_history_projects", latest["measurement"])
            self.assertTrue(status["ok"])
            self.assertEqual("publication-manifest.json", status["publication_manifest"])
            self.assertTrue((base / "feeds" / "alpha.md").exists())
            self.assertTrue((base / "site" / "index.html").exists())

    def test_change_feed_review_queue_audit_atom_badges_and_manifest(self) -> None:
        previous = {
            "schema_version": 1,
            "generated_at": "2026-08-30T15:36:00+00:00",
            "projects": [
                {
                    "id": "repo:one/fast",
                    "full_name": "one/fast",
                    "html_url": "https://github.com/one/fast",
                    "stars": 750,
                    "catalogs": ["alpha", "all"],
                },
                {
                    "id": "repo:gone/old",
                    "full_name": "gone/old",
                    "html_url": "https://github.com/gone/old",
                    "stars": 100,
                    "catalogs": ["beta", "all"],
                },
            ],
            "leaderboards": {
                "all": {"interesting": ["repo:gone/old", "repo:one/fast"]}
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            feed_dir, site_dir = base / "feeds", base / "site"
            radar.write_outputs(
                self.projects,
                self.cfg,
                self.history,
                [{"catalog": "alpha", "mode": "active", "ok": True}, {"catalog": "beta", "mode": "active", "ok": True}],
                NOW,
                output_dir=feed_dir,
                site_dir=site_dir,
            )
            reports = radar.write_reports(
                self.projects,
                self.cfg,
                previous,
                NOW,
                output_dir=feed_dir,
                site_dir=site_dir,
            )
            self.assertGreaterEqual(reports["new_discoveries"], 1)
            for relative in (
                "changes.json",
                "changes.md",
                "review-queue.json",
                "review-queue.md",
                "audit.json",
                "audit.md",
                "projects.atom",
                "publication-manifest.json",
            ):
                self.assertTrue((feed_dir / relative).exists(), relative)
            self.assertTrue((site_dir / "badges" / "count.json").exists())
            atom = (feed_dir / "projects.atom").read_text(encoding="utf-8")
            self.assertIn("urn:github-radar:repo:", atom)
            audit = json.loads((feed_dir / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(3, len(audit["catalogs"]))
            manifest = json.loads((feed_dir / "publication-manifest.json").read_text(encoding="utf-8"))
            self.assertGreater(manifest["file_count"], 10)
            latest_entry = next(
                item for item in manifest["files"]
                if item["scope"] == "feed" and item["path"] == "latest.json"
            )
            raw = (feed_dir / "latest.json").read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), latest_entry["sha256"])

    def test_total_and_catalog_shrink_guards(self) -> None:
        health = [
            {"catalog": "alpha", "mode": "active", "ok": True},
            {"catalog": "beta", "mode": "active", "ok": True},
        ]
        with self.assertRaisesRegex(ValueError, "shrank"):
            radar.validate_collection(
                self.projects, self.cfg, health, previous=100, allow_shrink=False
            )
        with self.assertRaisesRegex(ValueError, "catalog shrink guards"):
            radar.validate_collection(
                self.projects,
                self.cfg,
                health,
                previous=3,
                previous_catalogs={"alpha": 100, "beta": 1},
                allow_shrink=False,
            )


if __name__ == "__main__":
    unittest.main()
