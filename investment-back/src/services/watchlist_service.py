from __future__ import annotations

import uuid as uuid_lib
from typing import Any, Optional

import structlog
from sqlalchemy.orm import Session

from src.models.stock import Stock
from src.models.watchlist_v2 import AddedFromScenarioEnum, Watchlist


logger = structlog.get_logger()


class WatchlistService:
    """观察列表服务（v2）"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger.bind(service="watchlist")

    def list_watchlist(self, user_id: int) -> list[dict[str, Any]]:
        """获取用户观察列表（v2 + 股票摘要）"""
        rows = (
            self.db.query(Watchlist, Stock)
            .outerjoin(Stock, Watchlist.stock_id == Stock.stock_id)
            .filter(Watchlist.user_id == user_id)
            .order_by(Watchlist.created_at.desc())
            .all()
        )
        return [self._serialize_item(item, stock) for item, stock in rows]

    def get_watchlist_item(
        self, user_id: int, item_id: uuid_lib.UUID
    ) -> Optional[dict[str, Any]]:
        """获取单个观察项（v2 + 股票摘要）"""
        row = (
            self.db.query(Watchlist, Stock)
            .outerjoin(Stock, Watchlist.stock_id == Stock.stock_id)
            .filter(
                Watchlist.id == item_id,
                Watchlist.user_id == user_id,
            )
            .first()
        )
        if not row:
            return None

        item, stock = row
        return self._serialize_item(item, stock)

    def upsert_watchlist_item(
        self,
        user_id: int,
        stock_id: str,
        *,
        focus_reason: Optional[str] = None,
        focus_reason_provided: bool = False,
        added_from_scenario: Optional[AddedFromScenarioEnum] = None,
        source_analysis_id: Optional[uuid_lib.UUID] = None,
        notify_on_events: Optional[bool] = None,
    ) -> dict[str, Any]:
        """按 user_id + stock_id 执行 upsert"""
        existing = (
            self.db.query(Watchlist)
            .filter(
                Watchlist.user_id == user_id,
                Watchlist.stock_id == stock_id,
            )
            .first()
        )

        stock = self._get_stock(stock_id)
        if stock is None:
            self.logger.info("watchlist_stock_not_found", user_id=user_id, stock_id=stock_id)
            raise ValueError("STOCK_NOT_FOUND")

        if existing:
            if focus_reason_provided:
                existing.focus_reason = focus_reason
            if added_from_scenario is not None:
                existing.added_from_scenario = added_from_scenario
            if source_analysis_id is not None:
                existing.source_analysis_id = source_analysis_id
            if notify_on_events is not None:
                existing.notify_on_events = notify_on_events

            self.db.commit()
            self.db.refresh(existing)
            self.logger.info(
                "watchlist_upsert_existing",
                user_id=user_id,
                stock_id=stock_id,
                watchlist_id=str(existing.id),
            )
            return self._serialize_item(existing, stock)

        item = Watchlist(
            user_id=user_id,
            stock_id=stock_id,
            focus_reason=focus_reason if focus_reason_provided else None,
            added_from_scenario=added_from_scenario,
            source_analysis_id=source_analysis_id,
            notify_on_events=True if notify_on_events is None else notify_on_events,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        self.logger.info(
            "watchlist_created",
            user_id=user_id,
            stock_id=stock_id,
            watchlist_id=str(item.id),
        )
        return self._serialize_item(item, stock)

    def update_watchlist_item(
        self,
        user_id: int,
        item_id: uuid_lib.UUID,
        *,
        focus_reason: Optional[str] = None,
        focus_reason_provided: bool = False,
    ) -> Optional[dict[str, Any]]:
        """更新观察列表项"""
        row = (
            self.db.query(Watchlist, Stock)
            .outerjoin(Stock, Watchlist.stock_id == Stock.stock_id)
            .filter(
                Watchlist.id == item_id,
                Watchlist.user_id == user_id,
            )
            .first()
        )
        if not row:
            return None

        item, stock = row
        if focus_reason_provided:
            item.focus_reason = focus_reason

        self.db.commit()
        self.db.refresh(item)
        self.logger.info(
            "watchlist_updated",
            user_id=user_id,
            watchlist_id=str(item_id),
        )
        return self._serialize_item(item, stock)

    def remove_from_watchlist(self, user_id: int, item_id: uuid_lib.UUID) -> bool:
        """从观察列表删除"""
        item = (
            self.db.query(Watchlist)
            .filter(
                Watchlist.id == item_id,
                Watchlist.user_id == user_id,
            )
            .first()
        )
        if not item:
            return False

        self.db.delete(item)
        self.db.commit()
        self.logger.info(
            "watchlist_removed",
            user_id=user_id,
            watchlist_id=str(item_id),
        )
        return True

    def is_in_watchlist(self, user_id: int, stock_id: str) -> bool:
        """检查股票是否在观察列表中"""
        return (
            self.db.query(Watchlist)
            .filter(
                Watchlist.user_id == user_id,
                Watchlist.stock_id == stock_id,
            )
            .first()
            is not None
        )

    def _get_stock(self, stock_id: str) -> Optional[Stock]:
        return self.db.query(Stock).filter(Stock.stock_id == stock_id).first()

    def _serialize_item(
        self, item: Watchlist, stock: Optional[Stock]
    ) -> dict[str, Any]:
        if stock is None:
            self.logger.warning(
                "watchlist_stock_missing",
                watchlist_id=str(item.id),
                stock_id=item.stock_id,
            )

        return {
            "id": str(item.id),
            "user_id": int(item.user_id),
            "stock_id": item.stock_id,
            "stock_name": stock.stock_name if stock else item.stock_id,
            "market": stock.market if stock else "",
            "industry": stock.industry if stock else None,
            "focus_reason": item.focus_reason,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
