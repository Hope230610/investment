from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Literal

import structlog

from src.models.analysis import InteractionScenario, OutputMarkType
from src.models.user import UserProfile
from src.schemas.analysis import (
    AnalysisResult,
    BehaviorIntervention,
    DecisionCard,
    ExplanationLayer,
    MarketContext,
    ReasonPoint,
    UserFitSummary,
)
from src.schemas.stock import StockDetail, StockEvent, StockHistoryPoint, StockQuoteSnapshot


CN_TZ = timezone(timedelta(hours=8))

RISK_KEYWORDS = ("风险", "问询", "冻结", "减持", "诉讼", "监管", "终止", "亏损", "质押")
POSITIVE_KEYWORDS = ("回购", "增持", "分红", "中标", "增长", "签约", "合同", "盈利")
ANALYSIS_TEMPLATE_VERSION = "decision-card-v1"
ANALYSIS_POLICY_VERSION = "p0-quality-policy-v1"


class AnalysisGenerationService:
    """Generate product-facing analysis cards from normalized market data."""

    def __init__(self):
        self.logger = structlog.get_logger().bind(service="analysis_generation")

    def generate(
        self,
        detail: StockDetail,
        scenario: InteractionScenario,
        user_profile: UserProfile,
        scenario_payload: dict[str, Any] | None = None,
        intervention: BehaviorIntervention | None = None,
    ) -> AnalysisResult:
        del user_profile
        scenario_payload = scenario_payload or {}
        metrics = self._build_metrics(detail.quote_snapshot, detail.recent_history, detail.recent_events)

        if not detail.quote_snapshot and not detail.recent_history:
            return self._build_insufficient_data_result(detail, scenario, intervention)

        if scenario == InteractionScenario.PRE_TRADE_CHECK:
            return self._build_pre_trade_result(detail, metrics, scenario_payload, intervention)
        if scenario == InteractionScenario.POST_TRADE_REVIEW:
            return self._build_post_trade_result(detail, metrics, scenario_payload, intervention)
        return self._build_single_stock_result(detail, metrics, intervention)

    def _build_single_stock_result(
        self,
        detail: StockDetail,
        metrics: dict[str, Any],
        intervention: BehaviorIntervention | None,
    ) -> AnalysisResult:
        risk_score = metrics["risk_score"]
        if risk_score >= 3:
            headline = "当前更适合继续观察，暂不宜形成偏乐观判断"
        elif metrics["data_completeness"] < 2:
            headline = "当前信息仍不充分，建议先补充更多事实再判断"
        else:
            headline = "可以继续关注，但更适合等待下一次验证信号"

        reasons = [
            ReasonPoint(
                text=(
                    f"{detail.stock_name} 最新价 {self._fmt(detail.quote_snapshot.latest_price)} 元，"
                    f"当日涨跌幅 {self._fmt(detail.quote_snapshot.change_percent)}%。"
                ),
                tag=OutputMarkType.DATA_FACT,
            ),
            ReasonPoint(
                text=(
                    f"近 5 个交易日累计涨跌约 {self._fmt(metrics['five_day_return'])}%，"
                    f"近 20 个交易日累计涨跌约 {self._fmt(metrics['twenty_day_return'])}%。"
                ),
                tag=OutputMarkType.DATA_FACT,
            ),
            ReasonPoint(
                text=self._build_event_reason(detail.recent_events, metrics),
                tag=OutputMarkType.DATA_FACT if detail.recent_events else OutputMarkType.UNCERTAINTY,
            ),
            ReasonPoint(
                text=(
                    "综合价格波动、成交热度和公告事件看，当前更适合作为“继续跟踪、等待验证”的标的，"
                    "而不是凭单一信号快速下结论。"
                ),
                mark_type=OutputMarkType.MODEL_INFERENCE,
            ),
        ]

        review_at = datetime.now(CN_TZ) + timedelta(days=7)
        valid_until = review_at + timedelta(days=7)
        decision_card = self._build_decision_card(
            headline=headline,
            reasons=reasons,
            next_actions=[
                "把最近公告和价格变化加入观察清单，下次只比较新增变化。",
                "等下一次财报、公告或趋势确认后，再更新判断。",
                "如果继续关注，先写下你最在意的风险点和失效条件。",
            ],
            primary_risks=(
                "当前最大的风险不是单日价格波动，而是用尚未验证的短期信号替代完整判断。"
                "如果后续出现风险提示公告、放量下跌或波动继续放大，这个结论需要快速重评。"
            ),
            review_at=review_at,
            valid_until=valid_until,
            detail=detail,
            confidence_level=(
                "low" if metrics["data_completeness"] <= 1
                else "low" if risk_score >= 3
                else "medium" if risk_score >= 2 or metrics["data_completeness"] == 2
                else "high"
            ),
            risk_score=risk_score,
        )
        return AnalysisResult(
            status="ready",
            analysis_template_version=ANALYSIS_TEMPLATE_VERSION,
            analysis_policy_version=ANALYSIS_POLICY_VERSION,
            degrade_flags=[],
            intervention=intervention,
            decision_card=decision_card,
            fit_summary="这是一张偏观察型结论卡，更适合管理关注节奏，不适合直接驱动即时交易。",
            market_context=MarketContext(
                market_event=(
                    f"最近 20 个交易日累计涨跌约 {self._fmt(metrics['twenty_day_return'])}%，"
                    f"短线平均振幅约 {self._fmt(metrics['avg_amplitude'])}%。"
                ),
                impact_boundary="以上判断主要覆盖接下来 1 到 4 周的跟踪窗口，不替代长期基本面研究。",
                mark_type=OutputMarkType.MODEL_INFERENCE,
            ),
            explanation_layer=ExplanationLayer(
                plain_text=(
                    "现在更像是在看一家公司的近期变化是否足够支持继续跟踪。"
                    "如果事实还没有朝同一个方向收敛，最稳妥的动作通常不是立刻行动，而是继续观察。"
                ),
                case_example=(
                    "就像看体检报告，如果几项指标只是轻微波动，医生通常会建议复查和观察，"
                    "而不是立刻做激进处理。"
                ),
            ),
        )

    def _build_pre_trade_result(
        self,
        detail: StockDetail,
        metrics: dict[str, Any],
        scenario_payload: dict[str, Any],
        intervention: BehaviorIntervention | None,
    ) -> AnalysisResult:
        risk_score = metrics["risk_score"]
        intent = str(scenario_payload.get("intent") or "").lower()
        trigger = str(scenario_payload.get("trigger_reason") or "")
        emotion_level = int(scenario_payload.get("emotion_level") or 3)
        chasing_risk = intent in {"buy", "add"} and (
            (detail.quote_snapshot.change_percent or 0) >= 3
            or (metrics["five_day_return"] or 0) >= 8
            or trigger == "连续上涨"
        )
        panic_risk = intent in {"sell", "reduce"} and (
            (detail.quote_snapshot.change_percent or 0) <= -3
            or (metrics["five_day_return"] or 0) <= -8
            or trigger == "快速下跌"
        )
        emotional_risk = emotion_level >= 4

        if chasing_risk or panic_risk or emotional_risk:
            headline = "当前更适合先暂停动作，等触发条件重新验证"
        elif risk_score >= 3:
            headline = "当前不宜只凭单一信号行动，建议补充确认后再决策"
        else:
            headline = "可以保留计划，但先把条件、仓位和失效点写清楚"

        reasons = [
            ReasonPoint(
                text=(
                    f"最新价 {self._fmt(detail.quote_snapshot.latest_price)} 元，"
                    f"当日涨跌幅 {self._fmt(detail.quote_snapshot.change_percent)}%，"
                    f"近 5 日累计涨跌约 {self._fmt(metrics['five_day_return'])}%。"
                ),
                tag=OutputMarkType.DATA_FACT,
            ),
            ReasonPoint(
                text=self._build_event_reason(detail.recent_events, metrics),
                tag=OutputMarkType.DATA_FACT if detail.recent_events else OutputMarkType.UNCERTAINTY,
            ),
            ReasonPoint(
                text=(
                    f"当前意图为“{intent or '未填写'}”，触发原因是“{trigger or '未填写'}”，"
                    f"情绪评分为 {emotion_level}/5。"
                ),
                tag=OutputMarkType.DATA_FACT,
            ),
            ReasonPoint(
                text=self._build_pre_trade_inference(chasing_risk, panic_risk, emotional_risk),
                mark_type=OutputMarkType.MODEL_INFERENCE,
            ),
        ]

        review_at = datetime.now(CN_TZ) + timedelta(days=3)
        valid_until = review_at + timedelta(days=3)
        decision_card = self._build_decision_card(
            headline=headline,
            reasons=reasons,
            next_actions=[
                "把这次动作成立的前提写成一句话，再确认是否真有事实支撑。",
                "给自己设置一个最短等待时间，至少等下一次市场更新后再复核。",
                "如果仍要行动，先写清楚仓位边界、失效条件和复盘时间。",
            ],
            primary_risks=(
                "交易前最大的风险，是把情绪、消息刺激和价格波动误认为高质量信号。"
                "当涨跌幅扩大、风险公告出现或情绪评分继续升高时，应优先暂停动作，而不是放大动作。"
            ),
            review_at=review_at,
            valid_until=valid_until,
            detail=detail,
            confidence_level=(
                "low" if metrics["data_completeness"] <= 1
                else "low" if risk_score >= 3
                else "medium" if risk_score >= 2 or metrics["data_completeness"] == 2
                else "high"
            ),
            risk_score=risk_score,
        )
        return AnalysisResult(
            status="ready",
            analysis_template_version=ANALYSIS_TEMPLATE_VERSION,
            analysis_policy_version=ANALYSIS_POLICY_VERSION,
            degrade_flags=[],
            intervention=intervention,
            decision_card=decision_card,
            fit_summary="这是一张偏交易纪律检查卡，重点是限制错误动作，而不是为动作背书。",
            market_context=MarketContext(
                market_event=(
                    f"当前短线涨跌幅 {self._fmt(detail.quote_snapshot.change_percent)}%，"
                    f"最近 20 日累计涨跌约 {self._fmt(metrics['twenty_day_return'])}%。"
                ),
                impact_boundary="这类结论的有效期较短，主要服务于本次动作前的确认，不适合长期沿用。",
                mark_type=OutputMarkType.MODEL_INFERENCE,
            ),
            explanation_layer=ExplanationLayer(
                plain_text=(
                    "交易前最重要的不是证明自己马上要做的事情是对的，"
                    "而是确认这件事不是被情绪推着走。"
                    "如果动作理由写不清，通常就不该着急执行。"
                ),
                case_example=(
                    "就像出门前看天气，如果你只是因为别人说“今天可能不错”就不带伞，"
                    "风险往往不在天气本身，而在你没有做最后一次确认。"
                ),
            ),
        )

    def _build_post_trade_result(
        self,
        detail: StockDetail,
        metrics: dict[str, Any],
        scenario_payload: dict[str, Any],
        intervention: BehaviorIntervention | None,
    ) -> AnalysisResult:
        risk_score = metrics["risk_score"]
        action_taken = str(scenario_payload.get("action_taken") or "未填写")
        outcome_summary = str(scenario_payload.get("outcome_summary") or "未填写")
        plan_deviation = scenario_payload.get("plan_deviation")
        judgement_quality = str(scenario_payload.get("judgement_quality") or "未填写")
        behavior_patterns = scenario_payload.get("behavior_patterns") or []

        if plan_deviation is True or behavior_patterns:
            headline = "本次更像执行偏差，先复盘再谈复制"
        elif "运气" in judgement_quality:
            headline = "这次结果不宜直接复制，先把运气和方法拆开看"
        else:
            headline = "本次复盘更有价值的是固化有效步骤，而不是追求一次性结论"

        reasons = [
            ReasonPoint(
                text=f"你记录的实际操作是“{action_taken}”，结果描述是“{outcome_summary}”。",
                tag=OutputMarkType.DATA_FACT,
            ),
            ReasonPoint(
                text=(
                    f"当前标的最新价 {self._fmt(detail.quote_snapshot.latest_price)} 元，"
                    f"近 20 日累计涨跌约 {self._fmt(metrics['twenty_day_return'])}%。"
                    "这些事实只能辅助复盘，不等同于你当时的完整决策环境。"
                ),
                tag=OutputMarkType.DATA_FACT,
            ),
            ReasonPoint(
                text=(
                    f"计划偏离：{self._format_plan_deviation(plan_deviation)}；"
                    f"自评“判断质量 vs 运气”为“{judgement_quality}”；"
                    f"识别到的行为模式共 {len(behavior_patterns)} 项。"
                ),
                tag=OutputMarkType.DATA_FACT,
            ),
            ReasonPoint(
                text=(
                    "复盘的关键不是证明这次赚亏是否正确，"
                    "而是确认你是否遵守了原计划，以及哪些信号下次仍值得重复使用。"
                ),
                mark_type=OutputMarkType.MODEL_INFERENCE,
            ),
        ]

        review_at = datetime.now(CN_TZ) + timedelta(days=14)
        valid_until = review_at + timedelta(days=14)
        decision_card = self._build_decision_card(
            headline=headline,
            reasons=reasons,
            next_actions=[
                "把这次操作拆成“判断、执行、结果”三段分别记录，不要只看盈亏。",
                "如果发现偏离计划，写下当时触发偏离的情绪或信息刺激。",
                "把这次最值得保留的一条规则写下来，作为下一次同类场景的提醒。",
            ],
            primary_risks=(
                "复盘阶段最大的风险，是把偶然结果误判成稳定方法。"
                "如果这次存在计划偏离、情绪驱动或高不确定性信息干扰，就不应直接复制本次动作。"
            ),
            review_at=review_at,
            valid_until=valid_until,
            detail=detail,
            confidence_level=(
                "low" if metrics["data_completeness"] <= 1
                else "low" if risk_score >= 3
                else "medium" if risk_score >= 2 or metrics["data_completeness"] == 2
                else "high"
            ),
            risk_score=risk_score,
        )
        return AnalysisResult(
            status="ready",
            analysis_template_version=ANALYSIS_TEMPLATE_VERSION,
            analysis_policy_version=ANALYSIS_POLICY_VERSION,
            degrade_flags=[],
            intervention=intervention,
            decision_card=decision_card,
            fit_summary="这是一张偏行为复盘卡，重点是优化下一次决策流程，而不是回头评判对错本身。",
            market_context=MarketContext(
                market_event=(
                    f"复盘时点的市场补充信息：最近 5 日累计涨跌约 {self._fmt(metrics['five_day_return'])}%，"
                    f"近 30 天抓到 {metrics['event_count']} 条相关公告或事件。"
                ),
                impact_boundary="这部分信息只用于补充复盘视角，不能替代交易发生当时的市场环境。",
                mark_type=OutputMarkType.MODEL_INFERENCE,
            ),
            explanation_layer=ExplanationLayer(
                plain_text=(
                    "一笔交易值不值得复制，不取决于最后赚没赚钱，"
                    "而取决于当时的判断和执行是否经得起重复。"
                    "复盘是为了把可重复的方法留下，把容易失控的环节挑出来。"
                ),
                case_example=(
                    "就像复盘一场考试，重点不是这道题碰巧做对了没有，"
                    "而是你用的方法下次还能不能稳定拿分。"
                ),
            ),
        )

    def _build_insufficient_data_result(
        self,
        detail: StockDetail,
        scenario: InteractionScenario,
        intervention: BehaviorIntervention | None,
    ) -> AnalysisResult:
        del scenario
        review_at = datetime.now(CN_TZ) + timedelta(days=2)
        valid_until = review_at + timedelta(days=2)
        decision_card = self._build_decision_card(
            headline="当前信息不足，建议暂不形成明确判断",
            reasons=[
                ReasonPoint(
                    text="本次外部行情或历史数据抓取不完整，无法形成稳定的事实底稿。",
                    mark_type=OutputMarkType.UNCERTAINTY,
                ),
                ReasonPoint(
                    text="当事实不完整时，任何偏乐观或偏悲观结论都容易被短期噪音放大。",
                    mark_type=OutputMarkType.UNCERTAINTY,
                ),
            ],
            next_actions=[
                "稍后重试一次，确认行情、公告和价格历史是否恢复完整。",
                "先查看最近公告和公司基本信息，不要只凭印象行动。",
                "如果这是交易前场景，先暂停动作，等待更完整的数据再判断。",
            ],
            primary_risks="当前风险在于信息不全而不是方向本身，一旦勉强下结论，错误代价会被放大。",
            review_at=review_at,
            valid_until=valid_until,
            detail=detail,
            confidence_level="low",
            risk_score=0,
        )
        return AnalysisResult(
            status="partial_ready",
            analysis_template_version=ANALYSIS_TEMPLATE_VERSION,
            analysis_policy_version=ANALYSIS_POLICY_VERSION,
            degrade_flags=["missing_market_data", "insufficient_evidence"],
            intervention=intervention,
            decision_card=decision_card,
            fit_summary="这是一张信息不足提示卡，目的是阻止在低数据质量下继续推进决策。",
            market_context=MarketContext(
                market_event="当前外部数据抓取不完整，无法可靠重建最近的价格和事件背景。",
                impact_boundary="在事实不完整时，最稳妥的动作通常是暂缓判断，而不是补脑式推断。",
                mark_type=OutputMarkType.UNCERTAINTY,
            ),
            explanation_layer=ExplanationLayer(
                plain_text="现在像是在资料没收齐的情况下做判断，继续往前走比停一下更危险。",
                case_example="就像看病时化验单还没出来，医生通常会先让你复查，而不是直接下重结论。",
            ),
        )

    def _build_decision_card(
        self,
        headline: str,
        reasons: list[ReasonPoint],
        next_actions: list[str],
        primary_risks: str,
        review_at: datetime,
        valid_until: datetime,
        detail: StockDetail,
        confidence_level: Literal["low", "medium", "high"] = "medium",
        risk_score: int = 0,
    ) -> DecisionCard:
        # supporting_evidence: 从 key_reason_summary 中提取 DATA_FACT 前 3 条
        supporting = [
            f"[支撑] {r.text}"
            for r in reasons
            if r.tag == OutputMarkType.DATA_FACT
        ][:3]
        if not supporting:
            supporting = [f"[支撑] {r.text}" for r in reasons[:3]]

        # counter_evidence: 基于风险得分和数据完整度生成
        counter: list[str] = []
        if risk_score >= 2 and detail.recent_events:
            latest = detail.recent_events[0]
            counter.append(f"如果「{latest.title}」相关风险兑现，判断方向可能需要重新评估")
        if risk_score >= 2:
            counter.append("当前判断建立在已知信号上，若新的不利信息出现，结论方向可能反转")
        if not detail.quote_snapshot or not detail.recent_history:
            counter.append("数据信息不足，当前方结论的可靠性有限，不宜过度依赖")
        if not counter:
            counter.append("短期催化剂消失或市场环境变化时，当前逻辑需重新评估")
            counter.append("结论有效期过后，判断应重新生成，不建议长期沿用")

        # invalidation_conditions: 固定 3 条
        invalidation: list[str] = [
            f"超过结论有效期（{valid_until.strftime('%Y-%m-%d')}）",
            "出现监管问询、风险提示、减持公告或重大不利事件",
            "价格出现放量异动（涨跌幅超过 ±5%）或原有趋势发生逆转",
        ]

        return DecisionCard(
            headline_judgement=headline,
            key_reason_summary=reasons,
            user_fit_summary=UserFitSummary(
                fit="更适合愿意先观察事实、重视纪律和复盘的投资者。",
                unfit="不适合希望系统直接给出买卖指令、且无法接受等待验证的人。",
            ),
            next_step_actions=next_actions,
            primary_risks=primary_risks,
            review_at=review_at,
            valid_until=valid_until,
            data_as_of=detail.quote_snapshot.data_as_of if detail.quote_snapshot else None,
            stock_snapshot=detail.quote_snapshot,
            company_profile=detail.company_profile,
            recent_events=detail.recent_events,
            data_sources=detail.data_sources,
            supporting_evidence=supporting,
            counter_evidence=counter,
            invalidation_conditions=invalidation,
            confidence_level=confidence_level,
        )

    def _build_metrics(
        self,
        snapshot: StockQuoteSnapshot | None,
        history: list[StockHistoryPoint],
        recent_events: list[StockEvent],
    ) -> dict[str, Any]:
        five_day_return = self._history_return(history, 5)
        twenty_day_return = self._history_return(history, 20)
        avg_amplitude = self._avg_amplitude(history[-10:])
        risk_event_count = self._keyword_count(recent_events, RISK_KEYWORDS)
        positive_event_count = self._keyword_count(recent_events, POSITIVE_KEYWORDS)
        risk_score = 0
        if snapshot and abs(snapshot.change_percent or 0) >= 4:
            risk_score += 1
        if avg_amplitude >= 4:
            risk_score += 1
        if risk_event_count:
            risk_score += 1
        if (five_day_return or 0) >= 8 or (five_day_return or 0) <= -8:
            risk_score += 1
        if snapshot and (snapshot.turnover_rate or 0) >= 5:
            risk_score += 1

        return {
            "five_day_return": five_day_return,
            "twenty_day_return": twenty_day_return,
            "avg_amplitude": avg_amplitude,
            "risk_event_count": risk_event_count,
            "positive_event_count": positive_event_count,
            "event_count": len(recent_events),
            "risk_score": risk_score,
            "data_completeness": int(snapshot is not None) + int(bool(history)) + int(bool(recent_events)),
        }

    def _history_return(self, history: list[StockHistoryPoint], days: int) -> float:
        if len(history) < 2:
            return 0.0
        end_point = history[-1]
        start_index = max(0, len(history) - days - 1)
        start_point = history[start_index]
        if not start_point.close_price:
            return 0.0
        return round(((end_point.close_price - start_point.close_price) / start_point.close_price) * 100, 2)

    def _avg_amplitude(self, points: Iterable[StockHistoryPoint]) -> float:
        values: list[float] = []
        for point in points:
            if not point.close_price:
                continue
            values.append(((point.high_price - point.low_price) / point.close_price) * 100)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def _keyword_count(self, recent_events: list[StockEvent], keywords: tuple[str, ...]) -> int:
        count = 0
        for event in recent_events:
            if any(keyword in event.title for keyword in keywords):
                count += 1
        return count

    def _build_event_reason(self, recent_events: list[StockEvent], metrics: dict[str, Any]) -> str:
        if not recent_events:
            return "近一段时间没有抓到足够多的公司公告或事件，事件维度仍有信息缺口。"

        latest = recent_events[0]
        if metrics["risk_event_count"] > 0:
            return (
                f"最近抓到 {len(recent_events)} 条公告或事件，最新一条是“{latest.title}”，"
                "事件层面需要偏谨慎解读。"
            )
        if metrics["positive_event_count"] > 0:
            return (
                f"最近抓到 {len(recent_events)} 条公告或事件，最新一条是“{latest.title}”，"
                "短期催化信息相对清晰。"
            )
        return (
            f"最近抓到 {len(recent_events)} 条公告或事件，最新一条是“{latest.title}”，"
            "目前更适合作为跟踪线索，而不是单独下结论。"
        )

    def _build_pre_trade_inference(
        self, chasing_risk: bool, panic_risk: bool, emotional_risk: bool
    ) -> str:
        if chasing_risk:
            return "当前更像是被上涨和触发信息推着行动，先冷静比立刻执行更重要。"
        if panic_risk:
            return "当前更像是被下跌压力推着行动，先确认基本面和原计划是否真的变化。"
        if emotional_risk:
            return "情绪波动已经足以影响判断质量，先把动作从“立刻执行”改成“延迟确认”更稳妥。"
        return "当前没有明显的情绪化特征，但仍需要把触发条件和失效条件写清楚，避免临场漂移。"

    def _format_plan_deviation(self, plan_deviation: Any) -> str:
        if plan_deviation is True:
            return "是"
        if plan_deviation is False:
            return "否"
        return "未填写"

    def _fmt(self, value: float | None) -> str:
        if value is None:
            return "--"
        return f"{value:.2f}"
