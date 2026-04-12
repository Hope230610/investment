"""情绪历史记录模型

对应 emotion_history 表，记录用户每日情绪评分（1-5），
用于绘制情绪趋势 sparkline。
"""
from datetime import datetime, date
from typing import Optional
import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db.session import Base


class EmotionHistory(Base):
    """用户情绪历史记录

    每日一条记录，upsert 模式（同一 user_id + recorded_date 覆盖）。
    """
    __tablename__ = "emotion_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    analysis_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 记录日期（每日一条，用于聚合查询）
    recorded_date = Column(Date, nullable=False)

    # 情绪评分 1-5
    emotion_level = Column(Integer, nullable=False)

    # 触发上下文（用于归因分析）
    intent = Column(String(50), nullable=True)
    trigger_reason = Column(String(100), nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="emotion_history")

    __table_args__ = (
        Index("ix_emotion_history_user_id", "user_id"),
        Index("ix_emotion_history_recorded_date", "recorded_date"),
        Index("ix_emotion_history_user_date", "user_id", "recorded_date", unique=True),
    )
