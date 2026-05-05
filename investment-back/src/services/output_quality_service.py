from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from src.schemas.analysis import DecisionCard


BLOCKED_TRADING_PHRASES = (
    "必须买",
    "必须买入",
    "建议买入",
    "建议卖出",
    "可以买入",
    "可以卖出",
    "可以重仓",
    "赶紧买",
    "赶紧卖",
    "赶紧卖出",
    "必须卖",
    "必须卖出",
    "明天一定涨",
    "明天会涨",
    "一定会涨",
    "稳赚",
    "目标收益",
    "跟着买",
    "抄底机会",
    "强烈推荐",
    "自动调仓",
    "自动交易",
    "无风险",
    "buy now",
    "sell now",
    "strong buy",
    "strong sell",
    "guaranteed return",
    "guaranteed profit",
    "risk-free",
    "target return",
    "follow me to buy",
    "auto trade",
)

SAFE_DEGRADED_ACTION_WORDS = (
    "观察",
    "等待",
    "补充",
    "重试",
    "重新",
    "复盘",
    "暂停",
    "复核",
    "评估",
)

DEGRADE_FLAGS_REQUIRE_LOW_CONFIDENCE = {
    "missing_market_data",
    "missing_announcements",
    "insufficient_evidence",
}


@dataclass
class OutputQualityIssue:
    code: str
    message: str


@dataclass
class OutputQualityReport:
    passed: bool
    issues: list[OutputQualityIssue] = field(default_factory=list)


class OutputQualityService:
    """Deterministic output quality checks for investment decision cards."""

    def evaluate_decision_card(
        self,
        decision_card: DecisionCard,
        *,
        degrade_flags: Iterable[str] | None = None,
    ) -> OutputQualityReport:
        flags = set(degrade_flags or [])
        issues: list[OutputQualityIssue] = []
        all_text = self._collect_text(decision_card)

        for phrase in BLOCKED_TRADING_PHRASES:
            if phrase in all_text:
                issues.append(OutputQualityIssue(
                    code="direct_trading_instruction",
                    message=f"Output contains a direct or deterministic trading expression: {phrase}",
                ))

        if not decision_card.supporting_evidence:
            issues.append(OutputQualityIssue("missing_supporting_evidence", "Missing supporting evidence"))
        if not decision_card.counter_evidence:
            issues.append(OutputQualityIssue("missing_counter_evidence", "Missing counter evidence"))
        if not decision_card.invalidation_conditions:
            issues.append(OutputQualityIssue("missing_invalidation_conditions", "Missing invalidation conditions"))
        if decision_card.confidence_level not in {"low", "medium", "high"}:
            issues.append(OutputQualityIssue("invalid_confidence_level", "Invalid confidence level"))
        if not decision_card.primary_risks.strip():
            issues.append(OutputQualityIssue("missing_primary_risks", "Missing primary risks"))

        if not flags and decision_card.data_as_of is None:
            issues.append(OutputQualityIssue("missing_data_as_of", "Complete result is missing data timestamp"))

        if flags & DEGRADE_FLAGS_REQUIRE_LOW_CONFIDENCE and decision_card.confidence_level == "high":
            issues.append(OutputQualityIssue(
                "high_confidence_with_degraded_data",
                "High confidence is not allowed when data or evidence is degraded",
            ))

        if flags:
            action_text = " ".join(decision_card.next_step_actions)
            if not any(word in action_text for word in SAFE_DEGRADED_ACTION_WORDS):
                issues.append(OutputQualityIssue(
                    "unsafe_degraded_next_actions",
                    "Degraded next actions must stay within observation, waiting, evidence collection, retry, reassessment, or review",
                ))

        return OutputQualityReport(passed=not issues, issues=issues)

    def assert_decision_card_passes(
        self,
        decision_card: DecisionCard,
        *,
        degrade_flags: Iterable[str] | None = None,
    ) -> None:
        report = self.evaluate_decision_card(decision_card, degrade_flags=degrade_flags)
        if report.passed:
            return
        details = "; ".join(f"{issue.code}: {issue.message}" for issue in report.issues)
        raise ValueError(f"OUTPUT_QUALITY_FAILED: {details}")

    def _collect_text(self, decision_card: DecisionCard) -> str:
        parts: list[str] = [
            decision_card.headline_judgement,
            decision_card.primary_risks,
            *decision_card.next_step_actions,
            *decision_card.supporting_evidence,
            *decision_card.counter_evidence,
            *decision_card.invalidation_conditions,
            decision_card.user_fit_summary.fit,
            decision_card.user_fit_summary.unfit,
        ]
        parts.extend(reason.text for reason in decision_card.key_reason_summary)
        return "\n".join(part for part in parts if part)
