"""分析结果模型

对应基线表 analysis_results（UUID 主键）。
六段式决策卡、降级标记、行为干预引用。
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db.session import Base
import enum


class ValidPeriodEnum(enum.Enum):
    """分析结论有效期"""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class OutputTagEnum(enum.Enum):
    """输出标记枚举"""
    DATA_FACT = "data_fact"
    MODEL_INFERENCE = "model_inference"
    UNCERTAINTY = "uncertainty"


class AnalysisResult(Base):
    """分析结果模型

    六段式决策卡结构，与 AnalysisTask 一对一关联。
    """
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    analysis_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 六段式决策卡
    headline_judgement = Column(Text, nullable=False)  # 判断结论
    key_reason_summary = Column(JSON, nullable=False)  # [string] 关键理由摘要
    user_fit_summary = Column(JSON, nullable=False)  # {fit: string, unfit: string}
    next_step_actions = Column(JSON, nullable=False)  # [string] 下一步动作
    primary_risks = Column(Text, nullable=False)  # 主要风险
    review_at = Column(DateTime, nullable=False)  # 复查时点

    # 证据结构（本次新增）
    supporting_evidence = Column(JSON, nullable=False, default=list)   # [string] 支撑证据
    counter_evidence = Column(JSON, nullable=False, default=list)      # [string] 反方证据
    invalidation_conditions = Column(JSON, nullable=False, default=list)  # [string] 失效条件
    confidence_level = Column(String(20), nullable=False, default="medium")  # low/medium/high

    # 行为干预引用
    intervention = Column(JSON, nullable=True)  # BehaviorIntervention JSON 结构

    # 适配性说明
    fit_summary = Column(Text, nullable=True)

    # 市场背景
    market_context = Column(JSON, nullable=True)  # MarketContext JSON 结构

    # AI 解释层
    explanation_layer = Column(JSON, nullable=True)  # ExplanationLayer JSON 结构

    # 详细推理面板
    detail_panels = Column(JSON, nullable=True)  # DetailPanels JSON 结构

    # 输出标记
    output_tags = Column(JSON, nullable=False, default=list)  # [OutputTagEnum]

    # 有效期
    valid_period = Column(
        Enum(
            ValidPeriodEnum,
            name="validperiodenum",
            values_callable=lambda cls: [e.value for e in cls],
            default=ValidPeriodEnum.MEDIUM,
        ),
        nullable=False,
    )

    # Relationships
    task = relationship("AnalysisTask", back_populates="result")

    __table_args__ = (
        Index("ix_analysis_results_task_id", "analysis_task_id", unique=True),
    )
