"""Apollo.io API client for lead discovery and enrichment.

Two use cases:
1. search_people() — POST /mixed_people/api_search (Recon: discover leads with ICP filters)
2. get_person_detail() — POST /people/match (Enrichment: fill gaps on known contacts)

Auth: X-Api-Key header. Rate limit: 200 req/hr. Timeout: 30s. Retry: 2x on 5xx, backoff on 429.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import httpx

APOLLO_BASE_URL = "https://api.apollo.io/api/v1"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 2


class ApolloClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("APOLLO_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=APOLLO_BASE_URL,
                timeout=DEFAULT_TIMEOUT,
                headers={
                    "Content-Type": "application/json",
                    "X-Api-Key": self.api_key,
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
        json_data.pop("api_key", None)  # Key sent via X-Api-Key header

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

    async def search_people(
        self,
        person_titles: Optional[list[str]] = None,
        person_seniorities: Optional[list[str]] = None,
        organization_num_employees_ranges: Optional[list[str]] = None,
        organization_industry_tag_ids: Optional[list[str]] = None,
        q_organization_keyword_tags: Optional[list[str]] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        """Search for people matching ICP filters. Used by Recon agent."""
        payload: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
        }
        if person_titles:
            payload["person_titles"] = person_titles
        if person_seniorities:
            payload["person_seniorities"] = person_seniorities
        if organization_num_employees_ranges:
            payload["organization_num_employees_ranges"] = organization_num_employees_ranges
        if organization_industry_tag_ids:
            payload["organization_industry_tag_ids"] = organization_industry_tag_ids
        if q_organization_keyword_tags:
            payload["q_organization_keyword_tags"] = q_organization_keyword_tags

        return await self._request("POST", "/mixed_people/api_search", payload)

    async def get_person_detail(
        self,
        apollo_id: Optional[str] = None,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """Match and enrich a specific person. Used by Enrichment agent.

        Best results when apollo_id or email is provided. Falls back to
        name + organization matching which may return partial data.
        """
        payload: dict[str, Any] = {}
        if apollo_id:
            payload["id"] = apollo_id
            payload["reveal_personal_emails"] = True
        if email:
            payload["email"] = email
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if organization_name:
            payload["organization_name"] = organization_name
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url

        return await self._request("POST", "/people/match", payload)
