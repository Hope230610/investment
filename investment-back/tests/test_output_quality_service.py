from datetime import datetime

import pytest

from src.models.analysis import OutputMarkType
from src.schemas.analysis import DecisionCard, ReasonPoint, UserFitSummary
from src.services.output_quality_service import OutputQualityService


def make_card(**overrides):
    data = {
        "headline_judgement": "当前更适合继续观察，等待下一次验证信号",
        "key_reason_summary": [
            ReasonPoint(text="最新价与近 5 日走势已纳入判断。", tag=OutputMarkType.DATA_FACT),
            ReasonPoint(text="事件信息仍需继续跟踪。", tag=OutputMarkType.UNCERTAINTY),
        ],
        "user_fit_summary": UserFitSummary(
            fit="适合愿意先观察事实的投资者。",
            unfit="不适合希望系统直接给出买卖指令的人。",
        ),
        "next_step_actions": ["继续观察公告变化，等待下一次市场更新后复核。"],
        "primary_risks": "当前主要风险是信息不完整导致误判。",
        "review_at": datetime(2026, 5, 6, 10, 0, 0),
        "data_as_of": datetime(2026, 4, 29, 15, 0, 0),
        "supporting_evidence": ["[支撑] 最新价格和近期走势已纳入。"],
        "counter_evidence": ["风险公告或数据缺口可能削弱当前判断。"],
        "invalidation_conditions": ["出现重大不利公告时重新评估。"],
        "confidence_level": "medium",
    }
    data.update(overrides)
    return DecisionCard(**data)


def test_ready_card_passes_quality_gate():
    report = OutputQualityService().evaluate_decision_card(make_card())
    assert report.passed


def test_direct_trading_instruction_fails():
    report = OutputQualityService().evaluate_decision_card(
        make_card(headline_judgement="必须买入，明天一定涨")
    )
    assert not report.passed
    assert {issue.code for issue in report.issues} >= {"direct_trading_instruction"}


def test_missing_evidence_fields_fail():
    report = OutputQualityService().evaluate_decision_card(
        make_card(supporting_evidence=[], counter_evidence=[], invalidation_conditions=[])
    )
    assert not report.passed
    codes = {issue.code for issue in report.issues}
    assert "missing_supporting_evidence" in codes
    assert "missing_counter_evidence" in codes
    assert "missing_invalidation_conditions" in codes


def test_degraded_high_confidence_fails():
    report = OutputQualityService().evaluate_decision_card(
        make_card(confidence_level="high", data_as_of=None),
        degrade_flags=["insufficient_evidence"],
    )
    assert not report.passed
    assert "high_confidence_with_degraded_data" in {issue.code for issue in report.issues}


def test_degraded_safe_partial_ready_card_passes_without_timestamp():
    report = OutputQualityService().evaluate_decision_card(
        make_card(confidence_level="low", data_as_of=None),
        degrade_flags=["missing_market_data", "insufficient_evidence"],
    )
    assert report.passed


def test_assert_raises_with_actionable_message():
    with pytest.raises(ValueError, match="OUTPUT_QUALITY_FAILED"):
        OutputQualityService().assert_decision_card_passes(
            make_card(primary_risks="", supporting_evidence=[])
        )
