"""Bounded in-process worker that executes queued runs."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from app.db.repositories import SqlRunRepository
from app.db.session import SessionLocal
from app.engine.execution_service import execute_run

log = logging.getLogger(__name__)
_executor: ThreadPoolExecutor | None = None
_session_factory = SessionLocal


def set_session_factory(factory) -> None:
    """Tests call this so the worker uses the same database as the API."""
    global _session_factory
    _session_factory = factory


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        workers = int(os.environ.get("MAX_CONCURRENT_RUNS", "1"))
        _executor = ThreadPoolExecutor(
            max_workers=max(1, workers), thread_name_prefix="run-worker"
        )
    return _executor


def _safe_execute(run_id: str) -> None:
    try:
        execute_run(run_id, SqlRunRepository(session_factory=_session_factory))
    except Exception:
        log.exception("Run %s crashed", run_id)


def submit_run(run_id: str) -> None:
    _get_executor().submit(_safe_execute, run_id)
