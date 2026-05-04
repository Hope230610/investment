from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from src.models.analysis import (
    AnalysisStatus,
    InteractionScenario,
    OutputMarkType,
    ReviewTaskStatus,
)
from src.schemas.common import TimestampMixin
from src.schemas.stock import StockCompanyProfile, StockEvent, StockQuoteSnapshot


class UserFitSummary(BaseModel):
    fit: str
    unfit: str


class ReasonPoint(BaseModel):
    text: str
    tag: OutputMarkType = OutputMarkType.MODEL_INFERENCE


class MarketContext(BaseModel):
    market_event: str
    impact_boundary: str
    mark_type: OutputMarkType = OutputMarkType.MODEL_INFERENCE


class ExplanationLayer(BaseModel):
    plain_text: str
    case_example: str


class BehaviorIntervention(BaseModel):
    behavior_type: str
    severity: Literal["low", "medium", "high"]
    questions: List[str]


class DecisionCard(BaseModel):
    headline_judgement: str
    key_reason_summary: List[ReasonPoint]
    user_fit_summary: UserFitSummary
    next_step_actions: List[str]
    primary_risks: str
    review_at: datetime
    valid_until: Optional[datetime] = None
    data_as_of: Optional[datetime] = None
    stock_snapshot: Optional[StockQuoteSnapshot] = None
    company_profile: Optional[StockCompanyProfile] = None
    recent_events: List[StockEvent] = []
    data_sources: List[str] = []
    supporting_evidence: List[str] = []     # 支撑证据（本次新增）
    counter_evidence: List[str] = []         # 反方证据（本次新增）
    invalidation_conditions: List[str] = []  # 失效条件（本次新增）
    confidence_level: Literal["low", "medium", "high"] = "medium"  # 置信度等级（本次新增）


class AnalysisReasonBase(BaseModel):
    text: str
    order: int = 0
    mark_type: OutputMarkType


class AnalysisReasonCreate(AnalysisReasonBase):
    pass


class AnalysisReason(AnalysisReasonBase, TimestampMixin):
    id: int
    analysis_id: int

    class Config:
        from_attributes = True


class ReviewTaskBase(BaseModel):
    stock_id: Optional[str] = None
    stock_name: str
    scenario: str
    review_at: datetime
    status: ReviewTaskStatus = ReviewTaskStatus.PENDING


class ReviewTaskCreate(BaseModel):
    """旧路径创建用（Phase 1 迁移完成前保留）"""
    analysis_id: int
    stock_name: str
    scenario: str
    review_at: datetime


class ReviewTaskCreateV2(BaseModel):
    """新路径创建用（Phase 3 及之后）"""
    analysis_task_id: str
    stock_name: str
    scenario: str
    review_at: datetime


class ReviewTaskUpdate(BaseModel):
    status: Optional[ReviewTaskStatus] = None
    review_result: Optional[Dict[str, Any]] = None


class ReviewTask(TimestampMixin):
    """复盘任务 schema（迁移后主键为 UUID，外键为 analysis_task_id）

    旧路径兼容：analysis_id 为 Integer（来自 analyses 表）
    新路径：analysis_task_id 为 UUID（来自 analysis_tasks 表）
    两字段互斥，根据请求上下文填充其中一个。
    """
    id: int
    user_id: int
    analysis_task_id: Optional[str] = None  # 新路径 UUID
    analysis_id: Optional[int] = None  # 旧路径 Integer（向后兼容）
    stock_name: Optional[str] = None
    stock_id: Optional[str] = None
    scenario: str
    review_at: Optional[datetime] = None
    status: str  # 'pending' | 'completed' | 'expired'，DB 存字符串，避免枚举值大小写不匹配
    review_result: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

    @field_validator("analysis_task_id", mode="before")
    @classmethod
    def _convert_analysis_task_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v


class AnalysisBase(BaseModel):
    scenario: InteractionScenario
    scenario_payload: Optional[Dict[str, Any]] = None


class AnalysisCreate(AnalysisBase):
    stock_id: str


class AnalysisCreateResponse(BaseModel):
    """统一响应：无论新旧路径都返回 UUID 字符串 ID，便于前端直接导航。"""
    id: str
    status: str


class AnalysisUpdate(BaseModel):
    status: Optional[AnalysisStatus] = None
    headline: Optional[str] = None
    decision_card: Optional[Dict[str, Any]] = None
    fit_summary: Optional[str] = None
    market_context: Optional[Dict[str, Any]] = None
    explanation_layer: Optional[Dict[str, Any]] = None
    intervention: Optional[Dict[str, Any]] = None


class AnalysisResult(BaseModel):
    status: str
    analysis_template_version: str = "decision-card-v1"
    analysis_policy_version: str = "p0-quality-policy-v1"
    degrade_flags: List[str] = []
    intervention: Optional[BehaviorIntervention] = None
    decision_card: DecisionCard
    fit_summary: str
    market_context: MarketContext
    explanation_layer: ExplanationLayer


class Analysis(AnalysisBase, TimestampMixin):
    id: int
    user_id: int
    stock_id: str
    status: AnalysisStatus
    headline: Optional[str] = None
    decision_card: Optional[Dict[str, Any]] = None
    fit_summary: Optional[str] = None
    market_context: Optional[Dict[str, Any]] = None
    explanation_layer: Optional[Dict[str, Any]] = None
    intervention: Optional[Dict[str, Any]] = None
    review_at: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnalysisWithDetails(Analysis):
    stock_name: Optional[str] = None
    stock_market: Optional[str] = None
    stock_industry: Optional[str] = None
    reasons: List[AnalysisReason] = []
    review_tasks: List[ReviewTask] = []

    class Config:
        from_attributes = True


class DecisionCardV2(BaseModel):
    """新路径（六段式决策卡 + 证据结构）"""
    headline_judgement: str
    key_reason_summary: List[Dict[str, Any]]
    user_fit_summary: Dict[str, str]
    next_step_actions: List[str]
    primary_risks: str
    review_at: datetime
    supporting_evidence: List[str] = []   # 支撑证据（本次新增）
    counter_evidence: List[str] = []      # 反方证据（本次新增）
    invalidation_conditions: List[str] = []  # 失效条件（本次新增）
    confidence_level: Literal["low", "medium", "high"] = "medium"  # 置信度等级（本次新增）
    # 对外契约别名：confidence 是产品语言，confidence_level 是存储字段。
    confidence: Literal["low", "medium", "high"] = "medium"
    timestamp: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class InterventionInfo(BaseModel):
    """新路径行为干预信息"""
    behavior_type: str
    severity: Literal["low", "medium", "high"]
    questions: List[str]
    cooldown_minutes: Optional[int] = None


class GetAnalysisResponseV2(BaseModel):
    """新路径 get_analysis 完整响应（来自 analysis_tasks + analysis_results）"""
    analysis_id: str
    user_id: int
    stock_id: str
    scenario: str
    status: str
    degrade_flags: List[str] = []
    analysis_template_version: Optional[str] = None
    analysis_policy_version: Optional[str] = None
    intervention: Optional[InterventionInfo] = None
    decision_card: DecisionCardV2
    fit_summary: Optional[str] = None
    market_context: Optional[Dict[str, Any]] = None
    explanation_layer: Optional[Dict[str, Any]] = None
    detail_panels: Optional[Dict[str, Any]] = None
    review_task: Optional[Dict[str, Any]] = None  # {id, review_at, status}
    # UI 展示层字段（从实时行情数据获取，不持久化）
    stock_snapshot: Optional[StockQuoteSnapshot] = None
    company_profile: Optional[StockCompanyProfile] = None
    recent_events: List[StockEvent] = []
    data_sources: List[str] = []
    valid_until: Optional[datetime] = None
    data_as_of: Optional[datetime] = None
    timestamp: Optional[datetime] = None
    # 股票基本信息（从 StockDetail 获取）
    stock_name: Optional[str] = None
    stock_market: Optional[str] = None
    stock_industry: Optional[str] = None
    # 场景透传（intent / trigger_reason / emotion_level，用于标签推断）
    scenario_payload: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AnalysisRecord(BaseModel):
    """分析历史记录（支持 UUID 和 Integer 两种 ID）"""
    id: str  # 新路径为 UUID 字符串，旧路径为 Integer
    scenario: str
    stock_id: str
    stock_name: Optional[str] = None
    created_at: datetime
    status: str
    headline: Optional[str] = None

    class Config:
        from_attributes = True
