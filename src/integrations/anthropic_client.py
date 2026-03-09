"""Shared Anthropic API client for conversation analyst and follow-up draft agents.

Provides:
- Async completion with retry on server/overload errors (up to MAX_RETRIES)
- JSON extraction with one repair attempt on parse failure (strip code fences, fix trailing commas)
- Per-call timeout enforced at the SDK level
- Hard exception propagation — callers own failure isolation; no silent swallowing here

Model constants:
  HAIKU_MODEL  — cost-efficient batch analysis (claude-haiku-4-5-20251001)
  SONNET_MODEL — higher-quality drafting (claude-sonnet-4-6)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 2

# HTTP status codes that warrant a retry
_RETRYABLE_STATUS = {429, 500, 502, 503, 529}


class MissingAnthropicApiKeyError(ValueError):
    """Raised when the Anthropic client is initialized without an API key."""


def _repair_json(raw: str) -> str:
    """Best-effort JSON repair for common LLM output issues."""
    # Strip markdown code fences
    stripped = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped)

    # Remove trailing commas before closing braces/brackets
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)

    return stripped.strip()


class AnthropicClient:
    """Thin async wrapper around the Anthropic SDK with retry and JSON repair."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = (api_key or os.environ.get("ANTHROPIC_API_KEY", "")).strip()
        if not resolved_key:
            raise MissingAnthropicApiKeyError(
                "ANTHROPIC_API_KEY is required for AnthropicClient"
            )
        self._api_key = resolved_key
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                timeout=DEFAULT_TIMEOUT,
                max_retries=0,  # We handle retries ourselves for observability
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    async def complete(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        trace_context: dict[str, Any] | None = None,
    ) -> str:
        """Send a chat completion request and return the response text.

        Retries up to MAX_RETRIES times on retryable API errors.
        Raises anthropic.APIError (or subclass) on terminal failure.
        """
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(
                    "anthropic.complete attempt=%d model=%s max_tokens=%d temperature=%.2f system_chars=%d user_chars=%d trace=%s",
                    attempt + 1,
                    model,
                    max_tokens,
                    temperature,
                    len(system_prompt),
                    len(user_prompt),
                    trace_context or {},
                )
                response = await self._get_client().messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                logger.info(
                    "anthropic.complete success model=%s chars=%d trace=%s",
                    model,
                    len(response.content[0].text),
                    trace_context or {},
                )
                return response.content[0].text

            except anthropic.RateLimitError as e:
                logger.warning("Anthropic rate limit (attempt %d/%d): %s", attempt + 1, MAX_RETRIES + 1, e)
                last_exc = e
                if attempt < MAX_RETRIES:
                    import asyncio
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                raise

            except anthropic.APIStatusError as e:
                if e.status_code in _RETRYABLE_STATUS and attempt < MAX_RETRIES:
                    logger.warning(
                        "Anthropic API error %d (attempt %d/%d): %s",
                        e.status_code, attempt + 1, MAX_RETRIES + 1, e,
                    )
                    last_exc = e
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

            except anthropic.APIConnectionError as e:
                if attempt < MAX_RETRIES:
                    logger.warning("Anthropic connection error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES + 1, e)
                    last_exc = e
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        # Should be unreachable — retries raise on final attempt
        raise RuntimeError("complete() exhausted retries without raising") from last_exc

    async def complete_json(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        trace_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a completion request and parse the response as JSON.

        Attempts one JSON repair pass on parse failure.
        Raises ValueError if both the raw parse and the repaired parse fail.
        """
        raw = await self.complete(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            trace_context=trace_context,
        )

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # One repair attempt
        repaired = _repair_json(raw)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            logger.error(
                "JSON parse failed after repair attempt. model=%s raw_len=%d raw_preview=%.200s trace=%s",
                model,
                len(raw),
                raw,
                trace_context or {},
            )
            raise ValueError(
                f"Could not parse LLM response as JSON (model={model}): {e}"
            ) from e
