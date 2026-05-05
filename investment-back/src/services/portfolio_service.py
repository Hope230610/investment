from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.analysis import ReviewTask
from src.models.analysis_task import AnalysisTask
from src.models.portfolio import Holding, Transaction, TransactionSideEnum
from src.models.stock import Stock as StockModel
from src.schemas.portfolio import (
    HoldingCreate,
    HoldingItem,
    HoldingUpdate,
    PortfolioOverview,
    PortfolioSummary,
    TransactionCreate,
    TransactionItem,
    TransactionUpdate,
)


CONCENTRATION_ALERT_THRESHOLD = 0.4
CONCENTRATION_HIGH_THRESHOLD = 0.6


def _as_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    def list_holdings(self, user_id: int) -> list[HoldingItem]:
        holdings = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id)
            .order_by(Holding.position_updated_at.desc(), Holding.updated_at.desc())
            .all()
        )
        return self._serialize_holdings(holdings)

    def get_overview(self, user_id: int) -> PortfolioOverview:
        holdings = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id)
            .order_by(Holding.position_updated_at.desc(), Holding.updated_at.desc())
            .all()
        )
        items = self._serialize_holdings(holdings)
        return PortfolioOverview(summary=self._build_summary(items), holdings=items)

    def get_holding_context(self, user_id: int, stock_id: str) -> Optional[dict]:
        holding = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id, Holding.stock_id == stock_id)
            .first()
        )
        if not holding:
            return None
        total_value = sum(
            _as_float(h.quantity) * _as_float(h.current_price)
            for h in self.db.query(Holding).filter(Holding.user_id == user_id).all()
        )
        item = self._serialize_holding(holding, total_value)
        return item.model_dump(mode="json")

    def create_holding(self, user_id: int, payload: HoldingCreate) -> HoldingItem:
        stock = self._resolve_stock(payload.stock_id, payload.stock_name, payload.market)
        existing = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id, Holding.stock_id == payload.stock_id)
            .first()
        )
        now = datetime.utcnow()
        if existing:
            existing.stock_name = payload.stock_name or stock.stock_name
            existing.market = payload.market or stock.market
            existing.quantity = payload.quantity
            existing.cost_price = payload.cost_price
            existing.current_price = payload.current_price
            existing.note = payload.note
            existing.position_updated_at = payload.position_updated_at or now
            self.db.commit()
            self.db.refresh(existing)
            return self._serialize_holding_with_user_total(user_id, existing)

        holding = Holding(
            user_id=user_id,
            stock_id=payload.stock_id,
            stock_name=payload.stock_name or stock.stock_name,
            market=payload.market or stock.market,
            quantity=payload.quantity,
            cost_price=payload.cost_price,
            current_price=payload.current_price,
            note=payload.note,
            position_updated_at=payload.position_updated_at or now,
        )
        self.db.add(holding)
        self.db.commit()
        self.db.refresh(holding)
        return self._serialize_holding_with_user_total(user_id, holding)

    def update_holding(self, user_id: int, holding_id: UUID, payload: HoldingUpdate) -> Optional[HoldingItem]:
        holding = self.db.query(Holding).filter(Holding.id == holding_id, Holding.user_id == user_id).first()
        if not holding:
            return None

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(holding, field, value)
        if "position_updated_at" not in updates:
            holding.position_updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(holding)
        return self._serialize_holding_with_user_total(user_id, holding)

    def delete_holding(self, user_id: int, holding_id: UUID) -> bool:
        holding = self.db.query(Holding).filter(Holding.id == holding_id, Holding.user_id == user_id).first()
        if not holding:
            return False
        self.db.delete(holding)
        self.db.commit()
        return True

    def list_transactions(self, user_id: int, stock_id: Optional[str] = None, limit: int = 100) -> list[TransactionItem]:
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        if stock_id:
            query = query.filter(Transaction.stock_id == stock_id)
        transactions = query.order_by(Transaction.traded_at.desc()).limit(limit).all()
        return [self._serialize_transaction(tx) for tx in transactions]

    def create_transaction(self, user_id: int, payload: TransactionCreate) -> TransactionItem:
        stock = self._resolve_stock(payload.stock_id, payload.stock_name, payload.market)
        analysis_task_id = UUID(payload.analysis_task_id) if payload.analysis_task_id else None
        pre_trade_check_id = UUID(payload.pre_trade_check_id) if payload.pre_trade_check_id else None
        self._validate_transaction_references(
            user_id,
            analysis_task_id=analysis_task_id,
            pre_trade_check_id=pre_trade_check_id,
            review_task_id=payload.review_task_id,
        )
        tx = Transaction(
            user_id=user_id,
            stock_id=payload.stock_id,
            stock_name=payload.stock_name or stock.stock_name,
            market=payload.market or stock.market,
            side=TransactionSideEnum(payload.side),
            price=payload.price,
            quantity=payload.quantity,
            traded_at=payload.traded_at or datetime.utcnow(),
            reason=payload.reason,
            analysis_task_id=analysis_task_id,
            pre_trade_check_id=pre_trade_check_id,
            review_task_id=payload.review_task_id,
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return self._serialize_transaction(tx)

    def update_transaction(self, user_id: int, transaction_id: UUID, payload: TransactionUpdate) -> Optional[TransactionItem]:
        tx = self.db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).first()
        if not tx:
            return None
        updates = payload.model_dump(exclude_unset=True)
        if "side" in updates and updates["side"]:
            updates["side"] = TransactionSideEnum(updates["side"])
        if "analysis_task_id" in updates:
            updates["analysis_task_id"] = UUID(updates["analysis_task_id"]) if updates["analysis_task_id"] else None
        if "pre_trade_check_id" in updates:
            updates["pre_trade_check_id"] = UUID(updates["pre_trade_check_id"]) if updates["pre_trade_check_id"] else None
        self._validate_transaction_references(
            user_id,
            analysis_task_id=updates.get("analysis_task_id") if "analysis_task_id" in updates else None,
            pre_trade_check_id=updates.get("pre_trade_check_id") if "pre_trade_check_id" in updates else None,
            review_task_id=updates.get("review_task_id") if "review_task_id" in updates else None,
        )
        for field, value in updates.items():
            setattr(tx, field, value)
        self.db.commit()
        self.db.refresh(tx)
        return self._serialize_transaction(tx)

    def delete_transaction(self, user_id: int, transaction_id: UUID) -> bool:
        tx = self.db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).first()
        if not tx:
            return False
        self.db.delete(tx)
        self.db.commit()
        return True

    def _resolve_stock(self, stock_id: str, stock_name: Optional[str], market: Optional[str]) -> StockModel:
        stock = self.db.query(StockModel).filter(StockModel.stock_id == stock_id).first()
        if stock:
            if stock_name:
                stock.stock_name = stock_name
            if market:
                stock.market = market
            self.db.commit()
            self.db.refresh(stock)
            return stock

        stock = StockModel(
            stock_id=stock_id,
            stock_name=stock_name or stock_id,
            market=market or stock_id[:2].upper() or "NA",
        )
        self.db.add(stock)
        self.db.commit()
        self.db.refresh(stock)
        return stock

    def _validate_transaction_references(
        self,
        user_id: int,
        analysis_task_id: Optional[UUID] = None,
        pre_trade_check_id: Optional[UUID] = None,
        review_task_id: Optional[int] = None,
    ) -> None:
        if analysis_task_id and not self._analysis_task_belongs_to_user(user_id, analysis_task_id):
            raise ValueError("TRANSACTION_REFERENCE_NOT_FOUND")
        if pre_trade_check_id and not self._analysis_task_belongs_to_user(user_id, pre_trade_check_id):
            raise ValueError("TRANSACTION_REFERENCE_NOT_FOUND")
        if review_task_id and not self._review_task_belongs_to_user(user_id, review_task_id):
            raise ValueError("TRANSACTION_REFERENCE_NOT_FOUND")

    def _analysis_task_belongs_to_user(self, user_id: int, task_id: UUID) -> bool:
        return (
            self.db.query(AnalysisTask)
            .filter(AnalysisTask.id == task_id, AnalysisTask.user_id == user_id)
            .first()
            is not None
        )

    def _review_task_belongs_to_user(self, user_id: int, review_task_id: int) -> bool:
        return (
            self.db.query(ReviewTask)
            .filter(ReviewTask.id == review_task_id, ReviewTask.user_id == user_id)
            .first()
            is not None
        )

    def _serialize_holdings(self, holdings: list[Holding]) -> list[HoldingItem]:
        total_value = sum(_as_float(h.quantity) * _as_float(h.current_price) for h in holdings)
        return [self._serialize_holding(h, total_value) for h in holdings]

    def _serialize_holding_with_user_total(self, user_id: int, holding: Holding) -> HoldingItem:
        total_value = sum(
            _as_float(h.quantity) * _as_float(h.current_price)
            for h in self.db.query(Holding).filter(Holding.user_id == user_id).all()
        )
        return self._serialize_holding(holding, total_value)

    def _serialize_holding(self, holding: Holding, total_value: float) -> HoldingItem:
        quantity = _as_float(holding.quantity)
        cost_price = _as_float(holding.cost_price)
        current_price = _as_float(holding.current_price)
        market_value = quantity * current_price
        cost_value = quantity * cost_price
        unrealized_pnl = market_value - cost_value
        pnl_rate = unrealized_pnl / cost_value if cost_value else 0.0
        weight = market_value / total_value if total_value else 0.0
        return HoldingItem(
            id=str(holding.id),
            user_id=holding.user_id,
            stock_id=holding.stock_id,
            stock_name=holding.stock_name,
            market=holding.market,
            quantity=round(quantity, 4),
            cost_price=round(cost_price, 4),
            current_price=round(current_price, 4),
            market_value=round(market_value, 2),
            cost_value=round(cost_value, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            unrealized_pnl_rate=round(pnl_rate, 4),
            weight=round(weight, 4),
            note=holding.note,
            position_updated_at=holding.position_updated_at,
            created_at=holding.created_at,
            updated_at=holding.updated_at,
        )

    def _build_summary(self, holdings: list[HoldingItem]) -> PortfolioSummary:
        total_market_value = sum(item.market_value for item in holdings)
        total_cost_value = sum(item.cost_value for item in holdings)
        total_pnl = total_market_value - total_cost_value
        pnl_rate = total_pnl / total_cost_value if total_cost_value else 0.0
        max_item = max(holdings, key=lambda item: item.market_value, default=None)
        max_weight = (max_item.market_value / total_market_value) if max_item and total_market_value else 0.0
        risk_tips: list[str] = []
        concentration_alert = None
        if max_item and max_weight >= CONCENTRATION_HIGH_THRESHOLD:
            concentration_alert = f"{max_item.stock_name} 持仓占比已超过 60%，需要优先评估集中度风险。"
            risk_tips.append("组合高度集中，单一标的波动会显著影响整体结果。")
        elif max_item and max_weight >= CONCENTRATION_ALERT_THRESHOLD:
            concentration_alert = f"{max_item.stock_name} 持仓占比偏高，建议复核仓位边界。"
            risk_tips.append("单票占比超过 40%，需要确认是否仍符合原始资金计划。")
        if total_pnl < 0:
            risk_tips.append("组合处于浮亏状态，复盘时要区分事实变化和亏损情绪。")
        if not risk_tips:
            risk_tips.append("当前未发现明显集中度提示，仍需定期更新价格和持仓理由。")
        data_updated_at = max((item.position_updated_at for item in holdings), default=None)
        return PortfolioSummary(
            holding_count=len(holdings),
            total_market_value=round(total_market_value, 2),
            total_cost_value=round(total_cost_value, 2),
            total_unrealized_pnl=round(total_pnl, 2),
            total_unrealized_pnl_rate=round(pnl_rate, 4),
            max_position_weight=round(max_weight, 4),
            max_position_stock_id=max_item.stock_id if max_item else None,
            max_position_stock_name=max_item.stock_name if max_item else None,
            concentration_alert=concentration_alert,
            risk_tips=risk_tips,
            data_updated_at=data_updated_at,
        )

    def _serialize_transaction(self, tx: Transaction) -> TransactionItem:
        side = tx.side.value if hasattr(tx.side, "value") else tx.side
        price = _as_float(tx.price)
        quantity = _as_float(tx.quantity)
        return TransactionItem(
            id=str(tx.id),
            user_id=tx.user_id,
            stock_id=tx.stock_id,
            stock_name=tx.stock_name,
            market=tx.market,
            side=side,
            price=round(price, 4),
            quantity=round(quantity, 4),
            amount=round(price * quantity, 2),
            traded_at=tx.traded_at,
            reason=tx.reason,
            analysis_task_id=str(tx.analysis_task_id) if tx.analysis_task_id else None,
            pre_trade_check_id=str(tx.pre_trade_check_id) if tx.pre_trade_check_id else None,
            review_task_id=tx.review_task_id,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )
