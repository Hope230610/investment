import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_current_user, get_market_data_service
from src.models.user import User
from src.schemas.stock import StockDetail, StockSearchResult
from src.services.market_data_service import MarketDataService


router = APIRouter()
logger = structlog.get_logger()


@router.get("/search", response_model=StockSearchResult)
async def search_stocks(
    q: str = Query(..., min_length=1, max_length=100, description="Search keyword"),
    limit: int = Query(10, ge=1, le=20),
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
        raise HTTPException(
            status_code=502,
            detail="暂时无法获取实时股票搜索结果，请稍后再试",
        ) from exc

    return StockSearchResult(items=items, total=len(items))


@router.get("/{stock_id}", response_model=StockDetail)
async def get_stock(
    stock_id: str,
    current_user: User = Depends(get_current_user),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    """Return real-time stock detail for the analysis product."""
    del current_user
    logger.info("get_stock", stock_id=stock_id)

    try:
        return market_data_service.get_stock_detail(stock_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="股票标识无效") from exc
    except httpx.HTTPError as exc:
        logger.error("get_stock_failed", stock_id=stock_id, error=str(exc))
        raise HTTPException(
            status_code=502,
            detail="暂时无法获取该股票的最新数据，请稍后再试",
        ) from exc
