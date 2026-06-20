"""Optional secondary sources, off by default and behind CLI flags.

These broaden the feed beyond GitHub itself:

* **Hugging Face trending** (``/api/trending``) — surfaces trending models,
  datasets, and Spaces. We keep only entries that link to a GitHub repo (most
  Spaces and many model cards do), so they merge cleanly with the rest.
* **arXiv cs.AI** (Atom feed) — recent AI papers. Many list a GitHub repo in
  the abstract/links; we extract any ``github.com/owner/name`` reference.

Both are best-effort: unreachable or shape-changed feeds log and return ``[]``.
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

from ..http import FetchError, HttpClient
from ..models import Repo

LOGGER = logging.getLogger("github_radar.sources.extras")

HF_TRENDING_URL = "https://huggingface.co/api/trending"
ARXIV_URL = (
    "http://export.arxiv.org/api/query?"
    "search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=50"
)
_GITHUB_REF_RE = re.compile(r"github\.com/([\w.-]+/[\w.-]+)")


def parse_huggingface_trending(content: str) -> list[Repo]:
    """Extract GitHub repos referenced by Hugging Face trending entries."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        LOGGER.warning("Could not parse Hugging Face trending JSON: %s", exc)
        return []
    # The API returns either a list or {"recentlyTrending": [...]}.
    entries: list[dict[str, Any]]
    if isinstance(payload, dict):
        entries = payload.get("recentlyTrending") or payload.get("models") or []
    else:
        entries = payload
    repos: list[Repo] = []
    for entry in entries:
        repo_obj = entry.get("repoData") if isinstance(entry, dict) else None
        blob = json.dumps(entry)
        match = _GITHUB_REF_RE.search(blob)
        if not match:
            continue
        full_name = Repo.normalize_full_name(match.group(1))
        if "/" not in full_name:
            continue
        likes = 0
        if isinstance(repo_obj, dict):
            likes = int(repo_obj.get("likes") or 0)
        repos.append(
            Repo(
                full_name=full_name,
                stars=likes,
                sources={"huggingface"},
            )
        )
    return repos


def parse_arxiv_atom(content: str) -> list[Repo]:
    """Extract GitHub repos linked from recent arXiv cs.AI papers."""
    repos: list[Repo] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        LOGGER.warning("Could not parse arXiv Atom feed: %s", exc)
        return repos
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    seen: set[str] = set()
    for entry in root.findall("atom:entry", ns):
        summary = entry.findtext("atom:summary", default="", namespaces=ns) or ""
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        for match in _GITHUB_REF_RE.finditer(summary):
            full_name = Repo.normalize_full_name(match.group(1))
            if "/" not in full_name or full_name.lower() in seen:
                continue
            seen.add(full_name.lower())
            repos.append(
                Repo(
                    full_name=full_name,
                    description=re.sub(r"\s+", " ", title)[:200],
                    sources={"arxiv"},
                )
            )
    return repos


class HuggingFaceSource:
    name = "huggingface"

    def __init__(self, client: HttpClient) -> None:
        self.client = client

    def fetch(self) -> list[Repo]:
        try:
            response = self.client.get(HF_TRENDING_URL)
        except FetchError as exc:
            LOGGER.warning("Hugging Face trending failed: %s", exc)
            return []
        return parse_huggingface_trending(response.body)


class ArxivSource:
    name = "arxiv"

    def __init__(self, client: HttpClient) -> None:
        self.client = client

    def fetch(self) -> list[Repo]:
        try:
            response = self.client.get(ARXIV_URL, accept="application/atom+xml")
        except FetchError as exc:
            LOGGER.warning("arXiv cs.AI feed failed: %s", exc)
            return []
        return parse_arxiv_atom(response.body)
