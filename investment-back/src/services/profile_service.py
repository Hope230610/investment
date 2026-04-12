"""画像服务：行为标签更新 + 历史记录读写

对应 Phase 2 后端接入。
"""
from datetime import date as date_type, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from src.models.emotion_history import EmotionHistory
from src.models.judgment_history import JudgmentHistory
from src.models.user import UserProfile
from src.schemas.learning_feedback import (
    JudgmentHistoryPoint,
    LearningFeedbackRequest,
    LearningFeedbackResponse,
    EmotionHistoryPoint,
    LearningHistoryResponse,
)
import structlog

logger = structlog.get_logger()

# 判断质量分数字值映射（与前端 learningFeedback.ts 保持一致）
JUDGMENT_SCORE_MAP = {
    "主要来自判断": 100,
    "部分判断 + 部分运气": 50,
    "主要来自运气": 0,
    # "难以区分" 单独处理，不写 judgment_score
}


class ProfileService:
    """画像服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger.bind(service="profile")

    # ─── Emotion History ─────────────────────────────────────────────────────────

    def upsert_emotion_history(
        self,
        user_id: int,
        recorded_date: date_type,
        emotion_level: int,
        analysis_task_id: Optional[UUID] = None,
        intent: Optional[str] = None,
        trigger_reason: Optional[str] = None,
    ) -> EmotionHistory:
        """Upsert 情绪历史（同一天记录覆盖）"""
        stmt = insert(EmotionHistory).values(
            user_id=user_id,
            recorded_date=recorded_date,
            emotion_level=emotion_level,
            analysis_task_id=analysis_task_id,
            intent=intent,
            trigger_reason=trigger_reason,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="ix_emotion_history_user_date",
            set_={
                "emotion_level": emotion_level,
                "analysis_task_id": analysis_task_id,
                "intent": intent,
                "trigger_reason": trigger_reason,
                "created_at": datetime.utcnow(),
            },
        )
        result = self.db.execute(stmt)
        self.db.commit()
        # 获取插入/更新后的记录
        record = self.db.query(EmotionHistory).filter(
            and_(
                EmotionHistory.user_id == user_id,
                EmotionHistory.recorded_date == recorded_date,
            )
        ).first()
        return record

    def get_emotion_history(
        self, user_id: int, days: int = 30
    ) -> List[EmotionHistoryPoint]:
        """获取最近 N 天的情绪历史"""
        from datetime import timedelta

        cutoff = datetime.utcnow().date() - timedelta(days=days)
        records = (
            self.db.query(EmotionHistory)
            .filter(
                and_(
                    EmotionHistory.user_id == user_id,
                    EmotionHistory.recorded_date >= cutoff,
                )
            )
            .order_by(EmotionHistory.recorded_date)
            .all()
        )
        return [
            EmotionHistoryPoint(date=str(r.recorded_date), level=r.emotion_level)
            for r in records
        ]

    # ─── Judgment History ────────────────────────────────────────────────────────

    def upsert_judgment_history(
        self,
        user_id: int,
        judgment_date: date_type,
        judgment_label: str,
        is_hard_to_tell: bool,
        analysis_task_id: Optional[UUID] = None,
    ) -> Optional[JudgmentHistory]:
        """Upsert 判断质量历史（"难以区分"不写 score）"""
        if is_hard_to_tell:
            score = 0  # 占位，但前端应忽略
        else:
            score = JUDGMENT_SCORE_MAP.get(judgment_label, 0)

        stmt = insert(JudgmentHistory).values(
            user_id=user_id,
            judgment_date=judgment_date,
            judgment_score=score,
            judgment_label=judgment_label,
            is_hard_to_tell=is_hard_to_tell,
            analysis_task_id=analysis_task_id,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="ix_judgment_history_user_date",
            set_={
                "judgment_score": score,
                "judgment_label": judgment_label,
                "is_hard_to_tell": is_hard_to_tell,
                "analysis_task_id": analysis_task_id,
                "created_at": datetime.utcnow(),
            },
        )
        self.db.execute(stmt)
        self.db.commit()
        record = self.db.query(JudgmentHistory).filter(
            and_(
                JudgmentHistory.user_id == user_id,
                JudgmentHistory.judgment_date == judgment_date,
            )
        ).first()
        return record

    def get_judgment_history(
        self, user_id: int, days: int = 30
    ) -> List[JudgmentHistoryPoint]:
        """获取最近 N 天的判断质量历史"""
        from datetime import timedelta

        cutoff = datetime.utcnow().date() - timedelta(days=days)
        records = (
            self.db.query(JudgmentHistory)
            .filter(
                and_(
                    JudgmentHistory.user_id == user_id,
                    JudgmentHistory.judgment_date >= cutoff,
                )
            )
            .order_by(JudgmentHistory.judgment_date)
            .all()
        )
        return [
            JudgmentHistoryPoint(
                date=str(r.judgment_date),
                score=r.judgment_score,
                label=r.judgment_label,
                is_hard_to_tell=r.is_hard_to_tell,
            )
            for r in records
        ]

    # ─── Combined ───────────────────────────────────────────────────────────────

    def get_learning_history(
        self, user_id: int, days: int = 30
    ) -> LearningHistoryResponse:
        """获取完整的画像学习历史（情绪 + 判断质量）"""
        return LearningHistoryResponse(
            emotion_history=self.get_emotion_history(user_id, days),
            judgment_history=self.get_judgment_history(user_id, days),
        )

    def record_learning_feedback(
        self,
        user_id: int,
        data: LearningFeedbackRequest,
    ) -> LearningFeedbackResponse:
        """写入学习反馈：情绪历史 + 判断质量历史 + 行为标签合并"""
        today = datetime.utcnow().date()
        is_hard_to_tell = data.judgment_quality == "难以区分"

        # 1. Upsert emotion_history
        analysis_task_uuid = None
        if data.analysis_task_id:
            try:
                analysis_task_uuid = UUID(data.analysis_task_id)
            except ValueError:
                pass

        self.upsert_emotion_history(
            user_id=user_id,
            recorded_date=today,
            emotion_level=data.emotion_level,
            analysis_task_id=analysis_task_uuid,
            intent=data.intent,
            trigger_reason=data.trigger_reason,
        )

        # 2. Upsert judgment_history（"难以区分"时 judgment_score=0，但 is_hard_to_tell=True）
        self.upsert_judgment_history(
            user_id=user_id,
            judgment_date=today,
            judgment_label=data.judgment_quality,
            is_hard_to_tell=is_hard_to_tell,
            analysis_task_id=analysis_task_uuid,
        )

        # 3. 合并 behavior_tags 到 UserProfile
        tags_updated = self._merge_behavior_tags(user_id, data.tag_updates)

        logger.info(
            "learning_feedback_recorded",
            user_id=user_id,
            judgment_label=data.judgment_quality,
            is_hard_to_tell=is_hard_to_tell,
            tags_updated=tags_updated,
        )

        return LearningFeedbackResponse(
            success=True,
            tags_updated=tags_updated,
            judgment_recorded=not is_hard_to_tell,
        )

    def _merge_behavior_tags(
        self, user_id: int, tag_updates: List[dict]
    ) -> int:
        """合并行为标签到 UserProfile.behavior_tags

        - add: 追加到列表（不去重旧标签）
        - remove: 从列表移除
        - upgrade: 不改变列表内容（只记录升级事件）
        """
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        if not profile:
            return 0

        tags: List[str] = list(profile.behavior_tags or [])
        updated = 0

        for update in tag_updates:
            tag_name = update.get("tag", "")
            action = update.get("type", "add")

            if action == "add":
                if tag_name not in tags:
                    tags.append(tag_name)
                    updated += 1
            elif action == "remove":
                if tag_name in tags:
                    tags.remove(tag_name)
                    updated += 1
            # upgrade: 不改变列表

        profile.behavior_tags = tags
        self.db.commit()
        return updated
