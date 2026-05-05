from datetime import datetime

import httpx
import pytest

from src.services.market_data_service import MarketDataService


def test_mock_market_detail_does_not_call_external_http(monkeypatch):
    monkeypatch.setenv("E2E_MOCK_MARKET", "true")

    def fail_external_call(*args, **kwargs):
        raise AssertionError("external HTTP should not be called in mock market mode")

    monkeypatch.setattr("httpx.Client.get", fail_external_call)
    monkeypatch.setattr("httpx.Client.post", fail_external_call)

    service = MarketDataService()
    try:
        detail = service.get_stock_detail("SH600519")
        assert detail.stock_id == "SH600519"
        assert detail.stock_name == "贵州茅台"
        assert detail.quote_snapshot is not None
        assert detail.quote_snapshot.data_as_of == datetime(2026, 4, 30, 15, 0, tzinfo=detail.quote_snapshot.data_as_of.tzinfo)
        assert len(detail.recent_history) == 30
        assert detail.recent_events
        assert "E2E Mock Quote" in detail.data_sources
    finally:
        service.close()


def test_mock_market_search_is_deterministic(monkeypatch):
    monkeypatch.setenv("MOCK_MARKET_DATA", "true")

    service = MarketDataService()
    try:
        results = service.search_stocks("600519")
        assert [item.stock_id for item in results] == ["SH600519"]
        assert results[0].matched_by == "mock"
    finally:
        service.close()


def test_mock_market_rejects_unknown_stock(monkeypatch):
    monkeypatch.setenv("E2E_MOCK_MARKET", "true")
    service = MarketDataService()
    try:
        with pytest.raises(ValueError):
            service.get_stock_detail("SH999999")
    finally:
        service.close()


def test_real_market_detail_degrades_when_external_http_fails(monkeypatch):
    monkeypatch.delenv("E2E_MOCK_MARKET", raising=False)
    monkeypatch.delenv("MOCK_MARKET_DATA", raising=False)

    def fail_external_call(*args, **kwargs):
        raise httpx.ConnectError("simulated upstream outage")

    monkeypatch.setattr("httpx.Client.get", fail_external_call)
    monkeypatch.setattr("httpx.Client.post", fail_external_call)

    service = MarketDataService()
    try:
        detail = service.get_stock_detail("SH600519")
        assert detail.stock_id == "SH600519"
        assert detail.quote_snapshot is None
        assert detail.recent_history == []
        assert detail.recent_events == []
        assert detail.data_sources == ["external_market_data_degraded"]
    finally:
        service.close()
