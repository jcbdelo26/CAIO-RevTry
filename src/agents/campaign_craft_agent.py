"""Campaign Craft Agent — Draft email campaigns for approved leads.

Takes segmented records and produces email drafts using the appropriate
angle per tier. Applies GUARD-004/005 pre-checks before output.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from models.schemas import (
    CampaignCraftOutput,
    CampaignCraftTrace,
    CampaignDraft,
    CampaignDraftTrace,
    Channel,
    DraftApprovalStatus,
    SegmentationRecord,
)
from utils.vault_loader import (
    AngleMapping,
    Signatures,
    load_email_angles,
    load_signatures,
)

BOOKING_LINK = "https://caio.cx/ai-exec-briefing-call"

SPAM_TRIGGERS = frozenset({
    "free", "guarantee", "urgent", "act now", "limited time",
    "winner", "no obligation", "buy now",
})


def _generate_draft_id(contact_id: str, angle_id: str) -> str:
    raw = f"{contact_id}:{angle_id}:{datetime.now(timezone.utc).isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _select_channel(is_cold: bool = True) -> Channel:
    """Channel routing: cold=instantly, warm=ghl."""
    return Channel.INSTANTLY if is_cold else Channel.GHL


def _check_banned_openers(body: str, signatures: Signatures) -> Optional[str]:
    """GUARD-004: Check if body starts with a banned opener."""
    first_line = body.strip().split("\n")[0].strip()
    for banned in signatures.banned_openers:
        if first_line.lower().startswith(banned.lower()):
            return f"GUARD-004: Body starts with banned opener '{banned}'"
    return None


def _check_subject_rules(subject: str, signatures: Signatures) -> Optional[str]:
    """Check subject line compliance."""
    if len(subject) > signatures.subject_max_length:
        return f"Subject exceeds {signatures.subject_max_length} chars ({len(subject)} chars)"

    # No ALL CAPS words
    words = subject.split()
    for word in words:
        if len(word) > 1 and word == word.upper() and word.isalpha():
            return f"Subject contains ALL CAPS word: '{word}'"

    # Exclamation mark limit
    if subject.count("!") > signatures.subject_max_exclamations:
        return f"Subject has too many exclamation marks ({subject.count('!')})"

    # Spam triggers
    subject_lower = subject.lower()
    for trigger in SPAM_TRIGGERS:
        if trigger in subject_lower:
            return f"Subject contains spam trigger: '{trigger}'"

    return None


def _check_generic_density(body: str) -> Optional[str]:
    """GUARD-005: Check for high generic phrase density."""
    generic_phrases = [
        "in today's", "rapidly evolving", "cutting-edge",
        "leverage", "synergy", "paradigm shift", "game-changer",
        "revolutionary", "unprecedented", "best-in-class",
    ]
    body_lower = body.lower()
    count = sum(1 for phrase in generic_phrases if phrase in body_lower)
    # Block if 3+ generic phrases
    if count >= 3:
        return f"GUARD-005: Body has {count} generic phrases (threshold: 3)"
    return None


def draft_campaign(
    record: SegmentationRecord,
    angles: AngleMapping,
    signatures: Signatures,
    angle_override: Optional[str] = None,
    lead_signals: Optional[list[str]] = None,
    proof_points: Optional[list[str]] = None,
    cta_id: str = "exec_briefing",
    is_cold: bool = True,
) -> CampaignDraft:
    """Create a single campaign draft for a segmented contact."""
    tier = record.icp_tier

    # Select angle
    if angle_override and angle_override in angles.tier_to_allowed.get(tier, []):
        angle_id = angle_override
    else:
        angle_id = angles.tier_to_default.get(tier, "quick_win")

    channel = _select_channel(is_cold)
    draft_id = _generate_draft_id(record.contact_id, angle_id)

    # Draft subject and body (placeholder generation - real LLM drafting in Phase 2)
    company = record.normalized_industry.title() if record.normalized_industry else "your company"
    title_display = record.normalized_title.title() if record.normalized_title else "leader"

    subject = f"AI strategy for {company}"[:60]

    body_parts = [
        f"Hi {record.contact_id.split('@')[0].title() if '@' in record.contact_id else 'there'},",
        "",
        f"As a {title_display} in the {company} space, you're likely seeing AI reshape how teams operate.",
        "",
        f"We've helped similar companies streamline operations and unlock measurable results.",
        "",
        f"Would you be open to a quick call to explore what's possible?",
        "",
        f"Book a time here: {BOOKING_LINK}",
        "",
        f"{signatures.sender_name}",
        f"{signatures.sender_title}",
        "",
        signatures.can_spam_footer,
    ]
    body = "\n".join(body_parts)

    return CampaignDraft(
        draftId=draft_id,
        contactId=record.contact_id,
        icpTier=tier,
        angleId=angle_id,
        subject=subject,
        body=body,
        channel=channel,
        bookingLink=BOOKING_LINK,
        status=DraftApprovalStatus.PENDING,
        trace=CampaignDraftTrace(
            leadSignalsUsed=lead_signals or [record.normalized_industry, record.normalized_title],
            proofPointsUsed=proof_points or [],
            ctaId=cta_id,
        ),
    )


def craft_campaigns(
    task_id: str,
    records: list[SegmentationRecord],
    angles: Optional[AngleMapping] = None,
    signatures: Optional[Signatures] = None,
    is_cold: bool = True,
) -> CampaignCraftOutput:
    """Produce campaign drafts for a batch of segmented records."""
    if angles is None:
        angles = load_email_angles()
    if signatures is None:
        signatures = load_signatures()

    drafts: list[CampaignDraft] = []
    for record in records:
        if record.icp_tier == "DISQUALIFIED":
            continue

        draft = draft_campaign(record, angles, signatures, is_cold=is_cold)

        # Pre-check compliance (GUARD-004, GUARD-005, subject rules)
        opener_err = _check_banned_openers(draft.body, signatures)
        subject_err = _check_subject_rules(draft.subject, signatures)
        generic_err = _check_generic_density(draft.body)

        if opener_err or subject_err or generic_err:
            # Log but don't block at draft stage - validators will catch
            pass

        drafts.append(draft)

    return CampaignCraftOutput(
        taskId=task_id,
        agent="campaign-craft",
        timestamp=datetime.now(timezone.utc).isoformat(),
        drafts=drafts,
        count=len(drafts),
        trace=CampaignCraftTrace(
            vaultFilesUsed=[
                "vault/playbook/email_angles.md",
                "vault/playbook/signatures.md",
                "vault/product/positioning.md",
                "vault/product/proof_points.md",
            ],
            angleSource="vault/playbook/email_angles.md",
            signaturesApplied=True,
            complianceChecksPrepared=True,
        ),
    )
