from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from starlette.status import HTTP_404_NOT_FOUND, HTTP_502_BAD_GATEWAY
import httpx
import structlog

from src.api.deps import get_current_user, get_market_data_service
from src.models.user import User
from src.schemas.common import ErrorDetail, ErrorResponse
from src.schemas.stock import StockDetail, StockSearchResult
from src.services.market_data_service import MarketDataService


router = APIRouter()
logger = structlog.get_logger()


def api_error(
    status_code: int,
    code: str,
    message: str,
    request: Request = None,
    retryable: bool = False,
) -> JSONResponse:
    request_id = request.headers.get("x-request-id") if request else None
    body = ErrorResponse(error=ErrorDetail(
        code=code,
        message=message,
        request_id=request_id,
        retryable=retryable,
    ))
    return JSONResponse(status_code=status_code, content=body.model_dump())


@router.get("/search", response_model=StockSearchResult)
async def search_stocks(
    q: str = Query(..., min_length=1, max_length=100, description="Search keyword"),
    limit: int = Query(10, ge=1, le=20),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    """Search real A-share stocks by code, name, or pinyin."""
    del current_user
    logger.info("search_stocks", query=q, limit=limit)

    try:
        items = market_data_service.search_stocks(q, limit=limit)
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("search_stocks_failed", query=q, error=str(exc))
        return api_error(
            HTTP_502_BAD_GATEWAY,
            "MARKET_DATA_UNAVAILABLE",
            "暂时无法获取实时股票搜索结果，请稍后再试",
            request,
            retryable=True,
        )

    return StockSearchResult(items=items, total=len(items))


@router.get("/{stock_id}", response_model=StockDetail)
async def get_stock(
    stock_id: str,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    """Return real-time stock detail for the analysis product."""
    del current_user
    logger.info("get_stock", stock_id=stock_id)

    try:
        return market_data_service.get_stock_detail(stock_id)
    except ValueError as exc:
        return api_error(HTTP_404_NOT_FOUND, "STOCK_NOT_FOUND", "股票标识无效", request)
    except httpx.HTTPError as exc:
        logger.error("get_stock_failed", stock_id=stock_id, error=str(exc))
        return api_error(
            HTTP_502_BAD_GATEWAY,
            "MARKET_DATA_UNAVAILABLE",
            "暂时无法获取该股票的最新数据，请稍后再试",
            request,
            retryable=True,
        )
