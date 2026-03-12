"""Tests for dashboard endpoints — filters, batch actions."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from dashboard.followup_storage import get_followup_draft, save_followup_draft
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


@pytest.fixture(autouse=True)
def _use_tmp_outputs(tmp_path, monkeypatch):
    """Point OUTPUTS_DIR and REGISTRY_DIR to tmp_path for isolation."""
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


@pytest.fixture()
def client():
    from dashboard.app import app
    return TestClient(app)


@pytest.fixture()
def seeded_drafts(tmp_path):
    """Create a few test drafts on disk."""
    drafts_dir = tmp_path / "outputs" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    index = {}
    for i, (tier, status, channel) in enumerate([
        ("1", "PENDING", "instantly"),
        ("2", "PENDING", "ghl"),
        ("1", "APPROVED", "instantly"),
        ("3", "REJECTED", "heyreach"),
    ]):
        draft_id = f"test-draft-{i}"
        draft_data = {
            "draftId": draft_id,
            "contactId": f"contact{i}@acme.com",
            "icpTier": tier,
            "angleId": "ai_executive_briefing",
            "subject": f"Test subject {i} for Acme",
            "body": f"Hi Contact{i},\n\nTest body.\n\nBest,\nChris",
            "channel": channel,
            "bookingLink": "https://caio.cx/ai-exec-briefing-call",
            "status": status,
            "createdAt": "2026-03-07T00:00:00Z",
            "approvedAt": "2026-03-07T01:00:00Z" if status == "APPROVED" else None,
            "rejectedAt": "2026-03-07T01:00:00Z" if status == "REJECTED" else None,
            "rejectionReason": "test reason" if status == "REJECTED" else None,
        }
        path = drafts_dir / f"{draft_id}.json"
        path.write_text(json.dumps(draft_data, indent=2), encoding="utf-8")
        index[draft_id] = str(path)

    (drafts_dir / "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )
    return list(index.keys())


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


def _valid_followup_edit_body(prefix: str = "Updated subject") -> str:
    return (
        "Alex,\n\n"
        "You asked for timing options, so I pulled together a clearer next step.\n\n"
        f"{prefix} with a quick pilot outline and a few timing windows could help us keep momentum.\n\n"
        "Dani Apgar\n"
        "Head of Sales, Chief AI Officer\n"
        "Reply STOP to unsubscribe.\n"
        "Chief AI Officer LLC | 2021 Guadalupe Street, Suite 260, Austin, Texas 78705"
    )


def _basic_auth_headers(username: str = "dani", password: str = "secret") -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


@pytest.fixture()
def seeded_followups(tmp_path):
    summary = ContactConversationSummary(
        contactId="contact-followup-1",
        ghlContactId="ghl-contact-followup-1",
        firstName="Alex",
        lastName="Morgan",
        email="alex@acme.com",
        companyName="Acme",
        title="VP Revenue",
        threads=[
            ConversationThread.model_validate(
                {
                    "conversationId": "conv-1",
                    "contactId": "contact-followup-1",
                    "lastMessageDate": "2026-03-08T10:00:00+00:00",
                    "messageCount": 2,
                    "messages": [
                        {
                            "messageId": "m-2",
                            "conversationId": "conv-1",
                            "direction": "inbound",
                            "body": "Can you send timing options?",
                            "subject": "Re: next steps",
                            "timestamp": "2026-03-08T10:00:00+00:00",
                            "messageType": "Email",
                        },
                        {
                            "messageId": "m-1",
                            "conversationId": "conv-1",
                            "direction": "outbound",
                            "body": "Wanted to send next steps.",
                            "subject": "Next steps",
                            "timestamp": "2026-03-06T10:00:00+00:00",
                            "messageType": "Email",
                        },
                    ],
                }
            )
        ],
        totalMessages=2,
        lastInboundDate="2026-03-08T10:00:00+00:00",
        lastOutboundDate="2026-03-06T10:00:00+00:00",
        scannedAt="2026-03-08T10:05:00+00:00",
    )
    _write_indexed_model(
        tmp_path,
        "conversations",
        summary.contact_id,
        summary.model_dump(by_alias=True),
    )

    analysis = ConversationAnalysis(
        contactId=summary.contact_id,
        sourceConversationId="conv-1",
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        triggerReason="Latest message is inbound.",
        urgency=UrgencyLevel.HOT,
        keyTopics=["timing", "pilot"],
        recommendedAction="Reply with timing options.",
        conversationSummary="The contact asked for timing options.",
        daysSinceLastActivity=1,
        analyzedAt="2026-03-08T11:00:00+00:00",
    )
    _write_indexed_model(
        tmp_path,
        "conversation_analysis",
        analysis.contact_id,
        analysis.model_dump(by_alias=True),
    )

    draft = FollowUpDraft(
        draftId="followup-1",
        contactId=summary.contact_id,
        ghlContactId=summary.ghl_contact_id,
        sourceConversationId="conv-1",
        businessDate="2026-03-08",
        generationRunId="run-1",
        contactEmail=summary.email,
        contactName="Alex Morgan",
        companyName=summary.company_name,
        subject="Timing options for next week",
        body="Alex,\n\nThanks for the note about timing.\n\nDani Apgar\nHead of Sales, Chief AI Officer\nReply with \"unsubscribe\" to opt out.",
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        urgency=UrgencyLevel.HOT,
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        analysisSummary=analysis.conversation_summary,
        status=DraftApprovalStatus.PENDING,
        createdAt="2026-03-08T11:05:00+00:00",
    )
    save_followup_draft(draft)

    summary_two = ContactConversationSummary(
        contactId="contact-followup-2",
        ghlContactId="ghl-contact-followup-2",
        firstName="Jordan",
        lastName="Lee",
        email="jordan@beta.com",
        companyName="Beta Corp",
        title="Founder",
        threads=[
            ConversationThread.model_validate(
                {
                    "conversationId": "conv-2",
                    "contactId": "contact-followup-2",
                    "lastMessageDate": "2026-03-08T12:00:00+00:00",
                    "messageCount": 1,
                    "messages": [
                        {
                            "messageId": "m-3",
                            "conversationId": "conv-2",
                            "direction": "outbound",
                            "body": "Following up on the note I sent.",
                            "subject": "Checking in",
                            "timestamp": "2026-03-08T12:00:00+00:00",
                            "messageType": "Email",
                        }
                    ],
                }
            )
        ],
        totalMessages=1,
        lastInboundDate=None,
        lastOutboundDate="2026-03-08T12:00:00+00:00",
        scannedAt="2026-03-08T12:05:00+00:00",
    )
    _write_indexed_model(
        tmp_path,
        "conversations",
        summary_two.contact_id,
        summary_two.model_dump(by_alias=True),
    )

    analysis_two = ConversationAnalysis(
        contactId=summary_two.contact_id,
        sourceConversationId="conv-2",
        sentiment=ConversationSentiment.NEUTRAL,
        stage=ConversationStage.NEW,
        trigger=FollowUpTrigger.NO_REPLY,
        triggerReason="Latest message is outbound with no reply yet.",
        urgency=UrgencyLevel.WARM,
        keyTopics=["follow-up"],
        recommendedAction="Wait 2-3 days, then send a short personalized follow-up.",
        conversationSummary="The lead has not replied yet.",
        daysSinceLastActivity=0,
        analyzedAt="2026-03-08T12:30:00+00:00",
    )
    _write_indexed_model(
        tmp_path,
        "conversation_analysis",
        analysis_two.contact_id,
        analysis_two.model_dump(by_alias=True),
    )

    return draft.draft_id


class TestDashboardLoads:
    def test_empty_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "No drafts" in resp.text

    def test_dashboard_with_drafts(self, client, seeded_drafts):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "test-draft-0" in resp.text or "contact0@acme.com" in resp.text

    def test_cold_drafts_alias(self, client, seeded_drafts):
        resp = client.get("/cold-drafts")
        assert resp.status_code == 200
        assert "Campaign Drafts" in resp.text


class TestFilters:
    def test_filter_by_tier(self, client, seeded_drafts):
        resp = client.get("/?tier=1")
        assert resp.status_code == 200
        # Tier 1 drafts present, Tier 2/3 absent
        assert "contact0@acme.com" in resp.text  # Tier 1
        assert "contact1@acme.com" not in resp.text  # Tier 2

    def test_filter_by_status(self, client, seeded_drafts):
        resp = client.get("/?status=APPROVED")
        assert resp.status_code == 200
        assert "contact2@acme.com" in resp.text  # APPROVED
        assert "contact0@acme.com" not in resp.text  # PENDING

    def test_filter_by_channel(self, client, seeded_drafts):
        resp = client.get("/?channel=ghl")
        assert resp.status_code == 200
        assert "contact1@acme.com" in resp.text  # GHL
        assert "contact0@acme.com" not in resp.text  # Instantly

    def test_search(self, client, seeded_drafts):
        resp = client.get("/?search=contact1")
        assert resp.status_code == 200
        assert "contact1@acme.com" in resp.text
        assert "contact0@acme.com" not in resp.text


class TestBatchActions:
    @patch("dashboard.app.push_approved_draft_to_ghl", new_callable=AsyncMock)
    def test_batch_approve_empty(self, mock_ghl, client):
        mock_ghl.return_value = {"status": "pushed", "ghl_contact_id": "", "ghl_task_id": ""}
        resp = client.post(
            "/drafts/batch/approve",
            data={"draft_ids": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_batch_reject_empty(self, client):
        resp = client.post(
            "/drafts/batch/reject",
            data={"draft_ids": "", "reason": "test"},
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestWarmDashboardRoutes:
    def test_briefing_route(self, client, seeded_followups):
        resp = client.get("/briefing")
        assert resp.status_code == 200
        assert "Warm Follow-Up Briefing" in resp.text
        assert "Need Follow-Up" in resp.text

    def test_followups_route(self, client, seeded_followups):
        resp = client.get("/followups")
        assert resp.status_code == 200
        assert "Warm Follow-Up Queue" in resp.text
        assert "Alex Morgan" in resp.text
        # Analysis-only contacts (no draft) should NOT appear in the queue
        assert "Jordan Lee" not in resp.text
        assert "View Draft" in resp.text

    def test_followup_detail_route(self, client, seeded_followups):
        resp = client.get(f"/followups/{seeded_followups}", follow_redirects=False)
        assert resp.status_code == 307
        assert resp.headers["location"] == "/followups/contact/contact-followup-1?date=2026-03-08"

    def test_followup_contact_detail_route_with_draft(self, client, seeded_followups):
        resp = client.get("/followups/contact/contact-followup-1")
        assert resp.status_code == 200
        assert "Warm Follow-Up" in resp.text
        assert "Timing options for next week" in resp.text
        assert "Can you send timing options?" in resp.text
        assert "Save Draft" in resp.text
        assert "Approve" in resp.text

    def test_followup_contact_detail_route_without_draft(self, client, seeded_followups):
        resp = client.get("/followups/contact/contact-followup-2")
        assert resp.status_code == 200
        assert "Lead Analysis" in resp.text
        assert "No follow-up draft has been generated for this routed lead yet." in resp.text
        assert "The lead has not replied yet." in resp.text
        assert "Wait 2-3 days, then send a short personalized follow-up." in resp.text
        assert "Approve Draft" not in resp.text

    def test_followup_contact_detail_404_when_missing(self, client, seeded_followups):
        resp = client.get("/followups/contact/missing-contact")
        assert resp.status_code == 404

    @patch("pipeline.followup_dispatcher.dispatch_single_draft", new_callable=AsyncMock, return_value=(True, "dispatched"))
    def test_followup_approve_route(self, _mock_dispatch, client, seeded_followups):
        resp = client.post(
            f"/followups/{seeded_followups}/approve",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/followups/contact/contact-followup-1?date=2026-03-08"
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.APPROVED

    def test_followup_reject_route(self, client, seeded_followups):
        resp = client.post(
            f"/followups/{seeded_followups}/reject",
            data={"reason": "Too generic"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/followups/contact/contact-followup-1?date=2026-03-08"
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.REJECTED

    @patch("pipeline.followup_dispatcher.dispatch_single_draft", new_callable=AsyncMock, return_value=(True, "dispatched"))
    def test_followup_batch_approve(self, _mock_dispatch, client, seeded_followups):
        resp = client.post(
            "/followups/batch/approve",
            data={"draft_ids": seeded_followups},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.APPROVED

    @patch("pipeline.followup_dispatcher.dispatch_single_draft", new_callable=AsyncMock)
    def test_approve_dispatches_immediately(self, mock_dispatch, client, seeded_followups):
        mock_dispatch.return_value = (True, "dispatched")
        resp = client.post(
            f"/followups/{seeded_followups}/approve",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        mock_dispatch.assert_awaited_once()
        draft_arg = mock_dispatch.call_args[0][0]
        assert draft_arg.draft_id == seeded_followups

    @patch("pipeline.followup_dispatcher.dispatch_single_draft", new_callable=AsyncMock)
    def test_approve_succeeds_when_dispatch_fails(self, mock_dispatch, client, seeded_followups):
        mock_dispatch.side_effect = Exception("GHL down")
        resp = client.post(
            f"/followups/{seeded_followups}/approve",
            follow_redirects=False,
        )
        assert resp.status_code == 303
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.APPROVED

    @patch("pipeline.followup_dispatcher.dispatch_single_draft", new_callable=AsyncMock)
    def test_batch_approve_dispatches_each(self, mock_dispatch, client, seeded_followups):
        mock_dispatch.return_value = (True, "dispatched")
        resp = client.post(
            "/followups/batch/approve",
            data={"draft_ids": seeded_followups},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        mock_dispatch.assert_awaited_once()

    @patch("pipeline.followup_dispatcher.dispatch_single_draft", new_callable=AsyncMock, return_value=(True, "dispatched"))
    def test_briefing_shows_live_draft_status_counts(self, _mock_dispatch, client, seeded_followups):
        """Live draft status counts update when drafts are approved/rejected."""
        resp = client.get("/briefing")
        assert resp.status_code == 200
        # Initially all drafts are PENDING — check live count cards
        assert "Pending" in resp.text
        assert "Approved" in resp.text
        assert "Rejected" in resp.text

        # Approve the draft
        client.post(f"/followups/{seeded_followups}/approve", follow_redirects=False)
        resp2 = client.get("/briefing")
        assert resp2.status_code == 200
        # The approved count should be reflected in the live data
        assert "Approved" in resp2.text

    @patch("dashboard.app.run_followup_orchestrator", new_callable=AsyncMock)
    @patch("scripts.ghl_conversation_scanner.refresh_candidates", new_callable=AsyncMock)
    def test_generate_with_refresh_calls_refresh_candidates(self, mock_refresh, mock_orchestrator, client):
        mock_refresh.return_value = [{"ghl_contact_id": "c-1"}]
        mock_orchestrator.return_value = {
            "status": "complete", "briefing_date": "2026-03-09",
            "briefing_path": "outputs/briefings/2026-03-09.json",
            "saved": 1, "errors": [],
        }

        resp = client.post(
            "/followups/generate",
            data={"force": "true", "refresh": "true"},
        )

        assert resp.status_code == 200
        mock_refresh.assert_awaited_once()
        mock_orchestrator.assert_awaited_once()

    def test_briefing_route_shows_contact_level_actions(self, client, seeded_followups):
        resp = client.get("/briefing")
        assert resp.status_code == 200
        assert "/followups/contact/contact-followup-1?date=2026-03-08" in resp.text
        # Analysis-only contacts (no draft) should NOT appear in queue/briefing
        assert "/followups/contact/contact-followup-2?date=2026-03-08" not in resp.text
        assert "View Draft" in resp.text

    def test_followup_edit_persists_pending_draft(self, client, seeded_followups):
        resp = client.post(
            f"/followups/{seeded_followups}/edit",
            data={
                "subject": "Updated subject",
                "body": _valid_followup_edit_body("Updated subject"),
            },
            follow_redirects=False,
        )

        assert resp.status_code == 303
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.subject == "Updated subject"
        assert "You asked for timing options" in updated.body
        assert updated.status == DraftApprovalStatus.PENDING
        assert updated.edited_at is not None

    def test_followup_edit_resets_approved_draft_to_pending(self, client, seeded_followups):
        approved = get_followup_draft(seeded_followups)
        assert approved is not None
        approved.status = DraftApprovalStatus.APPROVED
        approved.approved_at = "2026-03-08T12:00:00+00:00"
        save_followup_draft(approved)

        resp = client.post(
            f"/followups/{seeded_followups}/edit",
            data={
                "subject": "Approved but edited",
                "body": _valid_followup_edit_body("Approved but edited"),
            },
            follow_redirects=False,
        )

        assert resp.status_code == 303
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.PENDING
        assert updated.approved_at is None

    def test_followup_edit_resets_rejected_draft_to_pending(self, client, seeded_followups):
        rejected = get_followup_draft(seeded_followups)
        assert rejected is not None
        rejected.status = DraftApprovalStatus.REJECTED
        rejected.rejected_at = "2026-03-08T12:00:00+00:00"
        rejected.rejection_reason = "Too generic"
        save_followup_draft(rejected)

        resp = client.post(
            f"/followups/{seeded_followups}/edit",
            data={
                "subject": "Rejected but edited",
                "body": _valid_followup_edit_body("Rejected but edited"),
            },
            follow_redirects=False,
        )

        assert resp.status_code == 303
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.PENDING
        assert updated.rejected_at is None
        assert updated.rejection_reason is None

    def test_followup_edit_resets_send_failed_draft_to_pending(self, client, seeded_followups):
        failed = get_followup_draft(seeded_followups)
        assert failed is not None
        failed.status = DraftApprovalStatus.SEND_FAILED
        failed.send_failed_at = "2026-03-08T12:00:00+00:00"
        failed.dispatch_error = "smtp timeout"
        save_followup_draft(failed)

        resp = client.post(
            f"/followups/{seeded_followups}/edit",
            data={
                "subject": "Retry subject",
                "body": _valid_followup_edit_body("Retry subject"),
            },
            follow_redirects=False,
        )

        assert resp.status_code == 303
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.PENDING
        assert updated.send_failed_at is None
        assert updated.dispatch_error is None

    def test_followup_edit_blocks_dispatched_draft(self, client, seeded_followups):
        dispatched = get_followup_draft(seeded_followups)
        assert dispatched is not None
        dispatched.status = DraftApprovalStatus.DISPATCHED
        save_followup_draft(dispatched)

        resp = client.post(
            f"/followups/{seeded_followups}/edit",
            data={
                "subject": "Should fail",
                "body": "Alex,\n\nBlocked edit.\n\nReply with \"unsubscribe\" to opt out.",
            },
        )

        assert resp.status_code == 409
        assert "can no longer be edited" in resp.text
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.subject == "Timing options for next week"

    def test_followup_edit_validation_failure_does_not_persist(self, client, seeded_followups):
        original = get_followup_draft(seeded_followups)
        assert original is not None

        resp = client.post(
            f"/followups/{seeded_followups}/edit",
            data={
                "subject": "",
                "body": "",
            },
        )

        assert resp.status_code == 422
        assert "Subject is required." in resp.text
        assert "Body is required." in resp.text
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.subject == original.subject
        assert updated.body == original.body

    def test_followup_edit_save_failure_returns_503_with_preserved_form(self, client, seeded_followups):
        with patch("dashboard.app.save_followup_draft", side_effect=RuntimeError("db write failed")):
            resp = client.post(
                f"/followups/{seeded_followups}/edit",
                data={
                    "subject": "Edited subject before failure",
                    "body": _valid_followup_edit_body("Edited subject before failure"),
                },
            )

        assert resp.status_code == 503
        assert "could not be saved right now" in resp.text
        assert "Edited subject before failure" in resp.text

    def test_followup_edit_save_failure_does_not_mutate_stored_draft(self, client, seeded_followups):
        original = get_followup_draft(seeded_followups)
        assert original is not None
        original_subject = original.subject
        original_body = original.body

        with patch("dashboard.app.save_followup_draft", side_effect=RuntimeError("db write failed")):
            client.post(
                f"/followups/{seeded_followups}/edit",
                data={
                    "subject": "Should not persist",
                    "body": _valid_followup_edit_body("Should not persist"),
                },
            )

        after = get_followup_draft(seeded_followups)
        assert after is not None
        assert after.subject == original_subject
        assert after.body == original_body

    def test_detail_falls_back_to_primary_thread_when_source_id_missing(self, client, seeded_followups):
        """When draft source_conversation_id doesn't match any thread, fall back to primary thread."""
        draft = get_followup_draft(seeded_followups)
        assert draft is not None
        draft.source_conversation_id = "conv-nonexistent"
        save_followup_draft(draft)

        resp = client.get("/followups/contact/contact-followup-1")
        assert resp.status_code == 200
        # Primary thread (conv-1) should still display as fallback
        assert "Can you send timing options?" in resp.text

    def test_detail_renders_cleanly_without_any_thread(self, client, tmp_path):
        """When the summary has no threads, the page renders without crashing."""
        summary_data = {
            "contactId": "contact-no-threads",
            "ghlContactId": "ghl-no-threads",
            "firstName": "No",
            "lastName": "Threads",
            "email": "nothreads@acme.com",
            "companyName": "Acme",
            "title": "VP",
            "threads": [],
            "totalMessages": 0,
            "lastInboundDate": None,
            "lastOutboundDate": None,
            "scannedAt": "2026-03-08T10:00:00+00:00",
        }
        _write_indexed_model(tmp_path, "conversations", "contact-no-threads", summary_data)

        analysis_data = {
            "contactId": "contact-no-threads",
            "sourceConversationId": "conv-missing",
            "sentiment": "neutral",
            "stage": "new",
            "trigger": "no_reply",
            "triggerReason": "No reply.",
            "urgency": "warm",
            "keyTopics": [],
            "recommendedAction": "Follow up.",
            "conversationSummary": "No threads available.",
            "daysSinceLastActivity": 5,
            "analyzedAt": "2026-03-08T11:00:00+00:00",
        }
        _write_indexed_model(tmp_path, "conversation_analysis", "contact-no-threads", analysis_data)

        resp = client.get("/followups/contact/contact-no-threads")
        assert resp.status_code == 200
        assert "no matching thread messages were loaded" in resp.text

    @patch("dashboard.app.run_followup_orchestrator", new_callable=AsyncMock)
    def test_followup_generate_triggers_manual_orchestrator(self, mock_orchestrator, client):
        mock_orchestrator.return_value = {
            "status": "complete",
            "briefing_date": "2026-03-09",
            "briefing_path": "outputs/briefings/2026-03-09.json",
            "saved": 2,
            "errors": [],
        }

        resp = client.post(
            "/followups/generate",
            data={"force": "true"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "complete"
        assert resp.json()["saved"] == 2
        assert mock_orchestrator.await_count == 1
        assert mock_orchestrator.await_args.kwargs == {
            "task_id": "warm-followup-manual",
            "force": True,
            "batch_size": None,
            "scan_days": None,
        }

    @patch("dashboard.app.run_followup_orchestrator", new_callable=AsyncMock)
    def test_followup_generate_returns_503_for_blocking_status(self, mock_orchestrator, client):
        mock_orchestrator.return_value = {
            "status": "blocked_missing_anthropic_api_key",
            "briefing_date": "2026-03-09",
            "briefing_path": None,
            "errors": ["ANTHROPIC_API_KEY is required for AnthropicClient"],
        }

        resp = client.post("/followups/generate")

        assert resp.status_code == 503
        assert resp.json()["status"] == "blocked_missing_anthropic_api_key"

    @patch("dashboard.app.run_followup_orchestrator", new_callable=AsyncMock)
    def test_followup_generate_returns_503_on_unexpected_failure(self, mock_orchestrator, client):
        mock_orchestrator.side_effect = RuntimeError("vault unavailable")

        resp = client.post("/followups/generate")

        assert resp.status_code == 503
        assert resp.json()["status"] == "error"
        assert resp.json()["saved"] == 0
        assert resp.json()["errors"] == ["Warm pipeline unavailable"]

    def test_scheduler_enabled_does_not_crash_without_apscheduler(self, monkeypatch):
        monkeypatch.setenv("SCHEDULER_ENABLED", "true")
        from dashboard.app import app

        with patch(
            "pipeline.scheduler.start_scheduler",
            side_effect=ImportError("apscheduler not installed"),
        ):
            with TestClient(app) as local_client:
                resp = local_client.get("/")

        assert resp.status_code == 200

    @patch("dashboard.app.dispatch_approved_followups", new_callable=AsyncMock)
    @patch("dashboard.app.dispatch_approved_drafts", new_callable=AsyncMock)
    def test_dispatch_run_returns_unified_payload(self, mock_cold, mock_warm, client):
        mock_warm.return_value = type(
            "WarmResult",
            (),
            {
                "dispatched": 2,
                "skipped_dedup": 1,
                "skipped_rate_limit": 0,
                "skipped_circuit_breaker": 0,
                "failed": 1,
                "errors": ["warm err"],
            },
        )()
        mock_cold.return_value = type(
            "ColdResult",
            (),
            {
                "dispatched": 1,
                "skipped_dedup": 0,
                "skipped_rate_limit": 1,
                "skipped_circuit_breaker": 0,
                "skipped_tier": 2,
                "skipped_deferred_channel": 3,
                "failed": 0,
                "errors": [],
            },
        )()

        resp = client.post("/dispatch/run")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["warm"]["dispatched"] == 2
        assert payload["cold"]["dispatched"] == 1
        assert payload["cold"]["skippedDeferredChannel"] == 3
        assert payload["totals"] == {"dispatched": 3, "failed": 1}


class TestCronWarmPipeline:
    def test_cron_rejects_missing_secret(self, client):
        resp = client.get("/api/cron/warm-pipeline")
        assert resp.status_code == 500

    def test_cron_rejects_bad_token(self, client, monkeypatch):
        monkeypatch.setenv("CRON_SECRET", "valid-secret-123")
        resp = client.get(
            "/api/cron/warm-pipeline",
            headers={"Authorization": "Bearer wrong-secret"},
        )
        assert resp.status_code == 401

    @patch("dashboard.app.dispatch_approved_followups", new_callable=AsyncMock)
    @patch("dashboard.app.run_followup_orchestrator", new_callable=AsyncMock)
    def test_cron_triggers_pipeline_with_valid_secret(self, mock_orchestrator, mock_dispatch, client, monkeypatch):
        monkeypatch.setenv("CRON_SECRET", "valid-secret-123")
        mock_orchestrator.return_value = {
            "status": "complete",
            "briefing_date": "2026-03-10",
            "saved": 5,
            "errors": [],
        }
        mock_dispatch.return_value = AsyncMock(
            dispatched=0, skipped_dedup=0, skipped_rate_limit=0,
            skipped_circuit_breaker=0, failed=0, errors=[],
        )

        resp = client.get(
            "/api/cron/warm-pipeline",
            headers={"Authorization": "Bearer valid-secret-123"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "complete"
        assert mock_orchestrator.await_args.kwargs["task_id"] == "warm-followup-cron"
        assert mock_orchestrator.await_args.kwargs["force"] is False

    @patch("dashboard.app.run_followup_orchestrator", new_callable=AsyncMock)
    def test_cron_returns_500_on_pipeline_failure(self, mock_orchestrator, client, monkeypatch):
        monkeypatch.setenv("CRON_SECRET", "valid-secret-123")
        mock_orchestrator.side_effect = RuntimeError("DB connection failed")

        resp = client.get(
            "/api/cron/warm-pipeline",
            headers={"Authorization": "Bearer valid-secret-123"},
        )

        assert resp.status_code == 500
        assert resp.json()["status"] == "error"

    @patch("dashboard.app.dispatch_approved_followups", new_callable=AsyncMock)
    @patch("dashboard.app.run_followup_orchestrator", new_callable=AsyncMock)
    def test_cron_auto_dispatches_after_generation(self, mock_orchestrator, mock_dispatch, client, monkeypatch):
        monkeypatch.setenv("CRON_SECRET", "valid-secret-123")
        mock_orchestrator.return_value = {
            "status": "complete",
            "briefing_date": "2026-03-11",
            "saved": 5,
            "errors": [],
        }
        mock_dispatch.return_value = AsyncMock(
            dispatched=5, skipped_dedup=0, skipped_rate_limit=0,
            skipped_circuit_breaker=0, failed=0, errors=[],
        )

        resp = client.get(
            "/api/cron/warm-pipeline",
            headers={"Authorization": "Bearer valid-secret-123"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "complete"
        assert payload["dispatch"]["dispatched"] == 5
        assert payload["dispatch"]["failed"] == 0
        mock_dispatch.assert_awaited_once()

    def test_cron_dispatch_endpoint_requires_secret(self, client):
        resp = client.get("/api/cron/dispatch")
        assert resp.status_code == 500

    @patch("dashboard.app.dispatch_approved_followups", new_callable=AsyncMock)
    def test_cron_dispatch_endpoint_dispatches_approved(self, mock_dispatch, client, monkeypatch):
        monkeypatch.setenv("CRON_SECRET", "valid-secret-123")
        mock_dispatch.return_value = AsyncMock(
            dispatched=3, skipped_dedup=1, skipped_rate_limit=0,
            skipped_circuit_breaker=0, failed=0, errors=[],
        )

        resp = client.get(
            "/api/cron/dispatch",
            headers={"Authorization": "Bearer valid-secret-123"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert payload["dispatched"] == 3
        assert payload["skippedDedup"] == 1
        mock_dispatch.assert_awaited_once()


class TestDashboardAuthAndWarmOnly:
    def test_healthz_stays_open_when_auth_enabled(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_AUTH_ENABLED", "true")
        monkeypatch.setenv("DASHBOARD_BASIC_AUTH_USER", "dani")
        monkeypatch.setenv("DASHBOARD_BASIC_AUTH_PASS", "secret")
        from dashboard.app import app

        with TestClient(app) as local_client:
            resp = local_client.get("/healthz")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_healthz_probes_postgres_when_enabled(self, client):
        class _FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query):
                assert query == "SELECT 1"

            def fetchone(self):
                return (1,)

        class _FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return _FakeCursor()

        class _FakeBackend:
            def _connect(self):
                return _FakeConnection()

        with (
            patch("dashboard.app.get_storage_backend_name", return_value="postgres"),
            patch("dashboard.app.get_storage_backend", return_value=_FakeBackend()),
        ):
            resp = client.get("/healthz")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["db"] == "connected"

    def test_healthz_returns_degraded_when_postgres_probe_fails(self, client):
        class _BrokenBackend:
            def _connect(self):
                raise RuntimeError("db unavailable")

        with (
            patch("dashboard.app.get_storage_backend_name", return_value="postgres"),
            patch("dashboard.app.get_storage_backend", return_value=_BrokenBackend()),
        ):
            resp = client.get("/healthz")

        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"
        assert resp.json()["db"] == "error"
        assert "db unavailable" in resp.json()["detail"]

    def test_auth_challenge_protects_dashboard_routes(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_AUTH_ENABLED", "true")
        monkeypatch.setenv("DASHBOARD_BASIC_AUTH_USER", "dani")
        monkeypatch.setenv("DASHBOARD_BASIC_AUTH_PASS", "secret")
        from dashboard.app import app

        with TestClient(app) as local_client:
            resp = local_client.get("/briefing")

        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == "Basic"

    def test_authorized_dashboard_request_succeeds(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_AUTH_ENABLED", "true")
        monkeypatch.setenv("DASHBOARD_BASIC_AUTH_USER", "dani")
        monkeypatch.setenv("DASHBOARD_BASIC_AUTH_PASS", "secret")
        from dashboard.app import app

        with TestClient(app) as local_client:
            resp = local_client.get("/briefing", headers=_basic_auth_headers())

        assert resp.status_code == 200

    def test_warm_only_mode_redirects_root_and_blocks_cold_routes(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_AUTH_ENABLED", "false")
        monkeypatch.setenv("WARM_ONLY_MODE", "true")
        monkeypatch.setenv("STORAGE_BACKEND", "postgres")
        monkeypatch.setenv("DATABASE_URL", "postgresql://example")
        from dashboard.app import app

        with TestClient(app) as local_client:
            root = local_client.get("/", follow_redirects=False)
            cold = local_client.get("/cold-drafts", follow_redirects=False)

        assert root.status_code == 307
        assert root.headers["location"] == "/briefing"
        assert cold.status_code == 404

    def test_warm_only_mode_requires_postgres_backend(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_AUTH_ENABLED", "false")
        monkeypatch.setenv("WARM_ONLY_MODE", "true")
        monkeypatch.setenv("STORAGE_BACKEND", "file")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from dashboard.app import app

        with pytest.raises(RuntimeError, match="WARM_ONLY_MODE=true requires STORAGE_BACKEND=postgres"):
            with TestClient(app):
                pass

    def test_followup_detail_returns_503_error_state_on_storage_failure(self, client):
        with patch("dashboard.app.get_followup_draft", side_effect=RuntimeError("db unavailable")):
            resp = client.get("/followups/followup-1")

        assert resp.status_code == 503
        assert "Follow-Up Unavailable" in resp.text
        assert "could not be loaded right now" in resp.text

    def test_followup_contact_detail_returns_503_error_state_on_storage_failure(self, client):
        with patch("dashboard.app.load_followup_queue", side_effect=RuntimeError("db unavailable")):
            resp = client.get("/followups/contact/contact-followup-1")

        assert resp.status_code == 503
        assert "Follow-Up Unavailable" in resp.text
        assert "could not be loaded right now" in resp.text

    def test_dispatch_view_renders_degraded_state_on_storage_failure(self, client):
        with patch("dashboard.app.list_followup_drafts", side_effect=RuntimeError("db unavailable")):
            resp = client.get("/dispatch")

        assert resp.status_code == 200
        assert "Dispatch data unavailable" in resp.text

    def test_dispatch_view_renders_cleanly_when_kpi_snapshot_is_absent(self, client):
        with patch("dashboard.app.KPITracker.get_latest_kpi", return_value=None):
            resp = client.get("/dispatch")

        assert resp.status_code == 200
        assert "Dispatch data unavailable" not in resp.text
        assert "Daily Limit / Channel" in resp.text

    def test_dispatch_view_uses_env_override_for_daily_limit(self, client, monkeypatch):
        monkeypatch.setenv("DISPATCH_DAILY_LIMIT", "30")

        with patch("dashboard.app.KPITracker.get_latest_kpi", return_value=None):
            resp = client.get("/dispatch")

        assert resp.status_code == 200
        assert ">30<" in resp.text

    def test_dispatch_status_returns_degraded_json_on_storage_failure(self, client):
        with patch("dashboard.app.CircuitBreaker", side_effect=RuntimeError("db unavailable")):
            resp = client.get("/dispatch/status")

        assert resp.status_code == 503
        assert resp.json()["status"] == "degraded"
        assert resp.json()["errors"] == ["Dispatch status unavailable"]

    @patch("dashboard.app.dispatch_approved_followups", new_callable=AsyncMock)
    def test_dispatch_run_returns_503_error_json_on_storage_failure(self, mock_warm, client):
        mock_warm.side_effect = RuntimeError("db unavailable")

        resp = client.post("/dispatch/run")

        assert resp.status_code == 503
        payload = resp.json()
        assert payload["status"] == "error"
        assert payload["totals"] == {"dispatched": 0, "failed": 0}
        assert payload["errors"] == ["Dispatch run failed"]
