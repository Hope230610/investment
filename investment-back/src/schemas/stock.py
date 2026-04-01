from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.common import TimestampMixin


class StockBase(BaseModel):
    stock_id: str = Field(..., max_length=20)
    stock_name: str = Field(..., max_length=100)
    market: str = Field(..., max_length=10)
    industry: Optional[str] = Field(None, max_length=100)


class StockCreate(StockBase):
    pass


class StockUpdate(BaseModel):
    stock_name: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None


class StockQuoteSnapshot(BaseModel):
    latest_price: Optional[float] = None
    change_amount: Optional[float] = None
    change_percent: Optional[float] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    previous_close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    turnover_rate: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    total_market_cap: Optional[float] = None
    circulating_market_cap: Optional[float] = None
    amplitude: Optional[float] = None
    data_as_of: Optional[datetime] = None


class StockHistoryPoint(BaseModel):
    date: datetime
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    volume: float


class StockCompanyProfile(BaseModel):
    description: Optional[str] = None
    business_scope: Optional[str] = None
    board_name: Optional[str] = None
    listing_date: Optional[str] = None
    source_url: Optional[str] = None


class StockEvent(BaseModel):
    title: str
    event_type: Optional[str] = None
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    source: str = "external"


class StockSearchItem(StockBase):
    stock_code: str
    security_type: Optional[str] = None
    pinyin: Optional[str] = None
    quote_id: Optional[str] = None
    matched_by: Optional[str] = None


class StockDetail(StockBase):
    stock_code: str
    security_type: Optional[str] = None
    pinyin: Optional[str] = None
    quote_id: Optional[str] = None
    quote_snapshot: Optional[StockQuoteSnapshot] = None
    company_profile: Optional[StockCompanyProfile] = None
    recent_events: list[StockEvent] = []
    recent_history: list[StockHistoryPoint] = []
    data_sources: list[str] = []


class Stock(StockBase, TimestampMixin):
    id: int
    listing_date: Optional[str] = None
    total_shares: Optional[float] = None
    float_shares: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    stock_code: Optional[str] = None
    security_type: Optional[str] = None
    pinyin: Optional[str] = None
    quote_id: Optional[str] = None
    matched_by: Optional[str] = None
    quote_snapshot: Optional[StockQuoteSnapshot] = None
    company_profile: Optional[StockCompanyProfile] = None
    recent_events: list[StockEvent] = []
    recent_history: list[StockHistoryPoint] = []
    data_sources: list[str] = []

    class Config:
        from_attributes = True


class StockSearchResult(BaseModel):
    items: list[StockSearchItem]
    total: int
