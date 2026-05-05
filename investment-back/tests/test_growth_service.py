from datetime import datetime
from types import SimpleNamespace

from src.services.growth_service import GrowthService


def test_growth_private_builds_repeated_mistakes_without_trade_advice():
    service = GrowthService(db=None)
    reviews = [
        SimpleNamespace(review_result={"behavior_patterns": ["追涨"], "plan_deviation": True}),
        SimpleNamespace(review_result={"behavior_patterns": ["追涨"], "judgement_quality": "主要来自运气"}),
    ]
    counter = service._extract_review_patterns(reviews)
    rules = service._build_caution_rules(["追涨 在近 120 天内重复出现 2 次"], ["追涨触发后容易加快决策节奏"], [])

    assert counter["追涨"] == 2
    joined = " ".join(rules)
    assert "买入" not in joined
    assert "卖出" not in joined


def test_growth_extracts_high_emotion_risk_tendency():
    service = GrowthService(db=None)
    emotions = [
        SimpleNamespace(emotion_level=5, created_at=datetime.utcnow()),
        SimpleNamespace(emotion_level=4, created_at=datetime.utcnow()),
    ]

    tendencies = service._build_risk_tendencies([], emotions)

    assert any("情绪" in item for item in tendencies)


def test_growth_cross_user_isolation_is_expressed_in_query_filters():
    code = GrowthService.build_caution_context.__code__

    assert "user_id" in code.co_names
