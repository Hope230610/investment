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


class ErrorDetail(BaseModel):
    """统一错误响应结构

    所有业务错误、认证错误和系统错误均使用此结构返回。
    前后端 MUST 以 code / message / request_id / retryable 作为统一解析入口。
    """
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"
    request_id: Optional[str] = None
    retryable: bool = False


class ErrorResponse(BaseModel):
    """统一错误响应包装"""
    error: ErrorDetail
