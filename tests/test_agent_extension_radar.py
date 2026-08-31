from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_extension_radar.py"
SPEC = importlib.util.spec_from_file_location("agent_extension_radar_script", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
radar = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = radar
SPEC.loader.exec_module(radar)


class ParsingTests(unittest.TestCase):
    def test_skill_frontmatter_parses_scalars_and_multiline_description(self) -> None:
        parsed = radar.parse_frontmatter(
            """---
name: repo-auditor
description: >
  Review a repository and
  identify risky changes.
license: MIT
---
# Instructions
"""
        )
        self.assertEqual(parsed["name"], "repo-auditor")
        self.assertEqual(parsed["description"], "Review a repository and identify risky changes.")
        self.assertEqual(parsed["license"], "MIT")

    def test_component_paths_are_normalized_to_roots(self) -> None:
        self.assertEqual(
            radar.component_root("skill", ".claude/skills/review/SKILL.md"),
            ".claude/skills/review",
        )
        self.assertEqual(
            radar.component_root("plugin", "packages/demo/.claude-plugin/plugin.json"),
            "packages/demo",
        )
        self.assertEqual(radar.component_root("tool", ""), "@repository")

    def test_github_repo_url_supports_https_and_ssh(self) -> None:
        self.assertEqual(
            radar.github_repo_from_url("https://github.com/example/project.git/tree/main/plugin"),
            "example/project",
        )
        self.assertEqual(
            radar.github_repo_from_url("git@github.com:example/project.git"),
            "example/project",
        )


class HistoryAndScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    def test_observed_growth_replaces_lifetime_estimate(self) -> None:
        repo = radar.RepoInfo(
            full_name="example/fast",
            html_url="https://github.com/example/fast",
            stars=150,
            forks=20,
            created_at="2026-01-01T00:00:00Z",
            pushed_at="2026-08-31T00:00:00Z",
            updated_at="2026-08-31T00:00:00Z",
            api_complete=True,
        )
        history = {
            "schema_version": 1,
            "days": {
                "2026-08-30": {"example/fast": {"stars": 145}},
                "2026-08-24": {"example/fast": {"stars": 100}},
                "2026-08-17": {"example/fast": {"stars": 80}},
            },
        }
        growth = radar.calculate_growth(repo, history, self.now)
        self.assertEqual(growth["delta_1d"], 5)
        self.assertEqual(growth["delta_7d"], 50)
        self.assertEqual(growth["signal_source"], "observed-history")
        self.assertGreater(growth["acceleration"], 0)

    def test_scores_are_bounded_and_popularity_is_ordered(self) -> None:
        high_repo = radar.RepoInfo(
            full_name="example/high",
            html_url="https://github.com/example/high",
            description="A mature tool",
            stars=5000,
            forks=500,
            created_at="2025-01-01T00:00:00Z",
            pushed_at="2026-08-30T00:00:00Z",
            updated_at="2026-08-30T00:00:00Z",
            topics=["agents"],
            license_spdx="MIT",
            api_complete=True,
        )
        low_repo = radar.RepoInfo(
            full_name="example/low",
            html_url="https://github.com/example/low",
            description="A small tool",
            stars=8,
            forks=1,
            created_at="2026-08-01T00:00:00Z",
            pushed_at="2026-08-20T00:00:00Z",
            updated_at="2026-08-20T00:00:00Z",
            license_spdx="MIT",
            api_complete=True,
        )
        items = [
            radar.ExtensionItem(
                id="tool:example/high:@repository",
                name="high",
                kind="tool",
                repo=high_repo,
                platforms=["claude"],
                catalogs=["claude-tools"],
                provenance=["test"],
                trust=0.8,
            ),
            radar.ExtensionItem(
                id="tool:example/low:@repository",
                name="low",
                kind="tool",
                repo=low_repo,
                platforms=["claude"],
                catalogs=["claude-tools"],
                provenance=["test"],
                trust=0.4,
            ),
        ]
        radar.score_items(items, {"schema_version": 1, "days": {}}, self.now)
        self.assertGreater(items[0].scores["popular"], items[1].scores["popular"])
        for item in items:
            for score in item.scores.values():
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)


class OutputTests(unittest.TestCase):
    def test_output_bundle_contains_all_formats(self) -> None:
        now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
        repo = radar.RepoInfo(
            full_name="example/demo",
            html_url="https://github.com/example/demo",
            description="Demonstration extension",
            stars=100,
            forks=10,
            created_at="2026-07-01T00:00:00Z",
            pushed_at="2026-08-31T00:00:00Z",
            updated_at="2026-08-31T00:00:00Z",
            topics=["claude"],
            license_spdx="MIT",
            api_complete=True,
        )
        item = radar.ExtensionItem(
            id="skill:example/demo:skills/demo",
            name="demo-skill",
            kind="skill",
            repo=repo,
            path="skills/demo/SKILL.md",
            source_url="https://github.com/example/demo/tree/main/skills/demo",
            description="Demonstration extension",
            platforms=["claude"],
            catalogs=["claude-skills", "agent-extensions"],
            provenance=["test"],
            trust=0.9,
            manifest_valid=True,
        )
        history = {"schema_version": 1, "days": {}}
        radar.score_items([item], history, now)
        history = radar.update_history(history, [item], now, 45)
        config = {
            "schema_version": 1,
            "leaderboard_size": 25,
            "max_items_per_repo_per_leaderboard": 8,
            "catalogs": [
                {"id": "claude-skills", "title": "Claude Skills", "description": "Skills"},
                {"id": "agent-extensions", "title": "Agent Extensions", "description": "All"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            counts = radar.write_outputs(
                [item], config, history, now, output_dir=base / "feeds", site_dir=base / "site"
            )
            self.assertEqual(counts["claude-skills"], 1)
            self.assertTrue((base / "feeds" / "claude-skills.md").exists())
            self.assertTrue((base / "feeds" / "claude-skills.json").exists())
            self.assertTrue((base / "feeds" / "latest.json").exists())
            self.assertTrue((base / "site" / "index.html").exists())
            payload = json.loads((base / "feeds" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["items"][0]["name"], "demo-skill")


class ConfigTests(unittest.TestCase):
    def test_config_rejects_duplicate_catalog_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "catalogs": [{"id": "same"}, {"id": "same"}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                radar.load_config(path)


if __name__ == "__main__":
    unittest.main()
