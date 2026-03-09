"""Tests for warm follow-up dispatcher."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dashboard.followup_storage import (
    approve_followup_draft,
    get_followup_draft,
    save_followup_draft,
)
from models.schemas import (
    ConversationSentiment,
    ConversationStage,
    DraftApprovalStatus,
    FollowUpDraft,
    FollowUpTrigger,
    UrgencyLevel,
)
from pipeline.circuit_breaker import CircuitBreaker
from pipeline.followup_dispatcher import dispatch_approved_followups
from pipeline.rate_limiter import DailyRateLimiter


@pytest.fixture(autouse=True)
def _use_tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


def _build_followup(
    draft_id: str = "followup-1",
    *,
    status: DraftApprovalStatus = DraftApprovalStatus.PENDING,
    ghl_contact_id: str = "ghl-contact-1",
    contact_email: str = "alex@acme.com",
) -> FollowUpDraft:
    return FollowUpDraft(
        draftId=draft_id,
        contactId=f"contact-{draft_id}",
        ghlContactId=ghl_contact_id,
        sourceConversationId="conv-1",
        businessDate="2026-03-09",
        generationRunId="run-1",
        contactEmail=contact_email,
        contactName="Alex Morgan",
        companyName="Acme",
        subject="Timing options for next week",
        body=(
            "Alex,\n\n"
            "Thanks for your note on timing for next week.\n\n"
            "Dani Apgar\n"
            "Head of Sales, Chief AI Officer\n"
            "Reply STOP to unsubscribe.\n"
            "Chief AI Officer Inc. | 5700 Harper Dr, Suite 210, Albuquerque, NM 87109"
        ),
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        urgency=UrgencyLevel.HOT,
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        analysisSummary="The contact asked for timing options.",
        status=status,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )


def _seed_approved_followup(**kwargs) -> FollowUpDraft:
    draft = _build_followup(**kwargs)
    save_followup_draft(draft)
    if draft.status != DraftApprovalStatus.APPROVED:
        approve_followup_draft(draft.draft_id)
    return draft


class TestFollowupDispatcher:
    @pytest.mark.asyncio
    async def test_dispatches_approved_followup(self, tmp_path):
        draft = _seed_approved_followup()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(return_value={"messageId": "msg-1"})
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        stored = get_followup_draft(draft.draft_id)
        assert result.dispatched == 1
        assert result.failed == 0
        assert stored is not None
        assert stored.status == DraftApprovalStatus.DISPATCHED
        mock_ghl.send_email.assert_called_once()
        kwargs = mock_ghl.send_email.call_args.kwargs
        assert kwargs["contact_id"] == "ghl-contact-1"
        assert kwargs["to_email"] == "alex@acme.com"

    @pytest.mark.asyncio
    async def test_dispatch_uses_latest_saved_subject_and_body(self, tmp_path):
        draft = _seed_approved_followup()
        latest = get_followup_draft(draft.draft_id)
        assert latest is not None
        latest.subject = "Edited subject for dispatch"
        latest.body = "Edited body for dispatch"
        save_followup_draft(latest)

        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(return_value={"messageId": "msg-1"})
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 1
        kwargs = mock_ghl.send_email.call_args.kwargs
        assert kwargs["subject"] == "Edited subject for dispatch"
        assert kwargs["body"] == "Edited body for dispatch"

    @pytest.mark.asyncio
    async def test_no_approved_followups_returns_empty_result(self, tmp_path):
        save_followup_draft(_build_followup(status=DraftApprovalStatus.PENDING))

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
        )

        assert result.dispatched == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_rate_limit_skips_warm_dispatch(self, tmp_path):
        _seed_approved_followup()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock()
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=1, state_path=tmp_path / "rl.json")
        rl.record_send("ghl")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 0
        assert result.skipped_rate_limit == 1
        mock_ghl.send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_warm_dispatch(self, tmp_path):
        _seed_approved_followup()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock()
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        cb.record_failure("ghl")
        cb.record_failure("ghl")
        cb.record_failure("ghl")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        assert result.dispatched == 0
        assert result.skipped_circuit_breaker == 1
        mock_ghl.send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_dedup_uses_canonical_ghl_identity(self, tmp_path):
        draft = _seed_approved_followup(ghl_contact_id="ghl-canonical-1")
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(return_value={"messageId": "msg-1"})
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        with patch(
            "pipeline.followup_dispatcher.check_dedup",
            AsyncMock(return_value=(False, None)),
        ) as mock_check_dedup:
            result = await dispatch_approved_followups(
                rate_limiter=rl,
                circuit_breaker=cb,
                ghl=mock_ghl,
            )

        assert result.dispatched == 1
        assert mock_check_dedup.await_args.kwargs["contact_id"] == "ghl-canonical-1"
        assert mock_check_dedup.await_args.kwargs["channel"] == "ghl"

    @pytest.mark.asyncio
    async def test_missing_ghl_contact_id_marks_send_failed(self, tmp_path):
        draft = _seed_approved_followup(ghl_contact_id="")
        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
        )

        stored = get_followup_draft(draft.draft_id)
        assert result.failed == 1
        assert stored is not None
        assert stored.status == DraftApprovalStatus.SEND_FAILED
        assert "No GHL contact ID" in stored.dispatch_error

    @pytest.mark.asyncio
    async def test_send_failure_marks_send_failed(self, tmp_path):
        draft = _seed_approved_followup()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(side_effect=Exception("SMTP timeout"))
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
            ghl=mock_ghl,
        )

        stored = get_followup_draft(draft.draft_id)
        assert result.failed == 1
        assert stored is not None
        assert stored.status == DraftApprovalStatus.SEND_FAILED
        assert stored.dispatch_error == "SMTP timeout"
