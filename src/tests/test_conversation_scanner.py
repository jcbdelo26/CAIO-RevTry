"""Tests for GHL conversation scanner and client GET methods."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.ghl_client import GHLClient
from scripts.ghl_conversation_scanner import (
    _parse_messages,
    compact_thread_messages,
    filter_eligible_summaries,
    has_valid_email,
    load_candidates,
    scan_all_contacts,
    scan_contact,
    select_primary_thread,
)


# ── GHLClient GET method tests ───────────────────────────────────────────────


class TestGHLClientGETMethods:
    @pytest.mark.asyncio
    async def test_search_conversations(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"conversations": [{"id": "conv-1"}]}
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.search_conversations("contact-abc")

        mock_http.request.assert_called_once()
        call_args = mock_http.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "/conversations/search"
        assert call_args[1]["params"]["contactId"] == "contact-abc"
        assert call_args[1]["params"]["locationId"] == "loc-123"
        assert result["conversations"][0]["id"] == "conv-1"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_messages(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "msg-1", "body": "Hello"}]}
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_messages("conv-1")

        call_args = mock_http.request.call_args
        assert "/conversations/conv-1/messages" in call_args[0][1]
        assert result["messages"][0]["body"] == "Hello"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_contact(self):
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"contact": {"id": "c-1", "firstName": "Jane"}}
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_contact("c-1")

        call_args = mock_http.request.call_args
        assert "/contacts/c-1" in call_args[0][1]
        assert result["contact"]["firstName"] == "Jane"

        await client.close()

    @pytest.mark.asyncio
    async def test_request_passes_params_for_get(self):
        """Verify _request passes params kwarg to httpx for GET requests."""
        client = GHLClient(api_key="test-key", location_id="loc-123")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client._request("GET", "/test", params={"foo": "bar"})

        call_kwargs = mock_http.request.call_args[1]
        assert call_kwargs["params"] == {"foo": "bar"}
        assert call_kwargs["json"] is None

        await client.close()


# ── Message parsing tests ────────────────────────────────────────────────────


class TestParseMessages:
    def test_filters_old_messages(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        old_date = (cutoff - timedelta(days=5)).isoformat()
        recent_date = (cutoff + timedelta(days=1)).isoformat()

        raw = [
            {"id": "old", "dateAdded": old_date, "direction": "outbound", "body": "old msg"},
            {"id": "new", "dateAdded": recent_date, "direction": "inbound", "body": "new msg"},
        ]

        result = _parse_messages(raw, "conv-1", cutoff)
        assert len(result) == 1
        assert result[0].message_id == "new"
        assert result[0].direction == "inbound"

    def test_handles_missing_timestamps(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        raw = [{"id": "no-ts", "body": "missing"}]
        result = _parse_messages(raw, "conv-1", cutoff)
        assert len(result) == 0

    def test_parses_all_fields(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        ts = datetime.now(timezone.utc).isoformat()
        raw = [{
            "id": "msg-1",
            "dateAdded": ts,
            "direction": "inbound",
            "body": "Hello!",
            "subject": "Re: Meeting",
            "type": "Email",
        }]

        result = _parse_messages(raw, "conv-1", cutoff)
        assert len(result) == 1
        assert result[0].subject == "Re: Meeting"
        assert result[0].body == "Hello!"
        assert result[0].message_type == "Email"


# ── Scanner tests ────────────────────────────────────────────────────────────


class TestScanContact:
    @pytest.mark.asyncio
    async def test_scan_contact_with_messages(self):
        ts = datetime.now(timezone.utc).isoformat()
        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(return_value={
            "conversations": [{"id": "conv-1"}],
        })
        mock_ghl.get_messages = AsyncMock(return_value={
            "messages": [
                {"id": "m1", "dateAdded": ts, "direction": "outbound", "body": "Hi there"},
                {"id": "m2", "dateAdded": ts, "direction": "inbound", "body": "Thanks!"},
            ],
        })

        contact = {
            "ghl_contact_id": "c-123",
            "email": "jane@acme.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "company_name": "Acme Corp",
        }

        result = await scan_contact(mock_ghl, contact, scan_days=30)

        assert result is not None
        assert result.contact_id == "c-123"
        assert result.first_name == "Jane"
        assert result.company_name == "Acme Corp"
        assert result.total_messages == 2
        assert result.last_inbound_date is not None
        assert result.last_outbound_date is not None
        assert len(result.threads) == 1

    @pytest.mark.asyncio
    async def test_scan_contact_no_conversations(self):
        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(return_value={"conversations": []})

        contact = {"ghl_contact_id": "c-empty"}
        result = await scan_contact(mock_ghl, contact, scan_days=30)

        assert result is not None
        assert result.total_messages == 0
        assert len(result.threads) == 0

    @pytest.mark.asyncio
    async def test_scan_contact_missing_id(self):
        mock_ghl = MagicMock()
        result = await scan_contact(mock_ghl, {}, scan_days=30)
        assert result is None

    @pytest.mark.asyncio
    async def test_scan_contact_api_error_returns_none(self):
        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(side_effect=Exception("API error"))

        contact = {"ghl_contact_id": "c-err"}
        result = await scan_contact(mock_ghl, contact, scan_days=30)
        assert result is None


class TestScanAllContacts:
    @pytest.mark.asyncio
    async def test_scan_all_writes_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))

        ts = datetime.now(timezone.utc).isoformat()
        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(return_value={
            "conversations": [{"id": "conv-1"}],
        })
        mock_ghl.get_messages = AsyncMock(return_value={
            "messages": [
                {"id": "m1", "dateAdded": ts, "direction": "outbound", "body": "Hello"},
            ],
        })
        mock_ghl.close = AsyncMock()

        candidates = [
            {"ghl_contact_id": "c-1", "email": "a@test.com", "first_name": "Alice"},
            {"ghl_contact_id": "c-2", "email": "b@test.com", "first_name": "Bob"},
        ]

        summaries = await scan_all_contacts(candidates, ghl=mock_ghl, scan_days=30)

        assert len(summaries) == 2

        # Check files were written
        conv_dir = tmp_path / "outputs" / "conversations"
        assert (conv_dir / "c-1.json").exists()
        assert (conv_dir / "c-2.json").exists()
        assert (conv_dir / "index.json").exists()

        # Verify index
        index = json.loads((conv_dir / "index.json").read_text())
        assert "c-1" in index
        assert "c-2" in index


class TestLoadCandidates:
    def test_loads_list_format(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        candidates = [{"ghl_contact_id": "c-1"}, {"ghl_contact_id": "c-2"}]
        (tmp_path / "ghl_followup_candidates.json").write_text(json.dumps(candidates))

        result = load_candidates(batch_size=10)
        assert len(result) == 2

    def test_loads_dict_format(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        data = {"candidates": [{"ghl_contact_id": "c-1"}]}
        (tmp_path / "ghl_followup_candidates.json").write_text(json.dumps(data))

        result = load_candidates(batch_size=10)
        assert len(result) == 1

    def test_respects_batch_size(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        candidates = [{"ghl_contact_id": f"c-{i}"} for i in range(20)]
        (tmp_path / "ghl_followup_candidates.json").write_text(json.dumps(candidates))

        result = load_candidates(batch_size=5)
        assert len(result) == 5

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        result = load_candidates()
        assert result == []

    def test_respects_daily_scan_batch_size_env(self, tmp_path, monkeypatch):
        """DAILY_SCAN_BATCH_SIZE env var controls batch size when no arg given."""
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        monkeypatch.setenv("DAILY_SCAN_BATCH_SIZE", "3")
        monkeypatch.delenv("MAX_SCAN_CONTACTS", raising=False)
        candidates = [{"ghl_contact_id": f"c-{i}"} for i in range(10)]
        (tmp_path / "ghl_followup_candidates.json").write_text(json.dumps(candidates))

        result = load_candidates()
        assert len(result) == 3

    def test_daily_scan_batch_size_takes_precedence_over_deprecated_alias(self, tmp_path, monkeypatch):
        """DAILY_SCAN_BATCH_SIZE wins over MAX_SCAN_CONTACTS when both are set."""
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        monkeypatch.setenv("DAILY_SCAN_BATCH_SIZE", "4")
        monkeypatch.setenv("MAX_SCAN_CONTACTS", "9")
        candidates = [{"ghl_contact_id": f"c-{i}"} for i in range(10)]
        (tmp_path / "ghl_followup_candidates.json").write_text(json.dumps(candidates))

        result = load_candidates()
        assert len(result) == 4

    def test_max_scan_contacts_is_deprecated_fallback(self, tmp_path, monkeypatch):
        """MAX_SCAN_CONTACTS works as fallback when DAILY_SCAN_BATCH_SIZE is absent."""
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        monkeypatch.delenv("DAILY_SCAN_BATCH_SIZE", raising=False)
        monkeypatch.setenv("MAX_SCAN_CONTACTS", "2")
        candidates = [{"ghl_contact_id": f"c-{i}"} for i in range(10)]
        (tmp_path / "ghl_followup_candidates.json").write_text(json.dumps(candidates))

        result = load_candidates()
        assert len(result) == 2

    def test_explicit_batch_size_arg_overrides_env(self, tmp_path, monkeypatch):
        """Explicit batch_size arg always takes precedence over env vars."""
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        monkeypatch.setenv("DAILY_SCAN_BATCH_SIZE", "8")
        candidates = [{"ghl_contact_id": f"c-{i}"} for i in range(10)]
        (tmp_path / "ghl_followup_candidates.json").write_text(json.dumps(candidates))

        result = load_candidates(batch_size=2)
        assert len(result) == 2


class TestScanContactEligibility:
    @pytest.mark.asyncio
    async def test_zero_message_contact_returns_summary_not_none(self):
        """Scanner returns summary for zero-message contacts (eligibility filter is orchestrator concern)."""
        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(return_value={"conversations": []})

        contact = {"ghl_contact_id": "c-empty", "email": "empty@test.com"}
        result = await scan_contact(mock_ghl, contact, scan_days=30)

        assert result is not None
        assert result.total_messages == 0
        assert result.threads == []

    @pytest.mark.asyncio
    async def test_no_email_contact_is_still_scanned(self):
        """Scanner does not filter by email — orchestrator handles that eligibility check."""
        ts = datetime.now(timezone.utc).isoformat()
        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(return_value={
            "conversations": [{"id": "conv-1"}],
        })
        mock_ghl.get_messages = AsyncMock(return_value={
            "messages": [{"id": "m1", "dateAdded": ts, "direction": "inbound", "body": "Hi"}],
        })

        contact = {"ghl_contact_id": "c-noemail", "email": ""}
        result = await scan_contact(mock_ghl, contact, scan_days=30)

        assert result is not None
        assert result.email == ""
        assert result.total_messages == 1

    @pytest.mark.asyncio
    async def test_threads_sorted_newest_first(self):
        """Messages within each thread are sorted newest first for primary-thread selection downstream."""
        now = datetime.now(timezone.utc)
        older_ts = (now - timedelta(hours=2)).isoformat()
        newer_ts = now.isoformat()

        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(return_value={
            "conversations": [{"id": "conv-1"}],
        })
        mock_ghl.get_messages = AsyncMock(return_value={
            "messages": [
                {"id": "m-old", "dateAdded": older_ts, "direction": "outbound", "body": "older"},
                {"id": "m-new", "dateAdded": newer_ts, "direction": "inbound", "body": "newer"},
            ],
        })

        contact = {"ghl_contact_id": "c-sort", "email": "sort@test.com"}
        result = await scan_contact(mock_ghl, contact, scan_days=30)

        assert result is not None
        thread = result.threads[0]
        assert thread.messages[0].message_id == "m-new"
        assert thread.messages[1].message_id == "m-old"
        assert thread.last_message_date == newer_ts


class TestWarmEligibilityHelpers:
    def test_has_valid_email(self):
        assert has_valid_email("valid@test.com") is True
        assert has_valid_email("invalid-email") is False

    @pytest.mark.asyncio
    async def test_select_primary_thread_uses_latest_thread_activity(self):
        now = datetime.now(timezone.utc)
        older_ts = (now - timedelta(days=2)).isoformat()
        newer_ts = now.isoformat()

        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(return_value={
            "conversations": [{"id": "conv-old"}, {"id": "conv-new"}],
        })
        mock_ghl.get_messages = AsyncMock(side_effect=[
            {"messages": [{"id": "m-old", "dateAdded": older_ts, "direction": "outbound", "body": "older"}]},
            {"messages": [{"id": "m-new", "dateAdded": newer_ts, "direction": "inbound", "body": "newer"}]},
        ])

        summary = await scan_contact(mock_ghl, {"ghl_contact_id": "c-1", "email": "a@test.com"}, scan_days=30)
        assert summary is not None

        primary = select_primary_thread(summary)
        assert primary is not None
        assert primary.conversation_id == "conv-new"

    def test_compact_thread_messages_orders_chronologically_and_trims(self):
        now = datetime.now(timezone.utc)
        raw_messages = []
        for i in range(10):
            raw_messages.append({
                "id": f"m-{i}",
                "dateAdded": (now - timedelta(minutes=i)).isoformat(),
                "direction": "inbound" if i % 2 else "outbound",
                "body": f"{'x' * 600}-{i}",
            })

        messages = _parse_messages(raw_messages, "conv-1", now - timedelta(days=1))
        messages.sort(key=lambda m: m.timestamp, reverse=True)
        thread = MagicMock()
        thread.messages = messages

        compacted = compact_thread_messages(thread, max_messages=8, max_body_chars=120)

        assert len(compacted) == 8
        assert compacted[0].timestamp < compacted[-1].timestamp
        assert all(len(message.body) <= 120 for message in compacted)

    @pytest.mark.asyncio
    async def test_filter_eligible_summaries_tracks_skip_reasons(self):
        ts = datetime.now(timezone.utc).isoformat()
        mock_ghl = MagicMock()
        mock_ghl.search_conversations = AsyncMock(side_effect=[
            {"conversations": []},
            {"conversations": [{"id": "conv-2"}]},
            {"conversations": [{"id": "conv-3"}]},
        ])
        mock_ghl.get_messages = AsyncMock(side_effect=[
            {"messages": [{"id": "m-2", "dateAdded": ts, "direction": "inbound", "body": "Hi"}]},
            {"messages": [{"id": "m-3", "dateAdded": ts, "direction": "outbound", "body": "Hello"}]},
        ])

        no_conversation = await scan_contact(mock_ghl, {"ghl_contact_id": "c-1", "email": "a@test.com"}, scan_days=30)
        no_email = await scan_contact(mock_ghl, {"ghl_contact_id": "c-2", "email": ""}, scan_days=30)
        eligible = await scan_contact(mock_ghl, {"ghl_contact_id": "c-3", "email": "ok@test.com"}, scan_days=30)

        filtered, skipped_no_conversation, skipped_no_email = filter_eligible_summaries(
            [no_conversation, no_email, eligible]  # type: ignore[list-item]
        )

        assert len(filtered) == 1
        assert filtered[0].contact_id == "c-3"
        assert skipped_no_conversation == 1
        assert skipped_no_email == 1
