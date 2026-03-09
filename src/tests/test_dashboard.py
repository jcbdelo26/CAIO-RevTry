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

    def test_followup_detail_route(self, client, seeded_followups):
        resp = client.get(f"/followups/{seeded_followups}")
        assert resp.status_code == 200
        assert "Timing options for next week" in resp.text
        assert "Can you send timing options?" in resp.text

    def test_followup_approve_route(self, client, seeded_followups):
        resp = client.post(
            f"/followups/{seeded_followups}/approve",
            follow_redirects=False,
        )
        assert resp.status_code == 303
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
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.REJECTED

    def test_followup_batch_approve(self, client, seeded_followups):
        resp = client.post(
            "/followups/batch/approve",
            data={"draft_ids": seeded_followups},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        updated = get_followup_draft(seeded_followups)
        assert updated is not None
        assert updated.status == DraftApprovalStatus.APPROVED

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

    def test_dispatch_view_renders_degraded_state_on_storage_failure(self, client):
        with patch("dashboard.app.list_followup_drafts", side_effect=RuntimeError("db unavailable")):
            resp = client.get("/dispatch")

        assert resp.status_code == 200
        assert "Dispatch data unavailable" in resp.text

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
