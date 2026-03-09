"""Gate 3 validator for warm follow-up drafts."""

from __future__ import annotations

import re
from typing import Optional

from models.schemas import ContactConversationSummary, ConversationAnalysis, FollowUpDraft, ValidationResult
from scripts.ghl_conversation_scanner import compact_thread_messages, select_primary_thread

COLD_OUTBOUND_PHRASES = frozenset({
    "came across your profile",
    "reaching out cold",
    "quick introduction",
    "ai executive briefing",
})


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _body_mentions_conversation(
    draft: FollowUpDraft,
    analysis: ConversationAnalysis,
    summary: Optional[ContactConversationSummary],
) -> bool:
    body = _normalize(draft.body)

    for topic in analysis.key_topics:
        topic_norm = _normalize(topic)
        if topic_norm and topic_norm in body:
            return True

    if summary is None:
        return False

    thread = None
    for candidate in summary.threads:
        if candidate.conversation_id == draft.source_conversation_id:
            thread = candidate
            break
    thread = thread or select_primary_thread(summary)
    if thread is None:
        return False

    for message in compact_thread_messages(thread, max_messages=3, max_body_chars=160):
        words = [word for word in re.findall(r"[a-zA-Z]{4,}", message.body.lower()) if word not in {"that", "with", "have", "from"}]
        if not words:
            continue
        phrase = " ".join(words[:3]).strip()
        if phrase and phrase in body:
            return True

    return False


def validate_followup_gate3(
    drafts: list[FollowUpDraft],
    analyses: dict[str, ConversationAnalysis],
    summaries: Optional[dict[str, ContactConversationSummary]] = None,
) -> ValidationResult:
    """Run warm business-alignment validation."""
    summaries = summaries or {}

    failures: list[str] = []
    checks_run = 0
    checks_passed = 0

    for draft in drafts:
        analysis = analyses.get(draft.contact_id)

        checks_run += 1
        if analysis is None:
            failures.append(f"Check 1: missing analysis for draft {draft.draft_id}")
        elif analysis.source_conversation_id != draft.source_conversation_id:
            failures.append(f"Check 1: source conversation mismatch for draft {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        if analysis is None or not _body_mentions_conversation(draft, analysis, summaries.get(draft.contact_id)):
            failures.append(f"Check 2: conversation reference missing for draft {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        if analysis is None or analysis.stage.value in {"won", "lost"}:
            failures.append(f"Check 3: invalid terminal stage for draft {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        body = _normalize(draft.body)
        if any(phrase in body for phrase in COLD_OUTBOUND_PHRASES):
            failures.append(f"Check 4: cold-outbound language detected in draft {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        if analysis is None:
            failures.append(f"Check 5: missing trigger evidence for draft {draft.draft_id}")
        elif analysis.trigger.value == "awaiting_our_response":
            if not any(marker in body for marker in ("you asked", "you mentioned", "reply", "?")):
                failures.append(f"Check 5: awaiting-response draft lacks reply-oriented language for {draft.draft_id}")
            else:
                checks_passed += 1
        elif analysis.trigger.value == "gone_cold":
            if any(marker in body for marker in ("urgent", "asap", "act now")):
                failures.append(f"Check 5: gone-cold draft is too forceful for {draft.draft_id}")
            else:
                checks_passed += 1
        else:
            checks_passed += 1

    return ValidationResult(
        gate="followup-gate3",
        passed=len(failures) == 0,
        checksRun=checks_run,
        checksPassed=checks_passed,
        failures=failures,
    )
