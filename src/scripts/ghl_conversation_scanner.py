"""GHL Conversation Scanner — pulls conversation history for active contacts.

Loads contacts from ghl_followup_candidates.json, fetches conversation threads
and messages from GHL Conversations API, filters to last N days, and stores
conversation snapshots for downstream sentiment analysis.

Rate limited: 0.5s between contacts to stay under 100 req/min GHL limit.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from integrations.ghl_client import GHLClient
from models.schemas import (
    ContactConversationSummary,
    ConversationMessage,
    ConversationThread,
)
from persistence.factory import get_storage_backend

logger = logging.getLogger(__name__)

DEFAULT_SCAN_DAYS = 30
DEFAULT_BATCH_SIZE = 50
INTER_CONTACT_DELAY = 0.5  # seconds between contacts
MAX_COMPACT_MESSAGES = 8
MAX_MESSAGE_BODY_CHARS = 500


def _outputs_dir() -> Path:
    return Path(os.environ.get("OUTPUTS_DIR", "outputs"))


def _conversations_dir() -> Path:
    d = _outputs_dir() / "conversations"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_candidates(batch_size: int | None = None) -> list[dict[str, Any]]:
    """Load follow-up candidates from the audit output."""
    candidates_path = _outputs_dir() / "ghl_followup_candidates.json"
    if not candidates_path.exists():
        logger.warning("No ghl_followup_candidates.json found at %s", candidates_path)
        return []

    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates = data if isinstance(data, list) else data.get("candidates", [])

    # DAILY_SCAN_BATCH_SIZE is the canonical env var; MAX_SCAN_CONTACTS is a deprecated alias
    limit = batch_size or int(
        os.environ.get("DAILY_SCAN_BATCH_SIZE")
        or os.environ.get("MAX_SCAN_CONTACTS", str(DEFAULT_BATCH_SIZE))
    )
    return candidates[:limit]


def _parse_timestamp(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None


def has_valid_email(email: str) -> bool:
    """Return True when the email is present and structurally valid enough for warm follow-up."""
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def _parse_messages(
    raw_messages: list[dict[str, Any]],
    conversation_id: str,
    cutoff: datetime,
) -> list[ConversationMessage]:
    """Parse and filter messages to those within the scan window."""
    messages: list[ConversationMessage] = []
    for msg in raw_messages:
        ts = msg.get("dateAdded", msg.get("createdAt", ""))
        if not ts:
            continue

        try:
            msg_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        if msg_time < cutoff:
            continue

        messages.append(ConversationMessage(
            messageId=msg.get("id", ""),
            conversationId=conversation_id,
            direction="inbound" if msg.get("direction") == "inbound" else "outbound",
            body=msg.get("body", msg.get("text", "")),
            subject=msg.get("subject"),
            timestamp=ts,
            messageType=msg.get("type", "Email"),
        ))

    return messages


def select_primary_thread(
    summary: ContactConversationSummary,
) -> Optional[ConversationThread]:
    """Choose the primary thread by most recent activity for v1 warm analysis."""
    threads = [thread for thread in summary.threads if thread.messages]
    if not threads:
        return None

    return max(
        threads,
        key=lambda thread: _parse_timestamp(thread.last_message_date) or datetime.min.replace(tzinfo=timezone.utc),
    )


def compact_thread_messages(
    thread: ConversationThread,
    max_messages: int = MAX_COMPACT_MESSAGES,
    max_body_chars: int = MAX_MESSAGE_BODY_CHARS,
) -> list[ConversationMessage]:
    """Return the most recent thread messages in chronological order with trimmed bodies."""
    selected = list(thread.messages[:max_messages])
    selected.reverse()

    compacted: list[ConversationMessage] = []
    for message in selected:
        body = message.body.strip()
        if len(body) > max_body_chars:
            body = body[: max_body_chars - 3].rstrip() + "..."

        compacted.append(message.model_copy(update={"body": body}))

    return compacted


def is_summary_eligible(summary: ContactConversationSummary) -> bool:
    """Warm analysis only runs on contacts with a real conversation and valid email."""
    return summary.total_messages > 0 and has_valid_email(summary.email) and select_primary_thread(summary) is not None


def filter_eligible_summaries(
    summaries: list[ContactConversationSummary],
) -> tuple[list[ContactConversationSummary], int, int]:
    """Split conversation summaries into eligible warm-analysis inputs and tracked skips."""
    eligible: list[ContactConversationSummary] = []
    skipped_no_conversation = 0
    skipped_no_email = 0

    for summary in summaries:
        if summary.total_messages <= 0 or select_primary_thread(summary) is None:
            skipped_no_conversation += 1
            continue
        if not has_valid_email(summary.email):
            skipped_no_email += 1
            continue
        eligible.append(summary)

    return eligible, skipped_no_conversation, skipped_no_email


async def scan_contact(
    ghl: GHLClient,
    contact: dict[str, Any],
    scan_days: int,
) -> Optional[ContactConversationSummary]:
    """Scan a single contact's conversation history from GHL."""
    contact_id = contact.get("ghl_contact_id", contact.get("id", ""))
    if not contact_id:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=scan_days)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        # Fetch conversation threads for this contact
        conv_result = await ghl.search_conversations(contact_id)
        conversations = conv_result.get("conversations", [])
    except Exception as e:
        logger.warning("Failed to fetch conversations for %s: %s", contact_id, e)
        return None

    threads: list[ConversationThread] = []
    all_messages: list[ConversationMessage] = []
    last_inbound: Optional[str] = None
    last_outbound: Optional[str] = None

    for conv in conversations:
        conv_id = conv.get("id", "")
        if not conv_id:
            continue

        try:
            msg_result = await ghl.get_messages(conv_id)
            raw_messages = msg_result.get("messages", [])
        except Exception as e:
            logger.warning("Failed to fetch messages for conversation %s: %s", conv_id, e)
            continue

        messages = _parse_messages(raw_messages, conv_id, cutoff)
        if not messages:
            continue

        # Track last inbound/outbound dates
        for msg in messages:
            if msg.direction == "inbound":
                if last_inbound is None or msg.timestamp > last_inbound:
                    last_inbound = msg.timestamp
            else:
                if last_outbound is None or msg.timestamp > last_outbound:
                    last_outbound = msg.timestamp

        # Sort messages newest first
        messages.sort(key=lambda m: m.timestamp, reverse=True)

        threads.append(ConversationThread(
            conversationId=conv_id,
            contactId=contact_id,
            lastMessageDate=messages[0].timestamp if messages else "",
            messageCount=len(messages),
            messages=messages,
        ))
        all_messages.extend(messages)

    threads.sort(
        key=lambda thread: _parse_timestamp(thread.last_message_date) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    return ContactConversationSummary(
        contactId=contact_id,
        ghlContactId=contact_id,
        firstName=contact.get("first_name", contact.get("firstName", "")),
        lastName=contact.get("last_name", contact.get("lastName", "")),
        email=contact.get("email", ""),
        companyName=contact.get("company_name", contact.get("companyName", "")),
        title=contact.get("title", ""),
        threads=threads,
        totalMessages=len(all_messages),
        lastInboundDate=last_inbound,
        lastOutboundDate=last_outbound,
        scannedAt=now_iso,
    )


async def scan_all_contacts(
    candidates: list[dict[str, Any]],
    ghl: GHLClient | None = None,
    scan_days: int | None = None,
) -> list[ContactConversationSummary]:
    """Scan conversation history for a batch of contacts."""
    days = scan_days or int(os.environ.get("FOLLOWUP_SCAN_DAYS", str(DEFAULT_SCAN_DAYS)))
    own_ghl = ghl is None
    if ghl is None:
        ghl = GHLClient()

    summaries: list[ContactConversationSummary] = []
    storage = get_storage_backend()

    try:
        for i, contact in enumerate(candidates):
            if i > 0:
                await asyncio.sleep(INTER_CONTACT_DELAY)

            summary = await scan_contact(ghl, contact, days)
            if summary is None:
                continue

            summaries.append(summary)
            storage.save_conversation_summary(summary)

    finally:
        if own_ghl:
            await ghl.close()

    eligible, skipped_no_conversation, skipped_no_email = filter_eligible_summaries(summaries)
    logger.info(
        "Scanned %d contacts, %d summaries, %d eligible, %d skipped no conversation, %d skipped no email",
        len(candidates),
        len(summaries),
        len(eligible),
        skipped_no_conversation,
        skipped_no_email,
    )
    return summaries


async def main() -> None:
    """CLI entry point for standalone scanning."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Scan GHL conversation history")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--days", type=int, default=DEFAULT_SCAN_DAYS)
    args = parser.parse_args()

    candidates = load_candidates(args.limit)
    if not candidates:
        logger.info("No candidates to scan")
        return

    logger.info("Scanning %d candidates (last %d days)", len(candidates), args.days)
    summaries = await scan_all_contacts(candidates, scan_days=args.days)
    logger.info(
        "Done: %d summaries, %d with messages",
        len(summaries),
        len([s for s in summaries if s.total_messages > 0]),
    )


if __name__ == "__main__":
    asyncio.run(main())
