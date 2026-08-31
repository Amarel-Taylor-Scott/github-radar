from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compact_agent_extension_outputs.py"
SPEC = importlib.util.spec_from_file_location("compact_agent_extension_outputs_script", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
compact = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = compact
SPEC.loader.exec_module(compact)


class NormalizationTests(unittest.TestCase):
    def expanded_payload(self) -> dict:
        repository = {
            "full_name": "example/extensions",
            "html_url": "https://github.com/example/extensions",
            "description": "Example repository",
            "stars": 120,
            "forks": 12,
            "open_issues": 0,
            "watchers": 0,
            "created_at": "2026-01-01T00:00:00Z",
            "pushed_at": "2026-08-31T00:00:00Z",
            "updated_at": "2026-08-31T00:00:00Z",
            "language": "Python",
            "topics": ["agents"],
            "license_spdx": "MIT",
            "archived": False,
            "default_branch": "main",
            "owner_type": "Organization",
            "api_complete": True,
        }
        return {
            "schema_version": 1,
            "generated_at": "2026-08-31T12:00:00+00:00",
            "count": 2,
            "catalogs": [
                {"id": "claude-skills", "title": "Claude Skills", "count": 2}
            ],
            "items": [
                {
                    "id": "skill:example/extensions:skills/one",
                    "name": "one",
                    "kind": "skill",
                    "description": "First skill",
                    "platforms": ["claude"],
                    "catalogs": ["claude-skills"],
                    "repo": repository,
                    "path": "skills/one/SKILL.md",
                    "source_url": "https://github.com/example/extensions/tree/main/skills/one",
                    "provenance": ["test"],
                    "evidence": ["path:skills/one/SKILL.md"],
                    "category": "",
                    "author": "",
                    "trust": 0.9,
                    "manifest_valid": True,
                    "metadata": {},
                    "growth": {"delta_7d": None, "stars_per_day": 1.2},
                    "scores": {"overall": 80.0, "momentum": 82.0},
                },
                {
                    "id": "skill:example/extensions:skills/two",
                    "name": "two",
                    "kind": "skill",
                    "description": "Second skill",
                    "platforms": ["claude"],
                    "catalogs": ["claude-skills"],
                    "repo": dict(repository),
                    "path": "skills/two/SKILL.md",
                    "source_url": "https://github.com/example/extensions/tree/main/skills/two",
                    "provenance": ["test"],
                    "evidence": ["path:skills/two/SKILL.md"],
                    "trust": 0.9,
                    "manifest_valid": True,
                    "growth": {"delta_7d": 4, "stars_per_day": 2.0},
                    "scores": {"overall": 90.0, "momentum": 92.0},
                },
            ],
        }

    def test_repository_metadata_is_stored_once(self) -> None:
        normalized = compact.normalize_payload(self.expanded_payload())
        self.assertEqual(normalized["schema_version"], 2)
        self.assertEqual(normalized["count"], 2)
        self.assertEqual(list(normalized["repositories"]), ["example/extensions"])
        self.assertEqual(normalized["items"][0]["name"], "two")
        self.assertEqual(normalized["items"][0]["repo"], "example/extensions")
        self.assertNotIn("full_name", normalized["repositories"]["example/extensions"])
        self.assertNotIn("metadata", normalized["items"][1])

    def test_duplicate_item_ids_are_removed(self) -> None:
        payload = self.expanded_payload()
        payload["items"].append(dict(payload["items"][0]))
        normalized = compact.normalize_payload(payload)
        self.assertEqual(normalized["count"], 2)


class PublicationTests(unittest.TestCase):
    def test_compactor_rewrites_catalogs_and_static_page(self) -> None:
        expanded = NormalizationTests().expanded_payload()
        catalog = {
            "schema_version": 1,
            "generated_at": expanded["generated_at"],
            "catalog": {
                "id": "claude-skills",
                "title": "Claude Skills",
                "description": "Skills",
            },
            "count": 2,
            "leaderboards": {
                "high_momentum": [expanded["items"][1]["id"]],
                "popular": [expanded["items"][0]["id"]],
            },
            "items": expanded["items"],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            feed = root / "feeds"
            site = root / "site"
            feed.mkdir()
            site.mkdir()
            (feed / "latest.json").write_text(json.dumps(expanded), encoding="utf-8")
            (feed / "claude-skills.json").write_text(json.dumps(catalog), encoding="utf-8")
            (feed / "status.json").write_text(
                json.dumps({"ok": True, "items": 2}), encoding="utf-8"
            )

            stats = compact.compact_outputs(feed, site)

            self.assertEqual(stats["items"], 2)
            self.assertEqual(stats["repositories"], 1)
            latest = json.loads((feed / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["schema_version"], 2)
            self.assertEqual(latest["items"][0]["repo"], "example/extensions")
            self.assertEqual(
                (feed / "latest.json").read_text(encoding="utf-8"),
                (site / "latest.json").read_text(encoding="utf-8"),
            )

            catalog_payload = json.loads(
                (feed / "claude-skills.json").read_text(encoding="utf-8")
            )
            self.assertEqual(catalog_payload["dataset"], "latest.json")
            self.assertNotIn("items", catalog_payload)
            self.assertEqual(
                catalog_payload["leaderboards"]["high_momentum"],
                [expanded["items"][1]["id"]],
            )

            page = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn("fetch('latest.json'", page)
            self.assertNotIn("const items=", page)
            status = json.loads((feed / "status.json").read_text(encoding="utf-8"))
            self.assertTrue(status["normalized"])
            self.assertEqual(status["publication_schema"], 2)


if __name__ == "__main__":
    unittest.main()
