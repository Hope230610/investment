from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.api.v1.analysis import api_error
from src.db.session import get_db
from src.models.user import User
from src.schemas.p3 import (
    AiEvalRequest,
    AiEvalResult,
    CreateShareSnapshotRequest,
    EntitlementView,
    PublicShareSnapshot,
    ShareSnapshotPrivate,
)
from src.services.ai_eval_service import AiEvalService
from src.services.entitlement_service import EntitlementLimitExceeded, EntitlementService
from src.services.growth_service import GrowthService
from src.services.share_service import ShareService


router = APIRouter()


@router.get("/growth/caution-context")
async def get_growth_caution_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return GrowthService(db).build_caution_context(current_user.id)


@router.post("/ai-eval", response_model=AiEvalResult)
async def evaluate_ai_output(
    payload: AiEvalRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entitlement = EntitlementService(db)
    if not entitlement.view(current_user.id).feature_flags.get("ai_eval"):
        return api_error(403, "ENTITLEMENT_REQUIRED", "当前方案暂未开放 AI 评测接口", request)
    return AiEvalService().evaluate(
        payload.output,
        case_id=payload.case_id,
        holding_context_source=payload.holding_context_source,
    )


@router.get("/entitlements", response_model=EntitlementView)
async def get_entitlements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return EntitlementService(db).view(current_user.id)


@router.post("/shares", response_model=ShareSnapshotPrivate)
async def create_share_snapshot(
    payload: CreateShareSnapshotRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return ShareService(db).create_from_analysis(
            current_user.id,
            payload.source_id,
            privacy_level=payload.privacy_level,
            expires_in_days=payload.expires_in_days,
        )
    except EntitlementLimitExceeded as exc:
        return api_error(409, "ENTITLEMENT_LIMIT_EXCEEDED", f"{exc.usage_key} 已达到当前方案限制", request)
    except ValueError as exc:
        code = str(exc)
        status = 404 if code in {"ANALYSIS_NOT_FOUND", "ANALYSIS_RESULT_NOT_READY"} else 400
        return api_error(status, code, code, request)


@router.delete("/shares/{share_id}")
async def revoke_share_snapshot(
    share_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not ShareService(db).revoke(current_user.id, share_id):
        return api_error(404, "SHARE_NOT_FOUND", "分享卡片不存在", request)
    return {"message": "revoked"}


@router.get("/shares/{share_id}", response_model=ShareSnapshotPrivate)
async def get_my_share_snapshot(
    share_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snapshot = ShareService(db).get_private(current_user.id, share_id)
    if not snapshot:
        return api_error(404, "SHARE_NOT_FOUND", "分享卡片不存在", request)
    return snapshot


@router.get("/public/shares/{share_id}", response_model=PublicShareSnapshot)
async def get_public_share_snapshot(
    share_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    snapshot = ShareService(db).get_public(share_id)
    if not snapshot:
        return JSONResponse(status_code=404, content={"error": {"code": "SHARE_NOT_AVAILABLE", "message": "分享卡片不存在、已撤销或已过期"}})
    return snapshot
