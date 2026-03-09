"""Tests for warm follow-up scheduler."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from pipeline import scheduler as scheduler_module


@pytest.fixture(autouse=True)
def _use_tmp_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("SCHEDULER_TIMEZONE", "America/Chicago")
    scheduler_module.stop_scheduler()
    scheduler_module.reset_scheduler_state()
    yield
    scheduler_module.stop_scheduler()


class TestSchedulerConfig:
    def test_job_kwargs_use_6am_america_chicago(self):
        kwargs = scheduler_module.get_scheduler_job_kwargs()

        assert kwargs["hour"] == 6
        assert kwargs["minute"] == 0
        assert kwargs["timezone"] == "America/Chicago"

    def test_business_date_uses_local_scheduler_timezone(self):
        reference_time = datetime(2026, 3, 9, 1, 30, tzinfo=timezone.utc)

        run_date = scheduler_module._business_date(reference_time)

        assert run_date == "2026-03-08"


class TestScheduledRunGuards:
    @pytest.mark.asyncio
    async def test_prevents_overlapping_runs(self):
        scheduler_module._save_state(
            {
                "running": True,
                "runningStartedAt": "2026-03-09T11:00:00+00:00",
                "lastRunDate": None,
                "lastStatus": None,
                "lastCompletedAt": None,
            }
        )

        result = await scheduler_module.run_scheduled_followups(
            reference_time=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc)
        )

        assert result["status"] == "already_running"

    @pytest.mark.asyncio
    async def test_prevents_second_run_same_day_without_force(self):
        with patch(
            "pipeline.scheduler.run_followup_orchestrator",
            AsyncMock(return_value={"status": "complete", "briefing_path": "x"}),
        ) as mock_run:
            first = await scheduler_module.run_scheduled_followups(
                reference_time=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc)
            )
            second = await scheduler_module.run_scheduled_followups(
                reference_time=datetime(2026, 3, 9, 18, 0, tzinfo=timezone.utc)
            )

        assert first["status"] == "complete"
        assert second["status"] == "already_ran_today"
        assert mock_run.await_count == 1

    @pytest.mark.asyncio
    async def test_force_allows_second_run_same_day(self):
        with patch(
            "pipeline.scheduler.run_followup_orchestrator",
            AsyncMock(return_value={"status": "complete", "briefing_path": "x"}),
        ) as mock_run:
            await scheduler_module.run_scheduled_followups(
                reference_time=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc)
            )
            forced = await scheduler_module.run_scheduled_followups(
                force=True,
                reference_time=datetime(2026, 3, 9, 18, 0, tzinfo=timezone.utc)
            )

        assert forced["status"] == "complete"
        assert mock_run.await_count == 2


class TestSchedulerRegistration:
    def test_start_scheduler_registers_daily_job(self):
        recorded = {}

        class FakeCronTrigger:
            def __init__(self, **kwargs):
                recorded["trigger_kwargs"] = kwargs

        class FakeScheduler:
            def __init__(self, timezone=None, job_defaults=None):
                recorded["scheduler_timezone"] = timezone
                recorded["job_defaults"] = job_defaults
                self.running = False

            def add_job(self, func, trigger=None, **kwargs):
                recorded["job_func"] = func
                recorded["job_trigger"] = trigger
                recorded["job_kwargs"] = kwargs

            def start(self):
                self.running = True
                recorded["started"] = True

            def shutdown(self, wait=False):
                self.running = False
                recorded["shutdown_wait"] = wait

        with patch(
            "pipeline.scheduler._load_apscheduler",
            return_value=(FakeScheduler, FakeCronTrigger),
        ):
            scheduler = scheduler_module.start_scheduler()

        assert scheduler.running is True
        assert recorded["scheduler_timezone"] == "America/Chicago"
        assert recorded["job_defaults"] == {"coalesce": True, "max_instances": 1}
        assert recorded["trigger_kwargs"] == {
            "hour": 6,
            "minute": 0,
            "timezone": "America/Chicago",
        }
        assert recorded["job_kwargs"]["id"] == scheduler_module.JOB_ID
        assert recorded["job_kwargs"]["kwargs"] == {"force": False}
        assert recorded["job_kwargs"]["max_instances"] == 1

        scheduler_module.stop_scheduler()
