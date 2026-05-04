"""RQ Worker entry point.

Run with:
    python -m src.workers

Or for a specific queue:
    rq worker analysis --url redis://localhost:6379/0
"""
from __future__ import annotations

import sys


def main() -> None:
    """Start an RQ worker listening on the "analysis" queue.

    redis and rq are imported inside this function so that:
    1. The API server does not require them to start (RQ_ASYNC=True path).
    2. The user gets a clear error message if the packages are missing,
       rather than a confusing ModuleNotFoundError at import time.
    """
    from src.core.config import get_settings

    settings = get_settings()

    if settings.RQ_ASYNC:
        print(
            "RQ_ASYNC=True: refusing to run worker process. "
            "Jobs run in-process inside the API server. "
            "Set RQ_ASYNC=false to enable a real RQ worker.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from redis import Redis as RedisCls
        from rq import Worker as RQWorkerCls
    except ImportError as exc:
        print(
            f"Cannot start RQ worker: {exc}.\n"
            "Install required packages: pip install rq redis\n"
            "Or set RQ_ASYNC=true to run jobs in-process without Redis.",
            file=sys.stderr,
        )
        sys.exit(1)

    redis_conn = RedisCls.from_url(settings.REDIS_URL, decode_responses=False)
    worker = RQWorkerCls(["analysis"], connection=redis_conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
