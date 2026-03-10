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


def _find_thread(summary: ContactConversationSummary, source_conversation_id: str):
    """Find the thread matching source_conversation_id, falling back to the primary thread."""
    for candidate in summary.threads:
        if candidate.conversation_id == source_conversation_id:
            return candidate
    return select_primary_thread(summary)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


_STOP_WORDS = frozenset({
    "that", "with", "have", "from", "this", "been", "were",
    "your", "they", "will", "just", "about", "would", "there",
    "what", "when", "know", "like", "some", "also", "more",
    "than", "them", "other", "into", "only", "over", "very",
    "each", "made", "much", "such", "even", "back", "come",
    "take", "good", "well", "same", "could", "should", "these",
    "those", "here", "then", "does", "done", "want", "need",
})


def _body_mentions_conversation(
    draft: FollowUpDraft,
    analysis: ConversationAnalysis,
    summary: Optional[ContactConversationSummary],
) -> bool:
    body = _normalize(draft.body)

    # Pass 1: exact topic substring (original behavior)
    for topic in analysis.key_topics:
        topic_norm = _normalize(topic)
        if topic_norm and topic_norm in body:
            return True

    # Pass 2: fuzzy topic word matching — match if 2+ topic words appear in body
    for topic in analysis.key_topics:
        topic_words = [w for w in _normalize(topic).split() if len(w) >= 4 and w not in _STOP_WORDS]
        if len(topic_words) >= 2:
            matches = sum(1 for w in topic_words if w in body)
            if matches >= 2:
                return True
        elif topic_words and topic_words[0] in body:
            return True

    if summary is None:
        return False

    thread = _find_thread(summary, draft.source_conversation_id)
    if thread is None:
        return False

    # Pass 3: 2-word message phrases (relaxed from 3)
    for message in compact_thread_messages(thread, max_messages=3, max_body_chars=160):
        words = [word for word in re.findall(r"[a-zA-Z]{4,}", message.body.lower()) if word not in _STOP_WORDS]
        if len(words) >= 2:
            phrase = " ".join(words[:2]).strip()
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
