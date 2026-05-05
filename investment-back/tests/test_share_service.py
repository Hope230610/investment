from datetime import datetime

from src.schemas.p3 import PublicShareSnapshot
from src.services.share_service import ShareService


def test_share_sanitizer_removes_sensitive_holding_fields_and_recommendations():
    service = ShareService(db=None)

    values = service._sanitize_list([
        "建议买入，quantity=100, cost_price=10, unrealized_pnl=500",
        "反方证据：若数据过期需要复核",
    ])
    text = " ".join(values)

    assert "建议买入" not in text
    assert "quantity" not in text
    assert "cost_price" not in text
    assert "unrealized_pnl" not in text


def test_share_sanitizer_can_be_applied_to_title_and_summary_text():
    service = ShareService(db=None)

    text = service._strip_sensitive(service.eval_service.sanitize_text(
        "strong buy with quantity=100 and cost_price=10"
    ))

    assert "strong buy" not in text
    assert "quantity" not in text
    assert "cost_price" not in text


def test_public_share_serializer_does_not_expose_user_or_source_ids():
    payload = PublicShareSnapshot(
        share_id="abc",
        title="结构化分析卡片",
        summary="仅展示决策过程",
        support_evidence=["data_fact: 事实"],
        counter_evidence=["model_inference: 反方"],
        risks=["uncertainty: 风险"],
        invalidation_conditions=["过期失效"],
        confidence_level="low",
        data_timestamp=None,
        disclaimer="非投资建议",
        created_at=datetime.utcnow(),
        expires_at=None,
    )

    data = payload.model_dump()

    assert "user_id" not in data
    assert "source_id" not in data
    assert payload.share_id == "abc"
