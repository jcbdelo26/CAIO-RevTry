"""Shared exclusion checking logic used by agents and validators.

Checks contacts against blocked domains and blocked emails from
vault/compliance/exclusions.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from utils.vault_loader import Exclusions, load_exclusions


@dataclass
class ExclusionResult:
    is_blocked: bool
    reason: Optional[str] = None
    rule_id: Optional[str] = None


def is_blocked_domain(email: str, exclusions: Exclusions) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].lower()
    return domain in exclusions.blocked_domains


def is_blocked_email(email: str, exclusions: Exclusions) -> bool:
    if not email:
        return False
    return email.lower() in exclusions.blocked_emails


def check_exclusions(email: str, exclusions: Optional[Exclusions] = None) -> ExclusionResult:
    """Check a contact email against all exclusion rules.

    Evaluation order per disqualification.md:
    1. DQ-008: Blocked domain (fastest lookup)
    2. DQ-009: Blocked email (exact match)
    """
    if exclusions is None:
        exclusions = load_exclusions()

    if not email:
        return ExclusionResult(is_blocked=False)

    email_lower = email.lower()

    # DQ-008: Blocked domain
    if "@" in email_lower:
        domain = email_lower.rsplit("@", 1)[1]
        if domain in exclusions.blocked_domains:
            return ExclusionResult(
                is_blocked=True,
                reason=f"DQ-008: Email domain '{domain}' is in blocked domains list",
                rule_id="DQ-008",
            )

    # DQ-009: Blocked email
    if email_lower in exclusions.blocked_emails:
        return ExclusionResult(
            is_blocked=True,
            reason=f"DQ-009: Email '{email_lower}' is in blocked emails list",
            rule_id="DQ-009",
        )

    return ExclusionResult(is_blocked=False)
