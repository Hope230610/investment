from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.db.session import get_db
from src.schemas.watchlist import WatchlistItem, WatchlistItemCreate, WatchlistItemUpdate
from src.api.deps import get_current_user
import structlog
from src.services.watchlist_service import WatchlistService

router = APIRouter()
logger = structlog.get_logger()

# 初始化服务
def get_watchlist_service(db: Session = Depends(get_db)):
    return WatchlistService(db)

@router.get("", response_model=List[WatchlistItem])
async def get_watchlist(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取观察列表"""
    logger.info("get_watchlist", user_id=current_user.id)

    service = get_watchlist_service(db)
    items = service.get_watchlist(current_user.id)

    return items

@router.post("", response_model=WatchlistItem)
async def add_to_watchlist(
    item_data: WatchlistItemCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """添加股票到观察列表"""
    logger.info("add_to_watchlist", user_id=current_user.id, stock_id=item_data.stock_id)

    service = get_watchlist_service(db)

    try:
        item = service.add_to_watchlist(current_user.id, item_data)
    except Exception as e:
        if "已存在" in str(e):
            raise HTTPException(status_code=400, detail="该股票已在观察列表中")
        elif "未找到" in str(e):
            raise HTTPException(status_code=404, detail="股票未找到")
        else:
            raise HTTPException(status_code=500, detail="添加到观察列表失败")

    return item

@router.put("/{item_id}", response_model=WatchlistItem)
async def update_watchlist_item(
    item_id: int,
    item_data: WatchlistItemUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新观察列表项"""
    logger.info("update_watchlist_item", item_id=item_id)

    service = get_watchlist_service(db)

    item = service.update_watchlist_item(current_user.id, item_id, item_data)

    if not item:
        raise HTTPException(status_code=404, detail="观察列表项未找到")

    return item

@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """从观察列表删除"""
    logger.info("remove_from_watchlist", item_id=item_id)

    service = get_watchlist_service(db)

    success = service.remove_from_watchlist(current_user.id, item_id)

    if not success:
        raise HTTPException(status_code=404, detail="观察列表项未找到")

    return {"message": "已从观察列表移除"}
