"""行为干预记录模型

对应基线表 behavior_interventions（UUID 主键）。
支持冷静期追踪、用户确认反馈和动作归因。
"""
from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db.session import Base
import enum


class BehaviorTypeEnum(enum.Enum):
    """行为类型枚举"""
    CHASING_RISE = "chasing_rise"
    PANIC_SELL = "panic_sell"
    FREQUENT_TRADING = "frequent_trading"


class SeverityLevelEnum(enum.Enum):
    """严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InterventionActionTakenEnum(enum.Enum):
    """干预后用户实际动作"""
    CONTINUED = "continued"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    LOGGED_ONLY = "logged_only"


class BehaviorIntervention(Base):
    """行为干预记录模型

    独立存储干预记录，支持冷静期追踪和归因分析。
    """
    __tablename__ = "behavior_interventions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    analysis_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 干预类型
    behavior_type = Column(
        Enum(
            BehaviorTypeEnum,
            name="behaviortypeenum",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )
    severity = Column(
        Enum(
            SeverityLevelEnum,
            name="severitylevelenum",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )

    # 冷静期
    cooldown_started_at = Column(DateTime, nullable=True)
    cooldown_ended_at = Column(DateTime, nullable=True)
    cooldown_questions = Column(JSON, nullable=True)  # [string]

    # 用户反馈
    user_acknowledged = Column(Boolean, default=False, nullable=False)
    user_notes = Column(Text, nullable=True)

    # 最终动作
    action_taken = Column(
        Enum(
            InterventionActionTakenEnum,
            name="interventionactiontakenenum",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=True,
    )

    # Relationships
    user = relationship("User", backref="behavior_interventions")
    task = relationship("AnalysisTask", back_populates="behavior_interventions")

    __table_args__ = (
        Index("ix_behavior_interventions_behavior_type", "behavior_type"),
        Index("ix_behavior_interventions_created_at", "created_at"),
    )
