"""Instantly V2 API client for cold email dispatch.

Auth: Authorization Bearer header.
Base URL: https://api.instantly.ai/api/v2
Rate limit: respect Instantly's domain limits.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

DEFAULT_BASE_URL = "https://api.instantly.ai/api/v2"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 2


class InstantlyClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("INSTANTLY_API_KEY", "")
        self.base_url = base_url or DEFAULT_BASE_URL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=DEFAULT_TIMEOUT,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        client = await self._get_client()
        for attempt in range(MAX_RETRIES + 1):
            resp = await client.request(method, path, **kwargs)
            if resp.status_code == 429 and attempt < MAX_RETRIES:
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        return {}

    async def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send a single cold email via Instantly."""
        payload: dict[str, Any] = {
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "body": body,
        }
        if campaign_id:
            payload["campaign_id"] = campaign_id
        return await self._request("POST", "/emails/send", json=payload)

    async def get_campaign_analytics(self, campaign_id: str) -> dict[str, Any]:
        """Get analytics for a specific campaign."""
        return await self._request("GET", f"/campaigns/{campaign_id}/analytics")

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
