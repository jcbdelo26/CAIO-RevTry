"""Dispatch Orchestrator — routes APPROVED drafts to GHL warm email.

Reads APPROVED drafts from storage, applies safety checks (dedup, rate limit,
circuit breaker), dispatches via GHL Conversations API, marks drafts DISPATCHED.

RAMP restriction: Tier 1 only, ≤5/day per channel.

DEFERRED: Instantly (cold email) and HeyReach (LinkedIn) — will be enabled
after GHL dispatch is verified in production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dashboard.storage import get_draft, list_drafts, mark_dispatched
from integrations.ghl_client import GHLClient
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
    skipped_deferred_channel: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


async def dispatch_approved_drafts(
    tier_restriction: int | None = None,
    rate_limiter: DailyRateLimiter | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    ghl: GHLClient | None = None,
) -> DispatchResult:
    """Load APPROVED drafts, apply safety checks, dispatch via GHL."""
    result = DispatchResult()

    tier_limit = tier_restriction or int(os.environ.get("DISPATCH_TIER_RESTRICTION", "1"))

    if rate_limiter is None:
        rate_limiter = DailyRateLimiter()
    if circuit_breaker is None:
        circuit_breaker = CircuitBreaker()

    own_ghl = ghl is None

    # Load APPROVED drafts
    all_drafts = list_drafts()
    approved = [d for d in all_drafts if d.status == DraftApprovalStatus.APPROVED]

    if not approved:
        return result

    for draft in approved:
        channel = draft.channel.value if hasattr(draft.channel, "value") else draft.channel

        # DEFERRED: Skip Instantly and HeyReach channels
        if channel in ("instantly", "heyreach"):
            result.skipped_deferred_channel += 1
            continue

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

        # Dispatch via GHL
        try:
            if own_ghl and ghl is None:
                ghl = GHLClient()

            # Resolve GHL contact ID from approval-time push result
            stored = get_draft(draft.draft_id)
            ghl_contact_id = ""
            if stored and stored.ghl_push_result:
                ghl_contact_id = stored.ghl_push_result.get("ghl_contact_id", "")

            if not ghl_contact_id:
                result.failed += 1
                result.errors.append(
                    f"{draft.draft_id}: No GHL contact ID — was draft approved via dashboard?"
                )
                continue

            # Resolve email: prefer contact_email, fall back to contact_id if it's an email
            to_email = draft.contact_email or (draft.contact_id if "@" in draft.contact_id else "")
            if not to_email:
                result.failed += 1
                result.errors.append(
                    f"{draft.draft_id}: No email address for dispatch"
                )
                continue

            await circuit_breaker.call(
                "ghl",
                ghl.send_email,
                contact_id=ghl_contact_id,
                to_email=to_email,
                subject=draft.subject,
                body=draft.body,
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
    if own_ghl and ghl:
        await ghl.close()

    return result
