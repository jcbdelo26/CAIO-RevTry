"""Tests for the warm follow-up draft agent."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from agents.followup_draft_agent import (
    DEFAULT_PROOF_POINTS,
    build_followup_prompt,
    draft_batch,
    draft_followup,
)
from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    ConversationMessage,
    ConversationSentiment,
    ConversationStage,
    ConversationThread,
    FollowUpTrigger,
    UrgencyLevel,
)
from utils.vault_loader import load_signatures


def _build_summary(contact_id: str = "c-1") -> ContactConversationSummary:
    now = datetime.now(timezone.utc)
    older_ts = (now - timedelta(days=2)).isoformat()
    latest_ts = (now - timedelta(hours=6)).isoformat()

    return ContactConversationSummary(
        contactId=contact_id,
        ghlContactId=f"ghl-{contact_id}",
        firstName="Jane",
        lastName="Doe",
        email="jane@acme.com",
        companyName="Acme Corp",
        title="VP Revenue",
        threads=[
            ConversationThread(
                conversationId="conv-1",
                contactId=contact_id,
                lastMessageDate=latest_ts,
                messageCount=2,
                messages=[
                    ConversationMessage(
                        messageId="m-2",
                        conversationId="conv-1",
                        direction="inbound",
                        body="We were discussing implementation timing last week.",
                        subject="Re: implementation",
                        timestamp=latest_ts,
                        messageType="Email",
                    ),
                    ConversationMessage(
                        messageId="m-1",
                        conversationId="conv-1",
                        direction="outbound",
                        body="Wanted to share how AI workflow automation could help.",
                        subject="AI workflow automation",
                        timestamp=older_ts,
                        messageType="Email",
                    ),
                ],
            )
        ],
        totalMessages=2,
        lastInboundDate=latest_ts,
        lastOutboundDate=older_ts,
        scannedAt=now.isoformat(),
    )


def _build_analysis(contact_id: str = "c-1") -> ConversationAnalysis:
    return ConversationAnalysis(
        contactId=contact_id,
        sourceConversationId="conv-1",
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        triggerReason="Latest message is inbound and expects our response.",
        urgency=UrgencyLevel.HOT,
        keyTopics=["implementation timing", "workflow automation"],
        recommendedAction="Answer the timing question and offer a next step.",
        conversationSummary="The contact is engaged and asked about timing.",
        daysSinceLastActivity=0,
        analyzedAt=datetime.now(timezone.utc).isoformat(),
    )


class TestPromptAssembly:
    def test_build_followup_prompt_is_minimal_and_warm_specific(self):
        prompt = build_followup_prompt(_build_analysis(), _build_summary(), load_signatures())

        assert "workflow automation" in prompt
        assert "implementation timing" in prompt
        assert DEFAULT_PROOF_POINTS[0] in prompt
        assert "bookingLink: https://caio.cx/ai-exec-briefing-call" in prompt
        assert "email_angles.md" not in prompt
        assert "ICP playbook" not in prompt


class TestDraftFollowup:
    @pytest.mark.asyncio
    async def test_draft_followup_returns_followup_draft(self):
        signatures = load_signatures()
        client = AsyncMock()
        client.complete_json = AsyncMock(return_value={
            "subject": "Timing on the AI workflow piece",
            "body": (
                "Jane,\n\n"
                "You asked about implementation timing in our last note, and I can map out the fastest path based on your workflow automation priorities.\n\n"
                "If it's easier, reply here with your current timeline and I can tailor the recommendation.\n\n"
                f"{signatures.sender_name}\n"
                f"{signatures.sender_title}\n\n"
                f"{signatures.can_spam_footer}"
            ),
        })

        draft = await draft_followup(
            _build_analysis(),
            _build_summary(),
            client=client,
            business_date="2026-03-09",
            generation_run_id="run-1",
            signatures=signatures,
        )

        assert draft.contact_id == "c-1"
        assert draft.ghl_contact_id == "ghl-c-1"
        assert draft.source_conversation_id == "conv-1"
        assert draft.business_date == "2026-03-09"
        assert draft.generation_run_id == "run-1"
        assert draft.contact_name == "Jane Doe"
        assert draft.subject == "Timing on the AI workflow piece"
        assert draft.status.value == "PENDING"

    @pytest.mark.asyncio
    async def test_draft_id_is_deterministic_per_business_date(self):
        signatures = load_signatures()
        client = AsyncMock()
        client.complete_json = AsyncMock(return_value={
            "subject": "Timing on the AI workflow piece",
            "body": (
                "Jane,\n\n"
                "You asked about implementation timing in our last note, and I can map out the fastest path based on your workflow automation priorities.\n\n"
                "If it's easier, reply here with your current timeline and I can tailor the recommendation.\n\n"
                f"{signatures.sender_name}\n"
                f"{signatures.sender_title}\n\n"
                f"{signatures.can_spam_footer}"
            ),
        })

        draft_one = await draft_followup(
            _build_analysis(),
            _build_summary(),
            client=client,
            business_date="2026-03-09",
            generation_run_id="run-1",
            signatures=signatures,
        )
        draft_two = await draft_followup(
            _build_analysis(),
            _build_summary(),
            client=client,
            business_date="2026-03-09",
            generation_run_id="run-2",
            signatures=signatures,
        )
        draft_three = await draft_followup(
            _build_analysis(),
            _build_summary(),
            client=client,
            business_date="2026-03-10",
            generation_run_id="run-3",
            signatures=signatures,
        )

        assert draft_one.draft_id == draft_two.draft_id
        assert draft_one.draft_id != draft_three.draft_id

    @pytest.mark.asyncio
    async def test_rejects_banned_opener(self):
        signatures = load_signatures()
        client = AsyncMock()
        client.complete_json = AsyncMock(return_value={
            "subject": "Quick thought",
            "body": (
                "Just checking in about the workflow automation conversation.\n\n"
                f"{signatures.sender_name}\n"
                f"{signatures.sender_title}\n\n"
                f"{signatures.can_spam_footer}"
            ),
        })

        with pytest.raises(ValueError, match="banned opener"):
            await draft_followup(
                _build_analysis(),
                _build_summary(),
                client=client,
                business_date="2026-03-09",
                generation_run_id="run-1",
                signatures=signatures,
            )

    @pytest.mark.asyncio
    async def test_rejects_terminal_stage(self):
        analysis = _build_analysis()
        analysis.stage = ConversationStage.WON
        client = AsyncMock()

        with pytest.raises(ValueError, match="terminal stage"):
            await draft_followup(
                analysis,
                _build_summary(),
                client=client,
                business_date="2026-03-09",
                generation_run_id="run-1",
                signatures=load_signatures(),
            )


class TestDraftBatch:
    @pytest.mark.asyncio
    async def test_batch_isolates_failures(self):
        good_analysis = _build_analysis(contact_id="c-good")
        bad_analysis = _build_analysis(contact_id="c-bad")
        summaries = [_build_summary(contact_id="c-good"), _build_summary(contact_id="c-bad")]
        signatures = load_signatures()

        client = AsyncMock()

        async def _side_effect(*args, **kwargs):
            trace = kwargs.get("trace_context", {})
            if trace.get("contactId") == "c-bad":
                return {
                    "subject": "Short note",
                    "body": "Following up.\n\nBad draft",
                }
            return {
                "subject": "Implementation timing",
                "body": (
                    "Jane,\n\n"
                    "You asked about timing in our last conversation, and I can map out the next step from there.\n\n"
                    "Reply here with what changed on your end and I’ll tailor the recommendation.\n\n"
                    f"{signatures.sender_name}\n"
                    f"{signatures.sender_title}\n\n"
                    f"{signatures.can_spam_footer}"
                ),
            }

        client.complete_json = AsyncMock(side_effect=_side_effect)

        result = await draft_batch(
            [good_analysis, bad_analysis],
            summaries,
            client=client,
            business_date="2026-03-09",
            generation_run_id="run-1",
            signatures=signatures,
        )

        assert len(result.drafts) == 1
        assert result.drafts[0].contact_id == "c-good"
        assert result.failed == 1
        assert result.errors == ["c-bad: Generated draft uses a banned opener"]
