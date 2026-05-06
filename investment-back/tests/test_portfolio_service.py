from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from src.schemas.portfolio import HoldingItem
from src.services.portfolio_service import PortfolioService


def _holding(stock_id: str, stock_name: str, market_value: float, cost_value: float) -> HoldingItem:
    now = datetime(2026, 5, 4, 10, 0, 0)
    return HoldingItem(
        id=f"00000000-0000-0000-0000-00000000000{stock_id[-1]}",
        user_id=1,
        stock_id=stock_id,
        stock_name=stock_name,
        market="SH",
        quantity=100,
        cost_price=cost_value / 100,
        current_price=market_value / 100,
        market_value=market_value,
        cost_value=cost_value,
        unrealized_pnl=market_value - cost_value,
        unrealized_pnl_rate=(market_value - cost_value) / cost_value,
        weight=0,
        note=None,
        position_updated_at=now,
        created_at=now,
        updated_at=now,
    )


def test_portfolio_summary_flags_high_concentration():
    service = PortfolioService(db=None)
    summary = service._build_summary([
        _holding("SZ000200", "5999元手机分期", 7000, 6000),
        _holding("SZ000201", "校园餐饮预算", 3000, 2500),
    ])

    assert summary.holding_count == 2
    assert summary.total_market_value == 10000
    assert summary.max_position_weight == 0.7
    assert summary.max_position_stock_id == "SZ000200"
    assert summary.concentration_alert is not None
    assert "集中" in summary.risk_tips[0]


def test_portfolio_summary_mentions_loss_context_without_trade_instruction():
    service = PortfolioService(db=None)
    summary = service._build_summary([
        _holding("SZ000202", "教材资料预算", 800, 1000),
        _holding("SZ000203", "社团活动预算", 700, 800),
    ])

    assert summary.total_unrealized_pnl == -300
    assert any("浮亏" in tip for tip in summary.risk_tips)
    assert "买入" not in " ".join(summary.risk_tips)
    assert "卖出" not in " ".join(summary.risk_tips)


def test_serialize_holding_handles_decimal_amounts_and_zero_total():
    now = datetime(2026, 5, 4, 10, 0, 0)
    holding = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        user_id=1,
        stock_id="SZ000200",
        stock_name="5999元手机分期",
        market="SZ",
        quantity=Decimal("10.0000"),
        cost_price=Decimal("100.0000"),
        current_price=Decimal("90.0000"),
        note=None,
        position_updated_at=now,
        created_at=now,
        updated_at=now,
    )

    item = PortfolioService(db=None)._serialize_holding(holding, total_value=0)

    assert item.market_value == 900
    assert item.unrealized_pnl == -100
    assert item.unrealized_pnl_rate == -0.1
    assert item.weight == 0


def test_holding_context_is_json_safe(monkeypatch):
    now = datetime(2026, 5, 4, 10, 0, 0)
    holding = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        user_id=1,
        stock_id="SZ000200",
        stock_name="5999元手机分期",
        market="SZ",
        quantity=Decimal("10.0000"),
        cost_price=Decimal("100.0000"),
        current_price=Decimal("90.0000"),
        note=None,
        position_updated_at=now,
        created_at=now,
        updated_at=now,
    )

    class Query:
        def __init__(self, rows):
            self.rows = rows

        def filter(self, *args):
            return self

        def first(self):
            return self.rows[0]

        def all(self):
            return self.rows

    class Db:
        def query(self, model):
            return Query([holding])

    context = PortfolioService(Db()).get_holding_context(1, "SZ000200")

    assert isinstance(context["position_updated_at"], str)
    assert isinstance(context["created_at"], str)
    assert isinstance(context["updated_at"], str)
