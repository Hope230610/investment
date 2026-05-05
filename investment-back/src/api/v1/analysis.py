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
from src.models.stock import Stock as StockModel
from src.models.user import User
from src.schemas.analysis import (
    AnalysisCreate,
    AnalysisCreateResponse,
    AnalysisRecord,
    GetAnalysisResponseV2,
    ReviewTask,
)
from src.schemas.stock import StockDetail
from src.schemas.watchlist import RecordReasonRequest, RecordReasonResponse
from src.services.analysis_service import _is_valid_uuid, AnalysisService
from src.services.entitlement_service import EntitlementLimitExceeded, EntitlementService
from src.services.growth_service import GrowthService
from src.services.market_data_service import MarketDataService
from src.services.portfolio_service import PortfolioService
from src.workers.dispatcher import enqueue_analysis_job


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
) -> StockDetail | JSONResponse:
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
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    """Create a real-data analysis job.

    Writes the task record and dispatches execution to the async worker
    (BackgroundTasks in dev via RQ_ASYNC=True; RQ queue in production).
    """
    logger.info(
        "create_analysis",
        scenario=analysis_data.scenario.value,
        stock_id=analysis_data.stock_id,
        user_id=current_user.id,
    )

    normalizer = (
        market_data_service.normalize_stock_id
        if hasattr(market_data_service, "normalize_stock_id")
        else MarketDataService().normalize_stock_id
    )
    try:
        market, stock_code = normalizer(analysis_data.stock_id)
    except ValueError:
        return api_error(404, "STOCK_NOT_FOUND", "鑲＄エ鏍囪瘑鏃犳晥", request)

    normalized_stock_id = f"{market}{stock_code}"
    if normalized_stock_id != analysis_data.stock_id:
        analysis_data = analysis_data.model_copy(update={"stock_id": normalized_stock_id})

    payload = dict(analysis_data.scenario_payload or {})
    display_stock_name = str(payload.get("stock_name") or normalized_stock_id).strip() or normalized_stock_id
    if hasattr(db, "query"):
        stock = db.query(StockModel).filter(StockModel.stock_id == normalized_stock_id).first()
        if not stock:
            stock = StockModel(
                stock_id=normalized_stock_id,
                stock_name=display_stock_name,
                market=market,
            )
            db.add(stock)
            db.commit()
        else:
            if stock.stock_name == stock.stock_id and display_stock_name != normalized_stock_id:
                stock.stock_name = display_stock_name
                db.commit()

    payload.pop("holding_context", None)
    payload.pop("growth_caution_context", None)

    holding_context = PortfolioService(db).get_holding_context(current_user.id, analysis_data.stock_id)
    if holding_context:
        payload["holding_context"] = holding_context
    if hasattr(db, "query"):
        payload["growth_caution_context"] = GrowthService(db).build_caution_context(current_user.id).model_dump(mode="json")
    analysis_data = analysis_data.model_copy(update={"scenario_payload": payload})

    if hasattr(db, "query"):
        try:
            EntitlementService(db).assert_within_limit(current_user.id, "daily_analysis", increment=True)
        except EntitlementLimitExceeded as exc:
            return api_error(
                HTTP_409_CONFLICT,
                "ENTITLEMENT_LIMIT_EXCEEDED",
                f"{exc.usage_key} 已达到当前方案限制",
                request,
            )

    analysis_service = AnalysisService(db)
    result_obj = analysis_service.create_analysis(current_user.id, analysis_data)

    task_uuid = str(result_obj.id)
    enqueue_analysis_job(task_uuid, background_tasks)
    db.refresh(result_obj)
    return AnalysisCreateResponse(
        id=task_uuid,
        status=result_obj.status.value,
    )


# Analysis job execution is dispatched to src/workers/ (RQ queue in prod; BackgroundTasks in dev).


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
        ReviewTaskModel.user_id == user_id,
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
    elif task.status == AnalysisStatusEnum.FAILED:
        if task.error_message:
            degrade_flags.append(f"analysis_error: {task.error_message}")
        else:
            degrade_flags.append("analysis_error")

    analysis_template_version = None
    analysis_policy_version = None
    if result and result.detail_panels:
        metadata = result.detail_panels.get("metadata") if isinstance(result.detail_panels, dict) else None
        if isinstance(metadata, dict):
            stored_flags = metadata.get("degrade_flags")
            if isinstance(stored_flags, list):
                for flag in stored_flags:
                    if isinstance(flag, str) and flag not in degrade_flags:
                        degrade_flags.append(flag)
            analysis_template_version = metadata.get("analysis_template_version")
            analysis_policy_version = metadata.get("analysis_policy_version")
            prompt_template_version = metadata.get("prompt_template_version")
            if prompt_template_version and not analysis_template_version:
                analysis_template_version = prompt_template_version

    # 决策卡
    if result:
        # valid_until = review_at + 7 天（与 generation_service 保持一致）
        from datetime import timedelta
        valid_until = result.review_at + timedelta(days=7) if result.review_at else None
        timestamp = result.created_at
        confidence = result.confidence_level or "medium"
        decision_card = {
            "headline_judgement": result.headline_judgement or "（分析中）",
            "key_reason_summary": result.key_reason_summary or [],
            "user_fit_summary": result.user_fit_summary or {"fit": "", "unfit": ""},
            "next_step_actions": result.next_step_actions or [],
            "primary_risks": result.primary_risks or "",
            "review_at": result.review_at,
            "valid_until": valid_until,
            "timestamp": timestamp,
            # 证据结构（本次新增）
            "supporting_evidence": result.supporting_evidence or [],
            "counter_evidence": result.counter_evidence or [],
            "invalidation_conditions": result.invalidation_conditions or [],
            "confidence_level": confidence,
            "confidence": confidence,
        }
        intervention_info = None
        if result.intervention:
            intervention_info = {
                "behavior_type": result.intervention.get("behavior_type", ""),
                "severity": result.intervention.get("severity", "medium"),
                "questions": result.intervention.get("questions", []),
            }
    else:
        valid_until = task.expired_at
        timestamp = task.updated_at or task.created_at
        decision_card = _build_pending_decision_card(task, response_status, timestamp, valid_until)
        intervention_info = None

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
    stored_stock = db.query(StockModel).filter(StockModel.stock_id == task.stock_id).first()
    stock_name = (
        stock_detail.stock_name
        if stock_detail
        else (stored_stock.stock_name if stored_stock else task.stock_id)
    )
    stock_market = stock_detail.market if stock_detail else (stored_stock.market if stored_stock else None)
    stock_industry = stock_detail.industry if stock_detail else (stored_stock.industry if stored_stock else None)

    return GetAnalysisResponseV2(
        analysis_id=str(task.id),
        user_id=task.user_id,
        stock_id=task.stock_id,
        scenario=task.scenario.value if hasattr(task.scenario, "value") else task.scenario,
        status=response_status,
        degrade_flags=degrade_flags,
        analysis_template_version=analysis_template_version,
        analysis_policy_version=analysis_policy_version,
        intervention=intervention_info,
        decision_card=decision_card,
        fit_summary=result.fit_summary if result else None,
        market_context=result.market_context if result else None,
        explanation_layer=result.explanation_layer if result else None,
        detail_panels=result.detail_panels if result else None,
        review_task=review_task_data,
        stock_snapshot=stock_snapshot,
        company_profile=company_profile,
        recent_events=recent_events,
        data_sources=data_sources,
        valid_until=valid_until,
        data_as_of=data_as_of,
        timestamp=data_as_of or (result.created_at if result else timestamp),
        stock_name=stock_name,
        stock_market=stock_market,
        stock_industry=stock_industry,
        scenario_payload=task.scenario_payload,
        holding_context=(task.scenario_payload or {}).get("holding_context") if task.scenario_payload else None,
    )


def _build_pending_decision_card(
    task,
    response_status: str,
    timestamp: Optional[datetime],
    valid_until: Optional[datetime],
) -> dict:
    """Return a schema-complete card while the async job is not ready yet."""
    failed = response_status == "failed"
    stock_id = getattr(task, "stock_id", "该股票")
    error_message = getattr(task, "error_message", None)
    headline = "分析失败，请稍后重试" if failed else "分析正在生成中，请稍后刷新"
    primary_risks = (
        "本次分析尚未形成可用结论，请不要基于当前占位内容做投资判断。"
        if not failed
        else "本次分析未成功生成，当前没有足够证据支持任何方向性判断。"
    )
    action = (
        "稍后重试分析；若持续失败，请检查股票标识或外部行情服务状态。"
        if failed
        else "等待分析完成后再阅读证据、反方证据和失效条件。"
    )
    if failed and error_message:
        action = f"{action} 错误信息：{error_message}"

    return {
        "headline_judgement": headline,
        "key_reason_summary": [],
        "user_fit_summary": {
            "fit": "适合先等待完整证据后再判断。",
            "unfit": "不适合在分析未完成或失败时直接行动。",
        },
        "next_step_actions": [action],
        "primary_risks": primary_risks,
        "review_at": valid_until or getattr(task, "expired_at", None),
        "valid_until": valid_until,
        "timestamp": timestamp,
        "supporting_evidence": [],
        "counter_evidence": [],
        "invalidation_conditions": [
            f"{stock_id} 的分析任务未返回完整证据前，当前占位结论无效。",
        ],
        "confidence_level": "low",
        "confidence": "low",
    }


@router.get("", response_model=List[AnalysisRecord])
async def get_analysis_records(
    scenario: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's analysis history from analysis_tasks + analysis_results."""
    del offset
    logger.info("get_analysis_records", user_id=current_user.id, scenario=scenario)

    return _get_analysis_records_from_new_tables(db, current_user.id, scenario, limit)


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
    """Persist a user-entered focus reason (UUID path only; integer IDs are no longer supported)."""
    if not _is_valid_uuid(analysis_id):
        return api_error(HTTP_400_BAD_REQUEST, "INVALID_ANALYSIS_ID", "无效的分析 ID 格式，请使用 UUID", request)

    return _add_watchlist_from_new_path(
        db, current_user.id, analysis_id, reason_data, request
    )


def _add_watchlist_from_new_path(
    db: Session, user_id: int, analysis_id: str, reason_data: RecordReasonRequest,
    request: Optional[Request] = None,
):
    """新表路径：将关注理由写入 watchlists 表（合并设计）"""
    import uuid as uuid_lib
    from src.models.watchlist_v2 import AddedFromScenarioEnum
    from src.services.watchlist_service import WatchlistService

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
    try:
        item = WatchlistService(db).upsert_watchlist_item(
            user_id,
            reason_data.stock_id,
            focus_reason=reason_data.reason,
            focus_reason_provided=True,
            added_from_scenario=added_from,
            source_analysis_id=uuid_val,
            notify_on_events=True,
        )
    except ValueError as exc:
        if str(exc) == "STOCK_NOT_FOUND":
            return api_error(HTTP_404_NOT_FOUND, "STOCK_NOT_FOUND", "股票未找到", request)
        raise

    return RecordReasonResponse(
        id=item["id"],
        user_id=item["user_id"],
        stock_id=item["stock_id"],
        focus_reason=item["focus_reason"] or "",
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )
