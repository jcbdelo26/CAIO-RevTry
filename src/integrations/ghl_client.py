"""GoHighLevel API client for contact upsert, task creation, and email dispatch.

Auth: Authorization Bearer header. Version: 2021-07-28.
Rate limit: 100 req/min. Timeout: 30s. Retry: 2x on 5xx, backoff on 429.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import httpx

DEFAULT_GHL_BASE_URL = "https://services.leadconnectorhq.com"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 2


class GHLClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        location_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("GHL_API_KEY", "")
        self.location_id = location_id or os.environ.get("GHL_LOCATION_ID", "")
        self.base_url = base_url or os.environ.get("GHL_BASE_URL", DEFAULT_GHL_BASE_URL)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=DEFAULT_TIMEOUT,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "Version": "2021-07-28",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self, method: str, path: str, json_data: dict[str, Any]
    ) -> dict[str, Any]:
        client = await self._get_client()

        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.request(method, path, json=json_data)

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "5"))
                    await asyncio.sleep(min(retry_after, 60))
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

        raise last_exc or RuntimeError("Request failed after retries")

    async def upsert_contact(
        self,
        email: str,
        first_name: str = "",
        last_name: str = "",
        company_name: str = "",
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Create or update a contact by email match.

        Returns the GHL contact object with id.
        """
        payload: dict[str, Any] = {
            "locationId": self.location_id,
            "email": email,
        }
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name
        if company_name:
            payload["companyName"] = company_name
        if tags:
            payload["tags"] = tags

        return await self._request("POST", "/contacts/upsert", payload)

    async def create_task(
        self,
        contact_id: str,
        title: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a follow-up task on a contact."""
        payload: dict[str, Any] = {
            "title": title,
            "completed": False,
        }
        if description:
            payload["description"] = description

        return await self._request(
            "POST", f"/contacts/{contact_id}/tasks", payload
        )

    async def send_email(
        self,
        contact_id: str,
        to_email: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """Send warm email via GHL Conversations API.

        Uses POST /conversations/messages with type=Email.
        Requires the GHL contact ID (not the email address).
        """
        payload: dict[str, Any] = {
            "type": "Email",
            "contactId": contact_id,
            "subject": subject,
            "body": body,
        }
        return await self._request("POST", "/conversations/messages", payload)
