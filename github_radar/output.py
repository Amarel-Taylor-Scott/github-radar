"""Output writers: JSON, a Markdown digest, and an Atom feed.

All three take the ranked ``list[Repo]`` and return a string (the CLI decides
where to write it). The writers are pure so they're trivial to test, and they
escape user-controlled text (descriptions can contain ``|``, ``<``, ``&``).
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Sequence

from .models import Repo

FEED_TITLE = "github-radar — popular & AI GitHub repositories"
FEED_ID = "urn:github-radar:feed"


def to_json(repos: Sequence[Repo], *, generated_at: datetime | None = None) -> str:
    """Serialize the feed to pretty JSON with a metadata envelope."""
    generated_at = generated_at or datetime.now(timezone.utc)
    payload = {
        "generated_at": generated_at.astimezone(timezone.utc).isoformat(),
        "count": len(repos),
        "repos": [
            {"rank": i, **repo.to_dict()} for i, repo in enumerate(repos, start=1)
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _md_escape(text: str) -> str:
    """Escape pipes/newlines so a description can't break a Markdown table."""
    return (text or "").replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()


def to_markdown(repos: Sequence[Repo], *, generated_at: datetime | None = None) -> str:
    """Render the feed as a Markdown digest with a ranked table."""
    generated_at = generated_at or datetime.now(timezone.utc)
    stamp = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# {FEED_TITLE}",
        "",
        f"_Generated {stamp} — {len(repos)} repositories, ranked by momentum-aware score._",
        "",
        "| # | Repo | ⭐ | Lang | Score | Description |",
        "|--:|------|--:|:-----|------:|:------------|",
    ]
    for i, repo in enumerate(repos, start=1):
        desc = _md_escape(repo.description)
        if len(desc) > 100:
            desc = desc[:97].rstrip() + "..."
        lang = repo.language or "—"
        lines.append(
            f"| {i} | [{repo.full_name}]({repo.url}) | {repo.stars:,} | "
            f"{lang} | {repo.score:.1f} | {desc} |"
        )
    lines.append("")
    return "\n".join(lines)


def to_atom(repos: Sequence[Repo], *, generated_at: datetime | None = None) -> str:
    """Render the feed as an Atom 1.0 XML document (valid, escaped via ElementTree)."""
    generated_at = generated_at or datetime.now(timezone.utc)
    updated = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ns = "http://www.w3.org/2005/Atom"
    feed = ET.Element("feed", xmlns=ns)
    ET.SubElement(feed, "title").text = FEED_TITLE
    ET.SubElement(feed, "id").text = FEED_ID
    ET.SubElement(feed, "updated").text = updated
    link = ET.SubElement(feed, "link")
    link.set("href", "https://github.com/trending")
    link.set("rel", "alternate")
    author = ET.SubElement(feed, "author")
    ET.SubElement(author, "name").text = "github-radar"

    for i, repo in enumerate(repos, start=1):
        entry = ET.SubElement(feed, "entry")
        ET.SubElement(entry, "title").text = f"#{i} {repo.full_name} (★{repo.stars:,})"
        ET.SubElement(entry, "id").text = f"urn:github-radar:{repo.full_name}"
        ET.SubElement(entry, "updated").text = repo.pushed_at or updated
        elink = ET.SubElement(entry, "link")
        elink.set("href", repo.url)
        elink.set("rel", "alternate")
        summary_bits = [repo.description or "(no description)"]
        meta = [f"score={repo.score:.1f}", f"stars={repo.stars}"]
        if repo.language:
            meta.append(f"lang={repo.language}")
        if repo.sources:
            meta.append("sources=" + ",".join(sorted(repo.sources)))
        summary_bits.append("[" + " ".join(meta) + "]")
        ET.SubElement(entry, "summary").text = " ".join(summary_bits)

    body = ET.tostring(feed, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n"


def write_outputs(
    repos: Sequence[Repo],
    *,
    formats: Sequence[str],
    out_dir: str,
    basename: str = "feed",
    generated_at: datetime | None = None,
) -> dict[str, str]:
    """Write the requested formats into ``out_dir``; return {format: path}.

    Supported formats: ``json``, ``markdown`` (``.md``), ``atom`` (``.xml``).
    """
    import os

    os.makedirs(out_dir, exist_ok=True)
    renderers = {
        "json": (to_json, "json"),
        "markdown": (to_markdown, "md"),
        "atom": (to_atom, "xml"),
    }
    written: dict[str, str] = {}
    for fmt in formats:
        if fmt not in renderers:
            raise ValueError(f"unknown output format: {fmt!r}")
        render, ext = renderers[fmt]
        path = os.path.join(out_dir, f"{basename}.{ext}")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(render(repos, generated_at=generated_at))
        written[fmt] = path
    return written
