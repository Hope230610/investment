from datetime import datetime
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.analysis import ReviewTask as ReviewTaskModel
from src.models.analysis import ReviewTaskStatus
from src.schemas.analysis import ReviewTask
from src.schemas.common import ErrorDetail, ErrorResponse


router = APIRouter()
logger = structlog.get_logger()


@router.get("", response_model=List[ReviewTask])
async def get_reviews(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return persisted review tasks for the current user."""
    logger.info("get_reviews", user_id=current_user.id)

    tasks = (
        db.query(ReviewTaskModel)
        .filter(ReviewTaskModel.user_id == current_user.id)
        .order_by(ReviewTaskModel.review_at.asc())
        .all()
    )

    now = datetime.now()
    has_updates = False
    for task in tasks:
        if task.status == ReviewTaskStatus.PENDING and task.review_at <= now:
            task.status = ReviewTaskStatus.EXPIRED
            has_updates = True

    if has_updates:
        db.commit()
        for task in tasks:
            db.refresh(task)

    logger.debug("review_tasks_count", count=len(tasks))
    return tasks


def api_error(
    status_code: int,
    code: str,
    message: str,
    request: Optional[Request] = None,
) -> JSONResponse:
    request_id = request.headers.get("x-request-id") if request else None
    body = ErrorResponse(error=ErrorDetail(
        code=code,
        message=message,
        request_id=request_id,
    ))
    return JSONResponse(status_code=status_code, content=body.model_dump())


@router.patch("/by-analysis/{analysis_task_id}", response_model=ReviewTask)
async def update_review_by_analysis_id(
    analysis_task_id: str,
    request: Request,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """通过 analysis_task_id 更新关联的 ReviewTask。

    前端 ResultPage 在 post-trade-review 提交后调用，
    用 UUID 格式的 analysis_task_id 定位 ReviewTask 并写入 review_result。
    """
    logger.info("update_review_by_analysis_id", analysis_task_id=analysis_task_id, user_id=current_user.id)

    try:
        uuid_val = UUID(analysis_task_id)
    except ValueError:
        return api_error(400, "INVALID_UUID", "Invalid analysis_task_id format", request)

    task = db.query(ReviewTaskModel).filter(
        ReviewTaskModel.analysis_task_id == uuid_val,
        ReviewTaskModel.user_id == current_user.id,
    ).first()

    if not task:
        return api_error(404, "REVIEW_TASK_NOT_FOUND", "Review task not found", request)

    if "review_result" in update_data:
        task.review_result = update_data["review_result"]

    if update_data.get("mark_completed"):
        task.status = ReviewTaskStatus.COMPLETED

    db.commit()
    db.refresh(task)
    status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)
    logger.info("review_task_updated_by_analysis", task_id=task.id, status=status_str)

    return task


@router.patch("/{review_task_id}", response_model=ReviewTask)
async def update_review_task(
    review_task_id: int,
    request: Request,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """通过整数 review_task_id 更新复盘任务。"""
    logger.info("update_review_task", review_task_id=review_task_id, user_id=current_user.id)

    task = db.query(ReviewTaskModel).filter(
        ReviewTaskModel.id == review_task_id,
        ReviewTaskModel.user_id == current_user.id,
    ).first()

    if not task:
        return api_error(404, "REVIEW_TASK_NOT_FOUND", "Review task not found", request)

    if "review_result" in update_data:
        task.review_result = update_data["review_result"]

    if update_data.get("mark_completed"):
        task.status = ReviewTaskStatus.COMPLETED

    db.commit()
    db.refresh(task)
    status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)
    logger.info("review_task_updated", task_id=task.id, status=status_str)

    return task

