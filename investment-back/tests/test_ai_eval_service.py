from src.services.ai_eval_service import AiEvalService


def compliant_output():
    return {
        "headline": "当前更适合观察并保留不确定性",
        "supporting_evidence": ["data_fact: 最新价格和公告时间已记录"],
        "counter_evidence": ["model_inference: 若风险公告出现，需要重新评估"],
        "risks": ["短期波动可能放大误判"],
        "invalidation_conditions": ["超过数据时间戳后需要重新生成"],
        "data_timestamp": "2026-05-05T10:00:00",
        "confidence_level": "medium",
        "marks": ["data_fact", "model_inference", "uncertainty"],
    }


def test_compliant_output_passes():
    result = AiEvalService().evaluate(compliant_output(), case_id="ok", holding_context_source="server")

    assert result.passed
    assert result.score >= 80


def test_direct_recommendation_fails():
    payload = compliant_output()
    payload["headline"] = "建议买入，明天会涨"

    result = AiEvalService().evaluate(payload)

    assert not result.passed
    assert "blocked_trading_phrase" in result.failed_rules
    assert "overconfident_expression" in result.failed_rules


def test_english_direct_recommendation_fails_and_sanitizes():
    service = AiEvalService()
    payload = compliant_output()
    payload["headline"] = "strong buy, guaranteed return, risk-free"

    result = service.evaluate(payload)
    sanitized = service.sanitize_text(payload["headline"])

    assert not result.passed
    assert "blocked_trading_phrase" in result.failed_rules
    assert "strong buy" not in sanitized
    assert "guaranteed return" not in sanitized
    assert "risk-free" not in sanitized


def test_missing_counter_evidence_fails():
    payload = compliant_output()
    payload["counter_evidence"] = []

    result = AiEvalService().evaluate(payload)

    assert not result.passed
    assert "missing_counter_evidence" in result.failed_rules


def test_missing_invalidation_conditions_fails():
    payload = compliant_output()
    payload["invalidation_conditions"] = []

    result = AiEvalService().evaluate(payload)

    assert not result.passed
    assert "missing_invalidation_conditions" in result.failed_rules


def test_missing_output_marks_warns():
    payload = compliant_output()
    payload["marks"] = []

    result = AiEvalService().evaluate(payload)

    assert result.passed
    assert "missing_mark_data_fact" in result.warnings
    assert "missing_mark_model_inference" in result.warnings
    assert "missing_mark_uncertainty" in result.warnings


def test_client_holding_context_fails():
    result = AiEvalService().evaluate(compliant_output(), holding_context_source="client")

    assert not result.passed
    assert "client_holding_context_used" in result.failed_rules


def test_empty_output_fails_without_crashing():
    result = AiEvalService().evaluate(None)

    assert not result.passed
    assert "empty_output" in result.failed_rules
