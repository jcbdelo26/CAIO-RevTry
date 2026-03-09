"""Warm follow-up draft agent.

Generates conversation-aware follow-up drafts from analyzed warm conversations.
This agent intentionally uses a narrow context package: compacted thread history,
sender/compliance signatures, and a small CTA/proof surface. It does not load
cold-outbound angle or ICP playbook context.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from integrations.anthropic_client import AnthropicClient, SONNET_MODEL
from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    ConversationMessage,
    FollowUpDraft,
)
from scripts.ghl_conversation_scanner import compact_thread_messages, select_primary_thread
from utils.vault_loader import Signatures, load_signatures

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 3
MAX_BODY_WORDS = 150
MAX_SUBJECT_CHARS = 60

DEFAULT_PROOF_POINTS = [
    "AI-powered workflow automation reduced manual task time by 40%.",
    "Intelligent CRM automation improved response rates by 2.5x.",
]

STAGE_TONE_GUIDANCE = {
    "new": "Keep the tone lightly personalized and low-pressure.",
    "engaged": "Sound warm, informed, and responsive to the current conversation.",
    "stalled": "Re-energize the thread gently with a clear, easy next step.",
    "won": "Do not draft if the thread is already won.",
    "lost": "Do not draft if the thread is already lost.",
}

TRIGGER_CTA_GUIDANCE = {
    "awaiting_our_response": "Primary CTA should usually be a direct reply CTA, not a booking push.",
    "no_reply": "CTA can offer either a simple reply or an optional booking link if it fits naturally.",
    "gone_cold": "CTA should be low-pressure and may offer a reply-first option before a booking link.",
}

SYSTEM_PROMPT = """You draft warm B2B follow-up emails grounded in a real prior conversation.

Return a single JSON object with exactly these keys:
- subject: short email subject line
- body: full plain-text email body

Rules:
- Reference the real prior conversation explicitly.
- Do not fabricate facts, meetings, deliverables, objections, or results.
- Do not use these openers as the opening line: hope this finds you well, just checking in, following up, circling back.
- Subject must be under 60 characters.
- Body must stay under 150 words.
- Match the tone to the conversation stage and urgency.
- A booking-link CTA is optional, not mandatory. A reply CTA is valid.
- Include the provided signature block and CAN-SPAM footer exactly.
"""


@dataclass
class DraftBatchResult:
    drafts: list[FollowUpDraft] = field(default_factory=list)
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def _generate_draft_id(contact_id: str, source_conversation_id: str, business_date: str) -> str:
    raw = f"{contact_id}:{source_conversation_id}:{business_date}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _display_name(summary: ContactConversationSummary) -> str:
    full_name = f"{summary.first_name} {summary.last_name}".strip()
    if full_name:
        return full_name
    return summary.email or summary.contact_id


def _find_source_thread(
    summary: ContactConversationSummary,
    source_conversation_id: str,
):
    for thread in summary.threads:
        if thread.conversation_id == source_conversation_id:
            return thread
    return select_primary_thread(summary)


def _format_messages(messages: list[ConversationMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        subject = f" | subject={message.subject}" if message.subject else ""
        lines.append(
            f"[{message.timestamp}] {message.direction.upper()}{subject} | body={message.body}"
        )
    return "\n".join(lines)


def _opening_line(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _count_words(text: str) -> int:
    return len([word for word in text.replace("\n", " ").split() if word.strip()])


def _validate_generated_draft(subject: str, body: str, signatures: Signatures) -> None:
    if not subject.strip():
        raise ValueError("Generated draft subject is empty")
    if len(subject.strip()) > MAX_SUBJECT_CHARS:
        raise ValueError(f"Generated draft subject exceeds {MAX_SUBJECT_CHARS} characters")
    if _count_words(body) > MAX_BODY_WORDS:
        raise ValueError(f"Generated draft body exceeds {MAX_BODY_WORDS} words")

    opener = _opening_line(body).lower()
    banned_openers = {
        "hope this finds you well",
        "just checking in",
        "following up",
        "circling back",
    }
    if any(opener.startswith(banned) for banned in banned_openers):
        raise ValueError("Generated draft uses a banned opener")

    if signatures.sender_name not in body:
        raise ValueError("Generated draft is missing sender name")
    if signatures.sender_title not in body:
        raise ValueError("Generated draft is missing sender title")
    if signatures.can_spam_footer not in body:
        raise ValueError("Generated draft is missing CAN-SPAM footer")


def build_followup_prompt(
    analysis: ConversationAnalysis,
    summary: ContactConversationSummary,
    signatures: Signatures,
) -> str:
    """Assemble the minimal warm drafting context."""
    source_thread = _find_source_thread(summary, analysis.source_conversation_id)
    if source_thread is None:
        raise ValueError(
            f"No source thread found for contact {summary.contact_id} conversation {analysis.source_conversation_id}"
        )

    compact_messages = compact_thread_messages(source_thread)
    display_name = _display_name(summary)
    tone_guidance = STAGE_TONE_GUIDANCE.get(analysis.stage.value, STAGE_TONE_GUIDANCE["engaged"])
    cta_guidance = TRIGGER_CTA_GUIDANCE.get(analysis.trigger.value, TRIGGER_CTA_GUIDANCE["no_reply"])

    return (
        "Contact metadata:\n"
        f"- contactId: {summary.contact_id}\n"
        f"- ghlContactId: {summary.ghl_contact_id}\n"
        f"- contactName: {display_name}\n"
        f"- companyName: {summary.company_name}\n"
        f"- title: {summary.title}\n"
        f"- sourceConversationId: {analysis.source_conversation_id}\n\n"
        "Conversation analysis:\n"
        f"- sentiment: {analysis.sentiment.value}\n"
        f"- stage: {analysis.stage.value}\n"
        f"- trigger: {analysis.trigger.value}\n"
        f"- triggerReason: {analysis.trigger_reason}\n"
        f"- urgency: {analysis.urgency.value}\n"
        f"- keyTopics: {', '.join(analysis.key_topics)}\n"
        f"- recommendedAction: {analysis.recommended_action}\n"
        f"- conversationSummary: {analysis.conversation_summary}\n\n"
        "Tone / CTA guidance:\n"
        f"- toneGuidance: {tone_guidance}\n"
        f"- ctaGuidance: {cta_guidance}\n\n"
        "Approved proof points (use only if naturally relevant; do not invent metrics):\n"
        + "\n".join(f"- {proof}" for proof in DEFAULT_PROOF_POINTS)
        + "\n\n"
        "Approved signature / compliance requirements:\n"
        f"- senderName: {signatures.sender_name}\n"
        f"- senderTitle: {signatures.sender_title}\n"
        f"- bookingLink: {signatures.booking_link}\n"
        f"- canSpamFooter:\n{signatures.can_spam_footer}\n\n"
        "Primary-thread messages (chronological, compacted):\n"
        f"{_format_messages(compact_messages)}"
    )


async def draft_followup(
    analysis: ConversationAnalysis,
    summary: ContactConversationSummary,
    *,
    client: AnthropicClient,
    business_date: str,
    generation_run_id: str,
    signatures: Signatures | None = None,
    created_at: Optional[datetime] = None,
) -> FollowUpDraft:
    """Generate a single warm follow-up draft."""
    signatures = signatures or load_signatures()

    if summary.contact_id != analysis.contact_id:
        raise ValueError("Conversation analysis contact_id does not match summary contact_id")
    if analysis.stage.value in {"won", "lost"}:
        raise ValueError(f"Cannot draft follow-up for terminal stage '{analysis.stage.value}'")

    prompt = build_followup_prompt(analysis, summary, signatures)
    payload = await client.complete_json(
        SONNET_MODEL,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        max_tokens=900,
        temperature=0.4,
        trace_context={
            "agent": "followup-draft",
            "contactId": analysis.contact_id,
            "sourceConversationId": analysis.source_conversation_id,
            "stage": analysis.stage.value,
            "trigger": analysis.trigger.value,
        },
    )

    subject = (payload.get("subject") or "").strip()
    body = (payload.get("body") or "").strip()
    _validate_generated_draft(subject, body, signatures)

    timestamp = (created_at or datetime.now(timezone.utc)).isoformat()
    return FollowUpDraft(
        draftId=_generate_draft_id(summary.contact_id, analysis.source_conversation_id, business_date),
        contactId=summary.contact_id,
        ghlContactId=summary.ghl_contact_id,
        sourceConversationId=analysis.source_conversation_id,
        businessDate=business_date,
        generationRunId=generation_run_id,
        contactEmail=summary.email,
        contactName=_display_name(summary),
        companyName=summary.company_name,
        subject=subject,
        body=body,
        trigger=analysis.trigger,
        urgency=analysis.urgency,
        sentiment=analysis.sentiment,
        stage=analysis.stage,
        analysisSummary=analysis.conversation_summary,
        createdAt=timestamp,
    )


async def draft_batch(
    analyses: list[ConversationAnalysis],
    summaries: list[ContactConversationSummary],
    *,
    client: AnthropicClient | None = None,
    business_date: str,
    generation_run_id: str,
    signatures: Signatures | None = None,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> DraftBatchResult:
    """Generate multiple warm follow-up drafts with per-contact failure isolation."""
    summaries_by_contact = {summary.contact_id: summary for summary in summaries}
    result = DraftBatchResult()
    own_client = client is None
    if client is None:
        client = AnthropicClient()
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _run(analysis: ConversationAnalysis) -> None:
        summary = summaries_by_contact.get(analysis.contact_id)
        if summary is None:
            result.failed += 1
            result.errors.append(f"{analysis.contact_id}: missing conversation summary")
            return

        async with semaphore:
            try:
                draft = await draft_followup(
                    analysis,
                    summary,
                    client=client,
                    business_date=business_date,
                    generation_run_id=generation_run_id,
                    signatures=signatures,
                )
            except Exception as exc:
                logger.warning("Warm draft generation failed for %s: %s", analysis.contact_id, exc)
                result.failed += 1
                result.errors.append(f"{analysis.contact_id}: {exc}")
                return

            result.drafts.append(draft)

    try:
        await asyncio.gather(*[_run(analysis) for analysis in analyses])
    finally:
        if own_client:
            await client.close()

    return result
