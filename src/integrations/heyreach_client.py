"""HeyReach API client for LinkedIn sequence dispatch.

Auth: X-API-KEY header.
Base URL: https://api.heyreach.io/api/v1
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

DEFAULT_BASE_URL = "https://api.heyreach.io/api/v1"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 2


class HeyReachClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("HEYREACH_API_KEY", "")
        self.base_url = base_url or DEFAULT_BASE_URL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=DEFAULT_TIMEOUT,
                headers={
                    "Content-Type": "application/json",
                    "X-API-KEY": self.api_key,
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

    async def add_lead_to_campaign(
        self,
        campaign_id: str,
        linkedin_url: str,
        first_name: str = "",
        last_name: str = "",
        company: str = "",
    ) -> dict[str, Any]:
        """Add a lead to a LinkedIn outreach campaign."""
        payload = {
            "linkedin_url": linkedin_url,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
        }
        return await self._request("POST", f"/campaigns/{campaign_id}/leads", json=payload)

    async def get_campaign_status(self, campaign_id: str) -> dict[str, Any]:
        """Get status of a LinkedIn campaign."""
        return await self._request("GET", f"/campaigns/{campaign_id}")

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
