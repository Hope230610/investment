from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.models.analysis_result import AnalysisResult
from src.models.analysis_task import AnalysisTask
from src.models.p3 import SharePrivacyLevelEnum, ShareSnapshot
from src.schemas.p3 import PublicShareSnapshot, ShareSnapshotPrivate
from src.services.ai_eval_service import AiEvalService
from src.services.entitlement_service import EntitlementService


SHARE_DISCLAIMER = "本卡片仅用于展示校园金融素养成长、风险教育和决策过程，不构成投资建议、收益承诺、购买建议或借贷诱导。"
SENSITIVE_KEYS = {"quantity", "cost_price", "current_price", "unrealized_pnl", "unrealized_pnl_rate", "transactions"}


class ShareService:
    def __init__(self, db: Session):
        self.db = db
        self.eval_service = AiEvalService()

    def create_from_analysis(
        self,
        user_id: int,
        analysis_id: str,
        *,
        privacy_level: str = "unlisted",
        expires_in_days: int = 30,
    ) -> ShareSnapshotPrivate:
        EntitlementService(self.db).assert_within_limit(user_id, "share_cards_daily", increment=True)
        task_uuid = uuid.UUID(analysis_id)
        task = self.db.query(AnalysisTask).filter(AnalysisTask.id == task_uuid, AnalysisTask.user_id == user_id).first()
        if not task:
            raise ValueError("ANALYSIS_NOT_FOUND")
        result = self.db.query(AnalysisResult).filter(AnalysisResult.analysis_task_id == task.id).first()
        if not result:
            raise ValueError("ANALYSIS_RESULT_NOT_READY")

        title = self._strip_sensitive(self.eval_service.sanitize_text(result.headline_judgement or "结构化分析卡片"))
        summary = self._strip_sensitive(self.eval_service.sanitize_text(result.fit_summary or result.primary_risks or ""))
        support = self._sanitize_list(result.supporting_evidence)
        counter = self._sanitize_list(result.counter_evidence)
        risks = self._sanitize_list([result.primary_risks] if result.primary_risks else [])
        invalidation = self._sanitize_list(result.invalidation_conditions)
        eval_result = self.eval_service.evaluate(
            {
                "title": title,
                "summary": summary,
                "supporting_evidence": support,
                "counter_evidence": counter,
                "risks": risks,
                "invalidation_conditions": invalidation,
                "confidence_level": result.confidence_level,
                "data_timestamp": result.created_at.isoformat() if result.created_at else None,
                "marks": ["data_fact", "model_inference", "uncertainty"],
            },
            case_id="share_snapshot",
            holding_context_source="server" if (task.scenario_payload or {}).get("holding_context") else "none",
        )
        if not eval_result.passed:
            raise ValueError("SHARE_COMPLIANCE_FAILED")

        snapshot = ShareSnapshot(
            share_id=self._new_share_id(),
            user_id=user_id,
            source_type="analysis",
            source_id=task.id,
            title=title,
            summary=summary,
            support_evidence=support,
            counter_evidence=counter,
            risks=risks,
            invalidation_conditions=invalidation,
            confidence_level=result.confidence_level or "low",
            data_timestamp=result.created_at,
            disclaimer=SHARE_DISCLAIMER,
            privacy_level=SharePrivacyLevelEnum(privacy_level),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
            sanitizer_version="share-sanitizer-v1",
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return self._private(snapshot)

    def revoke(self, user_id: int, share_id: str) -> bool:
        snapshot = self.db.query(ShareSnapshot).filter(ShareSnapshot.share_id == share_id, ShareSnapshot.user_id == user_id).first()
        if not snapshot:
            return False
        snapshot.revoked_at = datetime.utcnow()
        self.db.commit()
        return True

    def get_private(self, user_id: int, share_id: str) -> Optional[ShareSnapshotPrivate]:
        snapshot = self.db.query(ShareSnapshot).filter(ShareSnapshot.share_id == share_id, ShareSnapshot.user_id == user_id).first()
        return self._private(snapshot) if snapshot else None

    def get_public(self, share_id: str) -> Optional[PublicShareSnapshot]:
        snapshot = self.db.query(ShareSnapshot).filter(ShareSnapshot.share_id == share_id).first()
        if not snapshot or snapshot.revoked_at:
            return None
        if snapshot.expires_at and snapshot.expires_at <= datetime.utcnow():
            return None
        return PublicShareSnapshot(
            share_id=snapshot.share_id,
            title=snapshot.title,
            summary=snapshot.summary,
            support_evidence=list(snapshot.support_evidence or []),
            counter_evidence=list(snapshot.counter_evidence or []),
            risks=list(snapshot.risks or []),
            invalidation_conditions=list(snapshot.invalidation_conditions or []),
            confidence_level=snapshot.confidence_level,
            data_timestamp=snapshot.data_timestamp,
            disclaimer=snapshot.disclaimer,
            created_at=snapshot.created_at,
            expires_at=snapshot.expires_at,
        )

    def _private(self, snapshot: ShareSnapshot) -> ShareSnapshotPrivate:
        return ShareSnapshotPrivate(
            share_id=snapshot.share_id,
            source_type=snapshot.source_type,
            source_id=str(snapshot.source_id),
            title=snapshot.title,
            summary=snapshot.summary,
            support_evidence=list(snapshot.support_evidence or []),
            counter_evidence=list(snapshot.counter_evidence or []),
            risks=list(snapshot.risks or []),
            invalidation_conditions=list(snapshot.invalidation_conditions or []),
            confidence_level=snapshot.confidence_level,
            data_timestamp=snapshot.data_timestamp,
            disclaimer=snapshot.disclaimer,
            privacy_level=snapshot.privacy_level.value if hasattr(snapshot.privacy_level, "value") else snapshot.privacy_level,
            created_at=snapshot.created_at,
            expires_at=snapshot.expires_at,
            revoked_at=snapshot.revoked_at,
        )

    def _sanitize_list(self, values: Any) -> list[str]:
        if not isinstance(values, list):
            values = [values] if values else []
        result: list[str] = []
        for item in values:
            text = self._strip_sensitive(self.eval_service.sanitize_text(str(item)))
            if text:
                result.append(text[:300])
        return result[:5]

    def _strip_sensitive(self, text: str) -> str:
        sanitized = text
        for key in SENSITIVE_KEYS:
            sanitized = sanitized.replace(key, "[已脱敏]")
        return sanitized

    def _new_share_id(self) -> str:
        while True:
            candidate = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
            exists = self.db.query(ShareSnapshot).filter(ShareSnapshot.share_id == candidate).first()
            if not exists:
                return candidate
