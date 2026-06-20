"""Tests for dedup/merge across sources and the Repo model normalization."""

import unittest

from github_radar.aggregate import merge_repos
from github_radar.models import Repo


class NormalizationTests(unittest.TestCase):
    def test_full_name_from_url(self):
        r = Repo("https://github.com/openai/whisper")
        self.assertEqual(r.full_name, "openai/whisper")
        self.assertEqual(r.owner, "openai")
        self.assertEqual(r.name, "whisper")

    def test_full_name_strips_git_suffix_and_slashes(self):
        self.assertEqual(Repo.normalize_full_name("/owner/repo.git/"), "owner/repo")

    def test_url_defaults_from_full_name(self):
        self.assertEqual(Repo("a/b").url, "https://github.com/a/b")

    def test_dedup_key_is_case_insensitive(self):
        self.assertEqual(Repo("Owner/Repo").dedup_key, Repo("owner/repo").dedup_key)

    def test_sources_string_becomes_set(self):
        self.assertEqual(Repo("a/b", sources="search").sources, {"search"})


class MergeTests(unittest.TestCase):
    def test_dedup_collapses_same_repo_across_sources(self):
        repos = [
            Repo("OpenAI/whisper", stars=50000, sources={"search"}),
            Repo("openai/whisper", stars=51000, stars_today=300, sources={"trending"}),
        ]
        merged = merge_repos(repos)
        self.assertEqual(len(merged), 1)
        m = merged[0]
        self.assertEqual(m.stars, 51000)  # max wins
        self.assertEqual(m.stars_today, 300)
        self.assertEqual(m.sources, {"search", "trending"})

    def test_merge_fills_blank_text_fields(self):
        a = Repo("a/b", description="", language=None, sources={"trending"})
        b = Repo("a/b", description="hello", language="Python", sources={"search"})
        merged = merge_repos([a, b])[0]
        self.assertEqual(merged.description, "hello")
        self.assertEqual(merged.language, "Python")

    def test_merge_unions_topics(self):
        a = Repo("a/b", topics=["llm", "ai"])
        b = Repo("a/b", topics=["ai", "rag"])
        merged = merge_repos([a, b])[0]
        self.assertEqual(merged.topics, ["ai", "llm", "rag"])

    def test_invalid_full_names_are_dropped(self):
        merged = merge_repos([Repo("noslug"), Repo(""), Repo("a/b")])
        self.assertEqual([r.full_name for r in merged], ["a/b"])

    def test_first_seen_order_preserved(self):
        merged = merge_repos([Repo("z/z"), Repo("a/a"), Repo("z/z")])
        self.assertEqual([r.full_name for r in merged], ["z/z", "a/a"])


if __name__ == "__main__":
    unittest.main()
