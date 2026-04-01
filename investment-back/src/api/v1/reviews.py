from datetime import datetime
from typing import List

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.analysis import ReviewTask as ReviewTaskModel
from src.models.analysis import ReviewTaskStatus
from src.schemas.analysis import ReviewTask


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
        if task.analysis is not None:
            setattr(task, "stock_id", task.analysis.stock_id)

    if has_updates:
        db.commit()
        for task in tasks:
            db.refresh(task)
            if task.analysis is not None:
                setattr(task, "stock_id", task.analysis.stock_id)

    logger.debug("review_tasks_count", count=len(tasks))
    return tasks
