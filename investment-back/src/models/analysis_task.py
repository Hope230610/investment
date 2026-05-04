"""分析任务模型

对应基线表 analysis_tasks（UUID 主键）。
分析任务生命周期与结果输出分离，任务创建时保存用户画像快照。
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db.session import Base
from src.models.base import TimestampMixin
import enum


class AnalysisScenarioEnum(enum.Enum):
    """分析场景枚举"""
    SINGLE_STOCK_CHECK = "single_stock_check"
    PRE_TRADE_CHECK = "pre_trade_check"
    POST_TRADE_REVIEW = "post_trade_review"


class AnalysisStatusEnum(enum.Enum):
    """分析状态枚举（包含 partial_ready 中间态）"""
    PROCESSING = "processing"
    PARTIAL_READY = "partial_ready"
    READY = "ready"
    EXPIRED = "expired"
    FAILED = "failed"


class AnalysisTask(TimestampMixin, Base):
    """分析任务模型

    记录任务生命周期，输入快照，不含结果。
    """
    __tablename__ = "analysis_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    stock_id = Column(String(20), ForeignKey("stocks.stock_id"), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 场景信息（使用数据库已有的 interactionscenario enum，values_callable 确保用值而非名）
    scenario = Column(
        Enum(
            AnalysisScenarioEnum,
            name="interactionscenario",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )

    # 任务状态（使用数据库已有的 analysisstatusv2 enum）
    status = Column(
        Enum(
            AnalysisStatusEnum,
            name="analysisstatusv2",
            values_callable=lambda cls: [e.value for e in cls],
            default=AnalysisStatusEnum.PROCESSING,
        ),
        nullable=False,
    )

    # 输入快照
    user_profile_snapshot = Column(JSON, nullable=True)  # JSON: UserProfileSnapshot 结构
    scenario_payload = Column(JSON, nullable=True)  # JSON: ScenarioPayload 结构

    # 时间戳
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=False)

    # 错误信息
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="analysis_tasks")
    stock = relationship("Stock", backref="analysis_tasks")
    result = relationship(
        "AnalysisResult",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )
    behavior_interventions = relationship(
        "BehaviorIntervention",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    review_tasks = relationship(
        "ReviewTask",
        foreign_keys="ReviewTask.analysis_task_id",
        back_populates="task",
    )

    __table_args__ = (
        Index("ix_analysis_tasks_scenario", "scenario"),
        Index("ix_analysis_tasks_status", "status"),
        Index("ix_analysis_tasks_expired_at", "expired_at"),
    )
