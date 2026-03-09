"""Tests for dispatch orchestrator — GHL-only dispatch, deferred channels, safety checks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from dashboard.storage import approve_draft, get_draft, save_draft, update_draft_ghl_result
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


def _create_approved_draft(
    draft_id="d-001",
    tier="1",
    channel=Channel.GHL,
    ghl_contact_id="ghl-contact-123",
    contact_id="jane@acme.com",
    contact_email=None,
):
    """Create, approve, and set ghl_push_result on a draft."""
    draft = CampaignDraft(
        draftId=draft_id,
        contactId=contact_id,
        contactEmail=contact_email,
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
    if ghl_contact_id:
        update_draft_ghl_result(draft_id, {"ghl_contact_id": ghl_contact_id})
    return draft


class TestDispatcher:
    @pytest.mark.asyncio
    async def test_dispatches_ghl_draft(self, tmp_path):
        _create_approved_draft()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(return_value={"messageId": "msg-1"})
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 1
        assert result.failed == 0
        mock_ghl.send_email.assert_called_once()
        call_kwargs = mock_ghl.send_email.call_args.kwargs
        assert call_kwargs["contact_id"] == "ghl-contact-123"
        assert call_kwargs["subject"] == "AI Strategy for You"

    @pytest.mark.asyncio
    async def test_dispatches_ghl_pipeline_draft_with_contact_email(self, tmp_path):
        """GHL pipeline drafts use GHL ID as contact_id, email in contact_email."""
        _create_approved_draft(
            draft_id="d-ghl-pipe",
            contact_id="tPnm9gvEJjxMLlJ8EJK3",
            contact_email="garrett@godlan.com",
            ghl_contact_id="ghl-contact-456",
        )
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(return_value={"messageId": "msg-2"})
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 1
        call_kwargs = mock_ghl.send_email.call_args.kwargs
        assert call_kwargs["contact_id"] == "ghl-contact-456"
        assert call_kwargs["to_email"] == "garrett@godlan.com"

    @pytest.mark.asyncio
    async def test_ghl_dispatch_fails_without_contact_id(self, tmp_path):
        _create_approved_draft(draft_id="d-no-ghl", ghl_contact_id=None)
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock()
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 0
        assert result.failed == 1
        assert "No GHL contact ID" in result.errors[0]
        mock_ghl.send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_fails_without_email(self, tmp_path):
        """GHL pipeline draft with no contact_email and non-email contact_id fails."""
        _create_approved_draft(
            draft_id="d-no-email",
            contact_id="tPnm9gvEJjxMLlJ8EJK3",
            contact_email=None,
            ghl_contact_id="ghl-contact-789",
        )
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock()
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 0
        assert result.failed == 1
        assert "No email address" in result.errors[0]

    @pytest.mark.asyncio
    async def test_instantly_channel_deferred(self, tmp_path):
        _create_approved_draft(draft_id="d-inst", channel=Channel.INSTANTLY)
        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
        )

        assert result.dispatched == 0
        assert result.skipped_deferred_channel == 1

    @pytest.mark.asyncio
    async def test_heyreach_channel_deferred(self, tmp_path):
        _create_approved_draft(draft_id="d-hr", channel=Channel.HEYREACH)
        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
        )

        assert result.dispatched == 0
        assert result.skipped_deferred_channel == 1

    @pytest.mark.asyncio
    async def test_rate_limit_stops_dispatch(self, tmp_path):
        _create_approved_draft()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock()
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")
        for _ in range(5):
            rl.record_send("ghl")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 0
        assert result.skipped_rate_limit == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips(self, tmp_path):
        _create_approved_draft()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock()
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        cb.trip_all()
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 0
        assert result.skipped_circuit_breaker == 1

    @pytest.mark.asyncio
    async def test_tier_restriction(self, tmp_path):
        _create_approved_draft(draft_id="d-t2", tier="2")
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock()
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
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
        _create_approved_draft(draft_id="d-dup2")

        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(return_value={"messageId": "msg-1"})
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        # First dispatches, second caught by contact window dedup
        assert result.dispatched == 1
        assert result.skipped_dedup >= 1

    @pytest.mark.asyncio
    async def test_failed_send_marks_send_failed(self, tmp_path):
        _create_approved_draft(draft_id="d-fail")
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(side_effect=Exception("SMTP timeout"))
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_drafts(
            tier_restriction=1,
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        stored = get_draft("d-fail")
        assert result.failed == 1
        assert stored is not None
        assert stored.status == DraftApprovalStatus.SEND_FAILED
        assert stored.dispatch_error == "SMTP timeout"
        assert stored.send_failed_at is not None
