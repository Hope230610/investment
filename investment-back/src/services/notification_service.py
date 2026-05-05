"""通知聚合服务

拉取式聚合：从现有表（review_tasks、watchlists、analysis_results）中
实时聚合各类提醒，不依赖独立的通知持久化表。

提醒类型：
- review_reminder：待复盘任务（overdue / due_soon / upcoming）
- watchlist_alert：观察池股票的新事件（风险公告、价格异动等）
- analysis_invalidation：分析结论可能已失效（价格大幅偏离、风险关键词出现）
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import structlog
from sqlalchemy.orm import Session

from src.models.analysis import ReviewTask as ReviewTaskModel, ReviewTaskStatus
from src.models.analysis_task import AnalysisTask
from src.models.analysis_result import AnalysisResult
from src.models.stock import Stock as StockModel
from src.models.watchlist_v2 import Watchlist
from src.models.portfolio import Holding
from src.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    NotificationSummary,
    NotificationType,
    NotificationUrgency,
)
from src.services.market_data_service import MarketDataService


CN_TZ = timezone(timedelta(hours=8))

# 价格异动阈值（涨跌幅超过此值触发提醒）
PRICE_MOVEMENT_THRESHOLD = 0.05  # 5%

# 风险关键词（出现则触发风险提醒）
RISK_KEYWORDS = (
    "风险", "问询", "冻结", "减持", "诉讼", "监管",
    "终止", "亏损", "质押", "违规", "警示", "立案",
    "ST", "*ST", "暂停上市", "退市风险",
)


def _as_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.logger = structlog.get_logger().bind(service="notification")
        self.market = MarketDataService()

    def close(self):
        self.market.close()

    def get_notifications(self, user_id: int) -> NotificationListResponse:
        """聚合所有类型提醒"""
        notifications: list[NotificationItem] = []

        # 1. 复盘提醒
        notifications.extend(self._collect_review_reminders(user_id))

        # 2. 观察池异动提醒
        notifications.extend(self._collect_watchlist_alerts(user_id))

        # 3. 分析失效提醒
        notifications.extend(self._collect_analysis_invalidations(user_id))
        notifications.extend(self._collect_portfolio_risks(user_id))

        # 按紧迫程度 + 时间排序
        notifications = self._sort_notifications(notifications)

        # 计算摘要
        summary = self._build_summary(notifications)
        overdue_count = sum(
            1 for n in notifications
            if n.urgency in (NotificationUrgency.OVERDUE, NotificationUrgency.HIGH)
        )

        return NotificationListResponse(
            notifications=notifications,
            total=len(notifications),
            unread_count=overdue_count,
            summary=summary,
        )

    def get_summary(self, user_id: int) -> NotificationSummary:
        """Build a lightweight badge summary without market-data aggregation."""
        notifications: list[NotificationItem] = []
        notifications.extend(self._collect_review_reminders(user_id))
        notifications.extend(self._collect_portfolio_risks(user_id))

        summary = self._build_summary(notifications)
        invalidation_count = self._count_expired_analysis_candidates(user_id)
        summary.total += invalidation_count
        summary.invalidation_count = invalidation_count
        return summary

    def _collect_review_reminders(self, user_id: int) -> list[NotificationItem]:
        """收集待复盘提醒"""
        now = datetime.now()
        due_soon_cutoff = now + timedelta(days=3)

        tasks = (
            self.db.query(ReviewTaskModel)
            .filter(
                ReviewTaskModel.user_id == user_id,
                ReviewTaskModel.status.in_([
                    ReviewTaskStatus.PENDING,
                    ReviewTaskStatus.EXPIRED,
                ]),
            )
            .order_by(ReviewTaskModel.review_at.asc())
            .all()
        )

        notifications = []
        for task in tasks:
            review_at: datetime = task.review_at
            # 计算紧迫程度
            if task.status == ReviewTaskStatus.EXPIRED or review_at < now:
                urgency = NotificationUrgency.OVERDUE
                overdue_days = max(1, (now - review_at).days)
                title = f"复盘已逾期 {overdue_days} 天"
                description = f"{task.stock_name or task.stock_id or '该股票'} 的复盘任务已逾期，请尽快处理。"
            elif review_at <= due_soon_cutoff:
                days_left = (review_at - now).days
                urgency = NotificationUrgency.DUE_SOON
                title = f"复盘提醒：{task.stock_name or task.stock_id or '该股票'}"
                description = f"还有 {days_left} 天到达复盘时间，请做好准备。"
            else:
                urgency = NotificationUrgency.NORMAL
                title = f"待复盘：{task.stock_name or task.stock_id or '该股票'}"
                description = f"计划复盘时间：{review_at.strftime('%Y-%m-%d')}"

            # 构造跳转 URL
            stock_id = task.stock_id or ""
            stock_name = task.stock_name or stock_id or "该股票"
            action_url = (
                f"/analysis/post-trade"
                f"?stock_id={stock_id}"
                f"&stock_name={stock_name}"
                f"&pending_review_task_id={task.analysis_task_id}"
            )

            notifications.append(NotificationItem(
                id=str(uuid4()),
                type=NotificationType.REVIEW_REMINDER,
                title=title,
                description=description,
                urgency=urgency,
                stock_id=stock_id or None,
                stock_name=stock_name,
                action_url=action_url,
                created_at=review_at,
                metadata={
                    "review_task_id": task.id,
                    "analysis_task_id": str(task.analysis_task_id) if task.analysis_task_id else None,
                    "status": task.status.value if hasattr(task.status, "value") else str(task.status),
                },
            ))

        return notifications

    def _collect_watchlist_alerts(self, user_id: int) -> list[NotificationItem]:
        """收集观察池股票的新事件提醒"""
        # 查找用户开启事件提醒的观察池股票
        watchlist_items = (
            self.db.query(Watchlist)
            .filter(
                Watchlist.user_id == user_id,
                Watchlist.notify_on_events == True,  # noqa: E712
            )
            .all()
        )

        if not watchlist_items:
            return []

        notifications = []
        now = datetime.now()
        recent_window = now - timedelta(days=7)  # 只看近 7 天事件

        for item in watchlist_items:
            stock_id = item.stock_id
            stock_name = item.stock.stock_name if item.stock else stock_id

            try:
                detail = self.market.get_stock_detail(stock_id)
            except Exception as exc:
                self.logger.debug("watchlist_market_data_failed", stock_id=stock_id, error=str(exc))
                continue

            if not detail.recent_events:
                continue

            stock_name = detail.stock_name or stock_id

            for event in detail.recent_events:
                published_at = event.published_at
                if published_at and published_at < recent_window:
                    continue

                event_type = event.event_type or ""
                title_text = event.title or ""

                # 判断是否为风险事件
                is_risk = any(kw in (event_type + title_text) for kw in RISK_KEYWORDS)

                # 判断是否为价格异动
                is_price_move = False
                if detail.quote_snapshot:
                    change_pct = abs(detail.quote_snapshot.change_percent or 0)
                    if change_pct >= 3.0:  # 当日涨跌幅 ≥ 3%
                        is_price_move = True

                if not (is_risk or is_price_move):
                    continue

                if is_risk:
                    urgency = NotificationUrgency.HIGH
                    title = f"风险提醒：{stock_name}"
                    description = f"{event_type}：{title_text}" if title_text else "该股票出现风险事件，请关注。"
                else:
                    urgency = NotificationUrgency.DUE_SOON
                    change_str = f"+{detail.quote_snapshot.change_percent:.2f}%" if detail.quote_snapshot else ""
                    title = f"价格异动：{stock_name}"
                    description = f"当日涨跌 {change_str}，{title_text}" if title_text else f"当日涨跌 {change_str}"

                notifications.append(NotificationItem(
                    id=str(uuid4()),
                    type=NotificationType.WATCHLIST_ALERT,
                    title=title,
                    description=description[:200],  # 截断超长描述
                    urgency=urgency,
                    stock_id=stock_id,
                    stock_name=stock_name,
                    action_url=f"/analysis/single-stock?stock_id={stock_id}&stock_name={stock_name}",
                    created_at=published_at or now,
                    metadata={
                        "event_type": event_type,
                        "event_url": event.url,
                    },
                ))

        return notifications

    def _collect_analysis_invalidations(self, user_id: int) -> list[NotificationItem]:
        """收集分析结论可能已失效的提醒"""
        # 查找用户近 30 天内有分析结论的股票
        thirty_days_ago = datetime.now() - timedelta(days=30)

        tasks = (
            self.db.query(AnalysisTask)
            .join(AnalysisResult, AnalysisTask.id == AnalysisResult.analysis_task_id)
            .filter(
                AnalysisTask.user_id == user_id,
                AnalysisTask.created_at >= thirty_days_ago,
            )
            .order_by(AnalysisTask.created_at.desc())
            .limit(20)
            .all()
        )

        notifications = []
        now = datetime.now()

        for task in tasks:
            stock_id = task.stock_id
            stock_name = task.stock.stock_name if task.stock else stock_id

            # 获取最新行情
            try:
                detail = self.market.get_stock_detail(stock_id)
            except Exception:
                continue

            if not detail.quote_snapshot:
                continue

            # 获取分析结论中的价格基准（从 analysis_results 中取 headline_judgement）
            result = self.db.query(AnalysisResult).filter(
                AnalysisResult.analysis_task_id == task.id
            ).first()

            if not result or not result.key_reason_summary:
                continue

            # 检查价格是否大幅偏离（超过阈值）
            change_pct = detail.quote_snapshot.change_percent or 0

            is_invalidation = False
            invalidation_reason = ""

            # 条件1：当日大幅涨跌
            if abs(change_pct) >= 5.0:
                is_invalidation = True
                invalidation_reason = f"当日涨跌 {change_pct:+.2f}%，超出正常波动范围"

            # 条件2：近期有风险事件
            risk_events = [
                e for e in detail.recent_events
                if any(kw in (e.event_type or "") + (e.title or "") for kw in RISK_KEYWORDS)
            ]
            if risk_events:
                is_invalidation = True
                event_desc = risk_events[0].title or risk_events[0].event_type or "风险事件"
                invalidation_reason = f"出现风险关键词：{event_desc}"

            if not is_invalidation:
                continue

            # 生成失效提醒
            task_created = task.created_at or now
            days_ago = (now - task_created).days

            notifications.append(NotificationItem(
                id=str(uuid4()),
                type=NotificationType.ANALYSIS_INVALIDATION,
                title=f"结论可能失效：{stock_name}",
                description=(
                    f"上次分析（{days_ago} 天前）的结论可能已不适用。"
                    f"原因：{invalidation_reason}。"
                    f"建议重新分析后再做判断。"
                ),
                urgency=NotificationUrgency.HIGH if "风险" in invalidation_reason else NotificationUrgency.DUE_SOON,
                stock_id=stock_id,
                stock_name=stock_name,
                action_url=f"/analysis/single-stock?stock_id={stock_id}&stock_name={stock_name}",
                created_at=task_created,
                metadata={
                    "analysis_task_id": str(task.id),
                    "invalidation_reason": invalidation_reason,
                },
            ))

        return notifications

    def _count_expired_analysis_candidates(self, user_id: int) -> int:
        """Count locally expired analyses for lightweight summary badges."""
        from src.models.analysis_task import AnalysisStatusEnum

        return (
            self.db.query(AnalysisTask)
            .join(AnalysisResult, AnalysisTask.id == AnalysisResult.analysis_task_id)
            .filter(
                AnalysisTask.user_id == user_id,
                AnalysisTask.expired_at < datetime.now(),
                AnalysisTask.status.in_([
                    AnalysisStatusEnum.READY,
                    AnalysisStatusEnum.PARTIAL_READY,
                    AnalysisStatusEnum.EXPIRED,
                ]),
            )
            .count()
        )

    def _sort_notifications(self, notifications: list[NotificationItem]) -> list[NotificationItem]:
        """按紧迫程度（降序） + 创建时间（降序）排序"""
        urgency_order = {
            NotificationUrgency.OVERDUE: 0,
            NotificationUrgency.HIGH: 1,
            NotificationUrgency.DUE_SOON: 2,
            NotificationUrgency.NORMAL: 3,
        }
        return sorted(
            notifications,
            key=lambda n: (urgency_order.get(n.urgency, 99), -n.created_at.timestamp()),
        )

    def _collect_portfolio_risks(self, user_id: int) -> list[NotificationItem]:
        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).all()
        if not holdings:
            return []

        total_value = sum(_as_float(h.quantity) * _as_float(h.current_price) for h in holdings)
        if total_value <= 0:
            return []

        notifications: list[NotificationItem] = []
        now = datetime.now()
        for holding in holdings:
            market_value = _as_float(holding.quantity) * _as_float(holding.current_price)
            cost_value = _as_float(holding.quantity) * _as_float(holding.cost_price)
            weight = market_value / total_value
            pnl_rate = ((market_value - cost_value) / cost_value) if cost_value else 0

            if weight >= 0.6:
                notifications.append(NotificationItem(
                    id=str(uuid4()),
                    type=NotificationType.PORTFOLIO_RISK,
                    title=f"持仓集中度偏高：{holding.stock_name}",
                    description=f"{holding.stock_name} 当前约占组合 {weight * 100:.1f}%，需要优先复核仓位边界和原始买入理由。",
                    urgency=NotificationUrgency.HIGH,
                    stock_id=holding.stock_id,
                    stock_name=holding.stock_name,
                    action_url="/portfolio",
                    created_at=holding.position_updated_at or now,
                    metadata={"weight": weight},
                ))
            elif weight >= 0.4:
                notifications.append(NotificationItem(
                    id=str(uuid4()),
                    type=NotificationType.PORTFOLIO_RISK,
                    title=f"单票占比需要关注：{holding.stock_name}",
                    description=f"{holding.stock_name} 当前约占组合 {weight * 100:.1f}%，若继续加仓，需要补充新的事实证据。",
                    urgency=NotificationUrgency.DUE_SOON,
                    stock_id=holding.stock_id,
                    stock_name=holding.stock_name,
                    action_url="/portfolio",
                    created_at=holding.position_updated_at or now,
                    metadata={"weight": weight},
                ))

            if pnl_rate <= -0.15:
                notifications.append(NotificationItem(
                    id=str(uuid4()),
                    type=NotificationType.PORTFOLIO_RISK,
                    title=f"浮亏状态复盘提醒：{holding.stock_name}",
                    description=f"{holding.stock_name} 当前浮亏约 {pnl_rate * 100:.1f}%，建议区分事实变化、原始买入理由和亏损情绪。",
                    urgency=NotificationUrgency.DUE_SOON,
                    stock_id=holding.stock_id,
                    stock_name=holding.stock_name,
                    action_url=f"/analysis/post-trade?stock_id={holding.stock_id}&stock_name={holding.stock_name}",
                    created_at=holding.position_updated_at or now,
                    metadata={"unrealized_pnl_rate": pnl_rate},
                ))

        return notifications

    def _build_summary(self, notifications: list[NotificationItem]) -> NotificationSummary:
        overdue = sum(
            1 for n in notifications
            if n.urgency == NotificationUrgency.OVERDUE
        )
        due_soon = sum(
            1 for n in notifications
            if n.urgency == NotificationUrgency.DUE_SOON
        )
        watchlist_alerts = sum(
            1 for n in notifications
            if n.type == NotificationType.WATCHLIST_ALERT
        )
        invalidations = sum(
            1 for n in notifications
            if n.type == NotificationType.ANALYSIS_INVALIDATION
        )
        return NotificationSummary(
            total=len(notifications),
            overdue_count=overdue,
            due_soon_count=due_soon,
            watchlist_alert_count=watchlist_alerts,
            invalidation_count=invalidations,
        )
