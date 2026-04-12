"""观察列表模型 v2

合并后的 watchlists 表：
- 移除 watchlist_items / focus_reasons 分离设计
- UNIQUE(user_id, stock_id) 去重约束
- 新增 added_from_scenario / source_analysis_id / notify_on_events 字段
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db.session import Base
from src.models.base import TimestampMixin
import enum


class AddedFromScenarioEnum(enum.Enum):
    """添加来源场景枚举"""
    SINGLE_STOCK_CHECK = "single_stock_check"
    PRE_TRADE_CHECK = "pre_trade_check"
    POST_TRADE_REVIEW = "post_trade_review"


class Watchlist(TimestampMixin, Base):
    """合并后的观察列表模型

    以用户 + 股票为唯一约束，同一用户对同一股票不得重复添加。
    focus_reason 存储在表内，不再分离到 focus_reasons 表。
    """
    __tablename__ = "watchlists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    stock_id = Column(String(20), ForeignKey("stocks.stock_id"), index=True, nullable=False)

    # 关注理由（从原 focus_reasons 合并）
    focus_reason = Column(Text, nullable=True)

    # 来源信息
    added_from_scenario = Column(
        Enum(AddedFromScenarioEnum),
        nullable=True,
    )
    source_analysis_id = Column(UUID(as_uuid=True), nullable=True)

    # 事件提醒开关
    notify_on_events = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", backref="watchlists")
    stock = relationship("Stock", backref="watchlists")

    __table_args__ = (
        UniqueConstraint("user_id", "stock_id", name="uq_watchlists_user_stock"),
        Index("ix_watchlists_user_id", "user_id"),
        Index("ix_watchlists_stock_id", "stock_id"),
    )