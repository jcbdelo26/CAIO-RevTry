"""Tests for the shared Anthropic client wrapper."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import anthropic as anthropic_sdk
from integrations.anthropic_client import (
    HAIKU_MODEL,
    SONNET_MODEL,
    AnthropicClient,
    MissingAnthropicApiKeyError,
    _repair_json,
)


# ── JSON repair helper ───────────────────────────────────────────────────────


class TestRepairJson:
    def test_strips_markdown_code_fence(self):
        raw = "```json\n{\"key\": \"value\"}\n```"
        assert json.loads(_repair_json(raw)) == {"key": "value"}

    def test_strips_plain_code_fence(self):
        raw = "```\n{\"a\": 1}\n```"
        assert json.loads(_repair_json(raw)) == {"a": 1}

    def test_removes_trailing_commas(self):
        raw = '{"a": 1, "b": 2,}'
        assert json.loads(_repair_json(raw)) == {"a": 1, "b": 2}

    def test_removes_trailing_comma_in_array(self):
        raw = '[1, 2, 3,]'
        assert json.loads(_repair_json(raw)) == [1, 2, 3]

    def test_passes_through_valid_json(self):
        raw = '{"ok": true}'
        assert _repair_json(raw) == '{"ok": true}'

    def test_strips_whitespace(self):
        raw = "   {\"x\": 1}   "
        assert json.loads(_repair_json(raw)) == {"x": 1}


# ── Model constants ──────────────────────────────────────────────────────────


class TestModelConstants:
    def test_haiku_model_defined(self):
        assert HAIKU_MODEL == "claude-haiku-4-5-20251001"

    def test_sonnet_model_defined(self):
        assert SONNET_MODEL == "claude-sonnet-4-6"


class TestClientInit:
    def test_requires_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(MissingAnthropicApiKeyError):
            AnthropicClient()


# ── AnthropicClient.complete ─────────────────────────────────────────────────


class TestComplete:
    def _make_client_with_mock(self, return_text: str = "hello") -> tuple[AnthropicClient, MagicMock]:
        client = AnthropicClient(api_key="test-key")
        mock_messages = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=return_text)]
        mock_messages.create = AsyncMock(return_value=mock_response)
        client._client = MagicMock(messages=mock_messages, close=AsyncMock())
        return client, mock_messages

    @pytest.mark.asyncio
    async def test_returns_response_text(self):
        client, mock_messages = self._make_client_with_mock("response text")
        result = await client.complete(HAIKU_MODEL, "sys", "user")
        assert result == "response text"

    @pytest.mark.asyncio
    async def test_passes_correct_params(self):
        client, mock_messages = self._make_client_with_mock()
        await client.complete(
            model=SONNET_MODEL,
            system_prompt="Be helpful",
            user_prompt="Say hi",
            max_tokens=512,
            temperature=0.5,
        )
        call_kwargs = mock_messages.create.call_args[1]
        assert call_kwargs["model"] == SONNET_MODEL
        assert call_kwargs["system"] == "Be helpful"
        assert call_kwargs["max_tokens"] == 512
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["messages"][0]["content"] == "Say hi"

    @pytest.mark.asyncio
    async def test_retries_on_500_error(self):
        client = AnthropicClient(api_key="test-key")
        success_response = MagicMock()
        success_response.content = [MagicMock(text="ok")]

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                err = anthropic_sdk.APIStatusError(
                    "server error",
                    response=MagicMock(status_code=500),
                    body=None,
                )
                err.status_code = 500
                raise err
            return success_response

        client._client = MagicMock(messages=MagicMock(create=side_effect), close=AsyncMock())

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete(HAIKU_MODEL, "sys", "user")

        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_on_non_retryable_error(self):
        client = AnthropicClient(api_key="test-key")

        err = anthropic_sdk.APIStatusError(
            "not found",
            response=MagicMock(status_code=404),
            body=None,
        )
        err.status_code = 404
        client._client = MagicMock(messages=MagicMock(create=AsyncMock(side_effect=err)), close=AsyncMock())

        with pytest.raises(anthropic_sdk.APIStatusError):
            await client.complete(HAIKU_MODEL, "sys", "user")

    @pytest.mark.asyncio
    async def test_raises_after_exhausting_retries(self):
        client = AnthropicClient(api_key="test-key")

        err = anthropic_sdk.APIStatusError(
            "server error",
            response=MagicMock(status_code=500),
            body=None,
        )
        err.status_code = 500
        client._client = MagicMock(messages=MagicMock(create=AsyncMock(side_effect=err)), close=AsyncMock())

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(anthropic_sdk.APIStatusError):
                await client.complete(HAIKU_MODEL, "sys", "user")

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(self):
        client = AnthropicClient(api_key="test-key")
        success_response = MagicMock()
        success_response.content = [MagicMock(text="done")]

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise anthropic_sdk.RateLimitError(
                    "rate limit",
                    response=MagicMock(status_code=429),
                    body=None,
                )
            return success_response

        client._client = MagicMock(messages=MagicMock(create=side_effect), close=AsyncMock())

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete(HAIKU_MODEL, "sys", "user")

        assert result == "done"


# ── AnthropicClient.complete_json ────────────────────────────────────────────


class TestCompleteJson:
    def _make_client_returning(self, text: str) -> AnthropicClient:
        client = AnthropicClient(api_key="test-key")
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=text)]
        client._client = MagicMock(
            messages=MagicMock(create=AsyncMock(return_value=mock_response)),
            close=AsyncMock(),
        )
        return client

    @pytest.mark.asyncio
    async def test_parses_valid_json(self):
        client = self._make_client_returning('{"sentiment": "positive"}')
        result = await client.complete_json(HAIKU_MODEL, "sys", "user")
        assert result == {"sentiment": "positive"}

    @pytest.mark.asyncio
    async def test_repairs_code_fenced_json(self):
        client = self._make_client_returning('```json\n{"stage": "engaged"}\n```')
        result = await client.complete_json(HAIKU_MODEL, "sys", "user")
        assert result == {"stage": "engaged"}

    @pytest.mark.asyncio
    async def test_raises_value_error_on_unparseable(self):
        client = self._make_client_returning("This is not JSON at all, just prose.")
        with pytest.raises(ValueError, match="Could not parse LLM response"):
            await client.complete_json(HAIKU_MODEL, "sys", "user")

    @pytest.mark.asyncio
    async def test_repairs_trailing_comma(self):
        client = self._make_client_returning('{"a": 1, "b": 2,}')
        result = await client.complete_json(HAIKU_MODEL, "sys", "user")
        assert result == {"a": 1, "b": 2}
