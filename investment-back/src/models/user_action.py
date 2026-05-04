"""用户操作埋点模型

对应 user_actions 表，记录用户在系统内的关键操作行为。
支持追溯用户从分析到复盘的完整行为链路。
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from src.db.session import Base
import enum


class UserActionTypeEnum(enum.Enum):
    """用户操作类型枚举"""
    SCENARIO_SELECTED = "scenario_selected"
    ANALYSIS_SUBMITTED = "analysis_submitted"
    BEHAVIOR_INTERVENTION_SHOWN = "behavior_intervention_shown"
    COOLDOWN_STARTED = "cooldown_started"
    REVIEW_TASK_COMPLETED = "review_task_completed"


class UserAction(Base):
    """用户操作埋点模型"""
    __tablename__ = "user_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # 操作类型
    action_type = Column(Enum(UserActionTypeEnum), nullable=False, index=True)

    # 操作时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 操作附加数据（JSON）
    action_payload = Column(JSON, nullable=True)

    # 关联股票和分析任务
    stock_id = Column(String(20), nullable=True)
    analysis_task_id = Column(UUID(as_uuid=True), nullable=True)

    # 请求上下文
    page_path = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="user_actions")

    __table_args__ = (
        Index("ix_user_actions_created_at", "created_at"),
    )
