"""Tests for the warm follow-up orchestrator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from agents.conversation_analyst_agent import AnalysisBatchResult
from agents.followup_draft_agent import DraftBatchResult
from dashboard.followup_storage import get_followup_draft
from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    ConversationSentiment,
    ConversationStage,
    ConversationThread,
    DraftApprovalStatus,
    FollowUpDraft,
    FollowUpTrigger,
    UrgencyLevel,
)
from pipeline.circuit_breaker import CircuitBreaker
from pipeline.followup_orchestrator import run_followup_orchestrator
from utils.vault_loader import Exclusions, load_signatures
from validators.followup_gate2_validator import validate_followup_gate2
from validators.followup_gate3_validator import validate_followup_gate3


@pytest.fixture(autouse=True)
def _use_tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


def _build_summary(contact_id: str = "contact-1") -> ContactConversationSummary:
    return ContactConversationSummary(
        contactId=contact_id,
        ghlContactId=f"ghl-{contact_id}",
        firstName="Alex",
        lastName="Morgan",
        email="alex@acme.com",
        companyName="Acme",
        title="VP Revenue",
        threads=[
            ConversationThread.model_validate(
                {
                    "conversationId": "conv-1",
                    "contactId": contact_id,
                    "lastMessageDate": "2026-03-09T09:00:00+00:00",
                    "messageCount": 2,
                    "messages": [
                        {
                            "messageId": "m-2",
                            "conversationId": "conv-1",
                            "direction": "inbound",
                            "body": "Can you send timing options for next week?",
                            "subject": "Re: timing",
                            "timestamp": "2026-03-09T09:00:00+00:00",
                            "messageType": "Email",
                        },
                        {
                            "messageId": "m-1",
                            "conversationId": "conv-1",
                            "direction": "outbound",
                            "body": "Sharing next steps from our last note.",
                            "subject": "Next steps",
                            "timestamp": "2026-03-07T09:00:00+00:00",
                            "messageType": "Email",
                        },
                    ],
                }
            )
        ],
        totalMessages=2,
        lastInboundDate="2026-03-09T09:00:00+00:00",
        lastOutboundDate="2026-03-07T09:00:00+00:00",
        scannedAt="2026-03-09T09:05:00+00:00",
    )


def _build_analysis(contact_id: str = "contact-1") -> ConversationAnalysis:
    return ConversationAnalysis(
        contactId=contact_id,
        sourceConversationId="conv-1",
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        triggerReason="Latest message is inbound.",
        urgency=UrgencyLevel.HOT,
        keyTopics=["timing options", "next week"],
        recommendedAction="Reply with timing options for next week.",
        conversationSummary="The contact asked for timing options next week.",
        daysSinceLastActivity=0,
        analyzedAt="2026-03-09T09:10:00+00:00",
    )


def _build_valid_draft(contact_id: str = "contact-1") -> FollowUpDraft:
    return FollowUpDraft(
        draftId="followup-1",
        contactId=contact_id,
        ghlContactId=f"ghl-{contact_id}",
        sourceConversationId="conv-1",
        businessDate="2026-03-09",
        generationRunId="run-1",
        contactEmail="alex@acme.com",
        contactName="Alex Morgan",
        companyName="Acme",
        subject="Timing options for next week",
        body=(
            "Alex,\n\n"
            "Thanks for asking about timing options for next week. I can send over two windows that fit what you mentioned.\n\n"
            "Dani Apgar\n"
            "Head of Sales, Chief AI Officer\n"
            "Reply STOP to unsubscribe.\n"
            "Chief AI Officer Inc. | 5700 Harper Dr, Suite 210, Albuquerque, NM 87109"
        ),
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        urgency=UrgencyLevel.HOT,
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        analysisSummary="The contact asked for timing options next week.",
        status=DraftApprovalStatus.PENDING,
        createdAt="2026-03-09T09:15:00+00:00",
    )


class TestFollowupOrchestrator:
    @pytest.mark.asyncio
    async def test_aborts_when_ghl_circuit_breaker_open(self):
        cb = CircuitBreaker()
        cb.record_failure("ghl")
        cb.record_failure("ghl")
        cb.record_failure("ghl")

        result = await run_followup_orchestrator(
            candidate_records=[{"ghl_contact_id": "ghl-1"}],
            circuit_breaker=cb,
        )

        assert result["status"] == "circuit_open"
        assert result["briefing_path"] is None

    @pytest.mark.asyncio
    async def test_no_candidates_saves_empty_briefing_without_anthropic_key(self, tmp_path):
        result = await run_followup_orchestrator(
            candidate_records=[],
            reference_time=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc),
        )

        assert result["status"] == "no_candidates"
        assert result["briefing_path"] is not None

        briefing_path = tmp_path / "outputs" / "briefings" / "2026-03-09.json"
        assert briefing_path.exists()
        briefing = json.loads(briefing_path.read_text(encoding="utf-8"))
        assert briefing["totalContactsScanned"] == 0
        assert briefing["draftsGenerated"] == 0

    @pytest.mark.asyncio
    async def test_complete_run_saves_valid_draft_and_briefing(self, tmp_path):
        summary = _build_summary()
        analysis = _build_analysis()
        draft = _build_valid_draft()
        signatures = load_signatures()

        with (
            patch("pipeline.followup_orchestrator.scan_all_contacts", AsyncMock(return_value=[summary])),
            patch(
                "pipeline.followup_orchestrator.analyze_batch",
                AsyncMock(
                    return_value=AnalysisBatchResult(
                        analyses=[analysis],
                        skipped=0,
                        failed=0,
                        errors=[],
                        skipped_no_conversation=0,
                        skipped_no_email=0,
                    )
                ),
            ),
            patch(
                "pipeline.followup_orchestrator.draft_batch",
                AsyncMock(return_value=DraftBatchResult(drafts=[draft], failed=0, errors=[])),
            ),
            patch(
                "pipeline.followup_orchestrator.validate_followup_gate2",
                side_effect=lambda drafts: validate_followup_gate2(
                    drafts,
                    exclusions=Exclusions(blocked_domains=set(), blocked_emails=set()),
                    signatures=signatures,
                ),
            ),
            patch(
                "pipeline.followup_orchestrator.validate_followup_gate3",
                side_effect=validate_followup_gate3,
            ),
        ):
            result = await run_followup_orchestrator(
                candidate_records=[{"ghl_contact_id": "ghl-contact-1"}],
                anthropic_client=AsyncMock(),
                reference_time=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc),
            )

        assert result["status"] == "complete"
        assert result["saved"] == 1
        assert result["draft_failed"] == 0
        assert result["estimated_cost_usd"] == pytest.approx(0.012)
        assert get_followup_draft("followup-1") is not None

        briefing_path = tmp_path / "outputs" / "briefings" / "2026-03-09.json"
        assert briefing_path.exists()
        briefing = json.loads(briefing_path.read_text(encoding="utf-8"))
        assert briefing["contactsNeedingFollowup"] == 1
        assert briefing["hotCount"] == 1
        assert briefing["draftsGenerated"] == 1

        log_path = tmp_path / "outputs" / "logs" / "warm-followup-generate_followup-orchestrator.json"
        assert log_path.exists()

    @pytest.mark.asyncio
    async def test_invalid_draft_is_not_saved_and_counts_as_failure(self, tmp_path):
        summary = _build_summary()
        analysis = _build_analysis()
        signatures = load_signatures()
        invalid_draft = _build_valid_draft().model_copy(
            update={
                "draft_id": "followup-invalid",
                "body": "Just checking in about next week.",
            }
        )

        with (
            patch("pipeline.followup_orchestrator.scan_all_contacts", AsyncMock(return_value=[summary])),
            patch(
                "pipeline.followup_orchestrator.analyze_batch",
                AsyncMock(
                    return_value=AnalysisBatchResult(
                        analyses=[analysis],
                        skipped=0,
                        failed=0,
                        errors=[],
                        skipped_no_conversation=0,
                        skipped_no_email=0,
                    )
                ),
            ),
            patch(
                "pipeline.followup_orchestrator.draft_batch",
                AsyncMock(return_value=DraftBatchResult(drafts=[invalid_draft], failed=0, errors=[])),
            ),
            patch(
                "pipeline.followup_orchestrator.validate_followup_gate2",
                side_effect=lambda drafts: validate_followup_gate2(
                    drafts,
                    exclusions=Exclusions(blocked_domains=set(), blocked_emails=set()),
                    signatures=signatures,
                ),
            ),
            patch(
                "pipeline.followup_orchestrator.validate_followup_gate3",
                side_effect=validate_followup_gate3,
            ),
        ):
            result = await run_followup_orchestrator(
                candidate_records=[{"ghl_contact_id": "ghl-contact-1"}],
                anthropic_client=AsyncMock(),
                reference_time=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc),
            )

        assert result["status"] == "no_valid_drafts"
        assert result["saved"] == 0
        assert result["draft_failed"] == 1
        assert result["validation_failed"] == 1
        assert get_followup_draft("followup-invalid") is None

        briefing_path = tmp_path / "outputs" / "briefings" / "2026-03-09.json"
        assert briefing_path.exists()
        briefing = json.loads(briefing_path.read_text(encoding="utf-8"))
        assert briefing["draftFailedCount"] == 1

    @pytest.mark.asyncio
    async def test_same_day_force_rerun_overwrites_same_draft(self):
        summary = _build_summary()
        analysis = _build_analysis()
        signatures = load_signatures()
        first_draft = _build_valid_draft().model_copy(
            update={
                "draft_id": "same-day-draft",
                "subject": "First subject",
                "business_date": "2026-03-09",
                "generation_run_id": "run-1",
            }
        )
        second_draft = _build_valid_draft().model_copy(
            update={
                "draft_id": "same-day-draft",
                "subject": "Updated subject",
                "business_date": "2026-03-09",
                "generation_run_id": "run-2",
            }
        )

        with (
            patch("pipeline.followup_orchestrator.scan_all_contacts", AsyncMock(return_value=[summary])),
            patch(
                "pipeline.followup_orchestrator.analyze_batch",
                AsyncMock(
                    return_value=AnalysisBatchResult(
                        analyses=[analysis],
                        skipped=0,
                        failed=0,
                        errors=[],
                        skipped_no_conversation=0,
                        skipped_no_email=0,
                    )
                ),
            ),
            patch(
                "pipeline.followup_orchestrator.validate_followup_gate2",
                side_effect=lambda drafts: validate_followup_gate2(
                    drafts,
                    exclusions=Exclusions(blocked_domains=set(), blocked_emails=set()),
                    signatures=signatures,
                ),
            ),
            patch(
                "pipeline.followup_orchestrator.validate_followup_gate3",
                side_effect=validate_followup_gate3,
            ),
            patch(
                "pipeline.followup_orchestrator.draft_batch",
                AsyncMock(side_effect=[
                    DraftBatchResult(drafts=[first_draft], failed=0, errors=[]),
                    DraftBatchResult(drafts=[second_draft], failed=0, errors=[]),
                ]),
            ),
        ):
            await run_followup_orchestrator(
                candidate_records=[{"ghl_contact_id": "ghl-contact-1"}],
                anthropic_client=AsyncMock(),
                reference_time=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc),
            )
            result = await run_followup_orchestrator(
                candidate_records=[{"ghl_contact_id": "ghl-contact-1"}],
                anthropic_client=AsyncMock(),
                force=True,
                reference_time=datetime(2026, 3, 9, 18, 0, tzinfo=timezone.utc),
            )

        assert result["status"] == "complete"
        stored = get_followup_draft("same-day-draft")
        assert stored is not None
        assert stored.subject == "Updated subject"
        assert stored.generation_run_id == "run-2"

    @pytest.mark.asyncio
    async def test_next_day_force_rerun_creates_new_draft(self):
        summary = _build_summary()
        analysis = _build_analysis()
        signatures = load_signatures()
        day_one_draft = _build_valid_draft().model_copy(
            update={
                "draft_id": "draft-day-one",
                "subject": "Day one subject",
                "business_date": "2026-03-09",
                "generation_run_id": "run-1",
            }
        )
        day_two_draft = _build_valid_draft().model_copy(
            update={
                "draft_id": "draft-day-two",
                "subject": "Day two subject",
                "business_date": "2026-03-10",
                "generation_run_id": "run-2",
            }
        )

        with (
            patch("pipeline.followup_orchestrator.scan_all_contacts", AsyncMock(return_value=[summary])),
            patch(
                "pipeline.followup_orchestrator.analyze_batch",
                AsyncMock(
                    return_value=AnalysisBatchResult(
                        analyses=[analysis],
                        skipped=0,
                        failed=0,
                        errors=[],
                        skipped_no_conversation=0,
                        skipped_no_email=0,
                    )
                ),
            ),
            patch(
                "pipeline.followup_orchestrator.validate_followup_gate2",
                side_effect=lambda drafts: validate_followup_gate2(
                    drafts,
                    exclusions=Exclusions(blocked_domains=set(), blocked_emails=set()),
                    signatures=signatures,
                ),
            ),
            patch(
                "pipeline.followup_orchestrator.validate_followup_gate3",
                side_effect=validate_followup_gate3,
            ),
            patch(
                "pipeline.followup_orchestrator.draft_batch",
                AsyncMock(side_effect=[
                    DraftBatchResult(drafts=[day_one_draft], failed=0, errors=[]),
                    DraftBatchResult(drafts=[day_two_draft], failed=0, errors=[]),
                ]),
            ),
        ):
            await run_followup_orchestrator(
                candidate_records=[{"ghl_contact_id": "ghl-contact-1"}],
                anthropic_client=AsyncMock(),
                reference_time=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc),
            )
            await run_followup_orchestrator(
                candidate_records=[{"ghl_contact_id": "ghl-contact-1"}],
                anthropic_client=AsyncMock(),
                force=True,
                reference_time=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
            )

        assert get_followup_draft("draft-day-one") is not None
        assert get_followup_draft("draft-day-two") is not None
