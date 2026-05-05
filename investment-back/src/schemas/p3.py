from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GrowthCautionContext(BaseModel):
    repeated_mistakes: list[str] = Field(default_factory=list)
    behavior_patterns: list[str] = Field(default_factory=list)
    recent_review_findings: list[str] = Field(default_factory=list)
    risk_tendencies: list[str] = Field(default_factory=list)
    caution_rules: list[str] = Field(default_factory=list)
    suggested_review_questions: list[str] = Field(default_factory=list)
    confidence_level: Literal["low", "medium", "high"] = "low"
    generated_at: datetime


class AiEvalRequest(BaseModel):
    case_id: str = "ad_hoc"
    output: dict[str, Any] | str | None
    holding_context_source: Optional[Literal["server", "client", "none"]] = None


class AiEvalResult(BaseModel):
    case_id: str
    passed: bool
    score: int
    failed_rules: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    compliance_flags: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    evaluated_at: datetime


class CreateShareSnapshotRequest(BaseModel):
    source_type: Literal["analysis"] = "analysis"
    source_id: str
    privacy_level: Literal["public", "unlisted"] = "unlisted"
    expires_in_days: int = Field(default=30, ge=1, le=90)


class ShareSnapshotPrivate(BaseModel):
    share_id: str
    source_type: str
    source_id: str
    title: str
    summary: str
    support_evidence: list[str]
    counter_evidence: list[str]
    risks: list[str]
    invalidation_conditions: list[str]
    confidence_level: str
    data_timestamp: Optional[datetime] = None
    disclaimer: str
    privacy_level: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class PublicShareSnapshot(BaseModel):
    share_id: str
    title: str
    summary: str
    support_evidence: list[str]
    counter_evidence: list[str]
    risks: list[str]
    invalidation_conditions: list[str]
    confidence_level: str
    data_timestamp: Optional[datetime] = None
    disclaimer: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class EntitlementView(BaseModel):
    plan_code: Literal["free", "pro"]
    feature_flags: dict[str, bool]
    limits: dict[str, int | None]
    usage: dict[str, int]
