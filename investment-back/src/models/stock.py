from sqlalchemy import Column, Integer, String, Float, Text
from sqlalchemy.orm import relationship
from src.db.session import Base
from src.models.base import TimestampMixin

class Stock(TimestampMixin, Base):
    """股票模型"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    stock_id = Column(String(20), unique=True, index=True, nullable=False)  # 如 SH600519
    stock_name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False)  # SH, SZ, BSE
    industry = Column(String(100), nullable=True)
    # Basic info
    listing_date = Column(String(20), nullable=True)
    total_shares = Column(Float, nullable=True)  # 总股本
    float_shares = Column(Float, nullable=True)  # 流通股本
    # Financial metrics (cached)
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    # Relationships
    analyses = relationship("Analysis", back_populates="stock")
    watchlist_items = relationship("WatchlistItem", back_populates="stock")
