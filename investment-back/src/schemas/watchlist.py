from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from src.schemas.common import TimestampMixin

# 观察列表项
class WatchlistItemBase(BaseModel):
    stock_id: str = Field(..., max_length=20)
    focus_reason: Optional[str] = None

class WatchlistItemCreate(WatchlistItemBase):
    pass

class WatchlistItemUpdate(BaseModel):
    focus_reason: Optional[str] = None

class WatchlistItem(WatchlistItemBase, TimestampMixin):
    id: str
    user_id: int
    stock_name: str
    market: str
    industry: Optional[str] = None

    class Config:
        from_attributes = True

class WatchlistItemWithStock(WatchlistItem):
    pass

    class Config:
        from_attributes = True

# 关注理由
class FocusReasonBase(BaseModel):
    analysis_id: int
    stock_id: str = Field(..., max_length=20)
    reason: str

class FocusReasonCreate(FocusReasonBase):
    pass


class FocusReason(FocusReasonBase, TimestampMixin):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ─── 新路径：record-reason 专用 schema ─────────────────────────────────────────

class RecordReasonRequest(BaseModel):
    """POST /analysis/{uuid}/record-reason 请求体（仅 stock_id + reason）"""
    stock_id: str = Field(..., max_length=20)
    reason: str


class RecordReasonResponse(BaseModel):
    """POST /analysis/{uuid}/record-reason 响应（UUID 友好结构）"""
    id: str  # watchlists.id UUID 字符串
    user_id: int
    stock_id: str
    focus_reason: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
