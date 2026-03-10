"""Tests for warm follow-up validators."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    ConversationMessage,
    ConversationSentiment,
    ConversationStage,
    ConversationThread,
    DraftApprovalStatus,
    FollowUpDraft,
    FollowUpTrigger,
    UrgencyLevel,
)
from utils.vault_loader import Exclusions, load_signatures
from validators.followup_gate2_validator import validate_followup_gate2
from validators.followup_gate3_validator import validate_followup_gate3


def _build_summary() -> ContactConversationSummary:
    now = datetime.now(timezone.utc)
    older = (now - timedelta(days=2)).isoformat()
    latest = (now - timedelta(hours=3)).isoformat()

    return ContactConversationSummary(
        contactId="c-1",
        ghlContactId="ghl-c-1",
        firstName="Jane",
        lastName="Doe",
        email="jane@acme.com",
        companyName="Acme",
        title="VP Revenue",
        threads=[
            ConversationThread(
                conversationId="conv-1",
                contactId="c-1",
                lastMessageDate=latest,
                messageCount=2,
                messages=[
                    ConversationMessage(
                        messageId="m-2",
                        conversationId="conv-1",
                        direction="inbound",
                        body="Can you outline implementation timing for the workflow automation rollout?",
                        timestamp=latest,
                        subject="Re: workflow automation",
                        messageType="Email",
                    ),
                    ConversationMessage(
                        messageId="m-1",
                        conversationId="conv-1",
                        direction="outbound",
                        body="I can share how AI workflow automation is landing with similar teams.",
                        timestamp=older,
                        subject="workflow automation",
                        messageType="Email",
                    ),
                ],
            )
        ],
        totalMessages=2,
        lastInboundDate=latest,
        lastOutboundDate=older,
        scannedAt=now.isoformat(),
    )


def _build_analysis() -> ConversationAnalysis:
    return ConversationAnalysis(
        contactId="c-1",
        sourceConversationId="conv-1",
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        triggerReason="Latest message is inbound and expects our response.",
        urgency=UrgencyLevel.HOT,
        keyTopics=["implementation timing", "workflow automation"],
        recommendedAction="Answer the timing question and offer a simple next step.",
        conversationSummary="Jane asked about timing for the workflow automation rollout.",
        daysSinceLastActivity=0,
        analyzedAt=datetime.now(timezone.utc).isoformat(),
    )


def _build_valid_draft() -> FollowUpDraft:
    signatures = load_signatures()
    return FollowUpDraft(
        draftId="f-1",
        contactId="c-1",
        ghlContactId="ghl-c-1",
        sourceConversationId="conv-1",
        contactEmail="jane@acme.com",
        contactName="Jane Doe",
        companyName="Acme",
        subject="Implementation timing",
        body=(
            "Jane,\n\n"
            "You asked about implementation timing for the workflow automation rollout, so I can outline the fastest path based on how similar teams are deploying it.\n\n"
            "Reply here with your current timeline and I’ll tailor the recommendation.\n\n"
            f"{signatures.sender_name}\n"
            f"{signatures.sender_title}\n\n"
            f"{signatures.can_spam_footer}"
        ),
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        urgency=UrgencyLevel.HOT,
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        analysisSummary="Jane asked about timing for the rollout.",
        status=DraftApprovalStatus.PENDING,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )


class TestFollowupGate2:
    def test_valid_followup_passes_gate2(self):
        exclusions = Exclusions(blocked_domains=set(), blocked_emails=set())
        result = validate_followup_gate2([_build_valid_draft()], exclusions=exclusions, signatures=load_signatures())

        assert result.passed is True
        assert result.failures == []

    def test_banned_opener_and_footer_fail_gate2(self):
        draft = _build_valid_draft()
        draft.body = "Just checking in on this.\n\nNo footer."
        exclusions = Exclusions(blocked_domains=set(), blocked_emails=set())

        result = validate_followup_gate2([draft], exclusions=exclusions, signatures=load_signatures())

        assert result.passed is False
        assert any("CAN-SPAM footer missing" in failure for failure in result.failures)
        assert any("banned opener" in failure for failure in result.failures)


class TestFollowupGate3:
    def test_valid_followup_passes_gate3(self):
        draft = _build_valid_draft()
        analysis = _build_analysis()
        summary = _build_summary()

        result = validate_followup_gate3([draft], analyses={"c-1": analysis}, summaries={"c-1": summary})

        assert result.passed is True
        assert result.failures == []

    def test_generic_followup_fails_conversation_reference(self):
        draft = _build_valid_draft()
        draft.body = (
            "Jane,\n\n"
            "Wanted to reconnect and see if this is still a priority.\n\n"
            "Reply here if useful.\n\n"
            f"{load_signatures().sender_name}\n"
            f"{load_signatures().sender_title}\n\n"
            f"{load_signatures().can_spam_footer}"
        )

        result = validate_followup_gate3([draft], analyses={"c-1": _build_analysis()}, summaries={"c-1": _build_summary()})

        assert result.passed is False
        assert any("conversation reference missing" in failure for failure in result.failures)

    def test_relaxed_topic_matching_fuzzy_word_order(self):
        """'workflow automation' topic should match draft mentioning 'automation' and 'workflow' separately."""
        draft = _build_valid_draft()
        signatures = load_signatures()
        # Body mentions topic words in different order/context
        draft.body = (
            "Jane,\n\n"
            "Following up on the automation discussion — your workflow needs look like a great fit.\n\n"
            "Reply here with your current timeline.\n\n"
            f"{signatures.sender_name}\n"
            f"{signatures.sender_title}\n\n"
            f"{signatures.can_spam_footer}"
        )

        result = validate_followup_gate3([draft], analyses={"c-1": _build_analysis()}, summaries={"c-1": _build_summary()})

        assert result.passed is True

    def test_relaxed_topic_matching_two_word_phrase(self):
        """2-word message phrase from thread should match in body."""
        draft = _build_valid_draft()
        signatures = load_signatures()
        # Body includes 2-word phrase from the thread message "outline implementation"
        draft.body = (
            "Jane,\n\n"
            "Happy to outline implementation details for your team.\n\n"
            "Reply here if useful.\n\n"
            f"{signatures.sender_name}\n"
            f"{signatures.sender_title}\n\n"
            f"{signatures.can_spam_footer}"
        )

        result = validate_followup_gate3([draft], analyses={"c-1": _build_analysis()}, summaries={"c-1": _build_summary()})

        assert result.passed is True

    def test_cold_outbound_language_fails_gate3(self):
        draft = _build_valid_draft()
        draft.body = draft.body + "\n\nI came across your profile and wanted to reach out cold."

        result = validate_followup_gate3([draft], analyses={"c-1": _build_analysis()}, summaries={"c-1": _build_summary()})

        assert result.passed is False
        assert any("cold-outbound language" in failure for failure in result.failures)
