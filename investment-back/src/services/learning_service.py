"""用户学习历史聚合服务

从 judgment_history 和 emotion_history 表中拉取最近数据，
聚合成可被 AdaptationService 消费的结构化指标（LearningMetrics）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

import structlog
from sqlalchemy.orm import Session

from src.models.emotion_history import EmotionHistory
from src.models.judgment_history import JudgmentHistory


logger = structlog.get_logger()


# 判断质量分数映射（与 ProfileService.JUDGMENT_SCORE_MAP 保持一致）
_JUDGMENT_SCORE_MAP = {
    "主要来自判断": 100,
    "主要来自理性判断": 100,
    "部分判断 + 部分运气": 50,
    "部分判断 + 部分情绪": 50,
    "主要来自运气": 0,
    "主要来自情绪冲动": 0,
}


@dataclass
class LearningMetrics:
    """用户画像学习聚合指标

    由 UserLearningService.compute(user_id) 生成，
    传递给 AdaptationService 用于个性化调整输出。
    """

    # ── 判断质量 ───────────────────────────────────────────────────────────────
    judgment_avg: float = 50.0
    """所有有效记录的判断质量均值（0–100）"""

    judgment_trend: Optional[float] = None
    """近期均值相对历史均值的差值（正=近期改善，负=下滑），单位：百分点"""

    judgment_trend_direction: str = "stable"
    """趋势方向：up / down / stable"""

    judgment_recent_scores: List[int] = field(default_factory=list)
    """最近有效得分列表（用于展示）"""

    judgment_count: int = 0
    """有效记录总数"""

    judgment_hard_to_tell_count: int = 0
    """"难以区分"记录总数"""

    judgment_insufficient: bool = True
    """数据是否不足（< 3 条有效记录）"""

    # ── 情绪状态 ───────────────────────────────────────────────────────────────
    emotion_avg: float = 3.0
    """最近 30 天平均情绪（1–5）"""

    emotion_recent: int = 3
    """最近一条情绪评分（1–5）"""

    emotion_insufficient: bool = True
    """数据是否不足（< 3 条记录）"""

    # ── 综合信号 ───────────────────────────────────────────────────────────────
    high_emotion_flag: bool = False
    """情绪近期偏高（最近评分 >= 4），建议干预"""

    declining_judgment_flag: bool = False
    """判断质量近期下滑，建议加强风险提示"""

    frequent_trading_flag: bool = False
    """判断质量均值低于 40 且记录 >= 5，疑似频繁交易"""


class UserLearningService:
    """从数据库聚合用户学习历史，返回 LearningMetrics。"""

    DEFAULT_DAYS = 90  # 聚合时间窗口

    def __init__(self, db: Session):
        self.db = db

    def compute(self, user_id: int, days: int = DEFAULT_DAYS) -> LearningMetrics:
        """聚合指定时间窗口内的 judgment + emotion 历史，返回 LearningMetrics。"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        judgment_records = (
            self.db.query(JudgmentHistory)
            .filter(
                JudgmentHistory.user_id == user_id,
                JudgmentHistory.judgment_date >= cutoff.date(),
            )
            .order_by(JudgmentHistory.judgment_date.desc())
            .all()
        )

        emotion_records = (
            self.db.query(EmotionHistory)
            .filter(
                EmotionHistory.user_id == user_id,
                EmotionHistory.recorded_date >= cutoff.date(),
            )
            .order_by(EmotionHistory.recorded_date.desc())
            .all()
        )

        metrics = self._aggregate(judgment_records, emotion_records)
        logger.debug(
            "learning_metrics_computed",
            user_id=user_id,
            judgment_count=metrics.judgment_count,
            emotion_insufficient=metrics.emotion_insufficient,
            trend_direction=metrics.judgment_trend_direction,
        )
        return metrics

    def _aggregate(
        self,
        judgment_records: List[JudgmentHistory],
        emotion_records: List[EmotionHistory],
    ) -> LearningMetrics:
        # ── Judgment ──────────────────────────────────────────────────────────
        valid_records = [
            r for r in judgment_records
            if not r.is_hard_to_tell
        ]
        hard_to_tell_count = sum(1 for r in judgment_records if r.is_hard_to_tell)
        valid_scores = [r.judgment_score for r in valid_records]
        judgment_count = len(valid_scores)
        judgment_insufficient = judgment_count < 3
        recent_scores = valid_scores[:7]

        judgment_avg = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 50.0

        # 趋势：比较 date window：最近 7 天 vs 更早 8-14 天
        #   - 两窗口均有数据：delta = avg(recent 7d) - avg(8-14d ago)
        #   - 仅 recent 7d 有数据（历史不足 8 天）：delta = None，方向 = stable，不算 insufficient
        #   - 数据不足 3 条：delta = None，方向 = stable，judgment_insufficient = True
        now = datetime.utcnow()
        recent_cutoff = now.date() - timedelta(days=7)        # today - 7d（不含 today）
        older_start = now.date() - timedelta(days=14)        # today - 14d
        older_end = now.date() - timedelta(days=8)            # today - 8d（含）

        recent_window = [r for r in valid_records if r.judgment_date >= recent_cutoff]
        older_window = [
            r for r in valid_records
            if older_start <= r.judgment_date <= older_end
        ]

        if judgment_insufficient:
            delta = None
            trend_direction = "stable"
        elif not recent_window:
            delta = None
            trend_direction = "stable"
        elif not older_window:
            # 近期有数据但历史不足 8 天，无法对比，保守归为 stable
            delta = None
            trend_direction = "stable"
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

        # ── Emotion ────────────────────────────────────────────────────────────
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

        # ── 综合信号 ────────────────────────────────────────────────────────────
        high_emotion_flag = recent_emotion >= 4
        declining_judgment_flag = trend_direction == "down"
        frequent_trading_flag = (
            judgment_avg < 40 and judgment_count >= 5
        )

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
