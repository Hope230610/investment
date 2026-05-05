"""Task dispatcher — enqueues analysis jobs into the RQ queue.

This module is the single interface the API layer uses to schedule an
analysis job.  It abstracts away whether the job runs in-process
(RQ_ASYNC=True for development — fire-and-forget via BackgroundTasks)
or is dispatched to a real worker process (RQ_ASYNC=False for production).

Usage:
    from src.workers.dispatcher import enqueue_analysis_job
    enqueue_analysis_job(task_uuid_str)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import structlog

from src.core.config import get_settings


if TYPE_CHECKING:
    from redis import Redis
    from rq import Queue


logger = structlog.get_logger()
_settings = get_settings()

# Redis connection used by RQ — only created lazily when RQ_ASYNC=False
_redis_conn: Optional["Redis"] = None


def _get_queue() -> "Queue":
    """Return the shared RQ queue.

    redis and rq are imported here (not at module level) so that the
    in-process dev path (BackgroundTasks) does not require them.
    """
    global _redis_conn
    from rq import Queue as QueueCls

    if _redis_conn is None:
        from redis import Redis as _RedisCls
        _redis_conn = _RedisCls.from_url(_settings.REDIS_URL, decode_responses=False)
    return QueueCls("analysis", connection=_redis_conn)


def enqueue_analysis_job(
    task_uuid_str: str,
    background_tasks: "Optional[BackgroundTasks]" = None,
) -> None:
    """Dispatch an analysis job for the given task UUID.

    Dev mode (RQ_ASYNC=True, default):
        Job runs fire-and-forget in the current process via BackgroundTasks —
        the API request returns immediately without blocking.

    Production mode (RQ_ASYNC=False):
        Job is pushed to the Redis-backed RQ "analysis" queue and picked up by
        a real rq worker subprocess.  The API request returns immediately.

    Args:
        task_uuid_str: UUID of the AnalysisTask to execute.
        background_tasks: FastAPI BackgroundTasks dependency (dev mode only).
    """
    if _settings.RQ_ASYNC:
        # Dev mode: run in a background task so the API request returns at once.
        # Fall back to direct call if BackgroundTasks was not provided.
        if background_tasks is not None:
            from src.workers.tasks import run_analysis_job
            background_tasks.add_task(run_analysis_job, task_uuid_str)
        else:
            # Inline fallback for contexts where BackgroundTasks is unavailable.
            # Prefer passing background_tasks when calling from an endpoint.
            from src.workers.tasks import run_analysis_job
            run_analysis_job(task_uuid_str)
        return

    # Production mode: dispatch to a real RQ worker
    queue = _get_queue()
    queue.enqueue(
        "src.workers.tasks.run_analysis_job",
        task_uuid_str,
        job_timeout="5m",
    )
    logger.info("enqueue_analysis_job", task_id=task_uuid_str, queue="analysis")
