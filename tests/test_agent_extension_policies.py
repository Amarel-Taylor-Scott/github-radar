from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_agent_extension_radar.py"
SPEC = importlib.util.spec_from_file_location("run_agent_extension_radar_script", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
policies = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = policies
SPEC.loader.exec_module(policies)
core = policies.core


class FakeGitHub:
    def __init__(self) -> None:
        self.requested: list[str] = []

    def repository(self, full_name: str) -> core.RepoInfo:
        self.requested.append(full_name)
        return core.RepoInfo(
            full_name=full_name,
            html_url=f"https://github.com/{full_name}",
            description=f"Metadata for {full_name}",
            stars=100,
            forks=10,
            created_at="2026-01-01T00:00:00Z",
            pushed_at="2026-08-31T00:00:00Z",
            updated_at="2026-08-31T00:00:00Z",
            license_spdx="MIT",
            api_complete=True,
        )


def make_item(
    identifier: str,
    repository: str,
    catalog: str,
    *,
    complete: bool = False,
    path: str = "",
    provenance: list[str] | None = None,
    overall: float = 50.0,
) -> core.ExtensionItem:
    item = core.ExtensionItem(
        id=identifier,
        name=identifier.rsplit(":", 1)[-1],
        kind="skill",
        repo=core.RepoInfo(
            full_name=repository,
            html_url=f"https://github.com/{repository}",
            stars=100 if complete else 0,
            created_at="2026-06-01T00:00:00Z" if complete else "",
            pushed_at="2026-08-31T00:00:00Z" if complete else "",
            updated_at="2026-08-31T00:00:00Z" if complete else "",
            api_complete=complete,
        ),
        path=path,
        source_url=f"https://github.com/{repository}",
        description=f"Description for {identifier}",
        platforms=["test"],
        catalogs=[catalog],
        provenance=provenance or ["repository-search:test"],
        evidence=[f"path:{path}"] if path else ["query:test"],
        trust=0.5,
        manifest_valid=bool(path),
    )
    item.scores = {
        "overall": overall,
        "momentum": overall,
        "rising": overall,
        "popular": overall,
    }
    return item


class SourceNormalizationTests(unittest.TestCase):
    def test_bare_owner_repository_is_recognized(self) -> None:
        self.assertEqual(
            policies.github_repo_from_source("AlteredCraft/claude-code-plugins"),
            "AlteredCraft/claude-code-plugins",
        )
        self.assertEqual(
            policies.github_repo_from_source("github:example/project.git"),
            "example/project",
        )

    def test_non_github_or_deep_paths_are_not_guessed(self) -> None:
        self.assertIsNone(
            policies.github_repo_from_source("https://example.com/owner/repository")
        )
        self.assertIsNone(
            policies.github_repo_from_source("owner/repository/plugins/example")
        )

    def test_git_subdir_marketplace_source_uses_actual_repository(self) -> None:
        original = core.github_repo_from_url
        core.github_repo_from_url = policies.github_repo_from_source
        try:
            repository, path, ref, source_url = core.resolve_marketplace_source(
                {
                    "name": "api-security-testing",
                    "source": {
                        "source": "git-subdir",
                        "url": "42Crunch-AI/claude-plugins",
                        "path": "plugins/api-security-testing",
                        "ref": "v1.0.1",
                    },
                },
                "anthropics/claude-plugins-community",
            )
        finally:
            core.github_repo_from_url = original

        self.assertEqual(repository, "42Crunch-AI/claude-plugins")
        self.assertEqual(path, "plugins/api-security-testing")
        self.assertEqual(ref, "v1.0.1")
        self.assertEqual(
            source_url,
            "https://github.com/42Crunch-AI/claude-plugins/tree/v1.0.1/plugins/api-security-testing",
        )


class BalancedEnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    def test_budget_is_distributed_across_native_catalogs(self) -> None:
        github = FakeGitHub()
        config = {
            "max_repository_enrichments": 4,
            "include_all_catalog_id": "agent-extensions",
            "catalogs": [
                {"id": "claude-skills"},
                {"id": "claude-tools"},
                {"id": "claude-plugins"},
                {"id": "agent-extensions"},
            ],
        }
        collector = policies.BalancedCollector(config, github, self.now)
        values = [
            make_item("skill:a:one", "skills/a", "claude-skills", path="skills/one/SKILL.md"),
            make_item("skill:b:one", "skills/b", "claude-skills", path="skills/one/SKILL.md"),
            make_item("tool:a:root", "tools/a", "claude-tools"),
            make_item("plugin:a:root", "plugins/a", "claude-plugins", path=".claude-plugin/plugin.json"),
            make_item("agent:a:root", "agents/a", "agent-extensions"),
        ]
        collector.items = {item.id: item for item in values}

        collector._enrich_repositories()

        self.assertEqual(len(github.requested), 4)
        self.assertTrue(any(value.startswith("skills/") for value in github.requested))
        self.assertIn("tools/a", github.requested)
        self.assertIn("plugins/a", github.requested)
        self.assertIn("agents/a", github.requested)

    def test_exact_artifact_evidence_beats_keyword_only_candidate(self) -> None:
        github = FakeGitHub()
        config = {
            "max_repository_enrichments": 1,
            "include_all_catalog_id": "agent-extensions",
            "catalogs": [{"id": "claude-skills"}, {"id": "agent-extensions"}],
        }
        collector = policies.BalancedCollector(config, github, self.now)
        weak = make_item(
            "skill:weak:root",
            "weak/repository",
            "claude-skills",
            provenance=["repository-search:weak"],
        )
        exact = make_item(
            "skill:exact:one",
            "exact/repository",
            "claude-skills",
            path=".claude/skills/one/SKILL.md",
            provenance=["code-search:claude-skill-layout"],
        )
        collector.items = {weak.id: weak, exact.id: exact}

        collector._enrich_repositories()

        self.assertEqual(github.requested, ["exact/repository"])


class LeaderboardPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
        self.config = {
            "leaderboard_size": 3,
            "max_items_per_repo_per_leaderboard": 1,
        }

    def test_incomplete_records_do_not_displace_measured_records(self) -> None:
        measured = [
            make_item(
                f"skill:measured-{index}:root",
                f"measured/repo-{index}",
                "claude-skills",
                complete=True,
                overall=60.0 + index,
            )
            for index in range(3)
        ]
        incomplete = make_item(
            "skill:unknown:root",
            "unknown/repository",
            "claude-skills",
            complete=False,
            overall=100.0,
        )

        boards = policies.catalog_leaderboards(
            [*measured, incomplete], "claude-skills", self.config, self.now
        )

        self.assertNotIn(incomplete, boards["high_momentum"])
        self.assertEqual(len(boards["high_momentum"]), 3)

    def test_one_repository_cannot_fill_a_leaderboard(self) -> None:
        duplicates = [
            make_item(
                f"skill:bundle:item-{index}",
                "bundle/repository",
                "claude-skills",
                complete=True,
                path=f"skills/item-{index}/SKILL.md",
                overall=100.0 - index,
            )
            for index in range(5)
        ]
        independent = make_item(
            "skill:independent:root",
            "independent/repository",
            "claude-skills",
            complete=True,
            overall=50.0,
        )

        selected = policies.diverse_top(
            [*duplicates, independent], "overall", limit=5, max_per_repo=1
        )

        self.assertEqual(
            [item.repo.full_name for item in selected],
            ["bundle/repository", "independent/repository"],
        )


if __name__ == "__main__":
    unittest.main()
