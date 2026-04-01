from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.orm import Session

from src.models.analysis import Analysis as AnalysisModel
from src.models.analysis import AnalysisReason, AnalysisStatus
from src.models.stock import Stock as StockModel
from src.schemas.analysis import AnalysisCreate, AnalysisResult, AnalysisUpdate


logger = structlog.get_logger()


class AnalysisService:
    """Persistence helpers for analysis records."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger.bind(service="analysis")

    def create_analysis(self, user_id: int, analysis_data: AnalysisCreate) -> AnalysisModel:
        self.logger.info("creating_analysis", user_id=user_id)

        stock = self.db.query(StockModel).filter(
            StockModel.stock_id == analysis_data.stock_id
        ).first()
        if not stock:
            market = analysis_data.stock_id[:2].upper() if len(analysis_data.stock_id) >= 2 else "SZ"
            stock = StockModel(
                stock_id=analysis_data.stock_id,
                stock_name=analysis_data.stock_id,
                market=market,
            )
            self.db.add(stock)
            self.db.commit()

        analysis = AnalysisModel(
            user_id=user_id,
            stock_id=analysis_data.stock_id,
            scenario=analysis_data.scenario,
            status=AnalysisStatus.PROCESSING,
            scenario_payload=analysis_data.scenario_payload,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        self.logger.debug("analysis_created", analysis_id=analysis.id)
        return analysis

    def update_analysis(
        self, analysis_id: int, user_id: int, update_data: AnalysisUpdate
    ) -> Optional[AnalysisModel]:
        analysis = self.db.query(AnalysisModel).filter(
            AnalysisModel.id == analysis_id,
            AnalysisModel.user_id == user_id,
        ).first()
        if not analysis:
            return None

        update_fields = update_data.dict(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(analysis, field, value)

        self.db.commit()
        self.db.refresh(analysis)
        self.logger.debug("analysis_updated", analysis_id=analysis.id)
        return analysis

    def get_analysis(self, analysis_id: int, user_id: int) -> Optional[AnalysisModel]:
        return self.db.query(AnalysisModel).filter(
            AnalysisModel.id == analysis_id,
            AnalysisModel.user_id == user_id,
        ).first()

    def get_user_analyses(
        self, user_id: int, scenario: Optional[str] = None, limit: int = 100
    ) -> List[AnalysisModel]:
        query = self.db.query(AnalysisModel).filter(AnalysisModel.user_id == user_id)
        if scenario:
            query = query.filter(AnalysisModel.scenario == scenario)
        return query.order_by(AnalysisModel.created_at.desc()).limit(limit).all()

    def mark_analysis_completed(
        self, analysis_id: int, user_id: int, result: AnalysisResult
    ) -> bool:
        analysis = self.get_analysis(analysis_id, user_id)
        if not analysis:
            self.logger.error("analysis_not_found", analysis_id=analysis_id)
            return False

        analysis.status = AnalysisStatus.READY
        analysis.headline = result.decision_card.headline_judgement
        analysis.decision_card = result.decision_card.model_dump(mode="json")
        analysis.fit_summary = result.fit_summary
        analysis.market_context = result.market_context.model_dump(mode="json")
        analysis.explanation_layer = result.explanation_layer.model_dump(mode="json")
        analysis.intervention = (
            result.intervention.model_dump(mode="json")
            if result.intervention
            else None
        )
        analysis.review_at = result.decision_card.review_at
        analysis.valid_until = result.decision_card.valid_until

        self.db.commit()
        self.logger.info("analysis_completed", analysis_id=analysis_id)
        return True

    def save_analysis_reasons(
        self, analysis_id: int, reasons: List[Dict[str, Any]]
    ) -> List[AnalysisReason]:
        saved: List[AnalysisReason] = []
        for reason_data in reasons:
            reason = AnalysisReason(
                analysis_id=analysis_id,
                text=reason_data["text"],
                order=reason_data.get("order", 0),
                mark_type=reason_data["mark_type"],
            )
            self.db.add(reason)
            saved.append(reason)

        self.db.commit()
        for reason in saved:
            self.db.refresh(reason)

        self.logger.debug("reasons_saved", count=len(saved), analysis_id=analysis_id)
        return saved

    def has_expired(self, analysis: AnalysisModel) -> bool:
        if analysis.valid_until:
            return datetime.now() > analysis.valid_until
        return False

    def get_recent_analyses(self, user_id: int, days: int = 30) -> List[AnalysisModel]:
        since_date = datetime.now() - timedelta(days=days)
        return (
            self.db.query(AnalysisModel)
            .filter(
                AnalysisModel.user_id == user_id,
                AnalysisModel.created_at >= since_date,
            )
            .order_by(AnalysisModel.created_at.desc())
            .all()
        )
