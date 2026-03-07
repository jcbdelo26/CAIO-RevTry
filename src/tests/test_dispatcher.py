"""Tests for dispatch orchestrator — full flow, rate limit, circuit breaker, dedup."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from dashboard.storage import save_draft, approve_draft
from models.schemas import (
    CampaignDraft,
    CampaignDraftTrace,
    Channel,
    DraftApprovalStatus,
)
from pipeline.circuit_breaker import CircuitBreaker
from pipeline.dispatcher import dispatch_approved_drafts
from pipeline.rate_limiter import DailyRateLimiter


@pytest.fixture(autouse=True)
def _use_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


def _create_approved_draft(draft_id="d-001", tier="1", channel=Channel.INSTANTLY):
    """Create and approve a draft in storage."""
    draft = CampaignDraft(
        draftId=draft_id,
        contactId="contact-001",
        icpTier=tier,
        angleId="angle-1",
        subject="AI Strategy for You",
        body="Hello, I noticed your company...",
        channel=channel,
        bookingLink="https://caio.cx/call",
        trace=CampaignDraftTrace(
            leadSignalsUsed=["title"],
            proofPointsUsed=["case-study"],
            ctaId="cta-1",
        ),
    )
    save_draft(draft)
    approve_draft(draft_id)
    return draft


class TestDispatcher:
    @pytest.mark.asyncio
    async def test_dispatches_approved_draft(self, tmp_path):
        _create_approved_draft()
        mock_instantly = MagicMock()
        mock_instantly.send_email = AsyncMock(return_value={"id": "msg-1"})
        mock_instantly.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            instantly=mock_instantly,
        )

        assert result.dispatched == 1
        assert result.failed == 0
        mock_instantly.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_stops_dispatch(self, tmp_path):
        _create_approved_draft()
        mock_instantly = MagicMock()
        mock_instantly.send_email = AsyncMock()
        mock_instantly.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")
        # Exhaust the limit
        for _ in range(5):
            rl.record_send("instantly")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            instantly=mock_instantly,
        )

        assert result.dispatched == 0
        assert result.skipped_rate_limit == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips(self, tmp_path):
        _create_approved_draft()
        mock_instantly = MagicMock()
        mock_instantly.send_email = AsyncMock()
        mock_instantly.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        cb.trip_all()  # Trip all breakers
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            instantly=mock_instantly,
        )

        assert result.dispatched == 0
        assert result.skipped_circuit_breaker == 1

    @pytest.mark.asyncio
    async def test_tier_restriction(self, tmp_path):
        _create_approved_draft(draft_id="d-t2", tier="2")
        mock_instantly = MagicMock()
        mock_instantly.send_email = AsyncMock()
        mock_instantly.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,  # Only tier 1
            rate_limiter=rl,
            circuit_breaker=cb,
            instantly=mock_instantly,
        )

        assert result.dispatched == 0
        assert result.skipped_tier == 1

    @pytest.mark.asyncio
    async def test_no_approved_drafts(self, tmp_path):
        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            rate_limiter=rl,
            circuit_breaker=cb,
        )

        assert result.dispatched == 0

    @pytest.mark.asyncio
    async def test_dedup_skips_duplicate(self, tmp_path):
        _create_approved_draft(draft_id="d-dup1")
        _create_approved_draft(draft_id="d-dup2")  # Same content, different ID

        mock_instantly = MagicMock()
        mock_instantly.send_email = AsyncMock(return_value={"id": "msg-1"})
        mock_instantly.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            instantly=mock_instantly,
        )

        # First dispatches, second should be caught by contact window dedup
        assert result.dispatched == 1
        assert result.skipped_dedup >= 1
