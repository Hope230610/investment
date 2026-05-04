"""
Unit tests for UserLearningService._aggregate().

Tests cover all aggregation logic for LearningMetrics without requiring a real DB.
Each test provides a list of mock JudgmentHistory / EmotionHistory records
and asserts the computed LearningMetrics fields.

Run with: cd investment-back && pytest tests/test_learning_service.py -v
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional
import unittest


# ─── Mock record types ─────────────────────────────────────────────────────────

@dataclass
class MockJudgmentHistory:
    """Minimal stand-in for src.models.judgment_history.JudgmentHistory."""
    user_id: int
    judgment_date: date
    judgment_score: int
    is_hard_to_tell: bool
    analysis_task_id: Optional[str] = None
    judgment_label: str = ""


@dataclass
class MockEmotionHistory:
    """Minimal stand-in for src.models.emotion_history.EmotionHistory."""
    user_id: int
    recorded_date: date
    emotion_level: int
    analysis_task_id: Optional[str] = None


# ─── Re-implement _aggregate logic here (mirrors learning_service.py) ──────────

from dataclasses import dataclass as DC, field as DC_field

CN_TZ_DELTA = timedelta(hours=8)

@dataclass
class LearningMetrics:
    judgment_avg: float = 50.0
    judgment_trend: Optional[float] = None
    judgment_trend_direction: str = "stable"
    judgment_recent_scores: List[int] = DC_field(default_factory=list)
    judgment_count: int = 0
    judgment_hard_to_tell_count: int = 0
    judgment_insufficient: bool = True
    emotion_avg: float = 3.0
    emotion_recent: int = 3
    emotion_insufficient: bool = True
    high_emotion_flag: bool = False
    declining_judgment_flag: bool = False
    frequent_trading_flag: bool = False


def _aggregate(
    judgment_records: List[MockJudgmentHistory],
    emotion_records: List[MockEmotionHistory],
) -> LearningMetrics:
    """
    Mirror of UserLearningService._aggregate() for isolated unit testing.
    Must stay in sync with the real implementation.
    """
    # ── Judgment ────────────────────────────────────────────────────────────
    valid_records = [r for r in judgment_records if not r.is_hard_to_tell]
    hard_to_tell_count = sum(1 for r in judgment_records if r.is_hard_to_tell)
    valid_scores = [r.judgment_score for r in valid_records]
    judgment_count = len(valid_scores)
    judgment_insufficient = judgment_count < 3
    recent_scores = valid_scores[:7]
    judgment_avg = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 50.0

    # ── Trend (date window) ─────────────────────────────────────────────────
    now = datetime.utcnow()
    recent_cutoff = now.date() - timedelta(days=7)
    older_start = now.date() - timedelta(days=14)
    older_end = now.date() - timedelta(days=8)

    recent_window = [r for r in valid_records if r.judgment_date >= recent_cutoff]
    older_window = [
        r for r in valid_records if older_start <= r.judgment_date <= older_end
    ]

    if judgment_insufficient:
        delta, trend_direction = None, "stable"
    elif not recent_window:
        delta, trend_direction = None, "stable"
    elif not older_window:
        delta, trend_direction = None, "stable"
    else:
        avg_recent = sum(r.judgment_score for r in recent_window) / len(recent_window)
        avg_older = sum(r.judgment_score for r in older_window) / len(older_window)
        delta = round(avg_recent - avg_older, 1)
        if delta >= 5:
            trend_direction = "up"
        elif delta <= -5:
            trend_direction = "down"
        else:
            trend_direction = "stable"

    # ── Emotion ──────────────────────────────────────────────────────────────
    if emotion_records:
        recent_emotion = emotion_records[0].emotion_level
        emotion_avg = round(
            sum(r.emotion_level for r in emotion_records) / len(emotion_records), 1
        )
        emotion_insufficient = len(emotion_records) < 3
    else:
        recent_emotion = 3
        emotion_avg = 3.0
        emotion_insufficient = True

    # ── Signals ────────────────────────────────────────────────────────────
    high_emotion_flag = recent_emotion >= 4
    declining_judgment_flag = trend_direction == "down"
    frequent_trading_flag = judgment_avg < 40 and judgment_count >= 5

    return LearningMetrics(
        judgment_avg=judgment_avg,
        judgment_trend=delta,
        judgment_trend_direction=trend_direction,
        judgment_recent_scores=recent_scores,
        judgment_count=judgment_count,
        judgment_hard_to_tell_count=hard_to_tell_count,
        judgment_insufficient=judgment_insufficient,
        emotion_avg=emotion_avg,
        emotion_recent=recent_emotion,
        emotion_insufficient=emotion_insufficient,
        high_emotion_flag=high_emotion_flag,
        declining_judgment_flag=declining_judgment_flag,
        frequent_trading_flag=frequent_trading_flag,
    )


# ─── Test cases ────────────────────────────────────────────────────────────────

class TestLearningMetrics_EmptyData(unittest.TestCase):
    def test_empty_records_returns_defaults(self):
        m = _aggregate([], [])
        self.assertEqual(m.judgment_avg, 50.0)
        self.assertEqual(m.judgment_trend_direction, "stable")
        self.assertTrue(m.judgment_insufficient)
        self.assertTrue(m.emotion_insufficient)
        self.assertFalse(m.high_emotion_flag)
        self.assertFalse(m.declining_judgment_flag)
        self.assertFalse(m.frequent_trading_flag)

    def test_only_hard_to_tell_records_judgment_insufficient(self):
        today = datetime.utcnow().date()
        records = [
            MockJudgmentHistory(1, today, 0, is_hard_to_tell=True),
        ]
        m = _aggregate(records, [])
        self.assertTrue(m.judgment_insufficient)
        self.assertEqual(m.judgment_hard_to_tell_count, 1)


class TestLearningMetrics_JudgmentAggregation(unittest.TestCase):
    def test_single_record_judgment_insufficient(self):
        today = datetime.utcnow().date()
        records = [MockJudgmentHistory(1, today, 100, is_hard_to_tell=False)]
        m = _aggregate(records, [])
        self.assertTrue(m.judgment_insufficient)
        self.assertEqual(m.judgment_count, 1)

    def test_three_records_judgment_sufficient(self):
        today = datetime.utcnow().date()
        records = [
            MockJudgmentHistory(1, today, 100, is_hard_to_tell=False),
            MockJudgmentHistory(1, today - timedelta(days=1), 80, is_hard_to_tell=False),
            MockJudgmentHistory(1, today - timedelta(days=2), 60, is_hard_to_tell=False),
        ]
        m = _aggregate(records, [])
        self.assertFalse(m.judgment_insufficient)
        self.assertAlmostEqual(m.judgment_avg, 80.0, places=1)


class TestLearningMetrics_TrendDirection(unittest.TestCase):
    """Tests for judgment_trend_direction using date windows."""

    def _today(self, days_offset: int = 0) -> date:
        return datetime.utcnow().date() - timedelta(days=days_offset)

    def test_uptrend_detected(self):
        """recent avg (80) - older avg (60) = +20 → up"""
        records = [
            # recent window (today - 7d .. today)
            MockJudgmentHistory(1, self._today(1), 90, False),
            MockJudgmentHistory(1, self._today(2), 80, False),
            MockJudgmentHistory(1, self._today(3), 85, False),
            MockJudgmentHistory(1, self._today(4), 75, False),
            MockJudgmentHistory(1, self._today(5), 75, False),
            MockJudgmentHistory(1, self._today(6), 80, False),
            MockJudgmentHistory(1, self._today(7), 75, False),
            # older window (today - 14d .. today - 8d)
            MockJudgmentHistory(1, self._today(8), 50, False),
            MockJudgmentHistory(1, self._today(9), 55, False),
            MockJudgmentHistory(1, self._today(10), 60, False),
            MockJudgmentHistory(1, self._today(11), 55, False),
            MockJudgmentHistory(1, self._today(12), 65, False),
            MockJudgmentHistory(1, self._today(13), 60, False),
            MockJudgmentHistory(1, self._today(14), 55, False),
        ]
        m = _aggregate(records, [])
        self.assertEqual(m.judgment_trend_direction, "up")

    def test_downtrend_detected(self):
        """recent avg ≈ 50, older avg ≈ 80 → delta = -30 → down"""
        records = [
            # recent window
            MockJudgmentHistory(1, self._today(1), 60, False),
            MockJudgmentHistory(1, self._today(2), 50, False),
            MockJudgmentHistory(1, self._today(3), 55, False),
            MockJudgmentHistory(1, self._today(4), 45, False),
            MockJudgmentHistory(1, self._today(5), 50, False),
            MockJudgmentHistory(1, self._today(6), 48, False),
            MockJudgmentHistory(1, self._today(7), 45, False),
            # older window
            MockJudgmentHistory(1, self._today(8), 85, False),
            MockJudgmentHistory(1, self._today(9), 80, False),
            MockJudgmentHistory(1, self._today(10), 78, False),
            MockJudgmentHistory(1, self._today(11), 82, False),
            MockJudgmentHistory(1, self._today(12), 75, False),
            MockJudgmentHistory(1, self._today(13), 80, False),
            MockJudgmentHistory(1, self._today(14), 78, False),
        ]
        m = _aggregate(records, [])
        self.assertEqual(m.judgment_trend_direction, "down")
        self.assertTrue(m.declining_judgment_flag)

    def test_stable_when_delta_within_5_points(self):
        """avg recent = 65, avg older = 63 → delta = +2 → stable"""
        records = [
            MockJudgmentHistory(1, self._today(1), 65, False),
            MockJudgmentHistory(1, self._today(2), 68, False),
            MockJudgmentHistory(1, self._today(3), 62, False),
            MockJudgmentHistory(1, self._today(4), 65, False),
            MockJudgmentHistory(1, self._today(5), 67, False),
            MockJudgmentHistory(1, self._today(6), 63, False),
            MockJudgmentHistory(1, self._today(7), 64, False),
            # older window (narrow band 8-14d)
            MockJudgmentHistory(1, self._today(8), 63, False),
            MockJudgmentHistory(1, self._today(9), 62, False),
            MockJudgmentHistory(1, self._today(10), 64, False),
            MockJudgmentHistory(1, self._today(11), 63, False),
            MockJudgmentHistory(1, self._today(12), 65, False),
            MockJudgmentHistory(1, self._today(13), 62, False),
            MockJudgmentHistory(1, self._today(14), 63, False),
        ]
        m = _aggregate(records, [])
        self.assertEqual(m.judgment_trend_direction, "stable")
        self.assertFalse(m.declining_judgment_flag)

    def test_stable_when_no_older_window(self):
        """Only recent window (today - 7d .. today) has data → stable, not down"""
        today = datetime.utcnow().date()
        records = [
            MockJudgmentHistory(1, today - timedelta(days=1), 80, False),
            MockJudgmentHistory(1, today - timedelta(days=2), 60, False),
            MockJudgmentHistory(1, today - timedelta(days=3), 40, False),
        ]
        m = _aggregate(records, [])
        # No older window → cannot compare → stable
        self.assertEqual(m.judgment_trend_direction, "stable")
        self.assertIsNone(m.judgment_trend)
        self.assertFalse(m.declining_judgment_flag)

    def test_insufficient_when_less_than_3_valid_records(self):
        today = datetime.utcnow().date()
        records = [
            MockJudgmentHistory(1, today, 100, False),
            MockJudgmentHistory(1, today - timedelta(days=1), 80, False),
        ]
        m = _aggregate(records, [])
        self.assertTrue(m.judgment_insufficient)
        self.assertEqual(m.judgment_trend_direction, "stable")
        self.assertIsNone(m.judgment_trend)


class TestLearningMetrics_FrequentTradingFlag(unittest.TestCase):
    def _today(self, days_offset: int = 0) -> date:
        return datetime.utcnow().date() - timedelta(days=days_offset)

    def test_frequent_trading_flag_triggered(self):
        """avg < 40 AND count >= 5 → frequent_trading_flag = True"""
        records = [
            MockJudgmentHistory(1, self._today(i), 0, False)  # score = 0 (运气)
            for i in range(1, 8)
        ]
        m = _aggregate(records, [])
        self.assertTrue(m.frequent_trading_flag)
        self.assertLess(m.judgment_avg, 40)

    def test_frequent_trading_flag_not_triggered_with_high_avg(self):
        records = [
            MockJudgmentHistory(1, self._today(i), 90, False)
            for i in range(1, 8)
        ]
        m = _aggregate(records, [])
        self.assertFalse(m.frequent_trading_flag)

    def test_frequent_trading_flag_not_triggered_with_low_count(self):
        records = [
            MockJudgmentHistory(1, self._today(i), 0, False)
            for i in range(1, 5)  # only 4 records
        ]
        m = _aggregate(records, [])
        self.assertFalse(m.frequent_trading_flag)


class TestLearningMetrics_EmotionAggregation(unittest.TestCase):
    def _today(self, days_offset: int = 0) -> date:
        return datetime.utcnow().date() - timedelta(days=days_offset)

    def test_high_emotion_flag_triggered(self):
        records = [
            MockEmotionHistory(1, self._today(i), 4) for i in range(5)
        ]
        m = _aggregate([], records)
        self.assertTrue(m.high_emotion_flag)
        self.assertEqual(m.emotion_recent, 4)

    def test_high_emotion_flag_not_triggered(self):
        records = [
            MockEmotionHistory(1, self._today(i), 2) for i in range(5)
        ]
        m = _aggregate([], records)
        self.assertFalse(m.high_emotion_flag)

    def test_emotion_avg_computed(self):
        records = [
            MockEmotionHistory(1, self._today(i), level)
            for i, level in enumerate([5, 4, 3, 2, 1], start=0)
        ]
        m = _aggregate([], records)
        self.assertAlmostEqual(m.emotion_avg, 3.0, places=1)

    def test_emotion_insufficient_with_2_records(self):
        records = [
            MockEmotionHistory(1, self._today(0), 3),
            MockEmotionHistory(1, self._today(1), 2),
        ]
        m = _aggregate([], records)
        self.assertTrue(m.emotion_insufficient)


if __name__ == "__main__":
    unittest.main()