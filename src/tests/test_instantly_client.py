"""Tests for Instantly V2 client — auth, send email, analytics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.instantly_client import InstantlyClient


class TestInstantlyClient:
    def test_init_defaults(self, monkeypatch):
        monkeypatch.setenv("INSTANTLY_API_KEY", "test-key")
        client = InstantlyClient()
        assert client.api_key == "test-key"
        assert "instantly.ai" in client.base_url

    def test_init_explicit_key(self):
        client = InstantlyClient(api_key="explicit-key")
        assert client.api_key == "explicit-key"

    @pytest.mark.asyncio
    async def test_send_email_calls_api(self):
        client = InstantlyClient(api_key="test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "msg-1"}'
        mock_resp.json.return_value = {"id": "msg-1"}

        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_resp)
        mock_http.is_closed = False
        client._client = mock_http

        result = await client.send_email(
            from_email="chris@caio.com",
            to_email="jane@acme.com",
            subject="AI Strategy",
            body="Hello Jane",
        )
        assert result["id"] == "msg-1"
        mock_http.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self):
        client = InstantlyClient(api_key="test")
        mock_http = AsyncMock()
        mock_http.is_closed = False
        client._client = mock_http
        await client.close()
        mock_http.aclose.assert_called_once()
