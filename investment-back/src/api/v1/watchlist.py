import uuid as uuid_lib
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.user import User
from src.schemas.common import ErrorDetail, ErrorResponse, Message
from src.schemas.watchlist import WatchlistItem, WatchlistItemCreate, WatchlistItemUpdate
from src.services.watchlist_service import WatchlistService


router = APIRouter()
logger = structlog.get_logger()


def api_error(
    status_code: int,
    code: str,
    message: str,
    request: Optional[Request] = None,
    retryable: bool = False,
) -> JSONResponse:
    request_id = request.headers.get("x-request-id") if request else None
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            retryable=retryable,
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def get_watchlist_service(db: Session = Depends(get_db)) -> WatchlistService:
    return WatchlistService(db)


def _parse_watchlist_id(item_id: str) -> uuid_lib.UUID:
    try:
        return uuid_lib.UUID(item_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("INVALID_WATCHLIST_ID") from exc


@router.get("", response_model=List[WatchlistItem])
async def get_watchlist(
    request: Request,
    service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user),
):
    """获取观察列表（v2）"""
    logger.info("get_watchlist", user_id=current_user.id, source="watchlist_api_v2")

    try:
        return service.list_watchlist(current_user.id)
    except Exception as exc:
        logger.error("get_watchlist_failed", user_id=current_user.id, error=str(exc))
        return api_error(
            HTTP_500_INTERNAL_SERVER_ERROR,
            "WATCHLIST_QUERY_FAILED",
            "获取观察列表失败",
            request,
            retryable=True,
        )


@router.post("", response_model=WatchlistItem)
async def add_to_watchlist(
    item_data: WatchlistItemCreate,
    request: Request,
    service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user),
):
    """添加股票到观察列表（v2 upsert）"""
    logger.info(
        "add_to_watchlist",
        user_id=current_user.id,
        stock_id=item_data.stock_id,
        source="watchlist_api_v2",
    )

    try:
        return service.upsert_watchlist_item(
            current_user.id,
            item_data.stock_id,
            focus_reason=item_data.focus_reason,
            focus_reason_provided="focus_reason" in item_data.model_fields_set,
        )
    except ValueError as exc:
        if str(exc) == "STOCK_NOT_FOUND":
            return api_error(HTTP_404_NOT_FOUND, "STOCK_NOT_FOUND", "股票未找到", request)
        logger.error("add_to_watchlist_validation_failed", error=str(exc))
        return api_error(HTTP_400_BAD_REQUEST, "INVALID_WATCHLIST_PAYLOAD", "无效的观察列表请求", request)
    except Exception as exc:
        logger.error("add_to_watchlist_failed", user_id=current_user.id, error=str(exc))
        return api_error(
            HTTP_500_INTERNAL_SERVER_ERROR,
            "WATCHLIST_WRITE_FAILED",
            "添加到观察列表失败",
            request,
            retryable=True,
        )


@router.put("/{item_id}", response_model=WatchlistItem)
async def update_watchlist_item(
    item_id: str,
    item_data: WatchlistItemUpdate,
    request: Request,
    service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user),
):
    """更新观察列表项（v2）"""
    logger.info("update_watchlist_item", item_id=item_id, user_id=current_user.id)

    try:
        parsed_id = _parse_watchlist_id(item_id)
    except ValueError:
        return api_error(
            HTTP_400_BAD_REQUEST,
            "INVALID_WATCHLIST_ID",
            "无效的观察列表 ID 格式",
            request,
        )

    try:
        item = service.update_watchlist_item(
            current_user.id,
            parsed_id,
            focus_reason=item_data.focus_reason,
            focus_reason_provided="focus_reason" in item_data.model_fields_set,
        )
        if not item:
            return api_error(
                HTTP_404_NOT_FOUND,
                "WATCHLIST_ITEM_NOT_FOUND",
                "观察列表项未找到",
                request,
            )
        return item
    except Exception as exc:
        logger.error("update_watchlist_item_failed", item_id=item_id, error=str(exc))
        return api_error(
            HTTP_500_INTERNAL_SERVER_ERROR,
            "WATCHLIST_UPDATE_FAILED",
            "更新观察列表失败",
            request,
            retryable=True,
        )


@router.delete("/{item_id}", response_model=Message)
async def remove_from_watchlist(
    item_id: str,
    request: Request,
    service: WatchlistService = Depends(get_watchlist_service),
    current_user: User = Depends(get_current_user),
):
    """从观察列表删除（v2）"""
    logger.info("remove_from_watchlist", item_id=item_id, user_id=current_user.id)

    try:
        parsed_id = _parse_watchlist_id(item_id)
    except ValueError:
        return api_error(
            HTTP_400_BAD_REQUEST,
            "INVALID_WATCHLIST_ID",
            "无效的观察列表 ID 格式",
            request,
        )

    try:
        success = service.remove_from_watchlist(current_user.id, parsed_id)
        if not success:
            return api_error(
                HTTP_404_NOT_FOUND,
                "WATCHLIST_ITEM_NOT_FOUND",
                "观察列表项未找到",
                request,
            )
        return Message(message="已从观察列表移除")
    except Exception as exc:
        logger.error("remove_from_watchlist_failed", item_id=item_id, error=str(exc))
        return api_error(
            HTTP_500_INTERNAL_SERVER_ERROR,
            "WATCHLIST_DELETE_FAILED",
            "移除观察列表失败",
            request,
            retryable=True,
        )
