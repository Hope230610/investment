from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.models.analysis import ReviewTask
from src.models.behavior_intervention import BehaviorIntervention
from src.models.emotion_history import EmotionHistory
from src.models.judgment_history import JudgmentHistory
from src.schemas.p3 import GrowthCautionContext


class GrowthService:
    """Turns review and behavior history into neutral caution context."""

    def __init__(self, db: Session):
        self.db = db

    def build_caution_context(self, user_id: int, *, days: int = 120) -> GrowthCautionContext:
        cutoff = datetime.utcnow() - timedelta(days=days)
        reviews = (
            self.db.query(ReviewTask)
            .filter(ReviewTask.user_id == user_id, ReviewTask.updated_at >= cutoff)
            .order_by(ReviewTask.updated_at.desc())
            .limit(30)
            .all()
        )
        judgments = (
            self.db.query(JudgmentHistory)
            .filter(JudgmentHistory.user_id == user_id, JudgmentHistory.created_at >= cutoff)
            .order_by(JudgmentHistory.created_at.desc())
            .limit(30)
            .all()
        )
        emotions = (
            self.db.query(EmotionHistory)
            .filter(EmotionHistory.user_id == user_id, EmotionHistory.created_at >= cutoff)
            .order_by(EmotionHistory.created_at.desc())
            .limit(15)
            .all()
        )
        interventions = (
            self.db.query(BehaviorIntervention)
            .filter(BehaviorIntervention.user_id == user_id, BehaviorIntervention.created_at >= cutoff)
            .order_by(BehaviorIntervention.created_at.desc())
            .limit(20)
            .all()
        )

        review_patterns = self._extract_review_patterns(reviews)
        behavior_patterns = self._extract_behavior_patterns(interventions)
        recent_findings = self._extract_recent_findings(reviews, judgments)
        risk_tendencies = self._build_risk_tendencies(judgments, emotions)

        repeated = [
            f"{label} 在近 {days} 天内重复出现 {count} 次"
            for label, count in review_patterns.items()
            if count >= 2
        ][:5]
        caution_rules = self._build_caution_rules(repeated, behavior_patterns, risk_tendencies)

        signal_count = len(repeated) + len(behavior_patterns) + len(recent_findings) + len(risk_tendencies)
        confidence = "high" if signal_count >= 5 else "medium" if signal_count >= 2 else "low"
        return GrowthCautionContext(
            repeated_mistakes=repeated,
            behavior_patterns=behavior_patterns,
            recent_review_findings=recent_findings,
            risk_tendencies=risk_tendencies,
            caution_rules=caution_rules,
            suggested_review_questions=self._build_questions(caution_rules, risk_tendencies),
            confidence_level=confidence,
            generated_at=datetime.utcnow(),
        )

    def _extract_review_patterns(self, reviews: list[ReviewTask]) -> Counter[str]:
        counter: Counter[str] = Counter()
        for task in reviews:
            result = task.review_result if isinstance(task.review_result, dict) else {}
            patterns = result.get("behavior_patterns") or result.get("mistake_types") or []
            if isinstance(patterns, str):
                patterns = [patterns]
            for item in patterns:
                if isinstance(item, str) and item.strip():
                    counter[item.strip()] += 1
            if result.get("plan_deviation") is True:
                counter["计划偏离"] += 1
            if result.get("judgement_quality") and "运气" in str(result.get("judgement_quality")):
                counter["把结果误认为判断质量"] += 1
        return counter

    def _extract_behavior_patterns(self, interventions: list[BehaviorIntervention]) -> list[str]:
        counter: Counter[str] = Counter()
        for item in interventions:
            value = item.behavior_type.value if hasattr(item.behavior_type, "value") else str(item.behavior_type)
            counter[value] += 1
        labels = {
            "chasing_rise": "同伴影响或促销信息触发后容易加快决策节奏",
            "panic_sell": "预算压力或比较焦虑下容易放大冲动决策",
            "frequent_trading": "近期大额消费或分期频率偏高",
        }
        return [labels.get(key, key) for key, count in counter.items() if count >= 1][:5]

    def _extract_recent_findings(self, reviews: list[ReviewTask], judgments: list[JudgmentHistory]) -> list[str]:
        findings: list[str] = []
        for task in reviews[:5]:
            result = task.review_result if isinstance(task.review_result, dict) else {}
            summary = result.get("outcome_summary") or result.get("review_summary")
            if isinstance(summary, str) and summary.strip():
                findings.append(summary.strip()[:120])
        for record in judgments[:3]:
            if record.is_hard_to_tell:
                findings.append("最近存在难以区分判断与运气的记录")
            elif record.judgment_score <= 50:
                findings.append(f"最近一次判断质量自评偏低：{record.judgment_label}")
        return findings[:5]

    def _build_risk_tendencies(
        self,
        judgments: list[JudgmentHistory],
        emotions: list[EmotionHistory],
    ) -> list[str]:
        tendencies: list[str] = []
        valid_scores = [item.judgment_score for item in judgments if not item.is_hard_to_tell]
        if valid_scores and sum(valid_scores[:5]) / min(len(valid_scores), 5) < 50:
            tendencies.append("近期判断质量自评偏低，新的消费决策需要降低默认置信度")
        if len([item for item in judgments if item.is_hard_to_tell]) >= 2:
            tendencies.append("多次难以区分判断与运气，需要把可复用的决策规则写得更具体")
        if emotions and emotions[0].emotion_level >= 4:
            tendencies.append("最近情绪评分偏高，消费决策前需要冷静期或延迟确认")
        if len([item for item in emotions[:5] if item.emotion_level >= 4]) >= 2:
            tendencies.append("高情绪记录重复出现，需重点检查是否被促销信息或同伴影响触发")
        return tendencies[:5]

    def _build_caution_rules(
        self,
        repeated: list[str],
        behavior_patterns: list[str],
        risk_tendencies: list[str],
    ) -> list[str]:
        rules: list[str] = []
        if repeated:
            rules.append("本次分析前先确认历史重复错误是否再次出现，若出现则降低结论置信度")
        if any("追涨" in item for item in behavior_patterns) or any("同伴" in item for item in behavior_patterns):
            rules.append("若触发原因来自同伴影响、限时优惠或博主种草，先补充反方证据再继续")
        if any("下跌" in item for item in behavior_patterns) or any("焦虑" in item for item in behavior_patterns):
            rules.append("若触发原因来自预算压力或比较焦虑，先复核预算边界和真实需求而不是只看即时满足")
        if any("情绪" in item for item in risk_tendencies):
            rules.append("情绪评分偏高时，至少等待 48 小时冷静期后再复核")
        if any("判断质量" in item for item in risk_tendencies):
            rules.append("近期判断质量偏低时，输出必须保留不确定性和反方证据")
        if not rules:
            rules.append("历史样本不足，保持低置信度并完整记录本次判断证据")
        return rules[:6]

    def _build_questions(self, caution_rules: list[str], risk_tendencies: list[str]) -> list[str]:
        questions = [
            "这次判断的事实证据和个人推理是否已经分开记录？",
            "如果结论失效，最早会由哪个条件触发？",
        ]
        if any("情绪" in item for item in risk_tendencies):
            questions.append("当前行动是否由情绪、预算压力或同伴影响触发？")
        if caution_rules:
            questions.append("这次是否重复了历史上已经出现过的偏差？")
        return questions[:5]
