"""Tests for warm dashboard briefing data loaders."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from dashboard.briefing_loader import (
    load_contact_conversation,
    load_daily_briefing,
    load_followup_queue,
)
from dashboard.followup_storage import save_followup_draft
from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    ConversationSentiment,
    ConversationStage,
    ConversationThread,
    DailyBriefing,
    DraftApprovalStatus,
    FollowUpDraft,
    FollowUpTrigger,
    UrgencyLevel,
)


@pytest.fixture(autouse=True)
def _use_tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


def _write_indexed_model(tmp_path, subdir: str, file_id: str, data: dict) -> None:
    directory = tmp_path / "outputs" / subdir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{file_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    index_path = directory / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {}
    index[file_id] = str(path)
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def _build_summary(
    contact_id: str,
    *,
    email: str = "alex@acme.com",
    include_messages: bool = True,
    conversation_id: str = "conv-1",
    last_message_date: str = "2026-03-08T10:00:00+00:00",
) -> ContactConversationSummary:
    threads: list[ConversationThread] = []
    total_messages = 0
    last_inbound = None
    last_outbound = None

    if include_messages:
        threads = [
            ConversationThread.model_validate(
                {
                    "conversationId": conversation_id,
                    "contactId": contact_id,
                    "lastMessageDate": last_message_date,
                    "messageCount": 2,
                    "messages": [
                        {
                            "messageId": "m-2",
                            "conversationId": conversation_id,
                            "direction": "inbound",
                            "body": "Can we review this next week?",
                            "subject": "Re: timing",
                            "timestamp": last_message_date,
                            "messageType": "Email",
                        },
                        {
                            "messageId": "m-1",
                            "conversationId": conversation_id,
                            "direction": "outbound",
                            "body": "Wanted to send the next steps.",
                            "subject": "Timing",
                            "timestamp": "2026-03-06T10:00:00+00:00",
                            "messageType": "Email",
                        },
                    ],
                }
            )
        ]
        total_messages = 2
        last_inbound = last_message_date
        last_outbound = "2026-03-06T10:00:00+00:00"

    return ContactConversationSummary(
        contactId=contact_id,
        ghlContactId=f"ghl-{contact_id}",
        firstName="Alex",
        lastName="Morgan",
        email=email,
        companyName="Acme",
        title="VP Revenue",
        threads=threads,
        totalMessages=total_messages,
        lastInboundDate=last_inbound,
        lastOutboundDate=last_outbound,
        scannedAt="2026-03-08T10:05:00+00:00",
    )


def _build_analysis(contact_id: str, *, urgency: UrgencyLevel, trigger: FollowUpTrigger) -> ConversationAnalysis:
    return ConversationAnalysis(
        contactId=contact_id,
        sourceConversationId="conv-1",
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        trigger=trigger,
        triggerReason="Latest message is inbound.",
        urgency=urgency,
        keyTopics=["timing", "pilot"],
        recommendedAction="Reply with next-step options.",
        conversationSummary="The contact replied about next steps.",
        daysSinceLastActivity=1,
        analyzedAt="2026-03-08T11:00:00+00:00",
    )


def _build_draft(contact_id: str, *, status: DraftApprovalStatus = DraftApprovalStatus.PENDING) -> FollowUpDraft:
    return FollowUpDraft(
        draftId=f"draft-{contact_id}",
        contactId=contact_id,
        ghlContactId=f"ghl-{contact_id}",
        sourceConversationId="conv-1",
        businessDate="2026-03-08",
        generationRunId=f"run-{contact_id}",
        contactEmail="alex@acme.com",
        contactName="Alex Morgan",
        companyName="Acme",
        subject="Next steps for the pilot",
        body="Alex,\n\nThanks for the note about next week.\n\nDani Apgar\nHead of Sales, Chief AI Officer\nReply with \"unsubscribe\" to opt out.",
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        urgency=UrgencyLevel.HOT,
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        analysisSummary="The contact replied about next steps.",
        status=status,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )


class TestBriefingLoader:
    def test_load_daily_briefing_prefers_persisted_file(self, tmp_path):
        persisted = DailyBriefing(
            date="2026-03-08",
            totalContactsScanned=12,
            contactsNeedingFollowup=4,
            contactsSkippedNoConversation=3,
            contactsSkippedNoEmail=1,
            hotCount=2,
            warmCount=1,
            coolingCount=1,
            noReplyCount=1,
            awaitingResponseCount=2,
            goneColdCount=1,
            draftsGenerated=3,
            analysisFailedCount=2,
            draftFailedCount=1,
            estimatedCostUsd=0.42,
            generatedAt="2026-03-08T12:00:00+00:00",
        )
        _write_indexed_model(
            tmp_path,
            "briefings",
            "2026-03-08",
            persisted.model_dump(by_alias=True),
        )

        loaded = load_daily_briefing("2026-03-08")

        assert loaded.total_contacts_scanned == 12
        assert loaded.analysis_failed_count == 2
        assert loaded.estimated_cost_usd == pytest.approx(0.42)

    def test_load_daily_briefing_uses_business_timezone_for_default_date(self, tmp_path, monkeypatch):
        persisted = DailyBriefing(
            date="2026-03-08",
            totalContactsScanned=5,
            contactsNeedingFollowup=1,
            contactsSkippedNoConversation=0,
            contactsSkippedNoEmail=0,
            hotCount=1,
            warmCount=0,
            coolingCount=0,
            noReplyCount=0,
            awaitingResponseCount=1,
            goneColdCount=0,
            draftsGenerated=1,
            analysisFailedCount=0,
            draftFailedCount=0,
            estimatedCostUsd=0.01,
            generatedAt="2026-03-08T12:00:00+00:00",
        )
        _write_indexed_model(
            tmp_path,
            "briefings",
            "2026-03-08",
            persisted.model_dump(by_alias=True),
        )
        monkeypatch.setattr("dashboard.briefing_loader.current_business_date", lambda: "2026-03-08")

        loaded = load_daily_briefing()

        assert loaded.date == "2026-03-08"

    def test_load_daily_briefing_computes_counts_from_outputs(self, tmp_path):
        eligible = _build_summary("contact-1")
        no_conversation = _build_summary("contact-2", include_messages=False)
        no_email = _build_summary("contact-3", email="")

        for summary in [eligible, no_conversation, no_email]:
            _write_indexed_model(
                tmp_path,
                "conversations",
                summary.contact_id,
                summary.model_dump(by_alias=True),
            )

        analysis = _build_analysis(
            "contact-1",
            urgency=UrgencyLevel.HOT,
            trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        )
        _write_indexed_model(
            tmp_path,
            "conversation_analysis",
            analysis.contact_id,
            analysis.model_dump(by_alias=True),
        )
        save_followup_draft(_build_draft("contact-1"))

        briefing = load_daily_briefing("2026-03-08")

        assert briefing.total_contacts_scanned == 3
        assert briefing.contacts_needing_followup == 1
        assert briefing.contacts_skipped_no_conversation == 1
        assert briefing.contacts_skipped_no_email == 1
        assert briefing.hot_count == 1
        assert briefing.awaiting_response_count == 1
        assert briefing.drafts_generated == 1
        assert briefing.analysis_failed_count == 0
        assert briefing.draft_failed_count == 0

    def test_load_followup_queue_combines_warm_outputs(self, tmp_path):
        hot_summary = _build_summary("contact-hot")
        warm_summary = _build_summary(
            "contact-warm",
            conversation_id="conv-2",
            last_message_date="2026-03-05T09:00:00+00:00",
        )
        for summary in [hot_summary, warm_summary]:
            _write_indexed_model(
                tmp_path,
                "conversations",
                summary.contact_id,
                summary.model_dump(by_alias=True),
            )

        hot_analysis = _build_analysis(
            "contact-hot",
            urgency=UrgencyLevel.HOT,
            trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        )
        warm_analysis = _build_analysis(
            "contact-warm",
            urgency=UrgencyLevel.WARM,
            trigger=FollowUpTrigger.NO_REPLY,
        ).model_copy(update={"source_conversation_id": "conv-2"})
        for analysis in [hot_analysis, warm_analysis]:
            _write_indexed_model(
                tmp_path,
                "conversation_analysis",
                analysis.contact_id,
                analysis.model_dump(by_alias=True),
            )

        save_followup_draft(_build_draft("contact-hot", status=DraftApprovalStatus.PENDING))
        save_followup_draft(
            _build_draft("contact-warm", status=DraftApprovalStatus.APPROVED).model_copy(
                update={"source_conversation_id": "conv-2"}
            )
        )

        queue = load_followup_queue()

        assert [item["contactId"] for item in queue] == ["contact-hot", "contact-warm"]
        assert queue[0]["draft"].status == DraftApprovalStatus.PENDING
        assert queue[0]["analysis"].urgency == UrgencyLevel.HOT
        assert queue[0]["primaryThread"].conversation_id == "conv-1"
        assert queue[1]["draft"].status == DraftApprovalStatus.APPROVED
        assert queue[1]["sourceConversationId"] == "conv-2"

    def test_load_followup_queue_defaults_to_latest_business_date(self, tmp_path):
        summary = _build_summary("contact-1")
        _write_indexed_model(
            tmp_path,
            "conversations",
            summary.contact_id,
            summary.model_dump(by_alias=True),
        )
        analysis = _build_analysis(
            "contact-1",
            urgency=UrgencyLevel.HOT,
            trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        )
        _write_indexed_model(
            tmp_path,
            "conversation_analysis",
            analysis.contact_id,
            analysis.model_dump(by_alias=True),
        )

        older = _build_draft("contact-1").model_copy(
            update={
                "draft_id": "draft-old",
                "business_date": "2026-03-08",
                "generation_run_id": "run-old",
            }
        )
        newer = _build_draft("contact-1").model_copy(
            update={
                "draft_id": "draft-new",
                "business_date": "2026-03-09",
                "generation_run_id": "run-new",
                "subject": "Newest draft",
            }
        )
        save_followup_draft(older)
        save_followup_draft(newer)

        queue = load_followup_queue()

        assert len(queue) == 1
        assert queue[0]["draftId"] == "draft-new"
        assert queue[0]["businessDate"] == "2026-03-09"

    def test_load_contact_conversation_returns_full_summary(self, tmp_path):
        summary = _build_summary("contact-1")
        _write_indexed_model(
            tmp_path,
            "conversations",
            summary.contact_id,
            summary.model_dump(by_alias=True),
        )

        loaded = load_contact_conversation("contact-1")

        assert loaded is not None
        assert loaded.contact_id == "contact-1"
        assert loaded.threads[0].conversation_id == "conv-1"
