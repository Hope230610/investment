from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import uuid as uuid_lib

import httpx
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_502_BAD_GATEWAY

from src.api.deps import get_current_user, get_market_data_service
from src.schemas.common import ErrorDetail, ErrorResponse
from src.db.session import SessionLocal, get_db
from src.models.analysis import Analysis as AnalysisModel
from src.models.analysis import AnalysisReason as AnalysisReasonModel
from src.models.analysis import AnalysisStatus, ReviewTask as ReviewTaskModel
from src.models.analysis import ReviewTaskStatus
from src.models.stock import Stock as StockModel
from src.models.user import User
from src.models.watchlist import FocusReason as FocusReasonModel
from src.schemas.analysis import (
    Analysis,
    AnalysisCreate,
    AnalysisCreateResponse,
    AnalysisRecord,
    GetAnalysisResponseV2,
    InterventionInfo,
    DecisionCardV2,
    ReviewTask,
    ReviewTaskCreateV2,
)
from src.schemas.stock import StockDetail
from src.schemas.watchlist import FocusReason, FocusReasonCreate, RecordReasonRequest, RecordReasonResponse
from src.services.adaptation_service import AdaptationService
from src.services.analysis_generation_service import AnalysisGenerationService
from src.services.analysis_service import (
    ANALYSIS_ROUTING,
    _is_valid_uuid,
    _parse_analysis_id,
    AnalysisService,
)
from src.services.intervention_service import InterventionContext, InterventionService
from src.services.market_data_service import MarketDataService
from src.services.user_service import UserService


router = APIRouter()
logger = structlog.get_logger()


def api_error(
    status_code: int,
    code: str,
    message: str,
    request: Optional[Request] = None,
    retryable: bool = False,
) -> JSONResponse:
    """返回统一错误结构 {error: {code, message, request_id, retryable}}"""
    request_id = request.headers.get("x-request-id") if request else None
    body = ErrorResponse(error=ErrorDetail(
        code=code,
        message=message,
        request_id=request_id,
        retryable=retryable,
    ))
    return JSONResponse(status_code=status_code, content=body.model_dump())


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
    request: Optional[Request] = None,
) -> StockDetail:
    try:
        return market_data_service.get_stock_detail(stock_id)
    except ValueError as exc:
        return api_error(404, "STOCK_NOT_FOUND", "股票标识无效", request)
    except httpx.HTTPError as exc:
        logger.error("load_stock_detail_failed", stock_id=stock_id, error=str(exc))
        return api_error(
            HTTP_502_BAD_GATEWAY,
            "MARKET_DATA_UNAVAILABLE",
            "暂时无法获取该股票的实时数据，请稍后再试",
            request,
            retryable=True,
        )


@router.post("")
async def create_analysis(
    analysis_data: AnalysisCreate,
    background_tasks: BackgroundTasks,
    request: Request,
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

    stock_detail = _load_stock_detail_or_502(market_data_service, analysis_data.stock_id, request)
    _upsert_stock_record(db, stock_detail)

    analysis_service = AnalysisService(db)
    result_obj = analysis_service.create_analysis(current_user.id, analysis_data)

    # 路由分发：新路径返回 UUID，旧路径返回完整记录
    if ANALYSIS_ROUTING.get("analysis") == "new":
        task_uuid = str(result_obj.id)
        task_status = result_obj.status
        background_tasks.add_task(process_analysis_v2, task_uuid)
        db.refresh(result_obj)
        return AnalysisCreateResponse(
            id=task_uuid,
            status=task_status.value,
        )
    else:
        background_tasks.add_task(process_analysis, result_obj.id)
        db.refresh(result_obj)
        return result_obj


def process_analysis(analysis_id: int):
    """旧路径分析处理（legacy analyses 表）。

    仅在 ANALYSIS_ROUTING["analysis"] == "old" 时被调用。
    迁移 007 将 analyses 重命名为 analyses_legacy 后，
    此函数检测到旧表不存在则安全退出。
    """
    if ANALYSIS_ROUTING.get("analysis") != "old":
        logger.info("process_analysis_skipped", reason="routing_is_new")
        return

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


def process_analysis_v2(task_uuid_str: str):
    """新路径分析处理：直接处理 AnalysisTask，不依赖 legacy analyses 表。

    由 create_analysis 在 ANALYSIS_ROUTING["analysis"] == "new" 时调用。
    接收 analysis_task.id（UUID 字符串），生成分析结果写入 analysis_results。
    """
    from datetime import timedelta
    import uuid as uuid_lib
    from src.models.analysis import ReviewTask as ReviewTaskModel, ReviewTaskStatus

    db = SessionLocal()
    market_data_service = MarketDataService()
    try:
        task_uuid = uuid_lib.UUID(task_uuid_str)
        logger.info("process_analysis_v2", task_id=task_uuid_str)

        analysis_service = AnalysisService(db)
        user_service = UserService(db)
        adaptation_service = AdaptationService()
        intervention_service = InterventionService()
        generation_service = AnalysisGenerationService()

        # 读取 AnalysisTask
        from src.models.analysis_task import AnalysisTask, AnalysisScenarioEnum, AnalysisStatusEnum
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_uuid).first()
        if not task:
            logger.error("analysis_task_not_found", task_id=task_uuid_str)
            return

        stock_detail = market_data_service.get_stock_detail(task.stock_id)
        stock = _upsert_stock_record(db, stock_detail)
        user_profile = user_service.get_or_create_profile(task.user_id)
        scenario_payload = task.scenario_payload or {}

        # === 1. 生成分析结果 ===
        intervention = None
        if scenario_payload:
            context = InterventionContext(
                intent=scenario_payload.get("intent"),
                trigger_reason=scenario_payload.get("trigger_reason"),
                emotion_level=scenario_payload.get("emotion_level"),
                scenario=task.scenario.value if hasattr(task.scenario, "value") else task.scenario,
                recent_analyses=analysis_service.get_recent_analyses(task.user_id),
            )
            intervention = intervention_service.detect_and_intervene(user_profile, context)

        # InteractionScenario 枚举用于旧 generation_service
        from src.models.analysis import InteractionScenario
        scenario_enum = InteractionScenario(
            task.scenario.value if hasattr(task.scenario, "value") else task.scenario
        )
        result = generation_service.generate(
            detail=stock_detail,
            scenario=scenario_enum,
            user_profile=user_profile,
            scenario_payload=scenario_payload,
            intervention=intervention,
        )
        result.decision_card = adaptation_service.adapt_decision_for_user(
            result.decision_card,
            user_profile,
        )

        # === 2. 更新 AnalysisTask 状态 ===
        task.status = AnalysisStatusEnum.READY
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        # === 3. 写入 AnalysisResult ===
        from src.models.analysis_result import AnalysisResult, ValidPeriodEnum

        existing_result = db.query(AnalysisResult).filter(
            AnalysisResult.analysis_task_id == task.id
        ).first()

        if not existing_result:
            result_record = AnalysisResult(
                id=uuid_lib.uuid4(),
                analysis_task_id=task.id,
                headline_judgement=result.decision_card.headline_judgement,
                key_reason_summary=[
                    {"text": r.text, "mark_type": r.tag.value}
                    for r in result.decision_card.key_reason_summary
                ],
                user_fit_summary={
                    "fit": result.user_fit_summary.fit if hasattr(result, "user_fit_summary") else "",
                    "unfit": result.user_fit_summary.unfit if hasattr(result, "user_fit_summary") else "",
                },
                next_step_actions=[a for a in result.decision_card.next_step_actions],
                primary_risks="",
                review_at=_to_storage_datetime(result.decision_card.review_at),
                intervention=(
                    result.intervention.model_dump(mode="json")
                    if result.intervention else None
                ),
                fit_summary=result.fit_summary,
                market_context=result.market_context.model_dump(mode="json") if result.market_context else None,
                explanation_layer=result.explanation_layer.model_dump(mode="json") if result.explanation_layer else None,
                output_tags=["model_inference"],
                valid_period=ValidPeriodEnum.MEDIUM,
            )
            db.add(result_record)

        # === 4. 创建 ReviewTask（使用 analysis_task_id） ===
        review_at = _to_storage_datetime(result.decision_card.review_at)
        if review_at:
            review_task = (
                db.query(ReviewTaskModel)
                .filter(ReviewTaskModel.analysis_task_id == task.id)
                .first()
            )
            scenario_str = task.scenario.value if hasattr(task.scenario, "value") else task.scenario
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

        db.commit()
        logger.info("analysis_v2_completed", task_id=str(task.id))

    except Exception as exc:
        logger.error("analysis_v2_failed", task_id=task_uuid_str, error=str(exc))
        db.rollback()
    finally:
        market_data_service.close()
        db.close()


@router.get("/{analysis_id}", response_model=GetAnalysisResponseV2)
async def get_analysis(
    analysis_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    """Return a single analysis result.

    beta 阶段仅支持 UUID 格式（对应 analysis_tasks 表）。
    旧整数 ID 路径已废弃，直接返回 404。
    """
    if not _is_valid_uuid(analysis_id):
        return api_error(
            HTTP_400_BAD_REQUEST,
            "INVALID_ANALYSIS_ID",
            "无效的分析 ID 格式，请使用 UUID",
            request,
        )

    uuid_val = uuid_lib.UUID(analysis_id)
    if ANALYSIS_ROUTING.get("analysis") != "new":
        return api_error(HTTP_404_NOT_FOUND, "ANALYSIS_NOT_FOUND", "分析未找到", request)

    return _get_analysis_from_new_tables(
        db, current_user.id, uuid_val, market_data_service, request
    )


def _get_analysis_from_new_tables(
    db: Session, user_id: int, task_uuid: uuid_lib.UUID,
    market_data_service: MarketDataService,
    request: Optional[Request] = None,
) -> GetAnalysisResponseV2:
    """从新表构建 GetAnalysisResponseV2（含实时行情数据）"""
    from src.models.analysis_task import AnalysisTask, AnalysisStatusEnum
    from src.models.analysis_result import AnalysisResult
    from src.models.analysis import ReviewTask as ReviewTaskModel
    from src.schemas.stock import StockDetail

    task = db.query(AnalysisTask).filter(
        AnalysisTask.id == task_uuid,
        AnalysisTask.user_id == user_id,
    ).first()
    if not task:
        return api_error(HTTP_404_NOT_FOUND, "ANALYSIS_NOT_FOUND", "分析未找到", request)

    result = db.query(AnalysisResult).filter(
        AnalysisResult.analysis_task_id == task_uuid,
    ).first()

    review_tasks = db.query(ReviewTaskModel).filter(
        ReviewTaskModel.analysis_task_id == task_uuid,
    ).all()

    # 实时行情数据（用于 UI 展示层）
    stock_detail: Optional[StockDetail] = None
    try:
        stock_detail = market_data_service.get_stock_detail(task.stock_id)
    except Exception:
        pass  # 行情数据可选，降级处理

    # 状态映射
    status_map = {
        AnalysisStatusEnum.PROCESSING: "processing",
        AnalysisStatusEnum.PARTIAL_READY: "partial_ready",
        AnalysisStatusEnum.READY: "ready",
        AnalysisStatusEnum.EXPIRED: "expired",
        AnalysisStatusEnum.FAILED: "failed",
    }
    response_status = status_map.get(task.status, "processing")

    # degrade_flags
    degrade_flags: List[str] = []
    if task.status == AnalysisStatusEnum.PARTIAL_READY:
        degrade_flags.append("insufficient_evidence")

    # 决策卡
    if result:
        decision_card = {
            "headline_judgement": result.headline_judgement or "（分析中）",
            "key_reason_summary": result.key_reason_summary or [],
            "user_fit_summary": result.user_fit_summary or {"fit": "", "unfit": ""},
            "next_step_actions": result.next_step_actions or [],
            "primary_risks": result.primary_risks or "",
            "review_at": result.review_at,
        }
        intervention_info = None
        if result.intervention:
            intervention_info = {
                "behavior_type": result.intervention.get("behavior_type", ""),
                "severity": result.intervention.get("severity", "medium"),
                "questions": result.intervention.get("questions", []),
            }
        # valid_until = review_at + 7 天（与 generation_service 保持一致）
        from datetime import timedelta
        valid_until = result.review_at + timedelta(days=7) if result.review_at else None
    else:
        decision_card = {
            "headline_judgement": "（分析中）",
            "key_reason_summary": [],
            "user_fit_summary": {"fit": "", "unfit": ""},
            "next_step_actions": [],
            "primary_risks": "",
            "review_at": task.expired_at,
        }
        intervention_info = None
        valid_until = None

    # 复盘任务（取最新一条）
    review_task_data = None
    if review_tasks:
        rt = review_tasks[0]
        review_task_data = {
            "id": rt.id,
            "review_at": rt.review_at,
            "status": rt.status.value if hasattr(rt.status, "value") else rt.status,
        }

    # 实时行情字段（来自 market_data_service）
    stock_snapshot = stock_detail.quote_snapshot if stock_detail else None
    company_profile = stock_detail.company_profile if stock_detail else None
    recent_events = list(stock_detail.recent_events) if stock_detail else []
    data_sources = list(stock_detail.data_sources) if stock_detail else []
    data_as_of = stock_snapshot.data_as_of if stock_snapshot else None
    stock_name = stock_detail.stock_name if stock_detail else task.stock_id
    stock_market = stock_detail.market if stock_detail else None
    stock_industry = stock_detail.industry if stock_detail else None

    return GetAnalysisResponseV2(
        analysis_id=str(task.id),
        user_id=task.user_id,
        stock_id=task.stock_id,
        scenario=task.scenario.value if hasattr(task.scenario, "value") else task.scenario,
        status=response_status,
        degrade_flags=degrade_flags,
        intervention=intervention_info,
        decision_card=decision_card,
        fit_summary=result.fit_summary if result else None,
        market_context=result.market_context if result else None,
        explanation_layer=result.explanation_layer if result else None,
        review_task=review_task_data,
        stock_snapshot=stock_snapshot,
        company_profile=company_profile,
        recent_events=recent_events,
        data_sources=data_sources,
        valid_until=valid_until,
        data_as_of=data_as_of,
        stock_name=stock_name,
        stock_market=stock_market,
        stock_industry=stock_industry,
        scenario_payload=task.scenario_payload,
    )


@router.get("", response_model=List[AnalysisRecord])
async def get_analysis_records(
    scenario: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's analysis history.

    新表路由（ANALYSIS_ROUTING["analysis"] == "new"）：返回 analysis_tasks 记录
    旧表路由：返回 analyses 记录
    """
    del offset
    logger.info("get_analysis_records", user_id=current_user.id, scenario=scenario)

    if ANALYSIS_ROUTING.get("analysis") == "new":
        return _get_analysis_records_from_new_tables(db, current_user.id, scenario, limit)

    analysis_service = AnalysisService(db)
    analyses = analysis_service.get_user_analyses(current_user.id, scenario, limit)

    records = []
    for analysis in analyses:
        stock_name = analysis.stock.stock_name if analysis.stock else "未知股票"
        records.append(
            AnalysisRecord(
                id=str(analysis.id),  # 统一为字符串
                scenario=analysis.scenario.value,
                stock_id=analysis.stock_id,
                stock_name=stock_name,
                created_at=analysis.created_at,
                status=analysis.status.value,
                headline=analysis.headline,
            )
        )

    return records


def _get_analysis_records_from_new_tables(
    db: Session, user_id: int, scenario: Optional[str], limit: int
) -> List[AnalysisRecord]:
    """从新表（analysis_tasks + analysis_results）获取分析历史"""
    from src.models.analysis_task import AnalysisTask
    from src.models.analysis_result import AnalysisResult
    from src.models.stock import Stock as StockModel

    query = db.query(AnalysisTask).filter(AnalysisTask.user_id == user_id)
    if scenario:
        query = query.filter(AnalysisTask.scenario == scenario)

    tasks = query.order_by(AnalysisTask.created_at.desc()).limit(limit).all()

    records = []
    for task in tasks:
        result = db.query(AnalysisResult).filter(
            AnalysisResult.analysis_task_id == task.id
        ).first()

        stock = db.query(StockModel).filter(
            StockModel.stock_id == task.stock_id
        ).first()
        stock_name = stock.stock_name if stock else "未知股票"

        records.append(
            AnalysisRecord(
                id=str(task.id),
                scenario=task.scenario.value if hasattr(task.scenario, "value") else task.scenario,
                stock_id=task.stock_id,
                stock_name=stock_name,
                created_at=task.created_at,
                status=task.status.value if hasattr(task.status, "value") else task.status,
                headline=result.headline_judgement if result else None,
            )
        )

    return records


@router.post("/{analysis_id}/record-reason", response_model=RecordReasonResponse)
async def record_focus_reason(
    analysis_id: str,
    reason_data: RecordReasonRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Persist a user-entered focus reason.

    迁移期兼容：同时接受 UUID 和 Integer 格式。
    - UUID 格式 → 写入新 watchlists 表（Phase 3 迁移后）
    - Integer 格式 → 写入旧 focus_reasons 表（向后兼容）
    """
    if _is_valid_uuid(analysis_id):
        # 新表路径：写入 watchlists 表
        if ANALYSIS_ROUTING.get("analysis") == "new":
            return _add_watchlist_from_new_path(
                db, current_user.id, analysis_id, reason_data, request
            )
        return api_error(HTTP_404_NOT_FOUND, "ANALYSIS_NOT_FOUND", "分析未找到", request)

    try:
        int_id = int(analysis_id)
    except (ValueError, TypeError):
        return api_error(HTTP_400_BAD_REQUEST, "INVALID_ANALYSIS_ID", "无效的分析 ID 格式", request)

    logger.info("record_focus_reason", analysis_id=analysis_id, user_id=current_user.id)

    analysis_service = AnalysisService(db)
    analysis = analysis_service.get_analysis(int_id, current_user.id)
    if not analysis:
        return api_error(HTTP_404_NOT_FOUND, "ANALYSIS_NOT_FOUND", "分析未找到", request)

    # 旧路径：写入 focus_reasons 表
    from src.models.watchlist import FocusReason as FocusReasonModel
    focus_reason = FocusReasonModel(
        user_id=current_user.id,
        analysis_id=int_id,
        stock_id=reason_data.stock_id,
        reason=reason_data.reason,
    )
    db.add(focus_reason)
    db.commit()
    db.refresh(focus_reason)
    return RecordReasonResponse(
        id=str(focus_reason.id),
        user_id=focus_reason.user_id,
        stock_id=focus_reason.stock_id,
        focus_reason=focus_reason.reason or "",
        created_at=focus_reason.created_at,
        updated_at=focus_reason.updated_at,
    )


def _add_watchlist_from_new_path(
    db: Session, user_id: int, analysis_id: str, reason_data: RecordReasonRequest,
    request: Optional[Request] = None,
):
    """新表路径：将关注理由写入 watchlists 表（合并设计）"""
    import uuid as uuid_lib
    from src.models.watchlist_v2 import Watchlist, AddedFromScenarioEnum

    uuid_val = uuid_lib.UUID(analysis_id)

    # 查找 analysis_tasks 获取场景信息
    from src.models.analysis_task import AnalysisTask
    task = db.query(AnalysisTask).filter(
        AnalysisTask.id == uuid_val,
        AnalysisTask.user_id == user_id,
    ).first()
    if not task:
        return api_error(HTTP_404_NOT_FOUND, "ANALYSIS_NOT_FOUND", "分析未找到", request)

    # 枚举按 .value 落库（PG enum 实际存小写字符串）
    scenario_str = task.scenario.value if hasattr(task.scenario, "value") else task.scenario
    scenario_map = {
        "single_stock_check": AddedFromScenarioEnum.SINGLE_STOCK_CHECK,
        "pre_trade_check": AddedFromScenarioEnum.PRE_TRADE_CHECK,
        "post_trade_review": AddedFromScenarioEnum.POST_TRADE_REVIEW,
    }
    added_from = scenario_map.get(scenario_str, None)

    # 查找是否已存在（upsert 路径）
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.stock_id == reason_data.stock_id,
    ).first()

    if existing:
        # 幂等更新：同用户同股票的第二次写入只更新 focus_reason
        existing.focus_reason = reason_data.reason
        existing.added_from_scenario = added_from
        existing.source_analysis_id = uuid_val
        db.commit()
        db.refresh(existing)
        return RecordReasonResponse(
            id=str(existing.id),
            user_id=int(existing.user_id),
            stock_id=existing.stock_id,
            focus_reason=existing.focus_reason or "",
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )

    watchlist = Watchlist(
        user_id=user_id,
        stock_id=reason_data.stock_id,
        focus_reason=reason_data.reason,
        added_from_scenario=added_from,
        source_analysis_id=uuid_val,
        notify_on_events=True,
    )
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)

    return RecordReasonResponse(
        id=str(watchlist.id),
        user_id=int(user_id),
        stock_id=watchlist.stock_id,
        focus_reason=watchlist.focus_reason or "",
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at,
    )
