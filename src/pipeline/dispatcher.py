"""Dispatch Orchestrator — routes APPROVED drafts to outbound channels.

Reads APPROVED drafts from storage, applies safety checks (dedup, rate limit,
circuit breaker), dispatches to the correct channel, and marks drafts DISPATCHED.

RAMP restriction: Tier 1 only, ≤5/day per channel.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from dashboard.storage import get_draft, list_drafts, mark_dispatched
from integrations.ghl_client import GHLClient
from integrations.heyreach_client import HeyReachClient
from integrations.instantly_client import InstantlyClient
from models.schemas import DraftApprovalStatus
from pipeline.circuit_breaker import CircuitBreaker
from pipeline.dedup import check_dedup, compute_draft_hash, record_dispatch, record_hash
from pipeline.rate_limiter import DailyRateLimiter


@dataclass
class DispatchResult:
    dispatched: int = 0
    skipped_dedup: int = 0
    skipped_rate_limit: int = 0
    skipped_circuit_breaker: int = 0
    skipped_tier: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


async def dispatch_approved_drafts(
    tier_restriction: int | None = None,
    rate_limiter: DailyRateLimiter | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    instantly: InstantlyClient | None = None,
    ghl: GHLClient | None = None,
    heyreach: HeyReachClient | None = None,
    from_email: str | None = None,
    heyreach_campaign_id: str | None = None,
) -> DispatchResult:
    """Load APPROVED drafts, apply safety checks, dispatch to channels."""
    result = DispatchResult()

    tier_limit = tier_restriction or int(os.environ.get("DISPATCH_TIER_RESTRICTION", "1"))
    sender_email = from_email or os.environ.get("INSTANTLY_FROM_EMAIL", "")
    hr_campaign = heyreach_campaign_id or os.environ.get("HEYREACH_CAMPAIGN_ID", "")

    if rate_limiter is None:
        rate_limiter = DailyRateLimiter()
    if circuit_breaker is None:
        circuit_breaker = CircuitBreaker()

    own_instantly = instantly is None
    own_ghl = ghl is None
    own_heyreach = heyreach is None

    # Load APPROVED drafts
    all_drafts = list_drafts()
    approved = [d for d in all_drafts if d.status == DraftApprovalStatus.APPROVED]

    if not approved:
        return result

    for draft in approved:
        channel = draft.channel.value if hasattr(draft.channel, "value") else draft.channel

        # RAMP: Tier restriction
        try:
            tier_num = int(draft.icp_tier)
        except (ValueError, TypeError):
            tier_num = 99
        if tier_num > tier_limit:
            result.skipped_tier += 1
            continue

        # Rate limit check
        if not rate_limiter.can_send(channel):
            result.skipped_rate_limit += 1
            continue

        # Circuit breaker check
        if circuit_breaker.is_open(channel):
            result.skipped_circuit_breaker += 1
            continue

        # Dedup check
        is_dup, reason = await check_dedup(
            contact_id=draft.contact_id,
            channel=channel,
            subject=draft.subject,
            body=draft.body,
            draft_id=draft.draft_id,
        )
        if is_dup:
            result.skipped_dedup += 1
            continue

        # Dispatch to channel
        try:
            if channel == "instantly":
                if own_instantly and instantly is None:
                    instantly = InstantlyClient()
                await circuit_breaker.call(
                    "instantly",
                    instantly.send_email,
                    from_email=sender_email,
                    to_email=draft.contact_id,  # TODO: resolve contact email
                    subject=draft.subject,
                    body=draft.body,
                )
            elif channel == "ghl":
                if own_ghl and ghl is None:
                    ghl = GHLClient()
                await circuit_breaker.call(
                    "ghl",
                    ghl.upsert_contact,
                    email=draft.contact_id,
                    first_name="",
                    last_name="",
                    company_name="",
                    tags=[f"revtry-sent-ghl"],
                )
            elif channel == "heyreach":
                if own_heyreach and heyreach is None:
                    heyreach = HeyReachClient()
                await circuit_breaker.call(
                    "heyreach",
                    heyreach.add_lead_to_campaign,
                    campaign_id=hr_campaign,
                    linkedin_url="",  # TODO: resolve from enrichment data
                    first_name="",
                    last_name="",
                    company="",
                )

            # Success — mark dispatched and record
            mark_dispatched(draft.draft_id, channel)
            rate_limiter.record_send(channel)
            draft_hash = compute_draft_hash(draft.contact_id, draft.subject, draft.body, channel)
            record_hash(draft_hash)
            record_dispatch(draft.contact_id, channel, draft.draft_id)
            result.dispatched += 1

        except Exception as e:
            result.failed += 1
            result.errors.append(f"{draft.draft_id}: {e}")
            mark_dispatched(draft.draft_id, channel, error=str(e))

    # Cleanup
    if own_instantly and instantly:
        await instantly.close()
    if own_ghl and ghl:
        await ghl.close()
    if own_heyreach and heyreach:
        await heyreach.close()

    return result
