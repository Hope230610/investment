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
    intent: Optional[str] = None  # buy, sell, add, reduce
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

        # 追涨检测
        if self._is_chasing_rise(context, user_profile):
            self.logger.info("intervention_triggered", type="chasing_rise")
            return self._create_chasing_rise_intervention(user_profile)

        # 恐慌卖出检测
        if self._is_panic_sell(context, user_profile):
            self.logger.info("intervention_triggered", type="panic_sell")
            return self._create_panic_sell_intervention(user_profile)

        # 频繁交易检测
        if self._is_frequent_trading(context, user_profile):
            self.logger.info("intervention_triggered", type="frequent_trading")
            return self._create_frequent_trading_intervention(user_profile)

        # 情绪冲动检测
        if context.emotion_level and context.emotion_level >= 4:
            self.logger.info("intervention_triggered", type="emotional_impulse")
            return self._create_emotional_intervention(context.emotion_level)

        self.logger.debug("no_intervention_needed")
        return None

    def _is_chasing_rise(self, context: InterventionContext, profile: UserProfile) -> bool:
        """检测追涨倾向"""
        # 触发条件1：交易意图是买入/加仓，且触发原因是连续上涨
        if (
            context.intent in ['buy', 'add']
            and context.trigger_reason == '连续上涨'
        ):
            return True

        # 触发条件2：用户有追涨标签
        if BehaviorTag.CHASING_RISE in profile.behavior_tags:
            if context.intent in ['buy', 'add']:
                return True

        return False

    def _is_panic_sell(self, context: InterventionContext, profile: UserProfile) -> bool:
        """检测恐慌卖出倾向"""
        # 触发条件1：交易意图是卖出/减仓，且触发原因是快速下跌
        if (
            context.intent in ['sell', 'reduce']
            and context.trigger_reason == '快速下跌'
        ):
            return True

        # 触发条件2：用户有恐慌卖出标签
        if BehaviorTag.PANIC_SELL in profile.behavior_tags:
            if context.intent in ['sell', 'reduce']:
                return True

        return False

    def _is_frequent_trading(self, context: InterventionContext, profile: UserProfile) -> bool:
        """检测频繁交易倾向"""
        # 用户有频繁交易标签
        if BehaviorTag.FREQUENT_TRADING in profile.behavior_tags:
            # 检查最近的分析记录（模拟）
            if context.recent_analyses and len(context.recent_analyses) >= 5:
                return True

        return False

    def _create_chasing_rise_intervention(self, profile: UserProfile) -> BehaviorIntervention:
        """创建追涨干预"""
        questions = [
            "这次上涨有实质性的基本面支撑吗？还是只是短期情绪推动？",
            "我是否是因为 '害怕错过' 而想买入？",
            "如果现在下跌 10%，我能否接受？",
            "我有明确的止损和止盈计划吗？",
            "能否先等 24 小时，观察市场情况再做决定？"
        ]

        if profile.risk_tolerance == RiskTolerance.LOW:
            questions.append("考虑到您的风险承受能力，建议等待更明确的信号")

        return BehaviorIntervention(
            behavior_type="chasing_rise",
            severity="high",
            questions=questions
        )

    def _create_panic_sell_intervention(self, profile: UserProfile) -> BehaviorIntervention:
        """创建恐慌卖出干预"""
        questions = [
            "这一下跌是否影响了公司的长期基本面？",
            "我卖出是因为恐惧，还是基于理性判断？",
            "如果我现在卖出，是否会在更高价位买回来？",
            "这次下跌是否符合我之前的预期和计划？",
            "能否先深呼吸，冷静 10 分钟再重新考虑？"
        ]

        return BehaviorIntervention(
            behavior_type="panic_sell",
            severity="high",
            questions=questions
        )

    def _create_frequent_trading_intervention(self, profile: UserProfile) -> BehaviorIntervention:
        """创建频繁交易干预"""
        questions = [
            "我之前的交易都实现了预期的目标吗？",
            "频繁交易导致的摩擦成本（手续费、税费）对我的收益影响有多大？",
            "能否设定一个交易频率限制，比如每月最多交易 N 次？",
            "这只股票我准备持有多久？有没有明确的持有周期？"
        ]

        return BehaviorIntervention(
            behavior_type="frequent_trading",
            severity="medium",
            questions=questions
        )

    def _create_emotional_intervention(self, emotion_level: int) -> BehaviorIntervention:
        """创建情绪冲动干预"""
        if emotion_level == 5:
            severity = "high"
            questions = [
                "请立刻暂停操作，先做一些别的事情转移注意力",
                "您当前处于高度情绪化状态，建议至少等待 1 小时后再做决定"
            ]
        else:
            severity = "medium"
            questions = [
                "您当前情绪有一定波动，建议先冷静几分钟",
                "能否把决策写下来，分析利弊后再做决定？"
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
            "chasing_rise": "追涨倾向",
            "panic_sell": "恐慌卖出倾向",
            "frequent_trading": "频繁交易倾向",
            "emotional_impulse": "情绪冲动"
        }

        return {
            "type": type_map.get(intervention.behavior_type, intervention.behavior_type),
            "severity": severity_map.get(intervention.severity, intervention.severity),
            "question_count": len(intervention.questions)
        }
