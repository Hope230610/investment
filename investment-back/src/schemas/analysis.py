from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

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
    tag: OutputMarkType = OutputMarkType.MODEL_INFERENCE


class ExplanationLayer(BaseModel):
    plain_text: str
    case_example: str


class BehaviorIntervention(BaseModel):
    behavior_type: str
    severity: str
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


class ReviewTaskCreate(ReviewTaskBase):
    analysis_id: int


class ReviewTaskUpdate(BaseModel):
    status: Optional[ReviewTaskStatus] = None
    review_result: Optional[Dict[str, Any]] = None


class ReviewTask(ReviewTaskBase, TimestampMixin):
    id: int
    user_id: int
    analysis_id: int
    review_result: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AnalysisBase(BaseModel):
    scenario: InteractionScenario
    scenario_payload: Optional[Dict[str, Any]] = None


class AnalysisCreate(AnalysisBase):
    stock_id: str


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


class AnalysisRecord(BaseModel):
    id: int
    scenario: str
    stock_id: str
    stock_name: Optional[str] = None
    created_at: datetime
    status: AnalysisStatus
    headline: Optional[str] = None

    class Config:
        from_attributes = True
