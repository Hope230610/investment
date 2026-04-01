from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.watchlist import WatchlistItem
from src.models.stock import Stock
from src.schemas.watchlist import WatchlistItemCreate, WatchlistItemUpdate
import structlog

logger = structlog.get_logger()

class WatchlistService:
    """观察列表服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger.bind(service="watchlist")

    def get_watchlist(self, user_id: int) -> List[WatchlistItem]:
        """获取用户观察列表"""
        items = self.db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user_id
        ).all()
        return items

    def add_to_watchlist(
        self, user_id: int, item_data: WatchlistItemCreate
    ) -> WatchlistItem:
        """添加股票到观察列表"""
        # 检查是否已存在
        existing = self.db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user_id,
            WatchlistItem.stock_id == item_data.stock_id
        ).first()

        if existing:
            self.logger.info("already_in_watchlist", user_id=user_id, stock_id=item_data.stock_id)
            return existing

        # 创建新条目
        item = WatchlistItem(
            user_id=user_id,
            stock_id=item_data.stock_id,
            focus_reason=item_data.focus_reason
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        self.logger.info("added_to_watchlist", user_id=user_id, stock_id=item_data.stock_id)
        return item

    def update_watchlist_item(
        self, user_id: int, item_id: int, item_update: WatchlistItemUpdate
    ) -> Optional[WatchlistItem]:
        """更新观察列表项"""
        item = self.db.query(WatchlistItem).filter(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user_id
        ).first()

        if not item:
            return None

        if item_update.focus_reason is not None:
            item.focus_reason = item_update.focus_reason

        self.db.commit()
        self.db.refresh(item)
        self.logger.info("updated_watchlist_item", item_id=item_id)
        return item

    def remove_from_watchlist(self, user_id: int, item_id: int) -> bool:
        """从观察列表删除"""
        item = self.db.query(WatchlistItem).filter(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user_id
        ).first()

        if not item:
            return False

        self.db.delete(item)
        self.db.commit()
        self.logger.info("removed_from_watchlist", item_id=item_id)
        return True

    def is_in_watchlist(self, user_id: int, stock_id: str) -> bool:
        """检查股票是否在观察列表中"""
        return self.db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user_id,
            WatchlistItem.stock_id == stock_id
        ).first() is not None
