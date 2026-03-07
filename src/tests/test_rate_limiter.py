"""Tests for daily rate limiter — daily limit, channel isolation, reset."""

from __future__ import annotations

import pytest

from pipeline.rate_limiter import DailyRateLimiter, RAMP_LIMIT


@pytest.fixture
def rl(tmp_path):
    path = tmp_path / "counter.json"
    return DailyRateLimiter(daily_limit=5, state_path=path)


class TestDailyRateLimiter:
    def test_initial_can_send(self, rl):
        assert rl.can_send("instantly") is True
        assert rl.remaining("instantly") == 5

    def test_record_decrements_remaining(self, rl):
        rl.record_send("instantly")
        assert rl.remaining("instantly") == 4
        assert rl.can_send("instantly") is True

    def test_blocks_at_limit(self, rl):
        for _ in range(5):
            rl.record_send("instantly")
        assert rl.can_send("instantly") is False
        assert rl.remaining("instantly") == 0

    def test_channel_isolation(self, rl):
        for _ in range(5):
            rl.record_send("instantly")
        assert rl.can_send("instantly") is False
        assert rl.can_send("ghl") is True
        assert rl.remaining("ghl") == 5

    def test_persistence(self, tmp_path):
        path = tmp_path / "counter.json"
        rl1 = DailyRateLimiter(daily_limit=5, state_path=path)
        rl1.record_send("ghl")
        rl1.record_send("ghl")

        rl2 = DailyRateLimiter(daily_limit=5, state_path=path)
        assert rl2.remaining("ghl") == 3

    def test_get_counts(self, rl):
        rl.record_send("instantly")
        rl.record_send("ghl")
        rl.record_send("ghl")
        counts = rl.get_counts()
        assert counts["instantly"] == 1
        assert counts["ghl"] == 2
