"""Tests for the trending HTML + RSS parsers, against saved fixtures (offline)."""

import os
import unittest

from github_radar.sources.trending import parse_trending_html, parse_trending_rss

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return handle.read()


class TrendingHtmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repos = parse_trending_html(_read("trending_sample.html"))
        cls.by_name = {r.full_name: r for r in cls.repos}

    def test_finds_all_articles(self):
        self.assertEqual(len(self.repos), 3)

    def test_parses_full_names(self):
        self.assertIn("palmier-io/palmier-pro", self.by_name)
        self.assertIn("penpot/penpot", self.by_name)

    def test_parses_total_stars_without_corruption(self):
        """Star count must come from trailing text, not the SVG path digits."""
        # The fixture shows 2,853 / 51,101 / 6,827 — all small, sane integers.
        for repo in self.repos:
            self.assertLess(repo.stars, 10_000_000)
            self.assertGreater(repo.stars, 0)
        self.assertEqual(self.by_name["palmier-io/palmier-pro"].stars, 2853)

    def test_parses_language(self):
        self.assertEqual(self.by_name["palmier-io/palmier-pro"].language, "Swift")
        self.assertEqual(self.by_name["penpot/penpot"].language, "Clojure")

    def test_parses_stars_today(self):
        self.assertEqual(self.by_name["palmier-io/palmier-pro"].stars_today, 904)

    def test_parses_description(self):
        self.assertIn("video editor", self.by_name["palmier-io/palmier-pro"].description)

    def test_source_label_recorded(self):
        self.assertEqual(self.by_name["penpot/penpot"].sources, {"trending"})

    def test_malformed_html_does_not_crash(self):
        self.assertEqual(parse_trending_html("<html>nonsense</html>"), [])
        self.assertEqual(parse_trending_html(""), [])


class TrendingRssTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repos = parse_trending_rss(_read("trending_python.xml"))

    def test_extracts_items(self):
        self.assertEqual(len(self.repos), 3)

    def test_extracts_full_name_from_link(self):
        names = {r.full_name for r in self.repos}
        self.assertIn("google-research/timesfm", names)

    def test_rss_source_labelled(self):
        self.assertTrue(all(r.sources == {"trending-rss"} for r in self.repos))

    def test_malformed_rss_returns_empty(self):
        self.assertEqual(parse_trending_rss("<rss><broken>"), [])


if __name__ == "__main__":
    unittest.main()
