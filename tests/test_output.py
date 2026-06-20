"""Tests for the JSON / Markdown / Atom output writers (offline, pure)."""

import json
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from github_radar.models import Repo
from github_radar.output import to_atom, to_json, to_markdown

GEN = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)


def _sample():
    a = Repo("openai/whisper", description="ASR model", language="Python",
             stars=51000, url="https://github.com/openai/whisper",
             pushed_at="2026-06-19T00:00:00Z", sources={"search", "trending"})
    a.score = 42.5
    # Description with pipe + angle bracket + ampersand to test escaping.
    b = Repo("evil/repo", description="a|b <x> & y", stars=10, score=1.0)
    return [a, b]


class JsonTests(unittest.TestCase):
    def test_json_is_valid_with_envelope_and_ranks(self):
        data = json.loads(to_json(_sample(), generated_at=GEN))
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["repos"][0]["rank"], 1)
        self.assertEqual(data["repos"][0]["full_name"], "openai/whisper")
        self.assertEqual(sorted(data["repos"][0]["sources"]), ["search", "trending"])


class MarkdownTests(unittest.TestCase):
    def test_markdown_has_table_header_and_rows(self):
        md = to_markdown(_sample(), generated_at=GEN)
        self.assertIn("| # | Repo | ⭐ | Lang | Score | Description |", md)
        self.assertIn("[openai/whisper](https://github.com/openai/whisper)", md)
        self.assertIn("51,000", md)

    def test_markdown_escapes_pipe_in_description(self):
        md = to_markdown(_sample(), generated_at=GEN)
        self.assertIn(r"a\|b", md)  # pipe escaped so the table doesn't break


class AtomTests(unittest.TestCase):
    def test_atom_is_well_formed_xml(self):
        xml = to_atom(_sample(), generated_at=GEN)
        root = ET.fromstring(xml)  # raises if malformed
        ns = "{http://www.w3.org/2005/Atom}"
        entries = root.findall(f"{ns}entry")
        self.assertEqual(len(entries), 2)
        # Ampersand/angle brackets must be escaped by ElementTree.
        self.assertIn("&amp;", xml)


if __name__ == "__main__":
    unittest.main()
