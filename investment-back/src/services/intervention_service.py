from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from src.models.user import (
    UserProfile,
    ExperienceLevel,
    HoldingHorizon,
    RiskTolerance,
    BehaviorTag
)
from src.schemas.analysis import BehaviorIntervention
import structlog

logger = structlog.get_logger()

@dataclass
class InterventionContext:
    """干预上下文"""
    intent: Optional[str] = None  # purchase, delay, reduce_budget, review; legacy: buy, sell, add, reduce
    trigger_reason: Optional[str] = None
    emotion_level: Optional[int] = None
    scenario: Optional[str] = None
    recent_analyses: List[Dict] = None
    current_market_state: Optional[str] = None

class InterventionService:
    """行为干预服务"""

    def __init__(self):
        self.logger = logger.bind(service="intervention")

    def detect_and_intervene(
        self,
        user_profile: UserProfile,
        context: InterventionContext
    ) -> Optional[BehaviorIntervention]:
        """
        检测行为偏差并生成干预
        """
        self.logger.info("checking_intervention", context=str(context))

        # 冲动消费 / 盲目跟风检测
        if self._is_chasing_rise(context, user_profile):
            self.logger.info("intervention_triggered", type="impulsive_consumption")
            return self._create_chasing_rise_intervention(user_profile)

        # 过度焦虑检测
        if self._is_panic_sell(context, user_profile):
            self.logger.info("intervention_triggered", type="anxiety_spending")
            return self._create_panic_sell_intervention(user_profile)

        # 分期依赖 / 高频大额决策检测
        if self._is_frequent_trading(context, user_profile):
            self.logger.info("intervention_triggered", type="installment_dependency")
            return self._create_frequent_trading_intervention(user_profile)

        # 情绪冲动检测
        if context.emotion_level and context.emotion_level >= 4:
            self.logger.info("intervention_triggered", type="emotional_impulse")
            return self._create_emotional_intervention(context.emotion_level)

        self.logger.debug("no_intervention_needed")
        return None

    def _is_chasing_rise(self, context: InterventionContext, profile: UserProfile) -> bool:
        """检测冲动消费或盲目跟风倾向"""
        if (
            context.intent in ['purchase', 'buy', 'add']
            and context.trigger_reason in ['同学都换新机', '限时优惠', '博主种草', '连续上涨']
        ):
            return True

        # 兼容旧标签：chasing_rise 在比赛版本展示为盲目跟风
        if BehaviorTag.CHASING_RISE in profile.behavior_tags:
            if context.intent in ['purchase', 'buy', 'add']:
                return True

        return False

    def _is_panic_sell(self, context: InterventionContext, profile: UserProfile) -> bool:
        """检测过度焦虑导致的仓促决策"""
        if (
            context.intent in ['delay', 'review', 'sell', 'reduce']
            and context.trigger_reason in ['旧设备损坏', '快速下跌']
        ):
            return True

        # 兼容旧标签：panic_sell 在比赛版本展示为过度焦虑
        if BehaviorTag.PANIC_SELL in profile.behavior_tags:
            if context.intent in ['delay', 'review', 'sell', 'reduce']:
                return True

        return False

    def _is_frequent_trading(self, context: InterventionContext, profile: UserProfile) -> bool:
        """检测分期依赖或高频大额决策倾向"""
        if BehaviorTag.FREQUENT_TRADING in profile.behavior_tags:
            if context.recent_analyses and len(context.recent_analyses) >= 5:
                return True

        return False

    def _create_chasing_rise_intervention(self, profile: UserProfile) -> BehaviorIntervention:
        """创建冲动消费 / 盲目跟风干预"""
        questions = [
            "如果不能分期，你是否仍然愿意购买？",
            "这次购买是学习生活刚需，还是因为同伴影响和害怕落后？",
            "这笔支出是否已经超过本月可支配预算的安全线？",
            "是否存在 3000 元以内、也能满足核心需求的替代方案？",
            "能否先等 48 小时，冷静后再重新评估？"
        ]

        if profile.risk_tolerance == RiskTolerance.LOW:
            questions.append("考虑到你的财务风险承受能力，建议保留至少一个月生活费安全垫")

        return BehaviorIntervention(
            behavior_type="impulsive_consumption",
            severity="high",
            questions=questions
        )

    def _create_panic_sell_intervention(self, profile: UserProfile) -> BehaviorIntervention:
        """创建过度焦虑干预"""
        questions = [
            "这次焦虑来自真实需求，还是来自短期压力和比较？",
            "如果今天不做决定，会造成不可逆后果吗？",
            "是否可以先列出必要功能，再判断是否必须购买当前价位产品？",
            "本月预算是否允许这笔支出，不影响餐饮、交通和学习基本开销？",
            "能否先冷静 30 分钟，再重新填写判断理由？"
        ]

        return BehaviorIntervention(
            behavior_type="anxiety_spending",
            severity="high",
            questions=questions
        )

    def _create_frequent_trading_intervention(self, profile: UserProfile) -> BehaviorIntervention:
        """创建分期依赖干预"""
        questions = [
            "过去三个月是否已经有多笔分期或大额消费？",
            "分期是否让你低估了总价、手续费和逾期成本？",
            "能否设定一个大额消费频率限制，例如每月最多一次？",
            "这笔购买是否会挤压必要生活费或应急金？"
        ]

        return BehaviorIntervention(
            behavior_type="installment_dependency",
            severity="medium",
            questions=questions
        )

    def _create_emotional_intervention(self, emotion_level: int) -> BehaviorIntervention:
        """创建情绪冲动干预"""
        if emotion_level == 5:
            severity = "high"
            questions = [
                "请立刻暂停本次消费决策，先做一些别的事情转移注意力",
                "你当前处于高度情绪化状态，建议至少等待 48 小时后再做决定"
            ]
        else:
            severity = "medium"
            questions = [
                "你当前情绪有一定波动，建议先冷静几分钟",
                "能否把预算影响和替代方案写下来，再做决定？"
            ]

        return BehaviorIntervention(
            behavior_type="emotional_impulse",
            severity=severity,
            questions=questions
        )

    def get_intervention_summary(self, intervention: BehaviorIntervention) -> Dict[str, Any]:
        """获取干预摘要"""
        severity_map = {
            "low": "轻度提示",
            "medium": "中度干预",
            "high": "高度干预"
        }

        type_map = {
            "chasing_rise": "盲目跟风",
            "panic_sell": "过度焦虑",
            "frequent_trading": "分期依赖",
            "impulsive_consumption": "冲动消费",
            "anxiety_spending": "过度焦虑",
            "installment_dependency": "分期依赖",
            "emotional_impulse": "情绪冲动"
        }

        return {
            "type": type_map.get(intervention.behavior_type, intervention.behavior_type),
            "severity": severity_map.get(intervention.severity, intervention.severity),
            "question_count": len(intervention.questions)
        }
