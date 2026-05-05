from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from src.models.p3 import PlanCodeEnum, UsageCounter, UserEntitlement
from src.schemas.p3 import EntitlementView


PLAN_LIMITS: dict[str, dict[str, int | None]] = {
    "free": {
        "daily_analysis": 5,
        "watchlist_items": 20,
        "portfolio_holdings": 20,
        "share_cards_daily": 3,
        "growth_insight": 1,
        "ai_eval": 0,
    },
    "pro": {
        "daily_analysis": 50,
        "watchlist_items": 200,
        "portfolio_holdings": 200,
        "share_cards_daily": 30,
        "growth_insight": 1,
        "ai_eval": 1,
    },
}


class EntitlementLimitExceeded(ValueError):
    def __init__(self, usage_key: str, limit: int | None):
        super().__init__("ENTITLEMENT_LIMIT_EXCEEDED")
        self.usage_key = usage_key
        self.limit = limit


class EntitlementService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: int) -> UserEntitlement:
        item = self.db.query(UserEntitlement).filter(UserEntitlement.user_id == user_id).first()
        if item:
            return item
        item = UserEntitlement(user_id=user_id, plan_code=PlanCodeEnum.FREE, feature_flags={})
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_limits(self, user_id: int) -> dict[str, int | None]:
        entitlement = self.get_or_create(user_id)
        plan = entitlement.plan_code.value if hasattr(entitlement.plan_code, "value") else entitlement.plan_code
        return dict(PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]))

    def assert_within_limit(self, user_id: int, usage_key: str, *, increment: bool = False) -> None:
        limits = self.get_limits(user_id)
        limit = limits.get(usage_key)
        if limit is None:
            if increment:
                self.increment(user_id, usage_key)
            return
        current = self.get_usage(user_id, usage_key)
        if current >= limit:
            raise EntitlementLimitExceeded(usage_key, limit)
        if increment:
            self.increment(user_id, usage_key)

    def increment(self, user_id: int, usage_key: str, amount: int = 1) -> UsageCounter:
        today = date.today()
        item = (
            self.db.query(UsageCounter)
            .filter(
                UsageCounter.user_id == user_id,
                UsageCounter.usage_key == usage_key,
                UsageCounter.usage_date == today,
            )
            .first()
        )
        if not item:
            item = UsageCounter(user_id=user_id, usage_key=usage_key, usage_date=today, count=0)
            self.db.add(item)
        item.count += amount
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_usage(self, user_id: int, usage_key: str) -> int:
        today = date.today()
        item = (
            self.db.query(UsageCounter)
            .filter(
                UsageCounter.user_id == user_id,
                UsageCounter.usage_key == usage_key,
                UsageCounter.usage_date == today,
            )
            .first()
        )
        return int(item.count) if item else 0

    def view(self, user_id: int) -> EntitlementView:
        entitlement = self.get_or_create(user_id)
        plan = entitlement.plan_code.value if hasattr(entitlement.plan_code, "value") else entitlement.plan_code
        limits = self.get_limits(user_id)
        usage = {key: self.get_usage(user_id, key) for key in limits if key.endswith("_daily") or key == "daily_analysis"}
        flags = {
            "growth_insight": bool(limits.get("growth_insight")),
            "ai_eval": bool(limits.get("ai_eval")),
            "share_cards": bool(limits.get("share_cards_daily")),
        }
        flags.update(entitlement.feature_flags or {})
        return EntitlementView(plan_code=plan, feature_flags=flags, limits=limits, usage=usage)
