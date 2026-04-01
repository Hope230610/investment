from pydantic import BaseModel
from datetime import datetime
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class Message(BaseModel):
    """通用消息响应"""
    message: str

class PaginationParams(BaseModel):
    """分页参数"""
    skip: int = 0
    limit: int = 100

class TimestampMixin(BaseModel):
    """时间戳混合"""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    total: int
    skip: int
    limit: int
