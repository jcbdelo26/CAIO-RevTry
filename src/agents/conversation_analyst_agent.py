"""Conversation analyst for warm follow-up classification.

The analyst only processes warm-eligible conversation summaries. Trigger
classification is deterministic; the LLM fills in sentiment, stage, urgency,
topics, summary, and recommended action.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from integrations.anthropic_client import AnthropicClient, HAIKU_MODEL
from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    ConversationMessage,
    FollowUpTrigger,
    UrgencyLevel,
)
from persistence.factory import get_storage_backend
from scripts.ghl_conversation_scanner import (
    compact_thread_messages,
    filter_eligible_summaries,
    has_valid_email,
    select_primary_thread,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 5

SYSTEM_PROMPT = """You analyze warm B2B email conversations for follow-up readiness.

Return a single JSON object with exactly these keys:
- sentiment: one of positive, neutral, negative, cold
- stage: one of new, engaged, stalled, won, lost
- urgency: one of hot, warm, cooling
- keyTopics: array of short strings
- recommendedAction: concise action recommendation for the next follow-up
- conversationSummary: 1-2 sentence factual summary grounded only in the provided thread
- confidence: float 0.0-1.0 representing your confidence in the analysis quality. 1.0 = strong CRM signal, clear conversation context. 0.0 = sparse data, ambiguous signals.

Rules:
- Do not fabricate facts, meetings, offers, or objections not present in the thread.
- Use only the supplied conversation context.
- Keep keyTopics factual and short.
- If the thread is clearly active and awaiting a reply from us, urgency should usually be hot.
- If the thread is stale or weak, urgency should usually be warm or cooling.
"""


@dataclass
class AnalysisBatchResult:
    analyses: list[ConversationAnalysis] = field(default_factory=list)
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    skipped_no_conversation: int = 0
    skipped_no_email: int = 0
    skipped_dnd: int = 0
    skipped_active_sales: int = 0

def _parse_timestamp(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _days_since(timestamp: str | None, reference_time: datetime) -> int:
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return 0
    delta = reference_time - parsed
    return max(int(delta.total_seconds() // 86400), 0)


def classify_trigger(
    summary: ContactConversationSummary,
    *,
    reference_time: Optional[datetime] = None,
) -> tuple[FollowUpTrigger, str]:
    """Determine the follow-up trigger from conversation timing and direction."""
    reference_time = reference_time or datetime.now(timezone.utc)
    primary_thread = select_primary_thread(summary)
    if primary_thread is None or not primary_thread.messages:
        raise ValueError("Conversation summary has no primary thread for trigger classification")

    latest_message = primary_thread.messages[0]
    days_since_last_activity = _days_since(primary_thread.last_message_date, reference_time)
    last_inbound = _parse_timestamp(summary.last_inbound_date)
    last_outbound = _parse_timestamp(summary.last_outbound_date)

    if latest_message.direction == "inbound":
        return (
            FollowUpTrigger.AWAITING_OUR_RESPONSE,
            "Latest primary-thread message is inbound; we owe the next response.",
        )

    if last_inbound is not None and last_outbound is not None and days_since_last_activity >= 7:
        return (
            FollowUpTrigger.GONE_COLD,
            f"Thread had two-way engagement but no activity for {days_since_last_activity} day(s).",
        )

    if latest_message.direction == "outbound" and (
        last_inbound is None or (last_outbound is not None and last_inbound <= last_outbound)
    ):
        if days_since_last_activity >= 2:
            return (
                FollowUpTrigger.NO_REPLY,
                f"Latest primary-thread message is outbound and has been unanswered for {days_since_last_activity} day(s).",
            )

    return (
        FollowUpTrigger.NO_REPLY,
        "Latest visible activity is outbound and the thread still needs follow-up.",
    )


def _format_messages(messages: list[ConversationMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        lines.append(
            f"[{message.timestamp}] {message.direction.upper()} | "
            f"subject={message.subject or ''} | body={message.body}"
        )
    return "\n".join(lines)


def _default_urgency(trigger: FollowUpTrigger, days_since_last_activity: int) -> UrgencyLevel:
    if trigger == FollowUpTrigger.AWAITING_OUR_RESPONSE:
        return UrgencyLevel.HOT
    if trigger == FollowUpTrigger.NO_REPLY and days_since_last_activity <= 7:
        return UrgencyLevel.WARM
    return UrgencyLevel.COOLING


def _normalize_analysis_payload(
    payload: dict,
    *,
    summary: ContactConversationSummary,
    source_conversation_id: str,
    trigger: FollowUpTrigger,
    trigger_reason: str,
    analyzed_at: str,
    days_since_last_activity: int,
) -> ConversationAnalysis:
    conversation_summary = (
        payload.get("conversationSummary")
        or payload.get("conversation_summary")
        or "No summary provided."
    )
    key_topics = payload.get("keyTopics") or payload.get("key_topics") or []
    recommended_action = (
        payload.get("recommendedAction")
        or payload.get("recommended_action")
        or "Review thread manually before drafting."
    )
    urgency = payload.get("urgency") or _default_urgency(trigger, days_since_last_activity).value

    confidence = payload.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = None

    normalized = {
        "contactId": summary.contact_id,
        "sourceConversationId": source_conversation_id,
        "sentiment": payload.get("sentiment", "neutral"),
        "stage": payload.get("stage", "engaged"),
        "trigger": trigger.value,
        "triggerReason": trigger_reason,
        "urgency": urgency,
        "keyTopics": key_topics,
        "recommendedAction": recommended_action,
        "conversationSummary": conversation_summary,
        "daysSinceLastActivity": days_since_last_activity,
        "analyzedAt": analyzed_at,
        "confidence": confidence,
    }
    return ConversationAnalysis.model_validate(normalized)


def _save_analysis(analysis: ConversationAnalysis) -> None:
    get_storage_backend().save_conversation_analysis(analysis)


async def analyze_summary(
    summary: ContactConversationSummary,
    *,
    client: AnthropicClient,
    reference_time: Optional[datetime] = None,
) -> Optional[ConversationAnalysis]:
    """Analyze one eligible conversation summary into a warm follow-up classification."""
    if not has_valid_email(summary.email):
        return None

    reference_time = reference_time or datetime.now(timezone.utc)
    primary_thread = select_primary_thread(summary)
    if primary_thread is None:
        return None

    trigger, trigger_reason = classify_trigger(summary, reference_time=reference_time)
    compact_messages = compact_thread_messages(primary_thread)
    days_since_last_activity = _days_since(primary_thread.last_message_date, reference_time)

    user_prompt = (
        "Contact metadata:\n"
        f"- contactId: {summary.contact_id}\n"
        f"- ghlContactId: {summary.ghl_contact_id}\n"
        f"- firstName: {summary.first_name}\n"
        f"- lastName: {summary.last_name}\n"
        f"- email: {summary.email}\n"
        f"- companyName: {summary.company_name}\n"
        f"- title: {summary.title}\n"
        f"- sourceConversationId: {primary_thread.conversation_id}\n"
        f"- deterministicTrigger: {trigger.value}\n"
        f"- triggerReason: {trigger_reason}\n"
        f"- daysSinceLastActivity: {days_since_last_activity}\n\n"
        "Primary-thread messages (chronological, compacted):\n"
        f"{_format_messages(compact_messages)}"
    )

    raw = await client.complete_json(
        HAIKU_MODEL,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=800,
        temperature=0.1,
        trace_context={
            "agent": "conversation-analyst",
            "contactId": summary.contact_id,
            "sourceConversationId": primary_thread.conversation_id,
            "trigger": trigger.value,
        },
    )

    analysis = _normalize_analysis_payload(
        raw,
        summary=summary,
        source_conversation_id=primary_thread.conversation_id,
        trigger=trigger,
        trigger_reason=trigger_reason,
        analyzed_at=reference_time.isoformat(),
        days_since_last_activity=days_since_last_activity,
    )
    _save_analysis(analysis)
    return analysis


async def analyze_batch(
    summaries: list[ContactConversationSummary],
    *,
    client: AnthropicClient | None = None,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    reference_time: Optional[datetime] = None,
) -> AnalysisBatchResult:
    """Analyze a batch of summaries with per-contact failure isolation."""
    result = AnalysisBatchResult()
    filter_result = filter_eligible_summaries(summaries)
    eligible = filter_result.eligible
    result.skipped = len(summaries) - len(eligible)
    result.skipped_no_conversation = filter_result.skipped_no_conversation
    result.skipped_no_email = filter_result.skipped_no_email
    result.skipped_dnd = filter_result.skipped_dnd
    result.skipped_active_sales = filter_result.skipped_active_sales

    if not eligible:
        return result

    own_client = client is None
    if client is None:
        client = AnthropicClient()

    semaphore = asyncio.Semaphore(max_concurrent)
    reference_time = reference_time or datetime.now(timezone.utc)

    async def _run(summary: ContactConversationSummary) -> None:
        async with semaphore:
            try:
                analysis = await analyze_summary(
                    summary,
                    client=client,
                    reference_time=reference_time,
                )
            except Exception as exc:
                logger.warning("Conversation analysis failed for %s: %s", summary.contact_id, exc)
                result.failed += 1
                result.errors.append(f"{summary.contact_id}: {exc}")
                return

            if analysis is not None:
                result.analyses.append(analysis)

    try:
        await asyncio.gather(*[_run(summary) for summary in eligible])
    finally:
        if own_client:
            await client.close()

    return result
