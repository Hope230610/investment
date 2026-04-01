from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import httpx
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_market_data_service
from src.db.session import SessionLocal, get_db
from src.models.analysis import Analysis as AnalysisModel
from src.models.analysis import AnalysisReason as AnalysisReasonModel
from src.models.analysis import AnalysisStatus, ReviewTask as ReviewTaskModel
from src.models.analysis import ReviewTaskStatus
from src.models.stock import Stock as StockModel
from src.models.user import User
from src.models.watchlist import FocusReason as FocusReasonModel
from src.schemas.analysis import Analysis, AnalysisCreate, AnalysisRecord, AnalysisWithDetails
from src.schemas.stock import StockDetail
from src.schemas.watchlist import FocusReason, FocusReasonCreate
from src.services.adaptation_service import AdaptationService
from src.services.analysis_generation_service import AnalysisGenerationService
from src.services.analysis_service import AnalysisService
from src.services.intervention_service import InterventionContext, InterventionService
from src.services.market_data_service import MarketDataService
from src.services.user_service import UserService


router = APIRouter()
logger = structlog.get_logger()


def _to_storage_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _upsert_stock_record(db: Session, detail: StockDetail) -> StockModel:
    stock = db.query(StockModel).filter(StockModel.stock_id == detail.stock_id).first()
    if not stock:
        stock = StockModel(stock_id=detail.stock_id)
        db.add(stock)

    stock.stock_name = detail.stock_name
    stock.market = detail.market
    stock.industry = detail.industry
    stock.listing_date = detail.company_profile.listing_date if detail.company_profile else None
    stock.pe_ratio = detail.quote_snapshot.pe_ratio if detail.quote_snapshot else None
    stock.pb_ratio = detail.quote_snapshot.pb_ratio if detail.quote_snapshot else None

    db.commit()
    db.refresh(stock)
    return stock


def _load_stock_detail_or_502(
    market_data_service: MarketDataService,
    stock_id: str,
) -> StockDetail:
    try:
        return market_data_service.get_stock_detail(stock_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="股票标识无效") from exc
    except httpx.HTTPError as exc:
        logger.error("load_stock_detail_failed", stock_id=stock_id, error=str(exc))
        raise HTTPException(
            status_code=502,
            detail="暂时无法获取该股票的实时数据，请稍后再试",
        ) from exc


@router.post("", response_model=Analysis)
async def create_analysis(
    analysis_data: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    """Create a real-data analysis job."""
    logger.info(
        "create_analysis",
        scenario=analysis_data.scenario.value,
        stock_id=analysis_data.stock_id,
        user_id=current_user.id,
    )

    stock_detail = _load_stock_detail_or_502(market_data_service, analysis_data.stock_id)
    _upsert_stock_record(db, stock_detail)

    analysis_service = AnalysisService(db)
    analysis = analysis_service.create_analysis(current_user.id, analysis_data)

    background_tasks.add_task(process_analysis, analysis.id)
    db.refresh(analysis)
    return analysis


def process_analysis(analysis_id: int):
    """Fetch real market data, generate an analysis, and persist it."""
    db = SessionLocal()
    analysis: Optional[AnalysisModel] = None
    market_data_service = MarketDataService()

    try:
        logger.info("process_analysis", analysis_id=analysis_id)

        analysis_service = AnalysisService(db)
        user_service = UserService(db)
        adaptation_service = AdaptationService()
        intervention_service = InterventionService()
        generation_service = AnalysisGenerationService()

        analysis = db.query(AnalysisModel).filter(AnalysisModel.id == analysis_id).first()
        if not analysis:
            logger.error("analysis_not_found", analysis_id=analysis_id)
            return

        stock_detail = market_data_service.get_stock_detail(analysis.stock_id)
        stock = _upsert_stock_record(db, stock_detail)
        user_profile = user_service.get_or_create_profile(analysis.user_id)
        scenario_payload = analysis.scenario_payload or {}

        intervention = None
        if scenario_payload:
            context = InterventionContext(
                intent=scenario_payload.get("intent"),
                trigger_reason=scenario_payload.get("trigger_reason"),
                emotion_level=scenario_payload.get("emotion_level"),
                scenario=analysis.scenario.value,
                recent_analyses=analysis_service.get_recent_analyses(analysis.user_id),
            )
            intervention = intervention_service.detect_and_intervene(user_profile, context)

        result = generation_service.generate(
            detail=stock_detail,
            scenario=analysis.scenario,
            user_profile=user_profile,
            scenario_payload=scenario_payload,
            intervention=intervention,
        )
        result.decision_card = adaptation_service.adapt_decision_for_user(
            result.decision_card,
            user_profile,
        )

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
        analysis.review_at = _to_storage_datetime(result.decision_card.review_at)
        analysis.valid_until = _to_storage_datetime(result.decision_card.valid_until)

        db.query(AnalysisReasonModel).filter(
            AnalysisReasonModel.analysis_id == analysis.id
        ).delete()
        for index, reason in enumerate(result.decision_card.key_reason_summary):
            db.add(
                AnalysisReasonModel(
                    analysis_id=analysis.id,
                    text=reason.text,
                    order=index,
                    mark_type=reason.tag,
                )
            )

        if analysis.review_at:
            review_task = (
                db.query(ReviewTaskModel)
                .filter(ReviewTaskModel.analysis_id == analysis.id)
                .first()
            )
            if not review_task:
                review_task = ReviewTaskModel(
                    user_id=analysis.user_id,
                    analysis_id=analysis.id,
                    stock_name=stock.stock_name,
                    scenario=analysis.scenario.value,
                    review_at=analysis.review_at,
                )
                db.add(review_task)

            review_task.stock_name = stock.stock_name
            review_task.scenario = analysis.scenario.value
            review_task.review_at = analysis.review_at
            review_task.status = (
                ReviewTaskStatus.EXPIRED
                if analysis.review_at <= datetime.now()
                else ReviewTaskStatus.PENDING
            )

        db.commit()
        logger.info("analysis_completed", analysis_id=analysis_id)

    except Exception as exc:
        logger.error("analysis_failed", analysis_id=analysis_id, error=str(exc))
        if analysis is not None:
            analysis.status = AnalysisStatus.FAILED
            db.commit()
    finally:
        market_data_service.close()
        db.close()


@router.get("/{analysis_id}", response_model=AnalysisWithDetails)
async def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a single analysis result."""
    logger.info("get_analysis", analysis_id=analysis_id, user_id=current_user.id)

    analysis_service = AnalysisService(db)
    analysis = analysis_service.get_analysis(analysis_id, current_user.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="分析未找到")

    if analysis.stock is not None:
        setattr(analysis, "stock_name", analysis.stock.stock_name)
        setattr(analysis, "stock_market", analysis.stock.market)
        setattr(analysis, "stock_industry", analysis.stock.industry)

    for task in analysis.review_tasks:
        setattr(task, "stock_id", analysis.stock_id)

    return analysis


@router.get("", response_model=List[AnalysisRecord])
async def get_analysis_records(
    scenario: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's analysis history."""
    del offset
    logger.info("get_analysis_records", user_id=current_user.id, scenario=scenario)

    analysis_service = AnalysisService(db)
    analyses = analysis_service.get_user_analyses(current_user.id, scenario, limit)

    records = []
    for analysis in analyses:
        stock_name = analysis.stock.stock_name if analysis.stock else "未知股票"
        records.append(
            AnalysisRecord(
                id=analysis.id,
                scenario=analysis.scenario.value,
                stock_id=analysis.stock_id,
                stock_name=stock_name,
                created_at=analysis.created_at,
                status=analysis.status,
                headline=analysis.headline,
            )
        )

    return records


@router.post("/{analysis_id}/record-reason", response_model=FocusReason)
async def record_focus_reason(
    analysis_id: int,
    reason_data: FocusReasonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Persist a user-entered focus reason."""
    logger.info("record_focus_reason", analysis_id=analysis_id, user_id=current_user.id)

    analysis_service = AnalysisService(db)
    analysis = analysis_service.get_analysis(analysis_id, current_user.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="分析未找到")

    focus_reason = FocusReasonModel(
        user_id=current_user.id,
        analysis_id=analysis_id,
        stock_id=reason_data.stock_id,
        reason=reason_data.reason,
    )
    db.add(focus_reason)
    db.commit()
    db.refresh(focus_reason)
    return focus_reason
