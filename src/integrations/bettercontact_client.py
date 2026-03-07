"""BetterContact API client for contact enrichment.

Timeout: 45s per request. Batch timeout: 10 min.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import httpx

BETTERCONTACT_BASE_URL = "https://app.bettercontact.rocks/api/v2"
DEFAULT_TIMEOUT = 45.0
MAX_RETRIES = 2


class BetterContactClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("BETTERCONTACT_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BETTERCONTACT_BASE_URL,
                timeout=DEFAULT_TIMEOUT,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def enrich_contact(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_name: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        email: Optional[str] = None,
    ) -> dict[str, Any]:
        """Enrich a single contact with BetterContact data."""
        client = await self._get_client()

        payload: dict[str, Any] = {}
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if company_name:
            payload["company_name"] = company_name
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
        if email:
            payload["email"] = email

        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.post("/enrich", json=payload)

                if resp.status_code == 429:
                    await asyncio.sleep(min(5 * (attempt + 1), 60))
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)
                    last_exc = e
                    continue
                raise
            except httpx.TimeoutException as e:
                if attempt < MAX_RETRIES:
                    last_exc = e
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        raise last_exc or RuntimeError("BetterContact request failed after retries")
