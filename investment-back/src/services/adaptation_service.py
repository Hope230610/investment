from typing import TYPE_CHECKING, List, Optional, Dict, Any

from src.models.user import (
    UserProfile,
    ExperienceLevel,
    HoldingHorizon,
    RiskTolerance,
    BehaviorTag
)
from src.schemas.analysis import DecisionCard, UserFitSummary
import structlog

if TYPE_CHECKING:
    from src.services.learning_service import LearningMetrics


logger = structlog.get_logger()


class AdaptationService:
    """用户适配服务

    基于用户画像快照 + 学习历史聚合指标，对生成的决策卡进行个性化调整。
    """

    def __init__(self):
        self.logger = logger.bind(service="adaptation")

    def adapt_decision_for_user(
        self,
        decision_card: DecisionCard,
        user_profile: UserProfile,
        learning_metrics: Optional["LearningMetrics"] = None,
    ) -> DecisionCard:
        """
        为特定用户适配决策卡片。

        调整优先级（从高到低）：
        1. 学习历史信号（judgment trend / emotion level）—— 最高优先
        2. 行为标签（chasing_rise / panic_sell / frequent_trading）
        3. 风险承受偏好
        4. 持有周期
        5. 经验水平
        """
        self.logger.info(
            "adapting_decision",
            user_id=user_profile.user_id if hasattr(user_profile, "user_id") else None,
            behavior_tags=user_profile.behavior_tags,
            has_learning_metrics=learning_metrics is not None,
        )

        adapted = decision_card

        # 1. 学习历史信号（最高优先）
        if learning_metrics:
            adapted = self._adapt_from_learning_history(adapted, learning_metrics)

        # 2. 行为标签
        adapted = self._adapt_behavior_tags(adapted, user_profile.behavior_tags or [])

        # 3. 风险承受偏好
        adapted = self._adapt_risk_tolerance(adapted, user_profile.risk_tolerance)

        # 4. 持有周期（调整 next_step_actions 时间维度）
        adapted = self._adapt_holding_horizon(adapted, user_profile.holding_horizon)

        # 5. 经验水平
        adapted = self._adapt_experience_level(adapted, user_profile.experience_level)

        # 6. 重新计算用户适配摘要
        adapted.user_fit_summary = self._calculate_user_fit(
            adapted, user_profile, learning_metrics
        )

        self.logger.debug("adaptation_completed")
        return adapted

    # ─── 学习历史适配（最高优先）───────────────────────────────────────────────

    def _adapt_from_learning_history(
        self, decision: DecisionCard, metrics: "LearningMetrics"
    ) -> DecisionCard:
        """
        基于判断质量趋势和情绪状态调整决策卡。

        规则：
        - 情绪偏高（>= 4）：在 next_step_actions 前插入"冷静"建议
        - 判断质量下滑：降低 confidence_level 并前置风险提示
        - 判断质量极低 + 记录多：提示频繁交易风险
        """
        # ① confidence_level 下调规则
        new_confidence = decision.confidence_level

        if metrics.declining_judgment_flag:
            # 判断质量近期下滑 → 降一档
            if new_confidence == "high":
                new_confidence = "medium"
            elif new_confidence == "medium":
                new_confidence = "low"
            self.logger.info("confidence_downscaled_judgment_trend_down")

        if metrics.high_emotion_flag:
            # 情绪偏高 → 额外降一档（情绪化决策置信度不可高）
            if new_confidence == "high":
                new_confidence = "medium"
            elif new_confidence == "medium":
                new_confidence = "low"
            self.logger.info("confidence_downscaled_high_emotion")

        if new_confidence != decision.confidence_level:
            # Pydantic model — recreate to update field
            decision.confidence_level = new_confidence  # type: ignore[assignment]

        # ② next_step_actions 动态插入
        injected_actions: List[str] = []

        if metrics.high_emotion_flag:
            injected_actions.append(
                "【情绪提示】近期情绪评分偏高，请在冷静后再审视本次判断，避免情绪化决策"
            )

        if metrics.declining_judgment_flag:
            injected_actions.append(
                "【判断质量下滑】近期待验证的结论偏多，建议先等待信号确认再行动"
            )

        if metrics.frequent_trading_flag:
            injected_actions.append(
                "【交易频率偏高】当前判断质量均值偏低，建议降低交易频率，等信号更清晰再操作"
            )

        # ③ primary_risks 前置警告（情绪/判断质量问题时加重提示）
        if metrics.high_emotion_flag or metrics.declining_judgment_flag:
            extra_risk = ""
            if metrics.high_emotion_flag:
                extra_risk += "情绪评分近期偏高，当前决策受情绪影响的风险升高。 "
            if metrics.declining_judgment_flag:
                extra_risk += "判断质量近期有所下滑，历史判断错误率上升，需要更严格的验证标准。 "
            decision.primary_risks = extra_risk + decision.primary_risks

        # 将注入动作插入到 next_step_actions 最前
        if injected_actions:
            decision.next_step_actions = injected_actions + list(decision.next_step_actions)

        return decision

    # ─── 行为标签适配 ─────────────────────────────────────────────────────────

    def _adapt_behavior_tags(
        self, decision: DecisionCard, tags: List[str]
    ) -> DecisionCard:
        """
        根据用户行为标签追加针对性建议。

        与 _adapt_from_learning_history 的区别：
        - learning history：来自复盘反馈的客观聚合数据
        - behavior_tags：系统推断或用户确认的行为标签，更直接
        """
        tags_str = [t.value if isinstance(t, BehaviorTag) else t for t in tags]

        chasing = "chasing_rise" in tags_str or "追涨倾向" in tags_str
        panic = "panic_sell" in tags_str or "恐慌卖出" in tags_str
        frequent = "frequent_trading" in tags_str or "频繁交易" in tags_str
        stable = "stable_discipline" in tags_str or "纪律稳定" in tags_str

        if chasing:
            self.logger.info("adapting_for_chasing_rise_tag")
            decision.next_step_actions.insert(
                0,
                "【追涨提醒】请再次确认：本次判断是否因短期涨幅引发买入冲动？"
                "建议与前次判断间隔至少 2 个交易日。",
            )

        if panic:
            self.logger.info("adapting_for_panic_sell_tag")
            decision.next_step_actions.insert(
                0,
                "【恐慌提醒】请先冷静 10 分钟，确认下跌是否已触及基本面变化。",
            )

        if frequent:
            self.logger.info("adapting_for_frequent_trading_tag")
            decision.next_step_actions.append(
                "【频率提醒】建议减少换手频率，等待已有持仓信号验证后再考虑新操作。"
            )

        if stable:
            self.logger.info("adapting_for_stable_discipline_tag")
            # 纪律稳定用户不需要额外干预，追加一条强化鼓励
            decision.next_step_actions.append(
                "【保持纪律】您的历史判断质量稳定，建议继续维持当前节奏。"
            )

        return decision

    # ─── 风险承受偏好 ─────────────────────────────────────────────────────────

    def _adapt_risk_tolerance(
        self, decision: DecisionCard, tolerance: RiskTolerance
    ) -> DecisionCard:
        """
        根据风险承受偏好调整 primary_risks 权重和 next_step_actions 措辞。

        - LOW：加重风险措辞，强调止损边界
        - HIGH：适度降低保守提示，避免过度干预
        """
        if tolerance == RiskTolerance.LOW:
            if not decision.primary_risks.startswith("【风控提醒】"):
                decision.primary_risks = (
                    "【风控提醒】低风险偏好用户建议严格控制单笔仓位不超过总仓位的 20%，"
                    "并设定明确的止损边界。\n" + decision.primary_risks
                )
            # 低风险用户：确保止损建议在首位
            stop_loss_action = "建议设定止损线，明确失效边界后再决定是否操作"
            if stop_loss_action not in decision.next_step_actions:
                decision.next_step_actions.insert(
                    0 if len(decision.next_step_actions) < 2 else 1,
                    stop_loss_action,
                )

        elif tolerance == RiskTolerance.HIGH:
            # 高风险用户：不过度干预，但保留失效条件
            self.logger.debug("high_risk_tolerance_no_intervention")
            pass  # 不追加额外内容，避免过度干预

        return decision

    # ─── 持有周期 ─────────────────────────────────────────────────────────────

    def _adapt_holding_horizon(
        self, decision: DecisionCard, horizon: HoldingHorizon
    ) -> DecisionCard:
        """
        根据持有周期调整 next_step_actions 的时间维度。

        - SHORT：强调短期信号验证、止损
        - MEDIUM：平衡短期信号与中期逻辑
        - LONG：强调基本面验证、避免短期噪音干扰
        """
        if horizon == HoldingHorizon.SHORT:
            # 短期用户：追加短期验证建议（如果还没有的话）
            short_action = "建议在 3 个交易日内完成信号验证，逾期则重新评估"
            if short_action not in decision.next_step_actions:
                decision.next_step_actions.append(short_action)

        elif horizon == HoldingHorizon.LONG:
            # 长期用户：追加忽略短期噪音的建议
            long_action = (
                "【长期投资者提示】请忽略短期噪音，关注基本面逻辑是否发生实质变化"
            )
            if long_action not in decision.next_step_actions:
                decision.next_step_actions.append(long_action)

        return decision

    # ─── 经验水平 ─────────────────────────────────────────────────────────────

    def _adapt_experience_level(
        self, decision: DecisionCard, experience: ExperienceLevel
    ) -> DecisionCard:
        """
        根据经验水平调整 next_step_actions 的详细程度。

        - NOVICE：确保每条建议都是可执行的（不是抽象原则）
        - EXPERT：追加进阶验证步骤
        """
        if experience == ExperienceLevel.NOVICE:
            novice_action = (
                "【新手提示】每条建议都应转化为具体操作，例如设定价格提醒、"
                "写下本次判断的理由、设置复盘时间"
            )
            if novice_action not in decision.next_step_actions:
                decision.next_step_actions.append(novice_action)

        elif experience == ExperienceLevel.EXPERT:
            expert_action = (
                "【进阶建议】可进一步交叉验证该标的的行业对比和资金流向数据"
            )
            if expert_action not in decision.next_step_actions:
                decision.next_step_actions.append(expert_action)

        return decision

    # ─── 适配摘要计算 ──────────────────────────────────────────────────────────

    def _calculate_user_fit(
        self,
        decision: DecisionCard,
        user_profile: UserProfile,
        learning_metrics: Optional["LearningMetrics"] = None,
    ) -> UserFitSummary:
        """
        计算用户适配性摘要。

        规则：
        - 新手：统一描述
        - 专家：统一描述
        - 中级：根据判断质量趋势调整
        """
        base_fit = decision.user_fit_summary

        if user_profile.experience_level == ExperienceLevel.NOVICE:
            fit = "适合初学者，建议以学习为主，控制仓位，记录每次决策的理由"
            unfit = "不适合缺乏经验且追求快速收益的投资者"
        elif user_profile.experience_level == ExperienceLevel.EXPERT:
            fit = "适合有体系的投资者，可以根据技术面和基本面综合判断"
            unfit = "不适合缺乏独立分析能力的投资者"
        else:
            # 中级用户：结合判断质量趋势动态调整
            fit = base_fit.fit
            unfit = base_fit.unfit

            if learning_metrics and not learning_metrics.judgment_insufficient:
                if learning_metrics.judgment_trend_direction == "down":
                    fit = (
                        "适合有一定基础但近期判断质量有所下滑的投资者，"
                        "建议降低操作频率，重新验证判断方法"
                    )
                elif learning_metrics.judgment_trend_direction == "up":
                    fit = (
                        "适合有一定基础的投资者，近期判断质量持续改善，"
                        "可以维持当前节奏"
                    )

        return UserFitSummary(fit=fit, unfit=unfit)

    # ─── 诊断报告 ─────────────────────────────────────────────────────────────

    def generate_adaptation_report(self, user_profile: UserProfile) -> Dict[str, Any]:
        """
        生成用户适配诊断报告（供调试和审计）。
        """
        return {
            "profile": {
                "experience": user_profile.experience_level.value,
                "holding_horizon": user_profile.holding_horizon.value,
                "risk_tolerance": user_profile.risk_tolerance.value,
                "behavior_tags": [
                    t.value if isinstance(t, BehaviorTag) else t
                    for t in (user_profile.behavior_tags or [])
                ],
            },
            "adaptation_strategy": self._determine_strategy(user_profile),
        }

    def _determine_strategy(self, profile: UserProfile) -> str:
        """
        根据用户画像确定适配策略。
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
