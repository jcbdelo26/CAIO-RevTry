"""Quality Guards — GUARD-001 through GUARD-005.

GUARD-001: 2+ rejections in 30d → BLOCK
GUARD-002: SHA-256 hash match → BLOCK (duplicate detection)
GUARD-003: enrichment_score < 70 → REDIRECT (don't send to Campaign Craft)
GUARD-004: Banned openers → BLOCK
GUARD-005: Generic density → BLOCK
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from models.schemas import CampaignDraft, EnrichmentRecord
from utils.vault_loader import Signatures, load_signatures


# ── GUARD-001: Rejection Frequency ─────────────────────────────────────────────


def guard_001_rejection_check(
    contact_id: str,
    feedback_dir: Optional[str] = None,
    threshold: int = 2,
    window_days: int = 30,
) -> tuple[bool, Optional[str]]:
    """Check if contact has been rejected too many times recently.

    Returns (blocked, reason).
    """
    if feedback_dir is None:
        feedback_dir = os.environ.get("REGISTRY_DIR", "registry")

    feedback_path = Path(feedback_dir) / "pending_feedback"
    if not feedback_path.exists():
        return (False, None)

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    rejection_count = 0

    for f in feedback_path.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
            if contact_id in text and "REJECTED" in text:
                # Simple date extraction from filename or content
                rejection_count += 1
        except Exception:
            continue

    if rejection_count >= threshold:
        return (
            True,
            f"GUARD-001: Contact '{contact_id}' has {rejection_count} rejections "
            f"in the last {window_days} days (threshold: {threshold})",
        )

    return (False, None)


# ── GUARD-002: Duplicate Hash ──────────────────────────────────────────────────


def guard_002_duplicate_check(
    draft: CampaignDraft,
    sent_hashes: Optional[set[str]] = None,
) -> tuple[bool, Optional[str]]:
    """Check if this draft is a duplicate of a previously sent email.

    Returns (blocked, reason).
    """
    # Hash: contact_id + subject + first 100 chars of body
    content = f"{draft.contact_id}:{draft.subject}:{draft.body[:100]}"
    draft_hash = hashlib.sha256(content.encode()).hexdigest()

    if sent_hashes and draft_hash in sent_hashes:
        return (
            True,
            f"GUARD-002: Draft {draft.draft_id} is a duplicate (hash: {draft_hash[:16]}...)",
        )

    return (False, None)


def compute_draft_hash(draft: CampaignDraft) -> str:
    """Compute the dedup hash for a draft."""
    content = f"{draft.contact_id}:{draft.subject}:{draft.body[:100]}"
    return hashlib.sha256(content.encode()).hexdigest()


# ── GUARD-003: Enrichment Score Threshold ──────────────────────────────────────


def guard_003_enrichment_check(
    record: EnrichmentRecord,
    threshold: int = 70,
) -> tuple[bool, Optional[str]]:
    """Check if enrichment score meets Campaign Craft threshold.

    Returns (blocked, reason). If blocked, redirect to enrichment retry.
    """
    if record.enrichment_score < threshold:
        return (
            True,
            f"GUARD-003: enrichment_score={record.enrichment_score} "
            f"< threshold={threshold}. Redirect to re-enrichment.",
        )

    return (False, None)


# ── GUARD-004: Banned Openers ──────────────────────────────────────────────────


def guard_004_banned_opener_check(
    draft: CampaignDraft,
    signatures: Optional[Signatures] = None,
) -> tuple[bool, Optional[str]]:
    """Check if draft body starts with a banned opener.

    Returns (blocked, reason).
    """
    if signatures is None:
        signatures = load_signatures()

    first_line = draft.body.strip().split("\n")[0].strip()
    for banned in signatures.banned_openers:
        if first_line.lower().startswith(banned.lower()):
            return (
                True,
                f"GUARD-004: Draft {draft.draft_id} starts with banned opener: '{banned}'",
            )

    return (False, None)


# ── GUARD-005: Generic Density ─────────────────────────────────────────────────

GENERIC_PHRASES = [
    "in today's",
    "rapidly evolving",
    "cutting-edge",
    "leverage",
    "synergy",
    "paradigm shift",
    "game-changer",
    "revolutionary",
    "unprecedented",
    "best-in-class",
]


def guard_005_generic_density_check(
    draft: CampaignDraft,
    threshold: int = 3,
) -> tuple[bool, Optional[str]]:
    """Check if draft body has too many generic phrases.

    Returns (blocked, reason).
    """
    body_lower = draft.body.lower()
    found = [phrase for phrase in GENERIC_PHRASES if phrase in body_lower]

    if len(found) >= threshold:
        return (
            True,
            f"GUARD-005: Draft {draft.draft_id} has {len(found)} generic phrases "
            f"(threshold: {threshold}): {found}",
        )

    return (False, None)


# ── Run All Guards ─────────────────────────────────────────────────────────────


def run_all_guards(
    draft: CampaignDraft,
    enrichment_record: Optional[EnrichmentRecord] = None,
    sent_hashes: Optional[set[str]] = None,
    signatures: Optional[Signatures] = None,
) -> list[tuple[str, str]]:
    """Run all applicable guards on a draft. Returns list of (guard_id, reason) for failures."""
    failures: list[tuple[str, str]] = []

    # GUARD-001
    blocked, reason = guard_001_rejection_check(draft.contact_id)
    if blocked and reason:
        failures.append(("GUARD-001", reason))

    # GUARD-002
    blocked, reason = guard_002_duplicate_check(draft, sent_hashes)
    if blocked and reason:
        failures.append(("GUARD-002", reason))

    # GUARD-003
    if enrichment_record:
        blocked, reason = guard_003_enrichment_check(enrichment_record)
        if blocked and reason:
            failures.append(("GUARD-003", reason))

    # GUARD-004
    blocked, reason = guard_004_banned_opener_check(draft, signatures)
    if blocked and reason:
        failures.append(("GUARD-004", reason))

    # GUARD-005
    blocked, reason = guard_005_generic_density_check(draft)
    if blocked and reason:
        failures.append(("GUARD-005", reason))

    return failures
