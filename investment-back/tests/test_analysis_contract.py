from datetime import datetime, timedelta

from fastapi.responses import JSONResponse

from src.api.v1.analysis import _build_pending_decision_card, _load_stock_detail_or_502
from src.schemas.analysis import DecisionCardV2, GetAnalysisResponseV2


class FailingMarketDataService:
    def get_stock_detail(self, stock_id: str):
        raise ValueError(stock_id)


class PendingTask:
    stock_id = "SZ000001"
    error_message = None
    created_at = datetime(2026, 5, 4, 9, 30, 0)
    updated_at = datetime(2026, 5, 4, 9, 31, 0)
    expired_at = datetime(2026, 5, 4, 9, 40, 0)


def test_stock_detail_loader_returns_unified_error_response_on_invalid_stock():
    response = _load_stock_detail_or_502(FailingMarketDataService(), "BAD")

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert b"STOCK_NOT_FOUND" in response.body


def test_pending_decision_card_is_schema_complete_for_polling_state():
    timestamp = datetime(2026, 5, 4, 9, 31, 0)
    valid_until = timestamp + timedelta(minutes=10)

    card = _build_pending_decision_card(PendingTask(), "processing", timestamp, valid_until)
    parsed = DecisionCardV2(**card)

    assert parsed.confidence == "low"
    assert parsed.confidence_level == "low"
    assert parsed.timestamp == timestamp
    assert parsed.valid_until == valid_until
    assert parsed.invalidation_conditions


def test_analysis_response_contract_exposes_timestamp_and_confidence_aliases():
    timestamp = datetime(2026, 5, 4, 9, 31, 0)
    valid_until = timestamp + timedelta(days=7)
    card = _build_pending_decision_card(PendingTask(), "processing", timestamp, valid_until)

    response = GetAnalysisResponseV2(
        analysis_id="00000000-0000-0000-0000-000000000001",
        user_id=1,
        stock_id="SZ000001",
        scenario="single_stock_check",
        status="processing",
        decision_card=card,
        recent_events=[],
        data_sources=[],
        valid_until=valid_until,
        timestamp=timestamp,
    )

    payload = response.model_dump()
    assert payload["timestamp"] == timestamp
    assert payload["decision_card"]["confidence"] == "low"
    assert payload["decision_card"]["valid_until"] == valid_until
