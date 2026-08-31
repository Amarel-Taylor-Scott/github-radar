from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_extension_radar.py"
SPEC = importlib.util.spec_from_file_location("codex_plugin_source_core", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
radar = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = radar
SPEC.loader.exec_module(radar)


class CodexMarketplaceTests(unittest.TestCase):
    def test_local_codex_marketplace_source_resolves_to_marketplace_repo(self) -> None:
        repository, path, ref, source_url = radar.resolve_marketplace_source(
            {
                "name": "linear",
                "source": {
                    "source": "local",
                    "path": "./plugins/linear",
                },
            },
            "openai/plugins",
        )

        self.assertEqual(repository, "openai/plugins")
        self.assertEqual(path, "plugins/linear")
        self.assertEqual(ref, "main")
        self.assertEqual(
            source_url,
            "https://github.com/openai/plugins/tree/main/plugins/linear",
        )

    def test_codex_plugin_manifest_normalizes_to_plugin_root(self) -> None:
        self.assertEqual(
            radar.component_root(
                "plugin", "plugins/linear/.codex-plugin/plugin.json"
            ),
            "plugins/linear",
        )


class ProductionConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(
            (ROOT / "agent_extensions.json").read_text(encoding="utf-8")
        )

    def test_current_openai_plugin_marketplaces_are_first_class_sources(self) -> None:
        marketplaces = {
            entry["id"]: entry
            for entry in self.config["marketplaces"]
        }
        self.assertEqual(
            marketplaces["openai-codex-official"]["repository"],
            "openai/plugins",
        )
        self.assertEqual(
            marketplaces["openai-role-specific"]["repository"],
            "openai/role-specific-plugins",
        )
        self.assertEqual(
            marketplaces["openai-codex-official"]["platforms"], ["codex"]
        )

    def test_deprecated_openai_skills_repo_is_not_a_trusted_seed(self) -> None:
        repositories = {
            entry["repository"] for entry in self.config["repository_seeds"]
        }
        self.assertNotIn("openai/skills", repositories)
        self.assertIn("openai/plugins", repositories)
        self.assertIn("openai/role-specific-plugins", repositories)

    def test_exact_codex_plugin_manifest_detector_is_enabled(self) -> None:
        queries = {entry["id"]: entry for entry in self.config["code_queries"]}
        detector = queries["codex-plugin-manifest"]
        self.assertEqual(detector["kind"], "plugin")
        self.assertEqual(detector["platforms"], ["codex"])
        self.assertRegex(
            "plugins/example/.codex-plugin/plugin.json",
            detector["path_regex"],
        )


if __name__ == "__main__":
    unittest.main()
