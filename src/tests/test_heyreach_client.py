"""Tests for HeyReach client — auth, add lead, campaign status."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from integrations.heyreach_client import HeyReachClient


class TestHeyReachClient:
    def test_init_defaults(self, monkeypatch):
        monkeypatch.setenv("HEYREACH_API_KEY", "test-key")
        client = HeyReachClient()
        assert client.api_key == "test-key"
        assert "heyreach.io" in client.base_url

    def test_init_explicit_key(self):
        client = HeyReachClient(api_key="explicit-key")
        assert client.api_key == "explicit-key"

    @pytest.mark.asyncio
    async def test_add_lead_calls_api(self):
        client = HeyReachClient(api_key="test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"status": "added"}'
        mock_resp.json.return_value = {"status": "added"}

        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_resp)
        mock_http.is_closed = False
        client._client = mock_http

        result = await client.add_lead_to_campaign(
            campaign_id="camp-1",
            linkedin_url="https://linkedin.com/in/jane",
            first_name="Jane",
            last_name="Doe",
            company="Acme",
        )
        assert result["status"] == "added"
        mock_http.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self):
        client = HeyReachClient(api_key="test")
        mock_http = AsyncMock()
        mock_http.is_closed = False
        client._client = mock_http
        await client.close()
        mock_http.aclose.assert_called_once()
