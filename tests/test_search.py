"""Tests for the search-query builder and the search-item parser (offline)."""

import json
import os
import unittest
from datetime import datetime, timezone

from github_radar.config import Config
from github_radar.models import Repo
from github_radar.sources.search import build_search_query

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
NOW = datetime(2026, 6, 20, tzinfo=timezone.utc)


class QueryBuilderTests(unittest.TestCase):
    def test_default_query_uses_first_topic_stars_and_pushed(self):
        # GitHub can't OR topic: qualifiers, so each query targets one topic.
        q = build_search_query(Config(), now=NOW)
        self.assertIn("topic:llm", q)
        self.assertNotIn(" OR ", q)
        self.assertIn("stars:>100", q)
        self.assertIn("pushed:>2026-05-21", q)  # 30 days before NOW
        self.assertNotIn("created:>", q)

    def test_explicit_topic_targets_that_topic(self):
        q = build_search_query(Config(), topic="rag", now=NOW)
        self.assertIn("topic:rag", q)
        self.assertNotIn("topic:llm", q)

    def test_custom_topics_and_stars(self):
        cfg = Config(topics=["rag"], min_stars=500, window_days=7)
        q = build_search_query(cfg, now=NOW)
        self.assertIn("topic:rag", q)
        self.assertIn("stars:>500", q)
        self.assertIn("pushed:>2026-06-13", q)

    def test_created_filter_added_when_configured(self):
        cfg = Config(created_within_days=14)
        q = build_search_query(cfg, now=NOW)
        self.assertIn("created:>2026-06-06", q)

    def test_zero_min_stars_omits_stars_clause(self):
        q = build_search_query(Config(min_stars=0), now=NOW)
        self.assertNotIn("stars:>", q)

    def test_empty_topics_omits_topic_clause(self):
        q = build_search_query(Config(topics=[]), now=NOW)
        self.assertNotIn("topic:", q)
        self.assertIn("pushed:>", q)


class SearchItemParseTests(unittest.TestCase):
    def test_from_search_item_fixture(self):
        with open(os.path.join(FIXTURES, "search_llm.json")) as handle:
            payload = json.load(handle)
        repos = [Repo.from_search_item(it) for it in payload["items"]]
        self.assertEqual(len(repos), 2)
        first = repos[0]
        self.assertTrue("/" in first.full_name)
        self.assertGreater(first.stars, 0)
        self.assertEqual(first.sources, {"search"})
        self.assertEqual(first.owner, first.full_name.split("/")[0])

    def test_from_search_item_tolerates_missing_fields(self):
        repo = Repo.from_search_item({"full_name": "a/b", "owner": {"login": "a"}})
        self.assertEqual(repo.stars, 0)
        self.assertEqual(repo.description, "")
        self.assertIsNone(repo.language)


if __name__ == "__main__":
    unittest.main()
