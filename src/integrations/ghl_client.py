"""GoHighLevel API client for contact upsert, task creation, email dispatch,
and conversation history retrieval.

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


class MissingGhlCredentialsError(ValueError):
    """Raised when GHL client credentials are missing."""


class UnsafeContactMutationError(ValueError):
    """Raised when a contact write attempts an unsafe mutation."""


class GHLClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        location_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = (api_key or os.environ.get("GHL_API_KEY", "")).strip()
        self.location_id = (location_id or os.environ.get("GHL_LOCATION_ID", "")).strip()
        self.base_url = base_url or os.environ.get("GHL_BASE_URL", DEFAULT_GHL_BASE_URL)
        if not self.api_key:
            raise MissingGhlCredentialsError("GHL_API_KEY is required for GHLClient")
        if not self.location_id:
            raise MissingGhlCredentialsError("GHL_LOCATION_ID is required for GHLClient")
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
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()

        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.request(method, path, json=json_data, params=params)

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
        if tags is not None:
            raise UnsafeContactMutationError(
                "Contact upsert may not mutate tags. Use add_contact_tag() for additive tag writes only."
            )

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

        return await self._request("POST", "/contacts/upsert", payload)

    async def add_contact_tag(self, contact_id: str, tag: str) -> dict[str, Any]:
        """Append a single tag to an existing contact without replacing prior tags."""
        return await self.add_contact_tags(contact_id, [tag])

    async def add_contact_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]:
        """Append one or more tags to an existing contact without replacing prior tags."""
        safe_tags = [tag for tag in tags if tag]
        if not safe_tags:
            raise UnsafeContactMutationError("At least one non-empty tag is required.")
        return await self._request("POST", f"/contacts/{contact_id}/tags", {"tags": safe_tags})

    async def create_task(
        self,
        contact_id: str,
        title: str,
        description: str = "",
        due_days: int = 3,
    ) -> dict[str, Any]:
        """Create a follow-up task on a contact.

        GHL API requires 'dueDate' and uses 'body' (not 'description').
        """
        from datetime import datetime, timezone, timedelta

        due = (datetime.now(timezone.utc) + timedelta(days=due_days)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
        payload: dict[str, Any] = {
            "title": title,
            "dueDate": due,
            "completed": False,
        }
        if description:
            payload["body"] = description

        return await self._request(
            "POST", f"/contacts/{contact_id}/tasks", payload
        )

    async def send_email(
        self,
        contact_id: str,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send warm email via GHL Conversations API.

        Uses POST /conversations/messages with type=Email.
        Requires the GHL contact ID (not the email address).
        GHL API expects 'html' for email body and 'emailFrom' for sender.
        """
        sender = from_email or os.environ.get("GHL_FROM_EMAIL", "")

        # Convert plain text body to HTML (preserve line breaks)
        html_body = body.replace("\n", "<br>\n")

        payload: dict[str, Any] = {
            "type": "Email",
            "contactId": contact_id,
            "subject": subject,
            "html": html_body,
        }
        if sender:
            payload["emailFrom"] = sender

        return await self._request("POST", "/conversations/messages", payload)

    # ── Conversation Read Methods ─────────────────────────────────────────────

    async def search_conversations(self, contact_id: str) -> dict[str, Any]:
        """Search conversation threads for a contact.

        Uses GET /conversations/search with locationId and contactId.
        Returns conversation thread IDs and metadata.
        """
        return await self._request(
            "GET",
            "/conversations/search",
            params={"locationId": self.location_id, "contactId": contact_id},
        )

    async def get_messages(
        self, conversation_id: str, limit: int = 50
    ) -> dict[str, Any]:
        """Get messages for a conversation thread.

        Returns message history with subject, body, timestamps, direction.
        """
        return await self._request(
            "GET",
            f"/conversations/{conversation_id}/messages",
            params={"limit": limit},
        )

    async def get_contact(self, contact_id: str) -> dict[str, Any]:
        """Get a single contact by ID.

        Returns full contact record including name, email, company, tags.
        """
        return await self._request("GET", f"/contacts/{contact_id}")
