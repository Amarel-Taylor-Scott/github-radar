"""Command-line orchestration for the multi-domain Project Radar."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Optional

from github_radar.http import HttpClient
from github_radar.project_common import REPO_ROOT, parse_datetime, utc_now
from github_radar.project_discovery import Collector, GitHubAPI, load_config
from github_radar.project_history import load_history, update_history
from github_radar.project_rendering import (
    previous_publication, validate_collection, write_outputs,
)
from github_radar.project_scoring import score_projects

LOGGER = logging.getLogger("project_radar")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="project_radars.json", help="JSON configuration path")
    parser.add_argument("--token", default=None, help="GitHub token; defaults to GITHUB_TOKEN")
    parser.add_argument("--output-dir", default=None, help="Override feed directory")
    parser.add_argument("--site-dir", default=None, help="Override static-site directory")
    parser.add_argument("--now", default=None, help="Testing override: ISO timestamp")
    parser.add_argument("--allow-shrink", action="store_true", help="Bypass the previous-count shrink guard")
    parser.add_argument("--no-enrich", action="store_true", help="Skip repository metadata enrichment")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path
    config = load_config(config_path)
    if args.no_enrich:
        config["max_repository_enrichments"] = 0
    now = parse_datetime(args.now) if args.now else utc_now()
    if now is None:
        parser.error("--now must be a valid ISO timestamp")
    output_dir = Path(args.output_dir) if args.output_dir else REPO_ROOT / str(config["output_dir"])
    site_dir = Path(args.site_dir) if args.site_dir else REPO_ROOT / str(config["site_dir"])
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    if not site_dir.is_absolute():
        site_dir = REPO_ROOT / site_dir

    history = load_history(output_dir / "history.json")
    previous, previous_catalogs = previous_publication(output_dir)
    token = args.token or os.environ.get("GITHUB_TOKEN")
    client = HttpClient(
        token=token,
        user_agent="github-radar-project-catalogs/0.1 (+https://github.com/Amarel-Taylor-Scott/github-radar)",
        max_retries=3,
        min_interval=float(config["request_interval_seconds"]),
    )
    collector = Collector(
        config,
        GitHubAPI(
            client,
            search_interval_seconds=float(config["search_interval_seconds"]),
        ),
        now,
    )
    projects, source_health = collector.collect()
    validate_collection(
        projects,
        config,
        source_health,
        previous=previous,
        previous_catalogs=previous_catalogs,
        allow_shrink=args.allow_shrink,
    )
    score_projects(projects, config, history, now)
    updated_history = update_history(history, projects, now, int(config["history_days"]))
    counts = write_outputs(
        projects,
        config,
        updated_history,
        source_health,
        now,
        output_dir=output_dir,
        site_dir=site_dir,
    )
    LOGGER.info("Published %d unique projects across %d catalogs", len(projects), len(counts))
    for catalog_id, count in counts.items():
        LOGGER.info("  %s: %d", catalog_id, count)
    return 0
