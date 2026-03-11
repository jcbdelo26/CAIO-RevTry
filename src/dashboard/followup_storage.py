"""Persistence-backed warm follow-up storage for the follow-up dashboard."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from models.schemas import DraftApprovalStatus, FollowUpDraft
from persistence.factory import get_storage_backend


def save_followup_draft(draft: FollowUpDraft) -> FollowUpDraft:
    """Persist a warm follow-up draft."""
    get_storage_backend().save_followup_draft(draft)
    return draft


def get_followup_draft(draft_id: str) -> Optional[FollowUpDraft]:
    return get_storage_backend().get_followup_draft(draft_id)


def list_followup_drafts(
    *,
    business_date: str | None = None,
    latest_only: bool = False,
) -> list[FollowUpDraft]:
    """List warm follow-up drafts with pending work first."""
    drafts = get_storage_backend().list_followup_drafts(
        business_date=business_date,
        latest_only=latest_only,
    )

    status_order = {
        DraftApprovalStatus.PENDING: 0,
        DraftApprovalStatus.APPROVED: 1,
        DraftApprovalStatus.SEND_FAILED: 2,
        DraftApprovalStatus.DISPATCHED: 3,
        DraftApprovalStatus.REJECTED: 4,
    }
    drafts.sort(key=lambda draft: (draft.business_date, draft.created_at), reverse=True)
    drafts.sort(key=lambda draft: status_order.get(draft.status, 9))
    return drafts


def approve_followup_draft(draft_id: str) -> Optional[FollowUpDraft]:
    """Mark a warm follow-up draft as APPROVED."""
    draft = get_followup_draft(draft_id)
    if not draft:
        return None

    draft.status = DraftApprovalStatus.APPROVED
    draft.approved_at = datetime.now(timezone.utc).isoformat()
    save_followup_draft(draft)
    return draft


def reject_followup_draft(
    draft_id: str,
    reason: str = "",
    feedback_dir: Optional[str] = None,
) -> Optional[FollowUpDraft]:
    """Mark a warm follow-up draft as REJECTED and record rejection feedback."""
    draft = get_followup_draft(draft_id)
    if not draft:
        return None

    draft.status = DraftApprovalStatus.REJECTED
    draft.rejected_at = datetime.now(timezone.utc).isoformat()
    draft.rejection_reason = reason
    save_followup_draft(draft)

    get_storage_backend().record_feedback_event(
        draft_id=draft_id,
        channel="warm_followup",
        reason=reason,
        payload={
            "contactId": draft.contact_id,
            "status": draft.status.value,
            "rejectedAt": draft.rejected_at,
            "trigger": draft.trigger.value,
            "stage": draft.stage.value,
            "subject": draft.subject,
        },
    )

    return draft


def mark_followup_dispatched(
    draft_id: str,
    channel: str,
    ghl_message_id: Optional[str] = None,
) -> Optional[FollowUpDraft]:
    """Mark a warm follow-up draft as DISPATCHED after confirmed send success."""
    draft = get_followup_draft(draft_id)
    if not draft:
        return None

    draft.status = DraftApprovalStatus.DISPATCHED
    draft.dispatched_at = datetime.now(timezone.utc).isoformat()
    draft.dispatch_error = None
    if ghl_message_id:
        draft.ghl_message_id = ghl_message_id
    save_followup_draft(draft)
    return draft


def mark_followup_send_failed(
    draft_id: str,
    channel: str,
    error: str,
) -> Optional[FollowUpDraft]:
    """Mark a warm follow-up draft as SEND_FAILED after a confirmed send failure."""
    draft = get_followup_draft(draft_id)
    if not draft:
        return None

    draft.status = DraftApprovalStatus.SEND_FAILED
    draft.send_failed_at = datetime.now(timezone.utc).isoformat()
    draft.dispatch_error = error
    save_followup_draft(draft)
    return draft
