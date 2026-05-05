from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class HoldingBase(BaseModel):
    stock_id: str = Field(..., min_length=3, max_length=20)
    stock_name: Optional[str] = None
    market: Optional[str] = None
    quantity: float = Field(..., gt=0)
    cost_price: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    note: Optional[str] = Field(default=None, max_length=500)
    position_updated_at: Optional[datetime] = None


class HoldingCreate(HoldingBase):
    pass


class HoldingUpdate(BaseModel):
    stock_name: Optional[str] = None
    market: Optional[str] = None
    quantity: Optional[float] = Field(default=None, gt=0)
    cost_price: Optional[float] = Field(default=None, gt=0)
    current_price: Optional[float] = Field(default=None, gt=0)
    note: Optional[str] = Field(default=None, max_length=500)
    position_updated_at: Optional[datetime] = None


class HoldingItem(BaseModel):
    id: str
    user_id: int
    stock_id: str
    stock_name: str
    market: str
    quantity: float
    cost_price: float
    current_price: float
    market_value: float
    cost_value: float
    unrealized_pnl: float
    unrealized_pnl_rate: float
    weight: float
    note: Optional[str] = None
    position_updated_at: datetime
    created_at: datetime
    updated_at: datetime


class TransactionBase(BaseModel):
    stock_id: str = Field(..., min_length=3, max_length=20)
    stock_name: Optional[str] = None
    market: Optional[str] = None
    side: Literal["buy", "sell"]
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    traded_at: Optional[datetime] = None
    reason: Optional[str] = Field(default=None, max_length=1000)
    analysis_task_id: Optional[str] = None
    pre_trade_check_id: Optional[str] = None
    review_task_id: Optional[int] = None

    @field_validator("analysis_task_id", "pre_trade_check_id")
    @classmethod
    def _validate_uuid_string(cls, value: Optional[str]) -> Optional[str]:
        if value:
            UUID(value)
        return value


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    stock_name: Optional[str] = None
    market: Optional[str] = None
    side: Optional[Literal["buy", "sell"]] = None
    price: Optional[float] = Field(default=None, gt=0)
    quantity: Optional[float] = Field(default=None, gt=0)
    traded_at: Optional[datetime] = None
    reason: Optional[str] = Field(default=None, max_length=1000)
    analysis_task_id: Optional[str] = None
    pre_trade_check_id: Optional[str] = None
    review_task_id: Optional[int] = None

    @field_validator("analysis_task_id", "pre_trade_check_id")
    @classmethod
    def _validate_uuid_string(cls, value: Optional[str]) -> Optional[str]:
        if value:
            UUID(value)
        return value


class TransactionItem(BaseModel):
    id: str
    user_id: int
    stock_id: str
    stock_name: str
    market: str
    side: Literal["buy", "sell"]
    price: float
    quantity: float
    amount: float
    traded_at: datetime
    reason: Optional[str] = None
    analysis_task_id: Optional[str] = None
    pre_trade_check_id: Optional[str] = None
    review_task_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class PortfolioSummary(BaseModel):
    holding_count: int
    total_market_value: float
    total_cost_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_rate: float
    max_position_weight: float
    max_position_stock_id: Optional[str] = None
    max_position_stock_name: Optional[str] = None
    concentration_alert: Optional[str] = None
    risk_tips: list[str]
    data_updated_at: Optional[datetime] = None


class PortfolioOverview(BaseModel):
    summary: PortfolioSummary
    holdings: list[HoldingItem]
