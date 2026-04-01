from sqlalchemy import Column, Integer, String, Text, Enum, JSON, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from src.db.session import Base
from src.models.base import TimestampMixin
import enum

class AnalysisStatus(enum.Enum):
    """分析状态"""
    PROCESSING = "processing"
    READY = "ready"
    EXPIRED = "expired"
    FAILED = "failed"

class InteractionScenario(enum.Enum):
    """交互场景"""
    SINGLE_STOCK_CHECK = "single_stock_check"
    PRE_TRADE_CHECK = "pre_trade_check"
    POST_TRADE_REVIEW = "post_trade_review"

class OutputMarkType(enum.Enum):
    """输出标记类型"""
    DATA_FACT = "data_fact"
    MODEL_INFERENCE = "model_inference"
    UNCERTAINTY = "uncertainty"

class Analysis(TimestampMixin, Base):
    """分析记录模型"""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    stock_id = Column(String(20), ForeignKey("stocks.stock_id"), index=True, nullable=False)
    # Basic info
    scenario = Column(Enum(InteractionScenario), nullable=False)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PROCESSING, nullable=False)
    headline = Column(String(255), nullable=True)
    # Scenario payload (input data)
    scenario_payload = Column(JSON, nullable=True)
    # Decision card output
    decision_card = Column(JSON, nullable=True)
    # Fit summary
    fit_summary = Column(Text, nullable=True)
    # Market context
    market_context = Column(JSON, nullable=True)
    # Explanation layer
    explanation_layer = Column(JSON, nullable=True)
    # Intervention
    intervention = Column(JSON, nullable=True)
    # Time info
    review_at = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    # Relationships
    user = relationship("User", back_populates="analyses")
    stock = relationship("Stock", back_populates="analyses")
    reasons = relationship("AnalysisReason", back_populates="analysis", cascade="all, delete-orphan")
    review_tasks = relationship("ReviewTask", back_populates="analysis")

class AnalysisReason(TimestampMixin, Base):
    """分析理由模型"""
    __tablename__ = "analysis_reasons"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), index=True, nullable=False)
    text = Column(Text, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    mark_type = Column(Enum(OutputMarkType), nullable=False)
    # Relationships
    analysis = relationship("Analysis", back_populates="reasons")

class ReviewTaskStatus(enum.Enum):
    """复盘任务状态"""
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"

class ReviewTask(TimestampMixin, Base):
    """复盘任务模型"""
    __tablename__ = "review_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), index=True, nullable=False)
    stock_name = Column(String(100), nullable=False)
    scenario = Column(String(50), nullable=False)
    review_at = Column(DateTime, nullable=False)
    status = Column(Enum(ReviewTaskStatus), default=ReviewTaskStatus.PENDING, nullable=False)
    # Review result
    review_result = Column(JSON, nullable=True)
    # Relationships
    user = relationship("User", back_populates="reviews")
    analysis = relationship("Analysis", back_populates="review_tasks")
