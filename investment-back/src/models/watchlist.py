from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.db.session import Base
from src.models.base import TimestampMixin

class WatchlistItem(TimestampMixin, Base):
    """观察列表项模型（旧表，已重命名为 watchlist_items_legacy）"""
    __tablename__ = "watchlist_items_legacy"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    stock_id = Column(String(20), ForeignKey("stocks.stock_id"), index=True, nullable=False)
    focus_reason = Column(Text, nullable=True)
    # Relationships
    user = relationship("User", back_populates="watchlist")
    stock = relationship("Stock", back_populates="watchlist_items")

class FocusReason(TimestampMixin, Base):
    """关注理由模型（旧表，已重命名为 focus_reasons_legacy）"""
    __tablename__ = "focus_reasons_legacy"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    analysis_id = Column(Integer, index=True, nullable=False)
    stock_id = Column(String(20), index=True, nullable=False)
    reason = Column(Text, nullable=False)
