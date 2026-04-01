from typing import Optional, Dict, Any, List
from src.models.user import (
    UserProfile,
    ExperienceLevel,
    HoldingHorizon,
    RiskTolerance,
    BehaviorTag
)
from src.schemas.analysis import DecisionCard, UserFitSummary
import structlog

logger = structlog.get_logger()

class AdaptationService:
    """用户适配服务"""

    def __init__(self):
        self.logger = logger.bind(service="adaptation")

    def adapt_decision_for_user(
        self,
        decision_card: DecisionCard,
        user_profile: UserProfile
    ) -> DecisionCard:
        """
        为特定用户适配决策卡片
        """
        self.logger.info("adapting_decision", user_profile=str(user_profile))

        # 基础适配
        adapted = self._adapt_experience_level(decision_card, user_profile.experience_level)
        adapted = self._adapt_holding_horizon(adapted, user_profile.holding_horizon)
        adapted = self._adapt_risk_tolerance(adapted, user_profile.risk_tolerance)
        adapted = self._adapt_behavior_tags(adapted, user_profile.behavior_tags)

        # 重新计算用户适配摘要
        adapted.user_fit_summary = self._calculate_user_fit(adapted, user_profile)

        self.logger.debug("adaptation_completed")
        return adapted

    def _adapt_experience_level(
        self, decision: DecisionCard, experience: ExperienceLevel
    ) -> DecisionCard:
        """
        根据用户经验水平适配决策
        - 新手: 更详细的解释，更严格的风险提示
        - 中级: 平衡的建议
        - 专家: 更简洁的信息，更多的技术细节
        """
        # 目前我们保持原样，但可以根据经验水平调整理由和建议的详细程度
        return decision

    def _adapt_holding_horizon(
        self, decision: DecisionCard, horizon: HoldingHorizon
    ) -> DecisionCard:
        """
        根据用户持有周期适配决策
        - 短期: 更多关注技术面和短期信号
        - 中期: 平衡的基本面和技术面分析
        - 长期: 更多关注基本面和长期趋势
        """
        return decision

    def _adapt_risk_tolerance(
        self, decision: DecisionCard, tolerance: RiskTolerance
    ) -> DecisionCard:
        """
        根据用户风险承受能力适配决策
        - 低风险: 更保守的建议，强调安全边际
        - 中风险: 平衡的风险收益
        - 高风险: 更进取的建议，接受更高波动性
        """
        return decision

    def _adapt_behavior_tags(
        self, decision: DecisionCard, tags: List[BehaviorTag]
    ) -> DecisionCard:
        """
        根据用户行为标签适配决策
        """
        # 为有特定行为倾向的用户添加额外建议
        if BehaviorTag.CHASING_RISE in tags:
            self.logger.info("adapting_for_chasing_rise")
            decision.primary_risks = (
                "当前市场处于高波动阶段，您可能存在追涨倾向。"
                "建议严格控制仓位，设定明确的止损点。\n"
                + decision.primary_risks
            )
            decision.next_step_actions.insert(
                0, "请再次确认是否因短期涨幅引发了买入冲动"
            )
        elif BehaviorTag.PANIC_SELL in tags:
            self.logger.info("adapting_for_panic_sell")
            decision.primary_risks = (
                "您可能存在恐慌卖出倾向。当前市场波动可能是短期的。"
                "建议等待明确信号再行动。\n"
                + decision.primary_risks
            )
            decision.next_step_actions.insert(
                0, "请先冷静10分钟，重新评估市场情况"
            )
        elif BehaviorTag.FREQUENT_TRADING in tags:
            self.logger.info("adapting_for_frequent_trading")
            decision.next_step_actions.append(
                "建议减少交易频率，避免频繁换股导致的摩擦成本"
            )

        return decision

    def _calculate_user_fit(
        self, decision: DecisionCard, user_profile: UserProfile
    ) -> UserFitSummary:
        """
        计算用户适配性摘要
        """
        base_fit = decision.user_fit_summary

        # 根据用户属性调整适配性描述
        if user_profile.experience_level == ExperienceLevel.NOVICE:
            fit = "适合初学者，建议以学习为主，控制仓位"
            unfit = "不适合缺乏经验且追求快速收益的投资者"
        elif user_profile.experience_level == ExperienceLevel.EXPERT:
            fit = "适合有体系的投资者，可以根据技术面和基本面综合判断"
            unfit = "不适合缺乏独立分析能力的投资者"
        else:
            fit = base_fit.fit
            unfit = base_fit.unfit

        return UserFitSummary(fit=fit, unfit=unfit)

    def generate_adaptation_report(self, user_profile: UserProfile) -> Dict[str, Any]:
        """
        生成用户适配报告
        """
        report = {
            "profile": {
                "experience": user_profile.experience_level.value,
                "holding_horizon": user_profile.holding_horizon.value,
                "risk_tolerance": user_profile.risk_tolerance.value,
                "behavior_tags": [tag.value for tag in user_profile.behavior_tags]
            },
            "adaptation_strategy": self._determine_strategy(user_profile)
        }

        return report

    def _determine_strategy(self, profile: UserProfile) -> str:
        """
        根据用户画像确定适配策略
        """
        if (
            profile.experience_level == ExperienceLevel.NOVICE
            and profile.risk_tolerance == RiskTolerance.LOW
        ):
            return "保守策略：强调风险控制，建议低仓位参与"
        elif (
            profile.experience_level == ExperienceLevel.EXPERT
            and profile.risk_tolerance == RiskTolerance.HIGH
            and profile.holding_horizon == HoldingHorizon.LONG
        ):
            return "积极策略：关注长期价值，接受短期波动"
        else:
            return "平衡策略：综合考虑风险和收益，建议适度参与"
