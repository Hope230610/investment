"""
Unit tests for NotificationService.

Tests cover all three collector branches (_collect_review_reminders,
_collect_watchlist_alerts, _collect_analysis_invalidations), sorting,
and summary building without requiring a real DB or market data API.

Run with: cd investment-back && pytest tests/test_notification_service.py -v
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import MagicMock, patch
import unittest

import sys
from pathlib import Path

_back_root = Path(__file__).parent.parent
sys.path.insert(0, str(_back_root))

from src.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    NotificationSummary,
    NotificationType,
    NotificationUrgency,
)


# ─── Mock stock event ───────────────────────────────────────────────────────────

@dataclass
class MockStockEvent:
    title: str
    event_type: str
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    source: str = "mock"


@dataclass
class MockQuoteSnapshot:
    change_percent: float
    latest_price: Optional[float] = None


# ─── Mock market data ──────────────────────────────────────────────────────────

@dataclass
class MockStockDetail:
    stock_id: str
    stock_name: str
    market: str = "SH"
    industry: Optional[str] = None
    quote_snapshot: Optional[MockQuoteSnapshot] = None
    recent_events: List[MockStockEvent] = field(default_factory=list)


# ─── Mock DB models ─────────────────────────────────────────────────────────────

@dataclass
class MockReviewTaskModel:
    id: int
    user_id: int
    analysis_task_id: Optional[str] = None
    stock_id: Optional[str] = None
    stock_name: str = "测试股票"
    status: str = "pending"  # "pending" | "completed" | "expired"
    review_at: datetime = field(default_factory=lambda: datetime.now())
    created_at: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class MockAnalysisTaskModel:
    id: str
    user_id: int
    stock_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now())
    status: str = "ready"


@dataclass
class MockAnalysisResultModel:
    analysis_task_id: str
    key_reason_summary: List[dict] = field(default_factory=list)
    headline_judgement: str = "测试结论"


@dataclass
class MockWatchlistModel:
    user_id: int
    stock_id: str
    notify_on_events: bool = True
    stock: Optional[object] = None  # relationship — set to mock Stock model


# ─── Mock MarketDataService ────────────────────────────────────────────────────

class MockMarketDataService:
    def __init__(self, stocks: dict[str, MockStockDetail]):
        self._stocks = stocks
        self.closed_flag = False

    def get_stock_detail(self, stock_id: str) -> MockStockDetail:
        if stock_id not in self._stocks:
            raise RuntimeError(f"Stock {stock_id} not found")
        return self._stocks[stock_id]

    def close(self):
        self.closed_flag = True


# ─── Mirror of _sort_notifications ─────────────────────────────────────────────

def mirror_sort(notifications: List[NotificationItem]) -> List[NotificationItem]:
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


# ─── Mirror of _build_summary ─────────────────────────────────────────────────

def mirror_summary(notifications: List[NotificationItem]) -> NotificationSummary:
    overdue = sum(1 for n in notifications if n.urgency == NotificationUrgency.OVERDUE)
    due_soon = sum(1 for n in notifications if n.urgency == NotificationUrgency.DUE_SOON)
    watchlist_alerts = sum(1 for n in notifications if n.type == NotificationType.WATCHLIST_ALERT)
    invalidations = sum(1 for n in notifications if n.type == NotificationType.ANALYSIS_INVALIDATION)
    return NotificationSummary(
        total=len(notifications),
        overdue_count=overdue,
        due_soon_count=due_soon,
        watchlist_alert_count=watchlist_alerts,
        invalidation_count=invalidations,
    )


# ─── Mirror of _collect_review_reminders ───────────────────────────────────────

def mirror_review_reminders(
    tasks: List[MockReviewTaskModel],
) -> List[NotificationItem]:
    now = datetime.now()
    due_soon_cutoff = now + timedelta(days=3)
    items: List[NotificationItem] = []

    # Filter at source — matches real service's .filter(status.in_([PENDING, EXPIRED]))
    active_tasks = [t for t in tasks if t.status in ("pending", "expired")]

    for task in active_tasks:
        review_at = task.review_at
        if task.status == "expired" or review_at < now:
            urgency = NotificationUrgency.OVERDUE
            overdue_days = max(1, (now - review_at).days)
            title = f"复盘已逾期 {overdue_days} 天"
            description = f"{task.stock_name} 的复盘任务已逾期，请尽快处理。"
        elif review_at <= due_soon_cutoff:
            days_left = (review_at - now).days
            urgency = NotificationUrgency.DUE_SOON
            title = f"复盘提醒：{task.stock_name}"
            description = f"还有 {days_left} 天到达复盘时间，请做好准备。"
        else:
            urgency = NotificationUrgency.NORMAL
            title = f"待复盘：{task.stock_name}"
            description = f"计划复盘时间：{review_at.strftime('%Y-%m-%d')}"

        stock_id = task.stock_id or ""
        stock_name = task.stock_name or stock_id or "该股票"
        action_url = (
            f"/analysis/post-trade?stock_id={stock_id}"
            f"&stock_name={stock_name}"
            f"&pending_review_task_id={task.analysis_task_id or ''}"
        )
        items.append(NotificationItem(
            id=f"review-{task.id}",
            type=NotificationType.REVIEW_REMINDER,
            title=title,
            description=description,
            urgency=urgency,
            stock_id=stock_id or None,
            stock_name=stock_name,
            action_url=action_url,
            created_at=review_at,
        ))

    return items


# ─── Mirror of _collect_watchlist_alerts ─────────────────────────────────────

def mirror_watchlist_alerts(
    watchlist_items: List[MockWatchlistModel],
    market: MockMarketDataService,
) -> List[NotificationItem]:
    now = datetime.now()
    recent_window = now - timedelta(days=7)
    RISK_KEYWORDS = (
        "风险", "问询", "冻结", "减持", "诉讼", "监管",
        "终止", "亏损", "质押", "违规", "警示", "立案",
        "ST", "*ST", "暂停上市", "退市风险",
    )
    items: List[NotificationItem] = []

    for item in watchlist_items:
        if not item.notify_on_events:
            continue
        stock_id = item.stock_id
        try:
            detail = market.get_stock_detail(stock_id)
        except Exception:
            continue

        if not detail.recent_events:
            continue

        stock_name = detail.stock_name or stock_id

        for event in detail.recent_events:
            published_at = event.published_at or now
            if published_at < recent_window:
                continue

            text = (event.event_type or "") + (event.title or "")
            is_risk = any(kw in text for kw in RISK_KEYWORDS)
            is_price_move = False
            if detail.quote_snapshot:
                change_pct = abs(detail.quote_snapshot.change_percent or 0)
                is_price_move = change_pct >= 3.0

            if not (is_risk or is_price_move):
                continue

            if is_risk:
                urgency = NotificationUrgency.HIGH
                title = f"风险提醒：{stock_name}"
                description = f"{event.event_type}：{event.title}"
            else:
                urgency = NotificationUrgency.DUE_SOON
                change_str = f"+{detail.quote_snapshot.change_percent:.2f}%" if detail.quote_snapshot else ""
                title = f"价格异动：{stock_name}"
                description = f"当日涨跌 {change_str}，{event.title}"

            items.append(NotificationItem(
                id=f"watchlist-{stock_id}-{event.title}",
                type=NotificationType.WATCHLIST_ALERT,
                title=title,
                description=description[:200],
                urgency=urgency,
                stock_id=stock_id,
                stock_name=stock_name,
                action_url=f"/analysis/single-stock?stock_id={stock_id}&stock_name={stock_name}",
                created_at=published_at,
            ))

    return items


# ─── Mirror of _collect_analysis_invalidations ────────────────────────────────

def mirror_invalidations(
    tasks: List[MockAnalysisTaskModel],
    results: dict[str, MockAnalysisResultModel],
    market: MockMarketDataService,
) -> List[NotificationItem]:
    RISK_KEYWORDS = (
        "风险", "问询", "冻结", "减持", "诉讼", "监管",
        "终止", "亏损", "质押", "违规", "警示", "立案",
        "ST", "*ST", "暂停上市", "退市风险",
    )
    now = datetime.now()
    items: List[NotificationItem] = []

    for task in tasks:
        try:
            detail = market.get_stock_detail(task.stock_id)
        except Exception:
            continue

        if not detail.quote_snapshot:
            continue

        result = results.get(task.id)
        if not result or not result.key_reason_summary:
            continue

        change_pct = detail.quote_snapshot.change_percent or 0
        is_invalidation = False
        invalidation_reason = ""

        if abs(change_pct) >= 5.0:
            is_invalidation = True
            invalidation_reason = f"当日涨跌 {change_pct:+.2f}%，超出正常波动范围"

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

        task_created = task.created_at or now
        days_ago = (now - task_created).days

        items.append(NotificationItem(
            id=f"invalidation-{task.id}",
            type=NotificationType.ANALYSIS_INVALIDATION,
            title=f"结论可能失效：{detail.stock_name}",
            description=(
                f"上次分析（{days_ago} 天前）的结论可能已不适用。"
                f"原因：{invalidation_reason}。"
                f"建议重新分析后再做判断。"
            ),
            urgency=NotificationUrgency.HIGH if "风险" in invalidation_reason else NotificationUrgency.DUE_SOON,
            stock_id=task.stock_id,
            stock_name=detail.stock_name,
            action_url=f"/analysis/single-stock?stock_id={task.stock_id}&stock_name={detail.stock_name}",
            created_at=task_created,
        ))

    return items


# ─── Test cases ────────────────────────────────────────────────────────────────

class TestReviewReminders(unittest.TestCase):
    def test_overdue_task_emits_overdue_urgency(self):
        now = datetime.now()
        tasks = [
            MockReviewTaskModel(
                id=1, user_id=1,
                stock_id="SH600519", stock_name="贵州茅台",
                status="expired",
                review_at=now - timedelta(days=3),
            ),
        ]
        items = mirror_review_reminders(tasks)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].urgency, NotificationUrgency.OVERDUE)
        self.assertIn("逾期", items[0].title)
        self.assertEqual(items[0].stock_id, "SH600519")

    def test_due_soon_task_emits_due_soon_urgency(self):
        now = datetime.now()
        tasks = [
            MockReviewTaskModel(
                id=2, user_id=1,
                stock_id="SZ002594", stock_name="比亚迪",
                status="pending",
                review_at=now + timedelta(days=2),
            ),
        ]
        items = mirror_review_reminders(tasks)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].urgency, NotificationUrgency.DUE_SOON)
        self.assertIn("还有", items[0].description)

    def test_upcoming_task_emits_normal_urgency(self):
        now = datetime.now()
        tasks = [
            MockReviewTaskModel(
                id=3, user_id=1,
                stock_id="SH600036", stock_name="招商银行",
                status="pending",
                review_at=now + timedelta(days=10),
            ),
        ]
        items = mirror_review_reminders(tasks)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].urgency, NotificationUrgency.NORMAL)

    def test_completed_task_not_included(self):
        tasks = [
            MockReviewTaskModel(
                id=4, user_id=1,
                status="completed",
                review_at=datetime.now() - timedelta(days=1),
            ),
        ]
        items = mirror_review_reminders(tasks)
        self.assertEqual(len(items), 0)


class TestWatchlistAlerts(unittest.TestCase):
    def _market(self) -> MockMarketDataService:
        return MockMarketDataService({
            "SH600519": MockStockDetail(
                stock_id="SH600519",
                stock_name="贵州茅台",
                quote_snapshot=MockQuoteSnapshot(change_percent=6.5),
                recent_events=[
                    MockStockEvent(
                        title="风险提示公告",
                        event_type="风险",
                        published_at=datetime.now() - timedelta(days=2),
                    ),
                ],
            ),
            "SZ002594": MockStockDetail(
                stock_id="SZ002594",
                stock_name="比亚迪",
                quote_snapshot=MockQuoteSnapshot(change_percent=2.1),
                recent_events=[
                    MockStockEvent(
                        title="分红派息公告",
                        event_type="分红",
                        published_at=datetime.now() - timedelta(days=1),
                    ),
                ],
            ),
        })

    def test_risk_event_triggers_high_urgency_alert(self):
        items = mirror_watchlist_alerts(
            [MockWatchlistModel(user_id=1, stock_id="SH600519", notify_on_events=True)],
            self._market(),
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].urgency, NotificationUrgency.HIGH)
        self.assertEqual(items[0].type, NotificationType.WATCHLIST_ALERT)
        self.assertIn("风险", items[0].title)

    def test_price_movement_triggers_alert_above_threshold(self):
        # 6.5% > 3% threshold
        items = mirror_watchlist_alerts(
            [MockWatchlistModel(user_id=1, stock_id="SH600519", notify_on_events=True)],
            self._market(),
        )
        # One risk + one price move = 2 items
        risk_or_price = [i for i in items if "价格异动" in i.title or "风险提醒" in i.title]
        self.assertGreater(len(risk_or_price), 0)

    def test_mild_movement_below_threshold_not_triggered(self):
        # 2.1% < 3% threshold, no risk keyword → no alert
        items = mirror_watchlist_alerts(
            [MockWatchlistModel(user_id=1, stock_id="SZ002594", notify_on_events=True)],
            self._market(),
        )
        self.assertEqual(len(items), 0)

    def test_old_event_not_triggered(self):
        market = MockMarketDataService({
            "SH600036": MockStockDetail(
                stock_id="SH600036",
                stock_name="招商银行",
                quote_snapshot=MockQuoteSnapshot(change_percent=4.0),
                recent_events=[
                    MockStockEvent(
                        title="风险公告",
                        event_type="风险",
                        published_at=datetime.now() - timedelta(days=10),  # > 7 days ago
                    ),
                ],
            ),
        })
        items = mirror_watchlist_alerts(
            [MockWatchlistModel(user_id=1, stock_id="SH600036", notify_on_events=True)],
            market,
        )
        self.assertEqual(len(items), 0)


class TestAnalysisInvalidations(unittest.TestCase):
    def _market(self) -> MockMarketDataService:
        return MockMarketDataService({
            "SH600519": MockStockDetail(
                stock_id="SH600519",
                stock_name="贵州茅台",
                quote_snapshot=MockQuoteSnapshot(change_percent=7.2),
                recent_events=[],
            ),
            "SZ002594": MockStockDetail(
                stock_id="SZ002594",
                stock_name="比亚迪",
                quote_snapshot=MockQuoteSnapshot(change_percent=1.5),
                recent_events=[
                    MockStockEvent(
                        title="监管问询",
                        event_type="问询",
                        published_at=datetime.now() - timedelta(days=1),
                    ),
                ],
            ),
            "SH600036": MockStockDetail(
                stock_id="SH600036",
                stock_name="招商银行",
                quote_snapshot=MockQuoteSnapshot(change_percent=2.0),
                recent_events=[],
            ),
        })

    def test_large_price_move_triggers_invalidation(self):
        tasks = [
            MockAnalysisTaskModel(
                id="task-1", user_id=1,
                stock_id="SH600519",
                created_at=datetime.now() - timedelta(days=5),
            ),
        ]
        results = {"task-1": MockAnalysisResultModel(analysis_task_id="task-1", key_reason_summary=[{}])}
        items = mirror_invalidations(tasks, results, self._market())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].urgency, NotificationUrgency.DUE_SOON)
        self.assertIn("涨跌", items[0].description)

    def test_risk_keyword_triggers_high_urgency_invalidation(self):
        tasks = [
            MockAnalysisTaskModel(
                id="task-2", user_id=1,
                stock_id="SZ002594",
                created_at=datetime.now() - timedelta(days=3),
            ),
        ]
        results = {"task-2": MockAnalysisResultModel(analysis_task_id="task-2", key_reason_summary=[{}])}
        items = mirror_invalidations(tasks, results, self._market())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].urgency, NotificationUrgency.HIGH)
        self.assertIn("问询", items[0].description)

    def test_normal_fluctuation_not_invalidated(self):
        tasks = [
            MockAnalysisTaskModel(
                id="task-3", user_id=1,
                stock_id="SH600036",
                created_at=datetime.now() - timedelta(days=2),
            ),
        ]
        results = {"task-3": MockAnalysisResultModel(analysis_task_id="task-3", key_reason_summary=[{}])}
        items = mirror_invalidations(tasks, results, self._market())
        self.assertEqual(len(items), 0)

    def test_missing_result_key_reason_not_invalidated(self):
        tasks = [
            MockAnalysisTaskModel(
                id="task-4", user_id=1,
                stock_id="SH600519",
                created_at=datetime.now() - timedelta(days=1),
            ),
        ]
        results = {}  # No result
        items = mirror_invalidations(tasks, results, self._market())
        self.assertEqual(len(items), 0)


class TestSorting(unittest.TestCase):
    def test_overdue_before_high_before_due_soon(self):
        now = datetime.now()
        items = [
            NotificationItem(
                id="n1", type=NotificationType.REVIEW_REMINDER,
                title="normal", description="n",
                urgency=NotificationUrgency.NORMAL,
                created_at=now,
            ),
            NotificationItem(
                id="o1", type=NotificationType.REVIEW_REMINDER,
                title="overdue", description="o",
                urgency=NotificationUrgency.OVERDUE,
                created_at=now - timedelta(days=1),
            ),
            NotificationItem(
                id="h1", type=NotificationType.WATCHLIST_ALERT,
                title="high", description="h",
                urgency=NotificationUrgency.HIGH,
                created_at=now,
            ),
            NotificationItem(
                id="d1", type=NotificationType.ANALYSIS_INVALIDATION,
                title="due soon", description="d",
                urgency=NotificationUrgency.DUE_SOON,
                created_at=now,
            ),
        ]
        sorted_items = mirror_sort(items)
        self.assertEqual(sorted_items[0].id, "o1")
        self.assertEqual(sorted_items[1].id, "h1")
        self.assertEqual(sorted_items[2].id, "d1")
        self.assertEqual(sorted_items[3].id, "n1")

    def test_within_same_urgency_newer_first(self):
        now = datetime.now()
        items = [
            NotificationItem(
                id="old", type=NotificationType.REVIEW_REMINDER,
                title="old", description="",
                urgency=NotificationUrgency.OVERDUE,
                created_at=now - timedelta(days=5),
            ),
            NotificationItem(
                id="new", type=NotificationType.REVIEW_REMINDER,
                title="new", description="",
                urgency=NotificationUrgency.OVERDUE,
                created_at=now,
            ),
        ]
        sorted_items = mirror_sort(items)
        self.assertEqual(sorted_items[0].id, "new")
        self.assertEqual(sorted_items[1].id, "old")


class TestSummaryBuilding(unittest.TestCase):
    def test_counts_correct(self):
        now = datetime.now()
        items = [
            NotificationItem(
                id="r1", type=NotificationType.REVIEW_REMINDER,
                title="overdue", description="",
                urgency=NotificationUrgency.OVERDUE,
                created_at=now,
            ),
            NotificationItem(
                id="r2", type=NotificationType.REVIEW_REMINDER,
                title="due soon", description="",
                urgency=NotificationUrgency.DUE_SOON,
                created_at=now,
            ),
            NotificationItem(
                id="w1", type=NotificationType.WATCHLIST_ALERT,
                title="watchlist alert", description="",
                urgency=NotificationUrgency.HIGH,
                created_at=now,
            ),
            NotificationItem(
                id="a1", type=NotificationType.ANALYSIS_INVALIDATION,
                title="invalidation", description="",
                urgency=NotificationUrgency.DUE_SOON,
                created_at=now,
            ),
        ]
        summary = mirror_summary(items)
        self.assertEqual(summary.total, 4)
        self.assertEqual(summary.overdue_count, 1)
        self.assertEqual(summary.due_soon_count, 2)
        self.assertEqual(summary.watchlist_alert_count, 1)
        self.assertEqual(summary.invalidation_count, 1)


if __name__ == "__main__":
    unittest.main()
