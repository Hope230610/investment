from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db.session import Base
from src.models.base import TimestampMixin


class TransactionSideEnum(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class Holding(TimestampMixin, Base):
    """Current user-maintained holding snapshot."""

    __tablename__ = "holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    stock_id = Column(String(20), ForeignKey("stocks.stock_id"), index=True, nullable=False)
    stock_name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    cost_price = Column(Numeric(18, 4), nullable=False)
    current_price = Column(Numeric(18, 4), nullable=False)
    note = Column(Text, nullable=True)
    position_updated_at = Column(DateTime, nullable=False)

    user = relationship("User", backref="holdings")
    stock = relationship("Stock", backref="holdings")

    __table_args__ = (
        Index("ix_holdings_user_stock", "user_id", "stock_id", unique=True),
    )


class Transaction(TimestampMixin, Base):
    """User-entered buy/sell record."""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    stock_id = Column(String(20), ForeignKey("stocks.stock_id"), index=True, nullable=False)
    stock_name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False)
    side = Column(
        Enum(
            TransactionSideEnum,
            name="transactionside",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )
    price = Column(Numeric(18, 4), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    traded_at = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
    analysis_task_id = Column(UUID(as_uuid=True), ForeignKey("analysis_tasks.id"), nullable=True)
    pre_trade_check_id = Column(UUID(as_uuid=True), ForeignKey("analysis_tasks.id"), nullable=True)
    review_task_id = Column(Integer, ForeignKey("review_tasks.id"), nullable=True)

    user = relationship("User", backref="transactions")
    stock = relationship("Stock", backref="transactions")
    analysis_task = relationship("AnalysisTask", foreign_keys=[analysis_task_id])
    pre_trade_check = relationship("AnalysisTask", foreign_keys=[pre_trade_check_id])
    review_task = relationship("ReviewTask", foreign_keys=[review_task_id])

    __table_args__ = (
        Index("ix_transactions_user_traded_at", "user_id", "traded_at"),
        Index("ix_transactions_user_stock", "user_id", "stock_id"),
    )
