"""Warm follow-up scheduler.

Owns the disabled-by-default APScheduler cron configuration for the warm
follow-up generation pipeline and enforces:
- one run at a time
- one run per local business date unless forced
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from pipeline.followup_orchestrator import run_followup_orchestrator
from utils.business_time import current_business_date, get_business_timezone_name

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULER_TIMEZONE = "America/Chicago"
DEFAULT_RUN_HOUR = 6
DEFAULT_RUN_MINUTE = 0
JOB_ID = "warm_followup_daily"

_scheduler = None


def _registry_dir() -> Path:
    directory = Path(os.environ.get("REGISTRY_DIR", "registry"))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _state_path() -> Path:
    return _registry_dir() / "followup_scheduler_state.json"


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "running": False,
        "runningStartedAt": None,
        "lastRunDate": None,
        "lastStatus": None,
        "lastCompletedAt": None,
    }


def _save_state(state: dict[str, Any]) -> None:
    _state_path().write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def reset_scheduler_state() -> None:
    """Test/helper hook to clear persisted scheduler state."""
    path = _state_path()
    if path.exists():
        path.unlink()


def get_scheduler_timezone_name() -> str:
    return get_business_timezone_name()


def get_scheduler_timezone() -> ZoneInfo:
    from utils.business_time import get_business_timezone
    return get_business_timezone()


def get_scheduler_job_kwargs() -> dict[str, Any]:
    return {
        "hour": DEFAULT_RUN_HOUR,
        "minute": DEFAULT_RUN_MINUTE,
        "timezone": get_scheduler_timezone_name(),
    }


def _business_date(reference_time: Optional[datetime] = None) -> str:
    return current_business_date(reference_time)


def _load_apscheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ModuleNotFoundError as exc:
        raise ImportError(
            "apscheduler is required for pipeline.scheduler; install project dependencies first"
        ) from exc
    return BackgroundScheduler, CronTrigger


async def run_scheduled_followups(
    *,
    force: bool = False,
    reference_time: Optional[datetime] = None,
) -> dict[str, Any]:
    """Run the warm follow-up orchestrator with scheduler state guards."""
    state = _load_state()
    if state.get("running"):
        return {
            "status": "already_running",
            "briefing_date": _business_date(reference_time),
            "briefing_path": None,
            "errors": ["Warm follow-up scheduler is already running"],
        }

    run_date = _business_date(reference_time)
    if state.get("lastRunDate") == run_date and not force:
        return {
            "status": "already_ran_today",
            "briefing_date": run_date,
            "briefing_path": None,
            "errors": [],
        }

    state["running"] = True
    state["runningStartedAt"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)

    try:
        result = await run_followup_orchestrator(
            task_id=f"warm-followup-scheduled-{run_date}",
            force=force,
            reference_time=reference_time,
        )
        state["lastRunDate"] = run_date
        state["lastStatus"] = result.get("status")
        state["lastCompletedAt"] = datetime.now(timezone.utc).isoformat()
        return result
    finally:
        state["running"] = False
        _save_state(state)


def run_scheduled_followups_sync(*, force: bool = False) -> dict[str, Any]:
    """Sync wrapper used by APScheduler background jobs."""
    return asyncio.run(run_scheduled_followups(force=force))


def start_scheduler():
    """Start the warm follow-up scheduler if it is not already running."""
    global _scheduler

    if _scheduler is not None and getattr(_scheduler, "running", False):
        return _scheduler

    BackgroundScheduler, CronTrigger = _load_apscheduler()
    timezone_name = get_scheduler_timezone_name()
    job_kwargs = get_scheduler_job_kwargs()

    scheduler = BackgroundScheduler(
        timezone=timezone_name,
        job_defaults={"coalesce": True, "max_instances": 1},
    )
    scheduler.add_job(
        run_scheduled_followups_sync,
        trigger=CronTrigger(**job_kwargs),
        id=JOB_ID,
        replace_existing=True,
        kwargs={"force": False},
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    """Stop the global scheduler instance if it is running."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
