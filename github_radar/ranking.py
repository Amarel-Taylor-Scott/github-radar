"""Star-velocity ranking — the headline feature.

The goal is "what's hot *now*", not "what has the most all-time stars". A naive
sort by ``stargazers_count`` just lists the same handful of giants (transformers,
tensorflow, ...) forever. Instead each repo gets a blended ``score`` in roughly
``[0, 100]`` combining four signals:

1. **Popularity** — ``log10(stars)``. Log-scaled so a 200k-star repo doesn't
   swamp everything; an extra zero is worth a fixed bump, not 10x.
2. **Recency / freshness** — exponential decay on *days since last push*. A repo
   pushed today scores ~1.0; one quiet for a month decays toward 0. This is the
   knob that lets newcomers outrank dormant giants.
3. **Momentum** — the trending page's *stars-this-period* gain (``stars_today``),
   log-scaled. This is the closest free proxy for true star-velocity without
   GH Archive / BigQuery (see the README note).
4. **Trending presence** — a flat bonus for being surfaced by the trending
   feed(s) at all, and a smaller bonus per *additional* source that
   independently surfaced the repo (cross-source corroboration).

Weights are explicit and tunable via :class:`RankingWeights`. The formula is
deliberately simple and inspectable — a YC reviewer can read it in ten seconds.

**GH Archive note (optional, documented, not required):** true star-velocity
(stars/day over a trailing window) can be computed from the public GH Archive
event stream via BigQuery (``WatchEvent`` counts per repo per day). github-radar
deliberately avoids requiring BigQuery credentials; ``stars_today`` from the
trending page is the lightweight stand-in. The ``momentum`` term is structured
so a future GH Archive velocity figure can be dropped in unchanged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from .models import Repo


@dataclass(frozen=True)
class RankingWeights:
    """Tunable weights for the blended score. Defaults favour momentum."""

    popularity: float = 18.0
    recency: float = 28.0
    momentum: float = 16.0
    trending_bonus: float = 12.0
    multi_source_bonus: float = 6.0
    # Recency half-life in days: a repo idle this long loses half its recency.
    recency_half_life_days: float = 14.0


def _popularity(stars: int) -> float:
    """log10-scaled popularity in [0, ~1.2] for stars up to ~250k."""
    if stars <= 0:
        return 0.0
    # log10(1)=0 .. log10(250000)≈5.4; normalize by 6 so giants ~0.9.
    return min(math.log10(stars + 1) / 6.0, 1.2)


def _recency(pushed: Optional[datetime], now: datetime, half_life: float) -> float:
    """Exponential freshness in (0, 1]; 1.0 = pushed now, halves each half-life."""
    if pushed is None:
        return 0.0
    days = max((now - pushed).total_seconds() / 86400.0, 0.0)
    return math.pow(0.5, days / max(half_life, 0.1))


def _momentum(stars_today: Optional[int]) -> float:
    """log-scaled per-period star gain in [0, ~1.0] for gains up to ~10k."""
    if not stars_today or stars_today <= 0:
        return 0.0
    return min(math.log10(stars_today + 1) / 4.0, 1.0)


def score_repo(
    repo: Repo,
    *,
    weights: RankingWeights = RankingWeights(),
    now: Optional[datetime] = None,
) -> float:
    """Compute and attach a blended momentum-aware score to ``repo``.

    The score is written to ``repo.score`` (so writers can emit it) and also
    returned. ``now`` is injectable for deterministic tests.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    popularity = _popularity(repo.stars) * weights.popularity
    recency = _recency(repo.pushed_dt, now, weights.recency_half_life_days) * weights.recency
    momentum = _momentum(repo.stars_today) * weights.momentum

    is_trending = any(s.startswith("trending") for s in repo.sources)
    trending = weights.trending_bonus if is_trending else 0.0
    # Bonus for each source beyond the first (cross-source corroboration).
    multi = weights.multi_source_bonus * max(len(repo.sources) - 1, 0)

    repo.score = round(popularity + recency + momentum + trending + multi, 4)
    return repo.score


def rank(
    repos: Iterable[Repo],
    *,
    weights: RankingWeights = RankingWeights(),
    now: Optional[datetime] = None,
    top_n: Optional[int] = None,
) -> list[Repo]:
    """Score every repo and return them sorted by score (desc), stars as tiebreak."""
    now = now or datetime.now(timezone.utc)
    scored = list(repos)
    for repo in scored:
        score_repo(repo, weights=weights, now=now)
    scored.sort(key=lambda r: (r.score, r.stars), reverse=True)
    return scored[:top_n] if top_n else scored
