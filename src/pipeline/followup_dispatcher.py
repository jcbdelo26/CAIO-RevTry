"""Warm follow-up dispatcher.

Routes APPROVED warm follow-up drafts through the shared GHL safety chain:
rate limit, circuit breaker, dedup, and GHL send.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dashboard.followup_storage import (
    list_followup_drafts,
    mark_followup_dispatched,
    mark_followup_send_failed,
)
from integrations.ghl_client import GHLClient
from models.schemas import DraftApprovalStatus
from pipeline.circuit_breaker import CircuitBreaker
from pipeline.dedup import check_dedup, compute_draft_hash, record_dispatch, record_hash
from pipeline.rate_limiter import DailyRateLimiter


CHANNEL = "ghl"


@dataclass
class FollowupDispatchResult:
    dispatched: int = 0
    skipped_dedup: int = 0
    skipped_rate_limit: int = 0
    skipped_circuit_breaker: int = 0
    skipped_tier: int = 0
    skipped_deferred_channel: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


async def dispatch_approved_followups(
    *,
    rate_limiter: DailyRateLimiter | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    ghl: GHLClient | None = None,
) -> FollowupDispatchResult:
    """Dispatch APPROVED warm follow-up drafts through the shared GHL safety chain."""
    result = FollowupDispatchResult()
    rate_limiter = rate_limiter or DailyRateLimiter()
    circuit_breaker = circuit_breaker or CircuitBreaker()

    own_ghl = ghl is None
    drafts = [
        draft
        for draft in list_followup_drafts()
        if draft.status == DraftApprovalStatus.APPROVED
    ]
    if not drafts:
        return result

    for draft in drafts:
        if not rate_limiter.can_send(CHANNEL):
            result.skipped_rate_limit += 1
            continue

        if circuit_breaker.is_open(CHANNEL):
            result.skipped_circuit_breaker += 1
            continue

        dedup_id = draft.ghl_contact_id or draft.contact_id
        is_dup, reason = await check_dedup(
            contact_id=dedup_id,
            channel=CHANNEL,
            subject=draft.subject,
            body=draft.body,
            draft_id=draft.draft_id,
            ghl=ghl,
        )
        if is_dup:
            result.skipped_dedup += 1
            continue

        if not draft.ghl_contact_id:
            message = f"{draft.draft_id}: No GHL contact ID for warm dispatch"
            mark_followup_send_failed(draft.draft_id, CHANNEL, message)
            result.failed += 1
            result.errors.append(message)
            continue

        if not draft.contact_email:
            message = f"{draft.draft_id}: No email address for warm dispatch"
            mark_followup_send_failed(draft.draft_id, CHANNEL, message)
            result.failed += 1
            result.errors.append(message)
            continue

        try:
            if own_ghl and ghl is None:
                ghl = GHLClient()

            await circuit_breaker.call(
                CHANNEL,
                ghl.send_email,
                contact_id=draft.ghl_contact_id,
                to_email=draft.contact_email,
                subject=draft.subject,
                body=draft.body,
            )

            mark_followup_dispatched(draft.draft_id, CHANNEL)
            rate_limiter.record_send(CHANNEL)
            draft_hash = compute_draft_hash(dedup_id, draft.subject, draft.body, CHANNEL)
            record_hash(draft_hash)
            record_dispatch(dedup_id, CHANNEL, draft.draft_id)
            result.dispatched += 1
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"{draft.draft_id}: {exc}")
            mark_followup_send_failed(draft.draft_id, CHANNEL, str(exc))

    if own_ghl and ghl is not None:
        await ghl.close()

    return result
