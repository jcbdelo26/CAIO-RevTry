"""Tests for warm follow-up file storage."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from dashboard.followup_storage import (
    approve_followup_draft,
    get_followup_draft,
    list_followup_drafts,
    mark_followup_dispatched,
    mark_followup_send_failed,
    reject_followup_draft,
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


@pytest.fixture(autouse=True)
def _use_tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


def _build_draft(
    draft_id: str = "followup-1",
    *,
    status: DraftApprovalStatus = DraftApprovalStatus.PENDING,
    created_at: str | None = None,
) -> FollowUpDraft:
    return FollowUpDraft(
        draftId=draft_id,
        contactId=f"contact-{draft_id}",
        ghlContactId=f"ghl-{draft_id}",
        sourceConversationId="conv-1",
        businessDate="2026-03-09",
        generationRunId="run-1",
        contactEmail="jane@acme.com",
        contactName="Jane Doe",
        companyName="Acme",
        subject="Implementation timing",
        body="Jane,\n\nThanks for the note.\n\nDani Apgar\nHead of Sales, Chief AI Officer",
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        urgency=UrgencyLevel.HOT,
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        analysisSummary="The contact asked about timing.",
        status=status,
        createdAt=created_at or datetime.now(timezone.utc).isoformat(),
    )


class TestFollowupStorage:
    def test_save_and_get_followup_draft(self, tmp_path):
        draft = _build_draft()

        save_followup_draft(draft)
        loaded = get_followup_draft(draft.draft_id)

        assert loaded is not None
        assert loaded.draft_id == draft.draft_id
        assert loaded.source_conversation_id == "conv-1"

        index_path = tmp_path / "outputs" / "followups" / "index.json"
        assert index_path.exists()
        index = json.loads(index_path.read_text(encoding="utf-8"))
        assert draft.draft_id in index

    def test_list_followup_drafts_orders_pending_first(self):
        save_followup_draft(_build_draft("approved", status=DraftApprovalStatus.APPROVED, created_at="2026-03-08T00:00:00+00:00"))
        save_followup_draft(_build_draft("pending", status=DraftApprovalStatus.PENDING, created_at="2026-03-08T01:00:00+00:00"))
        save_followup_draft(_build_draft("failed", status=DraftApprovalStatus.SEND_FAILED, created_at="2026-03-08T02:00:00+00:00"))

        drafts = list_followup_drafts()

        assert [draft.draft_id for draft in drafts] == ["pending", "approved", "failed"]

    def test_approve_followup_draft_has_no_ghl_side_effects(self, tmp_path):
        draft = _build_draft()
        save_followup_draft(draft)

        approved = approve_followup_draft(draft.draft_id)

        assert approved is not None
        assert approved.status == DraftApprovalStatus.APPROVED
        assert approved.approved_at is not None
        assert not (tmp_path / "registry" / "pending_feedback" / f"{draft.draft_id}.md").exists()

    def test_reject_followup_draft_writes_feedback(self, tmp_path):
        draft = _build_draft()
        save_followup_draft(draft)

        rejected = reject_followup_draft(draft.draft_id, reason="Too generic")

        assert rejected is not None
        assert rejected.status == DraftApprovalStatus.REJECTED
        assert rejected.rejection_reason == "Too generic"
        feedback_path = tmp_path / "registry" / "pending_feedback" / f"{draft.draft_id}.md"
        assert feedback_path.exists()
        feedback = feedback_path.read_text(encoding="utf-8")
        assert "Warm Follow-Up Rejection Feedback" in feedback
        assert "Too generic" in feedback

    def test_mark_followup_dispatched(self):
        draft = _build_draft()
        save_followup_draft(draft)

        dispatched = mark_followup_dispatched(draft.draft_id, "ghl")

        assert dispatched is not None
        assert dispatched.status == DraftApprovalStatus.DISPATCHED
        assert dispatched.dispatched_at is not None

    def test_mark_followup_send_failed(self):
        draft = _build_draft()
        save_followup_draft(draft)

        failed = mark_followup_send_failed(draft.draft_id, "ghl", "SMTP timeout")

        assert failed is not None
        assert failed.status == DraftApprovalStatus.SEND_FAILED
        assert failed.send_failed_at is not None
        assert failed.dispatch_error == "SMTP timeout"

    def test_same_day_save_is_idempotent_by_draft_id(self):
        draft = _build_draft()
        save_followup_draft(draft)

        updated = draft.model_copy(
            update={
                "subject": "Updated timing note",
                "generation_run_id": "run-2",
            }
        )
        save_followup_draft(updated)

        drafts = list_followup_drafts()
        assert len(drafts) == 1
        assert drafts[0].subject == "Updated timing note"
        assert drafts[0].generation_run_id == "run-2"
