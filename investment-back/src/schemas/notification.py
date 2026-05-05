from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class NotificationType(str, Enum):
    REVIEW_REMINDER = "review_reminder"
    WATCHLIST_ALERT = "watchlist_alert"
    ANALYSIS_INVALIDATION = "analysis_invalidation"
    PORTFOLIO_RISK = "portfolio_risk"


class NotificationUrgency(str, Enum):
    OVERDUE = "overdue"
    DUE_SOON = "due_soon"
    NORMAL = "normal"
    HIGH = "high"


class NotificationItem(BaseModel):
    """单条提醒"""
    id: str  # UUID 字符串
    type: NotificationType
    title: str
    description: str
    urgency: NotificationUrgency = NotificationUrgency.NORMAL
    stock_id: Optional[str] = None
    stock_name: Optional[str] = None
    action_url: Optional[str] = None
    created_at: datetime
    metadata: Optional[dict] = None  # 附加数据（用于前端跳转参数等）


class NotificationSummary(BaseModel):
    """提醒摘要（用于 Tab Badge 等轻量场景）"""
    total: int
    overdue_count: int
    due_soon_count: int
    watchlist_alert_count: int
    invalidation_count: int


class NotificationListResponse(BaseModel):
    """提醒中心完整响应"""
    notifications: list[NotificationItem]
    total: int
    unread_count: int  # 本次返回中 urgency=OVERDUE 或 urgency=HIGH 的数量
    summary: NotificationSummary
