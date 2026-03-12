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
from pipeline.followup_dispatcher import dispatch_approved_followups, dispatch_single_draft
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
            "Chief AI Officer LLC | 2021 Guadalupe Street, Suite 260, Austin, Texas 78705"
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
    async def test_dispatched_draft_stores_ghl_message_id(self, tmp_path):
        draft = _seed_approved_followup()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(return_value={"messageId": "msg-captured-1", "status": "sent"})
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_followups(
            rate_limiter=rl, circuit_breaker=cb, ghl=mock_ghl,
        )

        stored = get_followup_draft(draft.draft_id)
        assert result.dispatched == 1
        assert stored is not None
        assert stored.ghl_message_id == "msg-captured-1"

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

    @pytest.mark.asyncio
    async def test_dry_run_dispatches_without_ghl_call(self, tmp_path):
        draft = _seed_approved_followup()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
            dry_run=True,
        )

        stored = get_followup_draft(draft.draft_id)
        assert result.dispatched == 1
        assert result.failed == 0
        assert stored is not None
        assert stored.status == DraftApprovalStatus.DISPATCHED

    @pytest.mark.asyncio
    async def test_dry_run_logs_edited_content(self, tmp_path, caplog):
        draft = _seed_approved_followup()
        latest = get_followup_draft(draft.draft_id)
        assert latest is not None
        latest.subject = "DRY RUN edited subject"
        latest.body = "DRY RUN edited body content"
        save_followup_draft(latest)
        approve_followup_draft(latest.draft_id)

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        import logging

        with caplog.at_level(logging.INFO, logger="pipeline.followup_dispatcher"):
            result = await dispatch_approved_followups(
                rate_limiter=rl,
                circuit_breaker=cb,
                dry_run=True,
            )

        assert result.dispatched == 1
        assert "DRY RUN edited subject" in caplog.text
        assert "DRY_RUN dispatch" in caplog.text

    @pytest.mark.asyncio
    async def test_dry_run_still_checks_rate_limit(self, tmp_path):
        _seed_approved_followup()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=1, state_path=tmp_path / "rl.json")
        rl.record_send("ghl")

        result = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
            dry_run=True,
        )

        assert result.dispatched == 0
        assert result.skipped_rate_limit == 1


class TestDispatchSingleDraft:
    @pytest.mark.asyncio
    async def test_sends_and_marks_dispatched(self, tmp_path):
        draft = _seed_approved_followup()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(return_value={"messageId": "msg-single-1"})
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        success, message = await dispatch_single_draft(
            draft, rate_limiter=rl, circuit_breaker=cb, ghl=mock_ghl,
        )

        assert success is True
        assert message == "dispatched"
        stored = get_followup_draft(draft.draft_id)
        assert stored is not None
        assert stored.status == DraftApprovalStatus.DISPATCHED
        assert stored.ghl_message_id == "msg-single-1"
        mock_ghl.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limited_returns_false(self, tmp_path):
        draft = _seed_approved_followup()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=1, state_path=tmp_path / "rl.json")
        rl.record_send("ghl")

        success, message = await dispatch_single_draft(
            draft, rate_limiter=rl, circuit_breaker=cb,
        )

        assert success is False
        assert message == "rate_limited"
        stored = get_followup_draft(draft.draft_id)
        assert stored is not None
        assert stored.status == DraftApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_returns_false(self, tmp_path):
        draft = _seed_approved_followup()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        cb.record_failure("ghl")
        cb.record_failure("ghl")
        cb.record_failure("ghl")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        success, message = await dispatch_single_draft(
            draft, rate_limiter=rl, circuit_breaker=cb,
        )

        assert success is False
        assert message == "circuit_breaker_open"

    @pytest.mark.asyncio
    async def test_send_failure_marks_failed_returns_false(self, tmp_path):
        draft = _seed_approved_followup()
        mock_ghl = MagicMock()
        mock_ghl.send_email = AsyncMock(side_effect=Exception("GHL timeout"))
        mock_ghl.close = AsyncMock()

        cb = CircuitBreaker(state_path=tmp_path / "cb.json")
        rl = DailyRateLimiter(daily_limit=5, state_path=tmp_path / "rl.json")

        success, message = await dispatch_single_draft(
            draft, rate_limiter=rl, circuit_breaker=cb, ghl=mock_ghl,
        )

        assert success is False
        assert "GHL timeout" in message
        stored = get_followup_draft(draft.draft_id)
        assert stored is not None
        assert stored.status == DraftApprovalStatus.SEND_FAILED
