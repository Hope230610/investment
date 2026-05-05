from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.api.v1 import analysis as analysis_api
from src.api.v1 import notifications as notifications_api
from src.api.v1 import portfolio as portfolio_api
from src.models.analysis import InteractionScenario
from src.schemas.analysis import AnalysisCreate
from src.schemas.notification import NotificationSummary
from src.schemas.portfolio import TransactionCreate
from src.services.analysis_service import AnalysisService
from src.services.portfolio_service import PortfolioService


@pytest.mark.asyncio
async def test_portfolio_holdings_are_scoped_to_current_user(monkeypatch):
    calls: list[int] = []

    class FakePortfolioService:
        def __init__(self, db):
            self.db = db

        def list_holdings(self, user_id: int):
            calls.append(user_id)
            return [{"id": "a-user-holding", "user_id": user_id}]

    monkeypatch.setattr(portfolio_api, "PortfolioService", FakePortfolioService)

    result = await portfolio_api.list_holdings(
        db=object(),
        current_user=SimpleNamespace(id=1),
    )

    assert calls == [1]
    assert result == [{"id": "a-user-holding", "user_id": 1}]


@pytest.mark.asyncio
async def test_portfolio_transactions_are_scoped_to_current_user(monkeypatch):
    calls: list[tuple[int, str | None, int]] = []

    class FakePortfolioService:
        def __init__(self, db):
            self.db = db

        def list_transactions(self, user_id: int, stock_id: str | None = None, limit: int = 100):
            calls.append((user_id, stock_id, limit))
            return [{"id": "a-user-transaction", "user_id": user_id}]

    monkeypatch.setattr(portfolio_api, "PortfolioService", FakePortfolioService)

    result = await portfolio_api.list_transactions(
        stock_id="SH600519",
        limit=50,
        db=object(),
        current_user=SimpleNamespace(id=1),
    )

    assert calls == [(1, "SH600519", 50)]
    assert result == [{"id": "a-user-transaction", "user_id": 1}]


@pytest.mark.asyncio
async def test_portfolio_summary_uses_only_current_user(monkeypatch):
    calls: list[int] = []
    summary = SimpleNamespace(
        holding_count=1,
        total_market_value=100,
        total_cost_value=90,
        total_unrealized_pnl=10,
        total_unrealized_pnl_rate=0.1111,
        max_position_weight=1,
        max_position_stock_id="SH600519",
        max_position_stock_name="A user stock",
        concentration_alert=None,
        risk_tips=[],
        data_updated_at=None,
    )

    class FakePortfolioService:
        def __init__(self, db):
            self.db = db

        def get_overview(self, user_id: int):
            calls.append(user_id)
            return SimpleNamespace(summary=summary)

    monkeypatch.setattr(portfolio_api, "PortfolioService", FakePortfolioService)

    result = await portfolio_api.get_portfolio_summary(
        db=object(),
        current_user=SimpleNamespace(id=1),
    )

    assert calls == [1]
    assert result is summary


@pytest.mark.asyncio
async def test_analysis_creation_removes_forged_holding_context_when_user_has_no_holding(monkeypatch):
    captured_payloads: list[dict | None] = []
    portfolio_calls: list[int] = []

    class FakePortfolioService:
        def __init__(self, db):
            self.db = db

        def get_holding_context(self, user_id: int, stock_id: str):
            portfolio_calls.append(user_id)
            if user_id == 2:
                return {"stock_id": stock_id, "user_id": 2, "weight": 0.99}
            return None

    class FakeAnalysisService:
        def __init__(self, db):
            self.db = db

        def create_analysis(self, user_id: int, analysis_data: AnalysisCreate):
            captured_payloads.append(analysis_data.scenario_payload)
            return SimpleNamespace(id=uuid4(), status=SimpleNamespace(value="processing"))

    monkeypatch.setattr(analysis_api, "PortfolioService", FakePortfolioService)
    monkeypatch.setattr(analysis_api, "AnalysisService", FakeAnalysisService)
    monkeypatch.setattr(analysis_api, "_load_stock_detail_or_502", lambda *args, **kwargs: SimpleNamespace(stock_id="SH600519"))
    monkeypatch.setattr(analysis_api, "_upsert_stock_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(analysis_api, "enqueue_analysis_job", lambda *args, **kwargs: None)

    response = await analysis_api.create_analysis(
        analysis_data=AnalysisCreate(
            stock_id="SH600519",
            scenario=InteractionScenario.SINGLE_STOCK_CHECK,
            scenario_payload={
                "intent": "observe",
                "holding_context": {"stock_id": "SH600519", "user_id": 2, "weight": 0.99},
            },
        ),
        request=SimpleNamespace(headers={}),
        background_tasks=SimpleNamespace(),
        db=SimpleNamespace(refresh=lambda obj: None),
        current_user=SimpleNamespace(id=1),
        market_data_service=object(),
    )

    assert response.status == "processing"
    assert portfolio_calls == [1]
    assert captured_payloads == [{"intent": "observe"}]


@pytest.mark.asyncio
async def test_analysis_creation_uses_server_holding_context_over_client_forgery(monkeypatch):
    captured_payloads: list[dict | None] = []
    server_context = {
        "stock_id": "SH600519",
        "stock_name": "server holding",
        "user_id": 1,
        "weight": 0.12,
        "unrealized_pnl": 88.0,
    }

    class FakePortfolioService:
        def __init__(self, db):
            self.db = db

        def get_holding_context(self, user_id: int, stock_id: str):
            assert user_id == 1
            assert stock_id == "SH600519"
            return server_context

    class FakeAnalysisService:
        def __init__(self, db):
            self.db = db

        def create_analysis(self, user_id: int, analysis_data: AnalysisCreate):
            captured_payloads.append(analysis_data.scenario_payload)
            return SimpleNamespace(id=uuid4(), status=SimpleNamespace(value="processing"))

    monkeypatch.setattr(analysis_api, "PortfolioService", FakePortfolioService)
    monkeypatch.setattr(analysis_api, "AnalysisService", FakeAnalysisService)
    monkeypatch.setattr(analysis_api, "_load_stock_detail_or_502", lambda *args, **kwargs: SimpleNamespace(stock_id="SH600519"))
    monkeypatch.setattr(analysis_api, "_upsert_stock_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(analysis_api, "enqueue_analysis_job", lambda *args, **kwargs: None)

    response = await analysis_api.create_analysis(
        analysis_data=AnalysisCreate(
            stock_id="SH600519",
            scenario=InteractionScenario.SINGLE_STOCK_CHECK,
            scenario_payload={
                "intent": "observe",
                "holding_context": {"stock_id": "SH600519", "user_id": 999, "weight": 9.99},
            },
        ),
        request=SimpleNamespace(headers={}),
        background_tasks=SimpleNamespace(),
        db=SimpleNamespace(refresh=lambda obj: None),
        current_user=SimpleNamespace(id=1),
        market_data_service=object(),
    )

    assert response.status == "processing"
    assert captured_payloads == [{"intent": "observe", "holding_context": server_context}]


def test_analysis_service_removes_forged_holding_context_when_user_has_no_holding(monkeypatch):
    import src.services.portfolio_service as portfolio_service_module

    class FakePortfolioService:
        def __init__(self, db):
            self.db = db

        def get_holding_context(self, user_id: int, stock_id: str):
            assert user_id == 1
            assert stock_id == "SH600519"
            return None

    monkeypatch.setattr(portfolio_service_module, "PortfolioService", FakePortfolioService)

    sanitized = AnalysisService(db=object())._with_server_holding_context(
        1,
        AnalysisCreate(
            stock_id="SH600519",
            scenario=InteractionScenario.PRE_TRADE_CHECK,
            scenario_payload={
                "intent": "buy",
                "holding_context": {"stock_id": "SH600519", "user_id": 2, "weight": 0.99},
            },
        ),
    )

    assert sanitized.scenario_payload == {"intent": "buy"}


def test_analysis_service_uses_server_holding_context_over_client_forgery(monkeypatch):
    import src.services.portfolio_service as portfolio_service_module

    server_context = {"stock_id": "SH600519", "user_id": 1, "weight": 0.2}

    class FakePortfolioService:
        def __init__(self, db):
            self.db = db

        def get_holding_context(self, user_id: int, stock_id: str):
            assert user_id == 1
            assert stock_id == "SH600519"
            return server_context

    monkeypatch.setattr(portfolio_service_module, "PortfolioService", FakePortfolioService)

    sanitized = AnalysisService(db=object())._with_server_holding_context(
        1,
        AnalysisCreate(
            stock_id="SH600519",
            scenario=InteractionScenario.PRE_TRADE_CHECK,
            scenario_payload={
                "intent": "buy",
                "holding_context": {"stock_id": "SH600519", "user_id": 999, "weight": 9.99},
            },
        ),
    )

    assert sanitized.scenario_payload == {"intent": "buy", "holding_context": server_context}


def _transaction_payload(**overrides) -> TransactionCreate:
    payload = {
        "stock_id": "SH600519",
        "stock_name": "Test Stock",
        "market": "SH",
        "side": "buy",
        "price": 100,
        "quantity": 1,
    }
    payload.update(overrides)
    return TransactionCreate(**payload)


class _FakeTransactionDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        pass


class _FakeTransactionUpdateDb(_FakeTransactionDb):
    def __init__(self, tx):
        super().__init__()
        self.tx = tx

    def query(self, model):
        class FakeQuery:
            def __init__(self, result):
                self.result = result

            def filter(self, *args):
                return self

            def first(self):
                return self.result

        return FakeQuery(self.tx)


def _portfolio_service_with_reference_rules(monkeypatch, *, own_analysis_ids=None, own_review_ids=None):
    own_analysis_ids = {str(item) for item in (own_analysis_ids or [])}
    own_review_ids = set(own_review_ids or [])
    db = _FakeTransactionDb()
    service = PortfolioService(db)

    monkeypatch.setattr(
        service,
        "_resolve_stock",
        lambda stock_id, stock_name, market: SimpleNamespace(stock_name=stock_name or stock_id, market=market or "SH"),
    )
    monkeypatch.setattr(
        service,
        "_analysis_task_belongs_to_user",
        lambda user_id, task_id: user_id == 1 and str(task_id) in own_analysis_ids,
    )
    monkeypatch.setattr(
        service,
        "_review_task_belongs_to_user",
        lambda user_id, review_task_id: user_id == 1 and review_task_id in own_review_ids,
    )
    monkeypatch.setattr(
        service,
        "_serialize_transaction",
        lambda tx: SimpleNamespace(
            user_id=tx.user_id,
            analysis_task_id=str(tx.analysis_task_id) if tx.analysis_task_id else None,
            pre_trade_check_id=str(tx.pre_trade_check_id) if tx.pre_trade_check_id else None,
            review_task_id=tx.review_task_id,
        ),
    )
    return service, db


def test_user_cannot_create_transaction_with_another_users_analysis_task(monkeypatch):
    other_analysis_id = uuid4()
    service, db = _portfolio_service_with_reference_rules(monkeypatch)

    with pytest.raises(ValueError, match="TRANSACTION_REFERENCE_NOT_FOUND"):
        service.create_transaction(1, _transaction_payload(analysis_task_id=str(other_analysis_id)))

    assert db.added == []


def test_user_cannot_create_transaction_with_another_users_review_task(monkeypatch):
    service, db = _portfolio_service_with_reference_rules(monkeypatch)

    with pytest.raises(ValueError, match="TRANSACTION_REFERENCE_NOT_FOUND"):
        service.create_transaction(1, _transaction_payload(review_task_id=2002))

    assert db.added == []


def test_user_cannot_create_transaction_with_another_users_pre_trade_check(monkeypatch):
    other_pre_trade_check_id = uuid4()
    service, db = _portfolio_service_with_reference_rules(monkeypatch)

    with pytest.raises(ValueError, match="TRANSACTION_REFERENCE_NOT_FOUND"):
        service.create_transaction(1, _transaction_payload(pre_trade_check_id=str(other_pre_trade_check_id)))

    assert db.added == []


def test_user_can_create_transaction_with_own_analysis_and_review_references(monkeypatch):
    own_analysis_id = uuid4()
    own_pre_trade_check_id = uuid4()
    service, db = _portfolio_service_with_reference_rules(
        monkeypatch,
        own_analysis_ids={own_analysis_id, own_pre_trade_check_id},
        own_review_ids={1001},
    )

    result = service.create_transaction(
        1,
        _transaction_payload(
            analysis_task_id=str(own_analysis_id),
            pre_trade_check_id=str(own_pre_trade_check_id),
            review_task_id=1001,
        ),
    )

    assert len(db.added) == 1
    assert result.user_id == 1
    assert result.analysis_task_id == str(own_analysis_id)
    assert result.pre_trade_check_id == str(own_pre_trade_check_id)
    assert result.review_task_id == 1001


def test_user_cannot_update_transaction_with_another_users_analysis_task(monkeypatch):
    from src.schemas.portfolio import TransactionUpdate

    tx = SimpleNamespace(id=uuid4(), user_id=1, analysis_task_id=None, pre_trade_check_id=None, review_task_id=None)
    service, _ = _portfolio_service_with_reference_rules(monkeypatch)
    service.db = _FakeTransactionUpdateDb(tx)
    other_analysis_id = uuid4()

    with pytest.raises(ValueError, match="TRANSACTION_REFERENCE_NOT_FOUND"):
        service.update_transaction(1, tx.id, TransactionUpdate(analysis_task_id=str(other_analysis_id)))

    assert tx.analysis_task_id is None


def test_user_can_update_transaction_with_own_review_reference(monkeypatch):
    from src.schemas.portfolio import TransactionUpdate

    tx = SimpleNamespace(id=uuid4(), user_id=1, analysis_task_id=None, pre_trade_check_id=None, review_task_id=None)
    service, _ = _portfolio_service_with_reference_rules(monkeypatch, own_review_ids={1001})
    service.db = _FakeTransactionUpdateDb(tx)

    result = service.update_transaction(1, tx.id, TransactionUpdate(review_task_id=1001))

    assert result.review_task_id == 1001
    assert tx.review_task_id == 1001


@pytest.mark.asyncio
async def test_notification_summary_is_scoped_to_current_user(monkeypatch):
    calls: list[int] = []

    class FakeNotificationService:
        def __init__(self, db):
            self.db = db

        def get_summary(self, user_id: int):
            calls.append(user_id)
            return NotificationSummary(
                total=1,
                overdue_count=0,
                due_soon_count=1,
                watchlist_alert_count=0,
                invalidation_count=0,
            )

        def close(self):
            pass

    monkeypatch.setattr(notifications_api, "NotificationService", FakeNotificationService)

    result = await notifications_api.get_notification_summary(
        request=SimpleNamespace(headers={}),
        db=object(),
        current_user=SimpleNamespace(id=1),
    )

    assert calls == [1]
    assert result.total == 1


def test_notification_summary_does_not_call_market_collectors(monkeypatch):
    from src.services.notification_service import NotificationService

    service = NotificationService.__new__(NotificationService)
    monkeypatch.setattr(service, "_collect_review_reminders", lambda user_id: [])
    monkeypatch.setattr(service, "_collect_portfolio_risks", lambda user_id: [])
    monkeypatch.setattr(service, "_count_expired_analysis_candidates", lambda user_id: 2)
    monkeypatch.setattr(
        service,
        "_collect_watchlist_alerts",
        lambda user_id: (_ for _ in ()).throw(AssertionError("market collector called")),
    )
    monkeypatch.setattr(
        service,
        "_collect_analysis_invalidations",
        lambda user_id: (_ for _ in ()).throw(AssertionError("market collector called")),
    )

    summary = service.get_summary(user_id=1)

    assert summary.total == 2
    assert summary.invalidation_count == 2
