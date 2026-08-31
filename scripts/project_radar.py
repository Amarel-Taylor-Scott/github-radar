#!/usr/bin/env python3
"""Run the configurable, repository-level GitHub Project Radar."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Re-export the public API so existing imports of this script remain compatible.
from github_radar.project_common import *  # noqa: F401,F403,E402
from github_radar.project_discovery import *  # noqa: F401,F403,E402
from github_radar.project_history import *  # noqa: F401,F403,E402
from github_radar.project_rendering import *  # noqa: F401,F403,E402
from github_radar.project_runner import main  # noqa: E402
from github_radar.project_scoring import *  # noqa: F401,F403,E402


if __name__ == "__main__":
    raise SystemExit(main())
