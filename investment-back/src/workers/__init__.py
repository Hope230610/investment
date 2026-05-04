"""Workers package — async job dispatch and execution.

Architecture:
  - dispatcher: called by FastAPI to enqueue a job (fire-and-forget)
  - tasks: the actual job body, same logic as the old process_analysis_v2
  - worker_main: entry point for `python -m src.workers`

API layer stays thin: it writes the task record and enqueues.
Worker process owns the heavy work (market data + LLM + DB writes).
"""
from src.workers.tasks import run_analysis_job

__all__ = ["run_analysis_job"]
