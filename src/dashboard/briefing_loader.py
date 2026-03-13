"""Read-only loaders for the warm follow-up dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    DailyBriefing,
    DraftApprovalStatus,
    FollowUpDraft,
)
from persistence.factory import get_storage_backend
from scripts.ghl_conversation_scanner import (
    filter_eligible_summaries,
    has_recent_manual_outbound,
    is_dnd_or_unsubscribed,
    select_primary_thread,
    _load_sales_team_user_ids,
)
from utils.business_time import current_business_date


def _urgency_counts(analyses: list[ConversationAnalysis]) -> dict[str, int]:
    counts = {"hot": 0, "warm": 0, "cooling": 0}
    for analysis in analyses:
        counts[analysis.urgency.value] += 1
    return counts


def _trigger_counts(analyses: list[ConversationAnalysis]) -> dict[str, int]:
    counts = {"no_reply": 0, "awaiting_our_response": 0, "gone_cold": 0}
    for analysis in analyses:
        counts[analysis.trigger.value] += 1
    return counts


def _status_rank(status: DraftApprovalStatus | None) -> int:
    order = {
        DraftApprovalStatus.PENDING: 0,
        DraftApprovalStatus.APPROVED: 1,
        DraftApprovalStatus.SEND_FAILED: 2,
        DraftApprovalStatus.DISPATCHED: 3,
        DraftApprovalStatus.REJECTED: 4,
        None: 5,
    }
    return order.get(status, 9)


def _urgency_rank(urgency: str | None) -> int:
    order = {"hot": 0, "warm": 1, "cooling": 2, None: 3}
    return order.get(urgency, 9)


def load_contact_conversation(contact_id: str) -> Optional[ContactConversationSummary]:
    """Load the full stored conversation summary for one contact."""
    return get_storage_backend().get_conversation_summary(contact_id)


def load_daily_briefing(date: Optional[str] = None) -> DailyBriefing:
    """Load a persisted briefing or compute one from current warm outputs."""
    storage = get_storage_backend()
    briefing_date = date or current_business_date()
    persisted = storage.get_daily_briefing(briefing_date)
    if persisted:
        return persisted

    summaries = storage.list_conversation_summaries()
    analyses = storage.list_conversation_analyses()
    drafts = storage.list_followup_drafts(business_date=briefing_date, latest_only=not bool(date))

    filter_result = filter_eligible_summaries(summaries)
    urgency_counts = _urgency_counts(analyses)
    trigger_counts = _trigger_counts(analyses)

    sales_user_ids = _load_sales_team_user_ids()
    tagged_active_sales = sum(1 for s in summaries if has_recent_manual_outbound(s, sales_user_ids))

    return DailyBriefing(
        date=briefing_date,
        totalContactsScanned=len(summaries),
        contactsNeedingFollowup=len(analyses),
        contactsSkippedNoConversation=filter_result.skipped_no_conversation,
        contactsSkippedNoEmail=filter_result.skipped_no_email,
        contactsSkippedActiveSales=tagged_active_sales,
        hotCount=urgency_counts["hot"],
        warmCount=urgency_counts["warm"],
        coolingCount=urgency_counts["cooling"],
        noReplyCount=trigger_counts["no_reply"],
        awaitingResponseCount=trigger_counts["awaiting_our_response"],
        goneColdCount=trigger_counts["gone_cold"],
        draftsGenerated=len(drafts),
        analysisFailedCount=0,
        draftFailedCount=0,
        estimatedCostUsd=0.0,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )


def _resolve_queue_date(date: Optional[str], drafts: list[FollowUpDraft]) -> str:
    if date:
        return date
    if drafts:
        return max(draft.business_date for draft in drafts)
    return current_business_date()


def _draft_or_fallback(draft, fallback_source, draft_attr: str, fallback_attr: str, default=""):
    """Resolve a field from the draft first, then from a fallback source."""
    if draft:
        value = getattr(draft, draft_attr, None)
        if value is not None:
            return value
    if fallback_source:
        return getattr(fallback_source, fallback_attr, default)
    return default


def _build_queue_item(
    *,
    contact_id: str,
    draft,
    analysis,
    summary,
    primary_thread,
    contact_name: str,
    queue_date: str,
    is_active_sales: bool = False,
) -> dict[str, Any]:
    """Assemble a single queue item dict from draft/analysis/summary data."""
    return {
        "contactId": contact_id,
        "ghlContactId": _draft_or_fallback(draft, summary, "ghl_contact_id", "ghl_contact_id"),
        "contactName": contact_name,
        "companyName": _draft_or_fallback(draft, summary, "company_name", "company_name"),
        "contactEmail": _draft_or_fallback(draft, summary, "contact_email", "email"),
        "draftId": draft.draft_id if draft else None,
        "sourceConversationId": _draft_or_fallback(draft, analysis, "source_conversation_id", "source_conversation_id"),
        "status": draft.status if draft else None,
        "subject": draft.subject if draft else "",
        "body": draft.body if draft else "",
        "urgency": _draft_or_fallback(draft, analysis, "urgency", "urgency", default=None),
        "sentiment": _draft_or_fallback(draft, analysis, "sentiment", "sentiment", default=None),
        "stage": _draft_or_fallback(draft, analysis, "stage", "stage", default=None),
        "trigger": _draft_or_fallback(draft, analysis, "trigger", "trigger", default=None),
        "analysisSummary": (
            draft.analysis_summary
            if draft and draft.analysis_summary
            else analysis.conversation_summary if analysis else ""
        ),
        "recommendedAction": analysis.recommended_action if analysis else "",
        "daysSinceLastActivity": analysis.days_since_last_activity if analysis else 0,
        "lastActivityAt": primary_thread.last_message_date if primary_thread else None,
        "primaryThread": primary_thread,
        "analysis": analysis,
        "draft": draft,
        "summary": summary,
        "businessDate": draft.business_date if draft else queue_date,
        "hasActiveSales": is_active_sales,
    }


def load_followup_queue(date: Optional[str] = None) -> list[dict[str, Any]]:
    """Build the warm review queue by joining drafts, analyses, and conversations."""
    storage = get_storage_backend()
    summaries = {
        summary.contact_id: summary
        for summary in storage.list_conversation_summaries()
    }
    analyses = {
        analysis.contact_id: analysis
        for analysis in storage.list_conversation_analyses()
    }
    if date:
        # Explicit date requested — filter to that date only
        all_drafts = storage.list_followup_drafts(business_date=date)
        drafts = all_drafts
        queue_date = date
    else:
        # No date filter — show ALL PENDING drafts across all dates.
        # A PENDING draft from any day is still actionable (e.g. after a partial cron run).
        all_drafts = storage.list_followup_drafts()
        _terminal = {DraftApprovalStatus.DISPATCHED, DraftApprovalStatus.REJECTED}
        drafts = [d for d in all_drafts if d.status not in _terminal]
        queue_date = _resolve_queue_date(None, drafts) if drafts else current_business_date()
    queue: list[dict[str, Any]] = []
    sales_user_ids = _load_sales_team_user_ids()
    # Show ALL analyzed contacts — those without drafts appear as analysis-only (non-approvable)
    draft_contact_ids = {draft.contact_id for draft in drafts}
    analysis_contact_ids = set(analyses.keys())
    contact_ids = sorted(draft_contact_ids | analysis_contact_ids)
    for contact_id in contact_ids:
        analysis = analyses.get(contact_id)
        summary = summaries.get(contact_id)
        primary_thread = select_primary_thread(summary) if summary else None
        contact_drafts = [draft for draft in drafts if draft.contact_id == contact_id]
        contact_drafts.sort(key=lambda draft: (draft.business_date, draft.created_at), reverse=True)
        draft = contact_drafts[0] if contact_drafts else None

        contact_name = ""
        if draft and draft.contact_name:
            contact_name = draft.contact_name
        elif summary:
            contact_name = f"{summary.first_name} {summary.last_name}".strip()

        is_active_sales = has_recent_manual_outbound(summary, sales_user_ids) if summary else False

        queue.append(_build_queue_item(
            contact_id=contact_id,
            draft=draft,
            analysis=analysis,
            summary=summary,
            primary_thread=primary_thread,
            contact_name=contact_name,
            queue_date=queue_date,
            is_active_sales=is_active_sales,
        ))

    # Defense-in-depth: remove DnD/unsubscribed contacts from queue display
    def _is_contactable(item: dict[str, Any]) -> bool:
        summary = item["summary"]
        return summary is None or not is_dnd_or_unsubscribed(summary)

    queue = [item for item in queue if _is_contactable(item)]

    queue.sort(
        key=lambda item: (
            _status_rank(item["status"]),
            _urgency_rank(item["urgency"].value if item["urgency"] else None),
            -(item["daysSinceLastActivity"] or 0),
        )
    )
    return queue
