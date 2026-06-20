"""Tests for the momentum-aware ranking. All offline, deterministic via ``now``."""

import unittest
from datetime import datetime, timedelta, timezone

from github_radar.models import Repo
from github_radar.ranking import RankingWeights, rank, score_repo

NOW = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ScoreRepoTests(unittest.TestCase):
    def test_fresh_push_outscores_stale_push_same_stars(self):
        """Recency must let a recently-pushed repo beat a dormant one."""
        fresh = Repo("a/fresh", stars=5000, pushed_at=_iso(NOW))
        stale = Repo("a/stale", stars=5000, pushed_at=_iso(NOW - timedelta(days=120)))
        self.assertGreater(score_repo(fresh, now=NOW), score_repo(stale, now=NOW))

    def test_recency_decays_by_half_life(self):
        """A repo idle exactly one half-life keeps ~half its recency term."""
        weights = RankingWeights(
            popularity=0, momentum=0, trending_bonus=0, multi_source_bonus=0,
            recency=100, recency_half_life_days=14,
        )
        now_push = Repo("a/now", pushed_at=_iso(NOW))
        half = Repo("a/half", pushed_at=_iso(NOW - timedelta(days=14)))
        s_now = score_repo(now_push, weights=weights, now=NOW)
        s_half = score_repo(half, weights=weights, now=NOW)
        self.assertAlmostEqual(s_half, s_now * 0.5, delta=0.5)

    def test_momentum_rewards_stars_today(self):
        """Two identical repos: the one trending harder ranks higher."""
        hot = Repo("a/hot", stars=1000, pushed_at=_iso(NOW), stars_today=2000,
                   sources={"trending"})
        warm = Repo("a/warm", stars=1000, pushed_at=_iso(NOW), stars_today=10,
                    sources={"trending"})
        self.assertGreater(score_repo(hot, now=NOW), score_repo(warm, now=NOW))

    def test_trending_presence_bonus(self):
        """Being on the trending page is itself a positive signal."""
        trending = Repo("a/t", stars=1000, pushed_at=_iso(NOW), sources={"trending"})
        plain = Repo("a/p", stars=1000, pushed_at=_iso(NOW), sources={"search"})
        self.assertGreater(score_repo(trending, now=NOW), score_repo(plain, now=NOW))

    def test_multi_source_corroboration_bonus(self):
        """A repo surfaced by several sources beats a single-source twin."""
        both = Repo("a/both", stars=1000, pushed_at=_iso(NOW),
                    sources={"search", "trending"})
        one = Repo("a/one", stars=1000, pushed_at=_iso(NOW), sources={"trending"})
        self.assertGreater(score_repo(both, now=NOW), score_repo(one, now=NOW))

    def test_log_scaling_prevents_giant_domination(self):
        """A 200k-star dormant giant should not automatically top a hot newcomer."""
        giant = Repo("a/giant", stars=200000,
                     pushed_at=_iso(NOW - timedelta(days=90)))
        newcomer = Repo("a/new", stars=3000, pushed_at=_iso(NOW),
                        stars_today=1500, sources={"search", "trending"})
        ranked = rank([giant, newcomer], now=NOW)
        self.assertEqual(ranked[0].full_name, "a/new")

    def test_score_attached_to_repo(self):
        repo = Repo("a/x", stars=100, pushed_at=_iso(NOW))
        returned = score_repo(repo, now=NOW)
        self.assertEqual(repo.score, returned)
        self.assertGreater(repo.score, 0)

    def test_zero_stars_no_push_scores_zero(self):
        self.assertEqual(score_repo(Repo("a/empty"), now=NOW), 0.0)


class RankOrderTests(unittest.TestCase):
    def test_rank_sorts_descending_and_truncates(self):
        repos = [
            Repo("a/low", stars=100, pushed_at=_iso(NOW - timedelta(days=200))),
            Repo("a/high", stars=5000, pushed_at=_iso(NOW), stars_today=900,
                 sources={"trending"}),
            Repo("a/mid", stars=2000, pushed_at=_iso(NOW - timedelta(days=10))),
        ]
        ranked = rank(repos, now=NOW, top_n=2)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0].full_name, "a/high")
        self.assertGreaterEqual(ranked[0].score, ranked[1].score)

    def test_stars_break_score_ties(self):
        weights = RankingWeights(recency=0, momentum=0, trending_bonus=0,
                                 multi_source_bonus=0, popularity=0)
        a = Repo("a/aa", stars=10)
        b = Repo("a/bb", stars=99)
        ranked = rank([a, b], weights=weights, now=NOW)
        self.assertEqual(ranked[0].full_name, "a/bb")


if __name__ == "__main__":
    unittest.main()
