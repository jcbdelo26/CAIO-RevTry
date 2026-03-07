"""Tests for circuit breaker — state transitions, trip on 3 failures, recovery."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from pipeline.circuit_breaker import CircuitBreaker, FAILURE_THRESHOLD, COOLDOWN_SECONDS


@pytest.fixture
def cb(tmp_path):
    path = tmp_path / "cb_state.json"
    return CircuitBreaker(state_path=path)


class TestCircuitBreaker:
    def test_initial_state_closed(self, cb):
        assert cb.get_state("instantly") == "CLOSED"
        assert not cb.is_open("instantly")

    def test_single_failure_stays_closed(self, cb):
        cb.record_failure("instantly")
        assert cb.get_state("instantly") == "CLOSED"
        assert not cb.is_open("instantly")

    def test_trips_after_3_failures(self, cb):
        for _ in range(FAILURE_THRESHOLD):
            cb.record_failure("instantly")
        assert cb.get_state("instantly") == "OPEN"
        assert cb.is_open("instantly")

    def test_success_resets_to_closed(self, cb):
        for _ in range(FAILURE_THRESHOLD):
            cb.record_failure("instantly")
        assert cb.get_state("instantly") == "OPEN"
        # Simulate cooldown by manipulating state
        cb._state["instantly"]["tripped_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=COOLDOWN_SECONDS + 1)
        ).isoformat()
        cb._save()
        # Should be HALF_OPEN after cooldown
        assert cb.get_state("instantly") == "HALF_OPEN"
        # Success resets to CLOSED
        cb.record_success("instantly")
        assert cb.get_state("instantly") == "CLOSED"

    def test_channel_isolation(self, cb):
        """Failures in one channel don't affect others."""
        for _ in range(FAILURE_THRESHOLD):
            cb.record_failure("instantly")
        assert cb.is_open("instantly")
        assert not cb.is_open("ghl")
        assert not cb.is_open("heyreach")

    def test_trip_all(self, cb):
        cb.trip_all()
        assert cb.is_open("instantly")
        assert cb.is_open("ghl")
        assert cb.is_open("heyreach")
        assert cb.is_open("apollo")

    @pytest.mark.asyncio
    async def test_call_wraps_success(self, cb):
        mock_fn = AsyncMock(return_value="ok")
        result = await cb.call("instantly", mock_fn, "arg1")
        assert result == "ok"
        mock_fn.assert_called_once_with("arg1")
        assert cb.get_state("instantly") == "CLOSED"

    @pytest.mark.asyncio
    async def test_call_wraps_failure(self, cb):
        mock_fn = AsyncMock(side_effect=RuntimeError("API down"))
        with pytest.raises(RuntimeError, match="API down"):
            await cb.call("instantly", mock_fn)
        # Should have 1 failure recorded
        assert cb._state["instantly"]["consecutive_failures"] == 1

    def test_persistence(self, tmp_path):
        path = tmp_path / "cb_state.json"
        cb1 = CircuitBreaker(state_path=path)
        cb1.record_failure("ghl")
        cb1.record_failure("ghl")

        # Load fresh instance
        cb2 = CircuitBreaker(state_path=path)
        assert cb2._state["ghl"]["consecutive_failures"] == 2
