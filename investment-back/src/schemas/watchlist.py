from pydantic import BaseModel, Field
from typing import Optional
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
    id: int
    user_id: int

    class Config:
        from_attributes = True

class WatchlistItemWithStock(WatchlistItem):
    stock_name: Optional[str] = None
    industry: Optional[str] = None

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
