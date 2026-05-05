from types import SimpleNamespace

import pytest

from src.services.entitlement_service import EntitlementLimitExceeded, EntitlementService, PLAN_LIMITS


class InMemoryEntitlementService(EntitlementService):
    def __init__(self, plan="free"):
        self.plan = plan
        self.usage = {}

    def get_limits(self, user_id: int):
        return dict(PLAN_LIMITS[self.plan])

    def get_usage(self, user_id: int, usage_key: str) -> int:
        return self.usage.get((user_id, usage_key), 0)

    def increment(self, user_id: int, usage_key: str, amount: int = 1):
        self.usage[(user_id, usage_key)] = self.get_usage(user_id, usage_key) + amount
        return SimpleNamespace(count=self.usage[(user_id, usage_key)])


def test_free_plan_daily_analysis_limit():
    service = InMemoryEntitlementService("free")
    service.usage[(1, "daily_analysis")] = 5

    with pytest.raises(EntitlementLimitExceeded):
        service.assert_within_limit(1, "daily_analysis")


def test_pro_plan_allows_more_daily_analysis():
    service = InMemoryEntitlementService("pro")
    service.usage[(1, "daily_analysis")] = 5

    service.assert_within_limit(1, "daily_analysis", increment=True)

    assert service.get_usage(1, "daily_analysis") == 6


def test_usage_isolated_by_user():
    service = InMemoryEntitlementService("free")
    service.usage[(1, "share_cards_daily")] = 3

    with pytest.raises(EntitlementLimitExceeded):
        service.assert_within_limit(1, "share_cards_daily")
    service.assert_within_limit(2, "share_cards_daily", increment=True)

    assert service.get_usage(2, "share_cards_daily") == 1
