from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_market_data_service
from src.db.session import get_db
from src.models.user import User
from src.schemas.common import ErrorDetail, ErrorResponse
from src.schemas.notification import NotificationListResponse, NotificationSummary
from src.services.notification_service import NotificationService
from src.services.market_data_service import MarketDataService


router = APIRouter()
logger = structlog.get_logger()


def api_error(
    status_code: int,
    code: str,
    message: str,
    request: Optional[Request] = None,
) -> JSONResponse:
    request_id = request.headers.get("x-request-id") if request else None
    body = ErrorResponse(error=ErrorDetail(
        code=code,
        message=message,
        request_id=request_id,
    ))
    return JSONResponse(status_code=status_code, content=body.model_dump())


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """聚合获取当前用户的所有提醒。

    返回三类提醒：
    - review_reminder：待复盘任务（overdue / due_soon / upcoming）
    - watchlist_alert：观察池股票的新事件（风险公告、价格异动等）
    - analysis_invalidation：分析结论可能已失效（价格大幅偏离、风险关键词出现）

    按紧迫程度 + 时间排序。
    """
    logger.info("get_notifications", user_id=current_user.id)

    try:
        service = NotificationService(db)
        try:
            result = service.get_notifications(current_user.id)
        finally:
            service.close()

        logger.debug(
            "notifications_loaded",
            user_id=current_user.id,
            total=result.total,
            unread=result.unread_count,
        )
        return result

    except Exception as exc:
        logger.error("get_notifications_failed", user_id=current_user.id, error=str(exc))
        return api_error(500, "NOTIFICATION_QUERY_FAILED", "获取提醒失败，请稍后再试", request)


@router.get("/summary", response_model=NotificationSummary)
async def get_notification_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取提醒摘要（轻量接口，用于 Tab Badge）"""
    logger.info("get_notification_summary", user_id=current_user.id)

    try:
        service = NotificationService(db)
        try:
            result = service.get_notifications(current_user.id)
        finally:
            service.close()
        return result.summary

    except Exception as exc:
        logger.error("get_notification_summary_failed", user_id=current_user.id, error=str(exc))
        return api_error(500, "NOTIFICATION_SUMMARY_FAILED", "获取提醒摘要失败", request)
