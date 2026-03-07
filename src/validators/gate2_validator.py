"""Gate 2 Validator — Compliance checks.

10 checks:
1. Blocked domains
2. Blocked emails
3. DQ rules applied
4. Rate limits respected
5. Channel routing correct
6. CAN-SPAM footer present
7. Unsubscribe mechanism
8. Spam triggers in subject
9. Subject line rules
10. Banned openers
"""

from __future__ import annotations

from typing import Optional

from models.schemas import (
    CampaignCraftOutput,
    CampaignDraft,
    Channel,
    ValidationResult,
)
from utils.vault_loader import (
    Exclusions,
    Signatures,
    load_exclusions,
    load_signatures,
)

SPAM_TRIGGERS = frozenset({
    "free", "guarantee", "urgent", "act now", "limited time",
    "winner", "no obligation", "buy now",
})

# Common acronyms that should NOT trigger the ALL-CAPS subject check
ALLOWED_ACRONYMS = frozenset({
    "AI", "IT", "CRM", "SaaS", "API", "CEO", "CTO", "CIO", "COO",
    "VP", "ROI", "KPI", "B2B", "MAP", "HR",
})


def validate_gate2(
    output: CampaignCraftOutput,
    exclusions: Optional[Exclusions] = None,
    signatures: Optional[Signatures] = None,
) -> ValidationResult:
    """Run Gate 2 compliance checks on Campaign Craft output."""
    if exclusions is None:
        exclusions = load_exclusions()
    if signatures is None:
        signatures = load_signatures()

    failures: list[str] = []
    checks_run = 0
    checks_passed = 0

    for draft in output.drafts:
        contact = draft.contact_id

        # Check 1: Blocked domains
        checks_run += 1
        if "@" in contact:
            domain = contact.rsplit("@", 1)[1].lower()
            if domain in exclusions.blocked_domains:
                failures.append(f"Check 1: Draft for blocked domain '{domain}' ({contact})")
            else:
                checks_passed += 1
        else:
            checks_passed += 1

        # Check 2: Blocked emails
        checks_run += 1
        if contact.lower() in exclusions.blocked_emails:
            failures.append(f"Check 2: Draft for blocked email '{contact}'")
        else:
            checks_passed += 1

        # Check 5: Channel routing — only GHL warm email is active
        checks_run += 1
        if draft.channel == Channel.GHL:
            checks_passed += 1
        elif draft.channel in (Channel.INSTANTLY, Channel.HEYREACH):
            failures.append(
                f"Check 5: Deferred channel '{draft.channel.value}' on draft {draft.draft_id} "
                f"— only GHL warm email is active"
            )
        else:
            failures.append(
                f"Check 5: Unknown channel '{draft.channel}' on draft {draft.draft_id}"
            )

        # Check 6: CAN-SPAM footer
        checks_run += 1
        if signatures.can_spam_footer not in draft.body:
            failures.append(f"Check 6: CAN-SPAM footer missing in draft {draft.draft_id}")
        else:
            checks_passed += 1

        # Check 7: Unsubscribe mechanism
        checks_run += 1
        if "STOP" not in draft.body and "unsubscribe" not in draft.body.lower():
            failures.append(f"Check 7: No unsubscribe mechanism in draft {draft.draft_id}")
        else:
            checks_passed += 1

        # Check 8: Spam triggers in subject
        checks_run += 1
        subject_lower = draft.subject.lower()
        found_triggers = [t for t in SPAM_TRIGGERS if t in subject_lower]
        if found_triggers:
            failures.append(f"Check 8: Spam triggers in subject: {found_triggers} ({draft.draft_id})")
        else:
            checks_passed += 1

        # Check 9: Subject line rules
        checks_run += 1
        subject_issues: list[str] = []
        if len(draft.subject) > signatures.subject_max_length:
            subject_issues.append(f"too long ({len(draft.subject)} chars)")
        words = draft.subject.split()
        caps_words = [w for w in words if len(w) > 1 and w == w.upper() and w.isalpha() and w not in ALLOWED_ACRONYMS]
        if caps_words:
            subject_issues.append(f"ALL CAPS: {caps_words}")
        if draft.subject.count("!") > signatures.subject_max_exclamations:
            subject_issues.append(f"too many '!' ({draft.subject.count('!')})")
        if subject_issues:
            failures.append(f"Check 9: Subject issues: {'; '.join(subject_issues)} ({draft.draft_id})")
        else:
            checks_passed += 1

        # Check 10: Banned openers
        checks_run += 1
        first_line = draft.body.strip().split("\n")[0].strip()
        banned_match = None
        for banned in signatures.banned_openers:
            if first_line.lower().startswith(banned.lower()):
                banned_match = banned
                break
        if banned_match:
            failures.append(f"Check 10: Banned opener '{banned_match}' in draft {draft.draft_id}")
        else:
            checks_passed += 1

    # Check 3: DQ rules applied (trace-level)
    checks_run += 1
    if output.trace.compliance_checks_prepared:
        checks_passed += 1
    else:
        failures.append("Check 3: complianceChecksPrepared is false")

    # Check 4: Rate limits (at batch level — we just verify the count is reasonable)
    checks_run += 1
    if len(output.drafts) <= 200:  # Max 200 emails/day
        checks_passed += 1
    else:
        failures.append(f"Check 4: Batch size {len(output.drafts)} exceeds daily rate limit (200)")

    return ValidationResult(
        gate="gate2",
        passed=len(failures) == 0,
        checksRun=checks_run,
        checksPassed=checks_passed,
        failures=failures,
    )
