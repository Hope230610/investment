from datetime import date as date_type
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TagUpdateSchema(BaseModel):
    """行为标签更新项"""
    tag: str = Field(..., description="标签中文名称，如「盲目跟风」「过度焦虑」「分期依赖」")
    type: Literal["add", "remove", "upgrade"] = Field(..., description="更新类型")
    source: str = Field(..., description="标签来源说明")


class LearningFeedbackRequest(BaseModel):
    """POST /api/v1/user/profile/learning-feedback 请求体"""
    analysis_task_id: Optional[str] = Field(
        default=None,
        description="关联的分析任务 UUID（可选）"
    )
    tag_updates: List[TagUpdateSchema] = Field(
        default_factory=list,
        description="行为标签更新列表"
    )
    judgment_quality: Literal[
        "主要来自判断",
        "主要来自理性判断",
        "部分判断 + 部分运气",
        "部分判断 + 部分情绪",
        "主要来自运气",
        "主要来自情绪冲动",
        "难以区分",
    ] = Field(..., description="判断质量选项")
    emotion_level: int = Field(
        ...,
        ge=1,
        le=5,
        description="本次复盘情绪评分 1-5"
    )
    intent: Optional[str] = Field(
        default=None,
        description="本次操作意图：buy/sell/add_position/reduce_position"
    )
    trigger_reason: Optional[str] = Field(
        default=None,
        description="触发原因描述"
    )


class LearningFeedbackResponse(BaseModel):
    """POST /api/v1/user/profile/learning-feedback 响应体"""
    success: bool
    tags_updated: int = Field(
        description="本次成功写入的行为标签数量"
    )
    judgment_recorded: bool = Field(
        description="判断质量是否已记录（难以区分时为 False）"
    )


class EmotionHistoryPoint(BaseModel):
    """情绪历史单条记录"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    level: int = Field(..., ge=1, le=5, description="情绪评分 1-5")

    class Config:
        from_attributes = True


class JudgmentHistoryPoint(BaseModel):
    """判断质量历史单条记录"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    score: int = Field(..., ge=0, le=100, description="判断得分 0-100")
    label: str = Field(..., description="判断标签原文")
    is_hard_to_tell: bool = Field(default=False)

    class Config:
        from_attributes = True


class LearningHistoryResponse(BaseModel):
    """GET /api/v1/user/profile/learning-history 响应体"""
    emotion_history: List[EmotionHistoryPoint]
    judgment_history: List[JudgmentHistoryPoint]
