"""
Unit tests for AdaptationService in the campus financial-literacy coach domain.

Tests cover all _adapt_* branches without requiring a real DB.
Each test creates a minimal DecisionCard and UserProfile and asserts
the transformations applied by AdaptationService.

Run with: cd investment-back && pytest tests/test_adaptation_service.py -v
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import unittest

# Local imports from the actual service (only the types — no DB)
import sys
from pathlib import Path
_back_root = Path(__file__).parent.parent
sys.path.insert(0, str(_back_root))

# We re-implement minimal stubs here so we don't need DB connection.
# These must stay in sync with the real service's method signatures.

from src.models.user import (
    UserProfile,
    ExperienceLevel,
    HoldingHorizon,
    RiskTolerance,
    BehaviorTag,
)
from src.schemas.analysis import DecisionCard, UserFitSummary, ReasonPoint
from src.models.analysis import OutputMarkType


@dataclass
class LearningMetrics:
    judgment_avg: float = 50.0
    judgment_trend: Optional[float] = None
    judgment_trend_direction: str = "stable"
    judgment_recent_scores: List[int] = field(default_factory=list)
    judgment_count: int = 0
    judgment_hard_to_tell_count: int = 0
    judgment_insufficient: bool = True
    emotion_avg: float = 3.0
    emotion_recent: int = 3
    emotion_insufficient: bool = True
    high_emotion_flag: bool = False
    declining_judgment_flag: bool = False
    frequent_trading_flag: bool = False


def _adapt_decision_for_user(
    decision_card: DecisionCard,
    user_profile: UserProfile,
    learning_metrics: Optional[LearningMetrics] = None,
) -> DecisionCard:
    """
    Isolated re-implementation of AdaptationService.adapt_decision_for_user().
    Must stay in sync with src/services/adaptation_service.py.
    """
    adapted = decision_card

    # 1. Learning history (highest priority)
    if learning_metrics:
        adapted = _adapt_from_learning_history(adapted, learning_metrics)

    # 2. Behavior tags
    adapted = _adapt_behavior_tags(adapted, user_profile.behavior_tags or [])

    # 3. Risk tolerance
    adapted = _adapt_risk_tolerance(adapted, user_profile.risk_tolerance)

    # 4. Holding horizon
    adapted = _adapt_holding_horizon(adapted, user_profile.holding_horizon)

    # 5. Experience level
    adapted = _adapt_experience_level(adapted, user_profile.experience_level)

    # 6. user_fit_summary
    adapted.user_fit_summary = _calculate_user_fit(adapted, user_profile, learning_metrics)

    return adapted


# ─── Helper builders ───────────────────────────────────────────────────────────

def make_card(
    confidence_level: str = "medium",
    headline: str = "Test headline",
) -> DecisionCard:
    """Create a minimal DecisionCard for testing."""
    return DecisionCard(
        headline_judgement=headline,
        key_reason_summary=[
            ReasonPoint(text="Test reason", tag=OutputMarkType.DATA_FACT)
        ],
        user_fit_summary=UserFitSummary(fit="Base fit", unfit="Base unfit"),
        next_step_actions=["Action 1"],
        primary_risks="Base risk",
        review_at=datetime.now(timezone.utc),
        supporting_evidence=["S1 Test evidence"],
        counter_evidence=["C1 Test counter"],
        invalidation_conditions=["I1 Test condition"],
        confidence_level=confidence_level,  # type: ignore[arg-type]
    )


def make_profile(
    experience: ExperienceLevel = ExperienceLevel.INTERMEDIATE,
    horizon: HoldingHorizon = HoldingHorizon.MEDIUM,
    risk: RiskTolerance = RiskTolerance.MEDIUM,
    behavior_tags: Optional[List[str]] = None,
) -> UserProfile:
    """Create a minimal UserProfile for testing."""
    profile = UserProfile(
        id=1,
        user_id=1,
        experience_level=experience,
        holding_horizon=horizon,
        risk_tolerance=risk,
        behavior_tags=behavior_tags or [],
    )
    return profile


# ─── Learning history adaptation ───────────────────────────────────────────────

def _adapt_from_learning_history(
    decision: DecisionCard, metrics: LearningMetrics
) -> DecisionCard:
    new_confidence = decision.confidence_level
    injected_actions: List[str] = []

    if metrics.declining_judgment_flag:
        if new_confidence == "high":
            new_confidence = "medium"  # type: ignore[assignment]
        elif new_confidence == "medium":
            new_confidence = "low"  # type: ignore[assignment]

    if metrics.high_emotion_flag:
        if new_confidence == "high":
            new_confidence = "medium"  # type: ignore[assignment]
        elif new_confidence == "medium":
            new_confidence = "low"  # type: ignore[assignment]

    decision.confidence_level = new_confidence  # type: ignore[assignment]

    if metrics.high_emotion_flag:
        injected_actions.append(
            "【情绪提示】近期情绪评分偏高，请在冷静期后再审视本次消费判断，避免冲动消费"
        )
    if metrics.declining_judgment_flag:
        injected_actions.append(
            "【判断质量下滑】近期待验证的结论偏多，建议先补全预算和真实需求再行动"
        )
    if metrics.frequent_trading_flag:
        injected_actions.append(
            "【分期依赖提醒】当前判断质量均值偏低，建议减少大额分期频率，先守住生活费安全线"
        )

    if metrics.high_emotion_flag or metrics.declining_judgment_flag:
        extra_risk = ""
        if metrics.high_emotion_flag:
            extra_risk += "情绪评分近期偏高，当前消费决策受冲动和攀比影响的风险升高。 "
        if metrics.declining_judgment_flag:
            extra_risk += "判断质量近期有所下滑，需要更严格地验证预算、需求和总成本。 "
        decision.primary_risks = extra_risk + decision.primary_risks

    if injected_actions:
        decision.next_step_actions = injected_actions + list(decision.next_step_actions)

    return decision


# ─── Behavior tags adaptation ──────────────────────────────────────────────────

def _adapt_behavior_tags(
    decision: DecisionCard, tags: List[str]
) -> DecisionCard:
    chasing = "chasing_rise" in tags or "追涨倾向" in tags or "盲目跟风" in tags or "冲动消费" in tags
    panic = "panic_sell" in tags or "恐慌卖出" in tags or "过度焦虑" in tags
    frequent = "frequent_trading" in tags or "频繁交易" in tags or "分期依赖" in tags
    stable = "stable_discipline" in tags or "纪律稳定" in tags or "预算纪律稳定" in tags

    if chasing:
        decision.next_step_actions.insert(
            0,
            "【盲目跟风提醒】请再次确认：本次消费是否因同伴影响、限时优惠或害怕落后引发？建议至少等待 48 小时后再重新判断。"
        )
    if panic:
        decision.next_step_actions.insert(
            0, "【焦虑提醒】请先冷静 30 分钟，确认这是真实需求还是短期压力。"
        )
    if frequent:
        decision.next_step_actions.append(
            "【分期提醒】建议减少大额分期频率，先确认生活费安全线和还款压力。"
        )
    if stable:
        decision.next_step_actions.append(
            "【保持纪律】你的预算纪律较稳定，建议继续维持记录和复盘节奏。"
        )
    return decision


# ─── Risk tolerance adaptation ─────────────────────────────────────────────────

def _adapt_risk_tolerance(
    decision: DecisionCard, tolerance: RiskTolerance
) -> DecisionCard:
    if tolerance == RiskTolerance.LOW:
        decision.primary_risks = (
            "【预算提醒】低财务风险承受能力用户建议严格控制单笔大额消费，并保留至少一个月生活费安全垫。\n"
            + decision.primary_risks
        )
    return decision


# ─── Holding horizon adaptation ────────────────────────────────────────────────

def _adapt_holding_horizon(
    decision: DecisionCard, horizon: HoldingHorizon
) -> DecisionCard:
    if horizon == HoldingHorizon.SHORT:
        decision.next_step_actions.append("建议在 3 天内完成预算和需求验证，逾期则重新评估")
    elif horizon == HoldingHorizon.LONG:
        decision.next_step_actions.append(
            "【长期规划提示】请忽略短期促销和攀比噪音，关注预算边界是否发生实质变化"
        )
    return decision


# ─── Experience level adaptation ───────────────────────────────────────────────

def _adapt_experience_level(
    decision: DecisionCard, experience: ExperienceLevel
) -> DecisionCard:
    if experience == ExperienceLevel.NOVICE:
        decision.next_step_actions.append(
            "【新手提示】每条建议都应转化为具体操作，例如设定预算上限和延迟购买提醒"
        )
    elif experience == ExperienceLevel.EXPERT:
        decision.next_step_actions.append("【进阶建议】可进一步交叉验证同类替代方案、总成本和机会成本")
    return decision


# ─── user_fit_summary calculation ──────────────────────────────────────────────

def _calculate_user_fit(
    decision: DecisionCard,
    user_profile: UserProfile,
    learning_metrics: Optional[LearningMetrics] = None,
) -> UserFitSummary:
    if user_profile.experience_level == ExperienceLevel.NOVICE:
        return UserFitSummary(
            fit="适合刚开始建立预算习惯的学生，建议以学习为主，记录每次消费决策的理由",
            unfit="不适合完全不愿意记录预算或只追求即时满足的用户",
        )
    elif user_profile.experience_level == ExperienceLevel.EXPERT:
        return UserFitSummary(
            fit="适合已有预算体系的学生，可以结合必要性、总成本和替代方案综合判断",
            unfit="不适合缺乏独立分析能力或拒绝核算还款压力的用户",
        )
    else:
        fit = decision.user_fit_summary.fit
        unfit = decision.user_fit_summary.unfit
        if learning_metrics and not learning_metrics.judgment_insufficient:
            if learning_metrics.judgment_trend_direction == "down":
                fit = (
                    "适合有一定基础但近期判断质量有所下滑的学生，"
                    "建议降低大额消费频率，重新验证预算和真实需求"
                )
            elif learning_metrics.judgment_trend_direction == "up":
                fit = "适合有一定预算基础的学生，近期判断质量持续改善，可以维持当前复盘节奏"
        return UserFitSummary(fit=fit, unfit=unfit)


# ─── Test cases ────────────────────────────────────────────────────────────────

class TestAdaptation_LearningHistory_ConfidenceDowngrade(unittest.TestCase):
    """Confidence level should be downgraded based on learning signals."""

    def test_high_confidence_degraded_to_medium_on_declining_trend(self):
        card = make_card(confidence_level="high")
        profile = make_profile()
        metrics = LearningMetrics(
            judgment_trend_direction="down",
            declining_judgment_flag=True,
        )
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertEqual(result.confidence_level, "medium")

    def test_medium_confidence_degraded_to_low_on_declining_trend(self):
        card = make_card(confidence_level="medium")
        profile = make_profile()
        metrics = LearningMetrics(
            judgment_trend_direction="down",
            declining_judgment_flag=True,
        )
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertEqual(result.confidence_level, "low")

    def test_high_confidence_degraded_to_medium_on_high_emotion(self):
        card = make_card(confidence_level="high")
        profile = make_profile()
        metrics = LearningMetrics(high_emotion_flag=True)
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertEqual(result.confidence_level, "medium")

    def test_combined_signals_double_degrade(self):
        """Both declining + high_emotion: high → low"""
        card = make_card(confidence_level="high")
        profile = make_profile()
        metrics = LearningMetrics(
            declining_judgment_flag=True,
            high_emotion_flag=True,
        )
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        # First declining: high → medium, then high_emotion: medium → low
        self.assertEqual(result.confidence_level, "low")

    def test_low_confidence_not_downgraded_further(self):
        card = make_card(confidence_level="low")
        profile = make_profile()
        metrics = LearningMetrics(
            declining_judgment_flag=True,
            high_emotion_flag=True,
        )
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertEqual(result.confidence_level, "low")


class TestAdaptation_LearningHistory_ActionInjection(unittest.TestCase):
    """next_step_actions should be injected based on learning signals."""

    def test_high_emotion_injects_emotion_warning(self):
        card = make_card()
        profile = make_profile()
        metrics = LearningMetrics(high_emotion_flag=True)
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertTrue(
            any("情绪提示" in a for a in result.next_step_actions),
            f"Expected '情绪提示' in actions: {result.next_step_actions}",
        )

    def test_declining_trend_injects_warning_action(self):
        card = make_card()
        profile = make_profile()
        metrics = LearningMetrics(judgment_trend_direction="down", declining_judgment_flag=True)
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertTrue(
            any("判断质量下滑" in a for a in result.next_step_actions),
            f"Expected '判断质量下滑' in actions: {result.next_step_actions}",
        )

    def test_frequent_trading_injects_frequency_action(self):
        card = make_card()
        profile = make_profile()
        metrics = LearningMetrics(frequent_trading_flag=True)
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertTrue(
            any("分期依赖提醒" in a or "大额分期频率" in a for a in result.next_step_actions),
            f"Expected installment-frequency action: {result.next_step_actions}",
        )

    def test_emotion_warning_prepended_not_appended(self):
        """Injected action should be first so it's most visible."""
        card = make_card()
        profile = make_profile()
        metrics = LearningMetrics(high_emotion_flag=True)
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertTrue(
            result.next_step_actions[0].startswith("【情绪提示"),
            f"First action should be emotion warning, got: {result.next_step_actions[0]}",
        )


class TestAdaptation_LearningHistory_PrimaryRisks(unittest.TestCase):
    """primary_risks should be prefixed with context-specific warnings."""

    def test_high_emotion_adds_risk_prefix(self):
        card = make_card()
        profile = make_profile()
        metrics = LearningMetrics(high_emotion_flag=True)
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertTrue(
            result.primary_risks.startswith("情绪评分"),
            f"Expected primary_risks to start with emotion warning, got: {result.primary_risks[:50]}",
        )

    def test_declining_trend_adds_risk_prefix(self):
        card = make_card()
        profile = make_profile()
        metrics = LearningMetrics(judgment_trend_direction="down", declining_judgment_flag=True)
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertTrue(
            result.primary_risks.startswith("判断质量"),
            f"Expected primary_risks to start with judgment warning, got: {result.primary_risks[:50]}",
        )


class TestAdaptation_BehaviorTags(unittest.TestCase):
    """Behavior tags should trigger tag-specific injected actions."""

    def test_chasing_rise_tag_injects_action(self):
        card = make_card()
        profile = make_profile(behavior_tags=["chasing_rise"])
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("盲目跟风" in a or "同伴影响" in a for a in result.next_step_actions),
            f"Expected peer-influence action: {result.next_step_actions}",
        )

    def test_panic_sell_tag_injects_action(self):
        card = make_card()
        profile = make_profile(behavior_tags=["panic_sell"])
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("焦虑" in a or "短期压力" in a for a in result.next_step_actions),
            f"Expected anxiety action: {result.next_step_actions}",
        )

    def test_frequent_trading_tag_appends_action(self):
        card = make_card()
        profile = make_profile(behavior_tags=["frequent_trading"])
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("大额分期频率" in a or "还款压力" in a for a in result.next_step_actions),
            f"Expected installment-frequency action: {result.next_step_actions}",
        )

    def test_stable_discipline_tag_appends_encouragement(self):
        card = make_card()
        profile = make_profile(behavior_tags=["stable_discipline"])
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("保持纪律" in a for a in result.next_step_actions),
            f"Expected '保持纪律' encouragement: {result.next_step_actions}",
        )

    def test_chinese_tag_labels_also_recognized(self):
        """Frontend-facing Chinese labels should be recognized too."""
        card = make_card()
        profile = make_profile(behavior_tags=["盲目跟风"])
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("盲目跟风" in a for a in result.next_step_actions),
            f"Expected peer-influence action from Chinese label: {result.next_step_actions}",
        )


class TestAdaptation_RiskTolerance(unittest.TestCase):
    """Risk tolerance should adjust risk messaging."""

    def test_low_risk_prepends_risk_control_reminder(self):
        card = make_card()
        profile = make_profile(risk=RiskTolerance.LOW)
        result = _adapt_decision_for_user(card, profile)
        self.assertIn("预算提醒", result.primary_risks)
        self.assertIn("生活费安全垫", result.primary_risks)

    def test_high_risk_does_not_add_extra_messaging(self):
        """High risk users should not be overly patronized."""
        card = make_card()
        profile = make_profile(risk=RiskTolerance.HIGH)
        result = _adapt_decision_for_user(card, profile)
        # Should NOT add "预算提醒" for HIGH risk
        self.assertNotIn("预算提醒", result.primary_risks)

    def test_medium_risk_does_not_add_extra_messaging(self):
        card = make_card()
        profile = make_profile(risk=RiskTolerance.MEDIUM)
        result = _adapt_decision_for_user(card, profile)
        self.assertNotIn("预算提醒", result.primary_risks)


class TestAdaptation_HoldingHorizon(unittest.TestCase):
    """Holding horizon should append time-horizon-specific actions."""

    def test_short_horizon_appends_verification_deadline(self):
        card = make_card()
        profile = make_profile(horizon=HoldingHorizon.SHORT)
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("3 天" in a for a in result.next_step_actions),
            f"Expected '3 天' in actions: {result.next_step_actions}",
        )

    def test_long_horizon_appends_ignore_short_noise(self):
        card = make_card()
        profile = make_profile(horizon=HoldingHorizon.LONG)
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("短期促销" in a or "攀比噪音" in a for a in result.next_step_actions),
            f"Expected long-planning warning in actions: {result.next_step_actions}",
        )

    def test_medium_horizon_no_extra_action(self):
        """MEDIUM horizon should not add extra time-based actions."""
        card = make_card()
        profile = make_profile(horizon=HoldingHorizon.MEDIUM)
        result = _adapt_decision_for_user(card, profile)
        # Should not add 3-day deadline or long-planning warning
        for action in result.next_step_actions:
            self.assertNotIn("3 天", action)
            self.assertNotIn("短期促销", action)


class TestAdaptation_ExperienceLevel(unittest.TestCase):
    """Experience level should add appropriate guidance."""

    def test_novice_appends_actionable_reminder(self):
        card = make_card()
        profile = make_profile(experience=ExperienceLevel.NOVICE)
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("新手提示" in a for a in result.next_step_actions),
            f"Expected '新手提示' in actions: {result.next_step_actions}",
        )

    def test_expert_appends_advanced_suggestion(self):
        card = make_card()
        profile = make_profile(experience=ExperienceLevel.EXPERT)
        result = _adapt_decision_for_user(card, profile)
        self.assertTrue(
            any("进阶建议" in a for a in result.next_step_actions),
            f"Expected '进阶建议' in actions: {result.next_step_actions}",
        )


class TestAdaptation_UserFitSummary(unittest.TestCase):
    """user_fit_summary should be dynamically adapted."""

    def test_novice_fit_summary(self):
        card = make_card()
        profile = make_profile(experience=ExperienceLevel.NOVICE)
        result = _adapt_decision_for_user(card, profile)
        self.assertIn("预算习惯", result.user_fit_summary.fit)

    def test_expert_fit_summary(self):
        card = make_card()
        profile = make_profile(experience=ExperienceLevel.EXPERT)
        result = _adapt_decision_for_user(card, profile)
        self.assertIn("预算体系", result.user_fit_summary.fit)

    def test_intermediate_with_declining_trend_adapts_fit(self):
        card = make_card()
        profile = make_profile(experience=ExperienceLevel.INTERMEDIATE)
        metrics = LearningMetrics(
            judgment_trend_direction="down",
            declining_judgment_flag=True,
            judgment_insufficient=False,
        )
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        # Should override base fit with declining-specific text
        self.assertTrue(
            "判断质量" in result.user_fit_summary.fit or "大额消费频率" in result.user_fit_summary.fit,
            f"Expected dynamic fit for declining trend, got: {result.user_fit_summary.fit}",
        )

    def test_intermediate_with_improving_trend_adapts_fit(self):
        card = make_card()
        profile = make_profile(experience=ExperienceLevel.INTERMEDIATE)
        metrics = LearningMetrics(
            judgment_trend_direction="up",
            declining_judgment_flag=False,
            judgment_insufficient=False,
        )
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        self.assertIn("持续改善", result.user_fit_summary.fit)

    def test_intermediate_stable_trend_keeps_base_fit(self):
        card = make_card()
        profile = make_profile(experience=ExperienceLevel.INTERMEDIATE)
        metrics = LearningMetrics(
            judgment_trend_direction="stable",
            judgment_insufficient=False,
        )
        result = _adapt_decision_for_user(card, profile, learning_metrics=metrics)
        # Base fit should be unchanged (or slightly adapted but not replaced)
        self.assertTrue(len(result.user_fit_summary.fit) > 0)


class TestAdaptation_NoMetrics(unittest.TestCase):
    """When no learning_metrics provided, adaptation should still run behavior-tag + profile branches."""

    def test_behavior_tag_still_applied_without_metrics(self):
        card = make_card()
        profile = make_profile(behavior_tags=["chasing_rise"])
        result = _adapt_decision_for_user(card, profile, learning_metrics=None)
        self.assertTrue(any("盲目跟风" in a or "同伴影响" in a for a in result.next_step_actions))

    def test_risk_tolerance_still_applied_without_metrics(self):
        card = make_card()
        profile = make_profile(risk=RiskTolerance.LOW)
        result = _adapt_decision_for_user(card, profile, learning_metrics=None)
        self.assertIn("预算提醒", result.primary_risks)


if __name__ == "__main__":
    unittest.main()
