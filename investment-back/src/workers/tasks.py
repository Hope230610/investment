"""Analysis job functions — callable from both RQ worker and FastAPI BackgroundTasks.

This module is the single canonical home for the analysis execution logic.
The old `process_analysis_v2` function (formerly in analysis.py) has been
extracted here so the API layer only needs to enqueue a job descriptor,
while the worker process handles all I/O (market data, LLM inference, DB writes).
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import structlog

from src.db.session import SessionLocal


logger = structlog.get_logger()


def run_analysis_job(task_uuid_str: str) -> None:
    """Execute a full analysis pipeline for the given AnalysisTask UUID.

    Called by RQ when a job is dequeued, or directly via BackgroundTasks in dev mode.

    Error handling: any exception is caught, the task record is updated to FAILED
    with the error message, so the frontend can poll and surface a meaningful message.
    """
    db = SessionLocal()
    market_data_service = None
    try:
        task_uuid = uuid_lib.UUID(task_uuid_str)
        logger.info("run_analysis_job", task_id=task_uuid_str)

        # Import heavy services lazily so the import graph stays clean
        from src.models.analysis import InteractionScenario, ReviewTask as ReviewTaskModel, ReviewTaskStatus
        from src.models.analysis_task import AnalysisTask, AnalysisStatusEnum
        from src.models.analysis_result import AnalysisResult, ValidPeriodEnum
        from src.models.stock import Stock as StockModel
        from src.services.adaptation_service import AdaptationService
        from src.services.analysis_generation_service import AnalysisGenerationService
        from src.services.analysis_service import AnalysisService
        from src.services.intervention_service import InterventionContext, InterventionService
        from src.services.learning_service import UserLearningService
        from src.services.market_data_service import MarketDataService
        from src.services.output_quality_service import OutputQualityService
        from src.services.portfolio_service import PortfolioService
        from src.services.growth_service import GrowthService
        from src.services.user_service import UserService

        market_data_service = MarketDataService()

        analysis_service = AnalysisService(db)
        user_service = UserService(db)
        adaptation_service = AdaptationService()
        intervention_service = InterventionService()
        generation_service = AnalysisGenerationService()
        learning_service = UserLearningService(db)
        output_quality_service = OutputQualityService()

        # ── 1. Load task ──────────────────────────────────────────────────────
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_uuid).first()
        if not task:
            logger.error("run_analysis_job_task_not_found", task_id=task_uuid_str)
            return

        # ── 2. Market data ─────────────────────────────────────────────────────
        stock_detail = market_data_service.get_stock_detail(task.stock_id)
        stock = _upsert_stock_record(db, stock_detail)
        user_profile = user_service.get_or_create_profile(task.user_id)
        scenario_payload: dict[str, Any] = dict(task.scenario_payload or {})
        scenario_payload.pop("holding_context", None)
        scenario_payload.pop("growth_caution_context", None)
        holding_context = PortfolioService(db).get_holding_context(task.user_id, task.stock_id)
        if holding_context:
            scenario_payload["holding_context"] = holding_context
        scenario_payload["growth_caution_context"] = GrowthService(db).build_caution_context(task.user_id).model_dump(mode="json")
        if scenario_payload != (task.scenario_payload or {}):
            task.scenario_payload = scenario_payload

        # ── 3. Behavior intervention ───────────────────────────────────────────
        intervention = None
        if scenario_payload:
            context = InterventionContext(
                intent=scenario_payload.get("intent"),
                trigger_reason=scenario_payload.get("trigger_reason"),
                emotion_level=scenario_payload.get("emotion_level"),
                scenario=(
                    task.scenario.value
                    if hasattr(task.scenario, "value")
                    else task.scenario
                ),
                recent_analyses=analysis_service.get_recent_analyses(task.user_id),
            )
            intervention = intervention_service.detect_and_intervene(user_profile, context)

        # ── 4. Generate analysis ───────────────────────────────────────────────
        scenario_enum = InteractionScenario(
            task.scenario.value
            if hasattr(task.scenario, "value")
            else task.scenario
        )
        result = generation_service.generate(
            detail=stock_detail,
            scenario=scenario_enum,
            user_profile=user_profile,
            scenario_payload=scenario_payload,
            intervention=intervention,
        )
        learning_metrics = learning_service.compute(task.user_id)
        result.decision_card = adaptation_service.adapt_decision_for_user(
            result.decision_card,
            user_profile,
            learning_metrics=learning_metrics,
        )
        output_quality_service.assert_decision_card_passes(
            result.decision_card,
            degrade_flags=result.degrade_flags,
        )

        # ── 5. Update task status ──────────────────────────────────────────────
        result_status = getattr(result, "status", "ready")
        task.status = (
            AnalysisStatusEnum.PARTIAL_READY
            if result_status == "partial_ready"
            else AnalysisStatusEnum.READY
        )
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        # ── 6. Persist analysis result ────────────────────────────────────────
        existing_result = db.query(AnalysisResult).filter(
            AnalysisResult.analysis_task_id == task.id
        ).first()

        if not existing_result:
            decision_card = result.decision_card
            result_record = AnalysisResult(
                id=uuid_lib.uuid4(),
                analysis_task_id=task.id,
                headline_judgement=decision_card.headline_judgement,
                key_reason_summary=[
                    {"text": r.text, "mark_type": r.tag.value}
                    for r in decision_card.key_reason_summary
                ],
                user_fit_summary={
                    "fit": decision_card.user_fit_summary.fit,
                    "unfit": decision_card.user_fit_summary.unfit,
                },
                next_step_actions=list(decision_card.next_step_actions),
                primary_risks=decision_card.primary_risks or "",
                review_at=_to_storage_datetime(decision_card.review_at),
                intervention=(
                    result.intervention.model_dump(mode="json")
                    if result.intervention else None
                ),
                fit_summary=result.fit_summary,
                market_context=(
                    result.market_context.model_dump(mode="json")
                    if result.market_context else None
                ),
                explanation_layer=(
                    result.explanation_layer.model_dump(mode="json")
                    if result.explanation_layer else None
                ),
                detail_panels={
                    "metadata": {
                        "analysis_template_version": result.analysis_template_version,
                        "analysis_policy_version": result.analysis_policy_version,
                        "degrade_flags": list(result.degrade_flags),
                        "prompt_template_id": "analysis_decision_card",
                        "prompt_template_version": result.analysis_template_version,
                        "model_provider": "rules_engine",
                        "model_name": "deterministic-v1",
                        "generated_at": datetime.utcnow().isoformat(),
                        "output_schema_version": "decision-card-v2",
                        "data_snapshot_timestamp": (
                            decision_card.data_as_of.isoformat()
                            if decision_card.data_as_of else None
                        ),
                    }
                },
                output_tags=["model_inference"],
                valid_period=ValidPeriodEnum.MEDIUM,
                # V2 evidence fields
                supporting_evidence=list(getattr(decision_card, "supporting_evidence", [])),
                counter_evidence=list(getattr(decision_card, "counter_evidence", [])),
                invalidation_conditions=list(getattr(decision_card, "invalidation_conditions", [])),
                confidence_level=getattr(decision_card, "confidence_level", "medium"),
            )
            db.add(result_record)

        # ── 7. Create review task ───────────────────────────────────────────────
        review_at = _to_storage_datetime(result.decision_card.review_at)
        scenario_str = (
            task.scenario.value
            if hasattr(task.scenario, "value")
            else task.scenario
        )
        skip_review = (
            scenario_str == "post_trade_review"
            and bool(scenario_payload.get("pending_review_task_id"))
        )
        if review_at and not skip_review:
            review_task = (
                db.query(ReviewTaskModel)
                .filter(ReviewTaskModel.analysis_task_id == task.id)
                .first()
            )
            if not review_task:
                review_task = ReviewTaskModel(
                    user_id=task.user_id,
                    analysis_task_id=task.id,
                    stock_id=task.stock_id,
                    stock_name=stock.stock_name,
                    scenario=scenario_str,
                    review_at=review_at,
                )
                db.add(review_task)
            review_task.stock_id = task.stock_id
            review_task.stock_name = stock.stock_name
            review_task.scenario = scenario_str
            review_task.review_at = review_at
            review_task.status = (
                ReviewTaskStatus.EXPIRED
                if review_at <= datetime.now()
                else ReviewTaskStatus.PENDING
            )
        else:
            logger.info(
                "run_analysis_job_review_skipped",
                task_id=str(task.id),
                reason="pending_review_resolution",
            )

        db.commit()
        logger.info("run_analysis_job_completed", task_id=str(task.id))

    except Exception as exc:
        logger.error("run_analysis_job_failed", task_id=task_uuid_str, error=str(exc))
        db.rollback()
        _persist_failure(db, task_uuid_str, str(exc))
        raise  # Re-raise so RQ marks the job as failed (enables retry/alerting)
    finally:
        if market_data_service is not None:
            market_data_service.close()
        db.close()


# ── helpers ────────────────────────────────────────────────────────────────────

def _to_storage_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _upsert_stock_record(db, detail) -> StockModel:
    """Persist or update a Stock record from a StockDetail schema object."""
    from src.models.stock import Stock as StockModel

    stock = db.query(StockModel).filter(
        StockModel.stock_id == detail.stock_id
    ).first()
    if not stock:
        stock = StockModel(stock_id=detail.stock_id)
        db.add(stock)

    stock.stock_name = detail.stock_name
    stock.market = detail.market
    stock.industry = detail.industry
    if detail.company_profile:
        stock.listing_date = detail.company_profile.listing_date
    if detail.quote_snapshot:
        stock.pe_ratio = detail.quote_snapshot.pe_ratio
        stock.pb_ratio = detail.quote_snapshot.pb_ratio

    db.commit()
    db.refresh(stock)
    return stock


def _persist_failure(db, task_uuid_str: str, error_message: str) -> None:
    """Mark an AnalysisTask as FAILED with an error message."""
    try:
        import uuid as uuid_lib
        from src.models.analysis_task import AnalysisTask, AnalysisStatusEnum

        task_uuid = uuid_lib.UUID(task_uuid_str)
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_uuid).first()
        if task:
            task.status = AnalysisStatusEnum.FAILED
            task.error_message = error_message
            db.commit()
    except Exception as commit_exc:
        logger.error(
            "run_analysis_job_failure_commit_failed",
            task_id=task_uuid_str,
            error=str(commit_exc),
        )
        db.rollback()
