"""Gate 2 validator for warm follow-up drafts."""

from __future__ import annotations

from typing import Optional

from models.schemas import FollowUpDraft, ValidationResult
from utils.vault_loader import Exclusions, Signatures, load_exclusions, load_signatures

SPAM_TRIGGERS = frozenset({
    "free", "guarantee", "urgent", "act now", "limited time",
    "winner", "no obligation", "buy now",
})

ALLOWED_ACRONYMS = frozenset({
    "AI", "IT", "CRM", "SaaS", "API", "CEO", "CTO", "CIO", "COO",
    "VP", "ROI", "KPI", "B2B", "MAP", "HR",
})

BANNED_WARM_OPENERS = frozenset({
    "hope this finds you well",
    "just checking in",
    "following up",
    "circling back",
})


def validate_followup_gate2(
    drafts: list[FollowUpDraft],
    exclusions: Optional[Exclusions] = None,
    signatures: Optional[Signatures] = None,
) -> ValidationResult:
    """Run compliance validation for warm follow-up drafts."""
    exclusions = exclusions or load_exclusions()
    signatures = signatures or load_signatures()

    failures: list[str] = []
    checks_run = 0
    checks_passed = 0

    for draft in drafts:
        contact_email = draft.contact_email.lower()

        checks_run += 1
        if "@" in contact_email and contact_email.rsplit("@", 1)[1] in exclusions.blocked_domains:
            failures.append(f"Check 1: blocked domain for draft {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        if contact_email in exclusions.blocked_emails:
            failures.append(f"Check 2: blocked email for draft {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        if signatures.can_spam_footer not in draft.body:
            failures.append(f"Check 3: CAN-SPAM footer missing for {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        if "STOP" not in draft.body and "unsubscribe" not in draft.body.lower():
            failures.append(f"Check 4: unsubscribe mechanism missing for {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        opener = next((line.strip().lower() for line in draft.body.splitlines() if line.strip()), "")
        if any(opener.startswith(phrase) for phrase in BANNED_WARM_OPENERS):
            failures.append(f"Check 5: banned opener for {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        if len(draft.subject.strip()) > signatures.subject_max_length:
            failures.append(f"Check 6: subject too long for {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        subject_lower = draft.subject.lower()
        found_triggers = [trigger for trigger in SPAM_TRIGGERS if trigger in subject_lower]
        if found_triggers:
            failures.append(f"Check 7: spam trigger(s) {found_triggers} in subject for {draft.draft_id}")
        else:
            checks_passed += 1

        checks_run += 1
        words = draft.subject.split()
        caps_words = [
            word for word in words
            if len(word) > 1 and word == word.upper() and word.isalpha() and word not in ALLOWED_ACRONYMS
        ]
        if caps_words or draft.subject.count("!") > signatures.subject_max_exclamations:
            failures.append(f"Check 8: subject formatting issue for {draft.draft_id}")
        else:
            checks_passed += 1

    return ValidationResult(
        gate="followup-gate2",
        passed=len(failures) == 0,
        checksRun=checks_run,
        checksPassed=checks_passed,
        failures=failures,
    )
