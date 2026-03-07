"""Tests for GHL client and service layer."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.ghl_client import GHLClient
from integrations.ghl_service import push_approved_draft_to_ghl
from models.schemas import Channel, DraftApprovalStatus, StoredDraft


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_stored_draft(**overrides) -> StoredDraft:
    defaults = {
        "draftId": "abc123",
        "contactId": "jane@acme.com",
        "icpTier": "1",
        "angleId": "ai_executive_briefing",
        "subject": "AI strategy for Acme",
        "body": "Hi Jane,\n\nLet's talk AI.\n\nBest,\nChris",
        "channel": Channel.GHL,
        "bookingLink": "https://caio.cx/ai-exec-briefing-call",
        "status": DraftApprovalStatus.APPROVED,
        "createdAt": "2026-03-07T00:00:00Z",
    }
    defaults.update(overrides)
    return StoredDraft.model_validate(defaults)


def _mock_response(status_code: int = 200, json_data: dict | None = None, headers: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# ── GHLClient Tests ───────────────────────────────────────────────────────────


class TestGHLClientUpsert:
    @pytest.mark.asyncio
    async def test_upsert_contact_success(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=_mock_response(
            200, {"contact": {"id": "ghl-contact-1", "email": "jane@acme.com"}}
        ))
        client._client = mock_http

        result = await client.upsert_contact(
            email="jane@acme.com",
            first_name="Jane",
            last_name="Doe",
            company_name="Acme",
            tags=["revtry-approved"],
        )

        assert result["contact"]["id"] == "ghl-contact-1"
        call_args = mock_http.request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["locationId"] == "loc-123"
        assert payload["email"] == "jane@acme.com"
        assert payload["tags"] == ["revtry-approved"]

    @pytest.mark.asyncio
    async def test_upsert_retry_on_500(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_http = AsyncMock()
        mock_http.is_closed = False

        fail_resp = _mock_response(500)
        ok_resp = _mock_response(200, {"contact": {"id": "ghl-contact-2"}})
        mock_http.request = AsyncMock(side_effect=[fail_resp, ok_resp])
        client._client = mock_http

        result = await client.upsert_contact(email="test@example.com")
        assert result["contact"]["id"] == "ghl-contact-2"
        assert mock_http.request.call_count == 2

    @pytest.mark.asyncio
    async def test_upsert_rate_limit_429(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_http = AsyncMock()
        mock_http.is_closed = False

        rate_resp = _mock_response(429, headers={"Retry-After": "1"})
        rate_resp.raise_for_status = MagicMock()  # 429 doesn't raise, just retries
        ok_resp = _mock_response(200, {"contact": {"id": "ghl-contact-3"}})
        mock_http.request = AsyncMock(side_effect=[rate_resp, ok_resp])
        client._client = mock_http

        result = await client.upsert_contact(email="test@example.com")
        assert result["contact"]["id"] == "ghl-contact-3"


class TestGHLClientSendEmail:
    @pytest.mark.asyncio
    async def test_send_email_success(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=_mock_response(
            200, {"messageId": "msg-1", "status": "sent"}
        ))
        client._client = mock_http

        result = await client.send_email(
            contact_id="ghl-contact-1",
            to_email="jane@acme.com",
            subject="AI Strategy",
            body="Hi Jane, let's discuss AI.",
        )

        assert result["messageId"] == "msg-1"
        call_args = mock_http.request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "Email"
        assert payload["contactId"] == "ghl-contact-1"
        assert payload["subject"] == "AI Strategy"
        assert "html" in payload  # GHL API uses 'html', not 'body'
        assert "body" not in payload

    @pytest.mark.asyncio
    async def test_send_email_retry_on_500(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_http = AsyncMock()
        mock_http.is_closed = False

        fail_resp = _mock_response(500)
        ok_resp = _mock_response(200, {"messageId": "msg-2"})
        mock_http.request = AsyncMock(side_effect=[fail_resp, ok_resp])
        client._client = mock_http

        result = await client.send_email(
            contact_id="ghl-contact-1",
            to_email="jane@acme.com",
            subject="Test",
            body="Body",
        )
        assert result["messageId"] == "msg-2"
        assert mock_http.request.call_count == 2

    @pytest.mark.asyncio
    async def test_send_email_uses_contact_id(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=_mock_response(200, {}))
        client._client = mock_http

        await client.send_email(
            contact_id="ghl-999",
            to_email="test@test.com",
            subject="Sub",
            body="Body",
        )

        call_args = mock_http.request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["contactId"] == "ghl-999"
        assert "/conversations/messages" in call_args[0][1]


class TestGHLClientTask:
    @pytest.mark.asyncio
    async def test_create_task_success(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=_mock_response(
            200, {"task": {"id": "task-1", "title": "Follow up"}}
        ))
        client._client = mock_http

        result = await client.create_task(
            contact_id="ghl-contact-1",
            title="Follow up: AI strategy",
            description="Approved draft for jane@acme.com",
        )

        assert result["task"]["id"] == "task-1"
        call_args = mock_http.request.call_args
        assert "/contacts/ghl-contact-1/tasks" in call_args[0][1]
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "dueDate" in payload  # GHL requires dueDate
        assert payload["body"] == "Approved draft for jane@acme.com"  # GHL uses 'body', not 'description'


# ── GHL Service Tests ─────────────────────────────────────────────────────────


class TestGHLService:
    @pytest.mark.asyncio
    async def test_push_approved_draft_success(self):
        draft = _make_stored_draft()
        mock_ghl = AsyncMock(spec=GHLClient)
        mock_ghl.upsert_contact = AsyncMock(return_value={
            "contact": {"id": "ghl-contact-1"}
        })
        mock_ghl.create_task = AsyncMock(return_value={
            "task": {"id": "task-1"}
        })

        result = await push_approved_draft_to_ghl(draft, ghl=mock_ghl)

        assert result["status"] == "pushed"
        assert result["ghl_contact_id"] == "ghl-contact-1"
        assert result["ghl_task_id"] == "task-1"
        mock_ghl.upsert_contact.assert_awaited_once()
        mock_ghl.create_task.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_push_failure_returns_error_dict(self):
        draft = _make_stored_draft()
        mock_ghl = AsyncMock(spec=GHLClient)
        mock_ghl.upsert_contact = AsyncMock(side_effect=Exception("Connection refused"))

        result = await push_approved_draft_to_ghl(draft, ghl=mock_ghl)

        assert result["status"] == "ghl_push_failed"
        assert "Connection refused" in result["error"]
