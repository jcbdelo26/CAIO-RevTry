"""3-Layer Dedup — prevents duplicate outreach before dispatch.

Layer 1: Hash dedup — draft content hash against sent_hashes.json
Layer 2: Contact+channel window — no same contact on same channel within 30 days
Layer 3: GHL tag check — if contact has 'revtry-sent-{channel}' tag, skip
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


WINDOW_DAYS = 30


def _registry_path(filename: str) -> Path:
    registry = Path(os.environ.get("REGISTRY_DIR", "registry"))
    registry.mkdir(parents=True, exist_ok=True)
    return registry / filename


def compute_draft_hash(contact_id: str, subject: str, body: str, channel: str) -> str:
    """Compute a content hash for a draft to detect exact duplicates."""
    content = f"{contact_id}|{subject}|{body}|{channel}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _load_json(path: Path) -> dict | list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Layer 1: Hash Dedup ──────────────────────────────────────────────────────


def check_hash_dedup(draft_hash: str) -> tuple[bool, Optional[str]]:
    """Check if this exact draft has been sent before.

    Returns: (is_duplicate, reason)
    """
    path = _registry_path("sent_hashes.json")
    hashes = _load_json(path)
    if isinstance(hashes, dict) and draft_hash in hashes:
        return True, f"Duplicate hash: {draft_hash} (sent {hashes[draft_hash]})"
    return False, None


def record_hash(draft_hash: str) -> None:
    """Record a draft hash after successful dispatch."""
    path = _registry_path("sent_hashes.json")
    hashes = _load_json(path)
    if not isinstance(hashes, dict):
        hashes = {}
    hashes[draft_hash] = datetime.now(timezone.utc).isoformat()
    _save_json(path, hashes)


# ── Layer 2: Contact+Channel Window ──────────────────────────────────────────


def check_contact_window(contact_id: str, channel: str) -> tuple[bool, Optional[str]]:
    """Check if this contact was sent to on this channel within the dedup window.

    Returns: (is_duplicate, reason)
    """
    path = _registry_path("dispatch_log.json")
    log = _load_json(path)
    if not isinstance(log, list):
        return False, None

    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)

    for entry in log:
        if entry.get("contact_id") == contact_id and entry.get("channel") == channel:
            sent_at = datetime.fromisoformat(entry["sent_at"])
            if sent_at > cutoff:
                return True, f"Contact {contact_id} sent via {channel} on {entry['sent_at']} (within {WINDOW_DAYS}d window)"

    return False, None


def record_dispatch(contact_id: str, channel: str, draft_id: str) -> None:
    """Record a successful dispatch to the log."""
    path = _registry_path("dispatch_log.json")
    log = _load_json(path)
    if not isinstance(log, list):
        log = []
    log.append({
        "contact_id": contact_id,
        "channel": channel,
        "draft_id": draft_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_json(path, log)


# ── Layer 3: GHL Tag Check ───────────────────────────────────────────────────


async def check_ghl_tag(contact_id: str, channel: str, ghl=None) -> tuple[bool, Optional[str]]:
    """Check if the GHL contact has a 'revtry-sent-{channel}' tag.

    Returns: (is_duplicate, reason)
    Falls back to not-duplicate if GHL client is unavailable.
    """
    if not ghl:
        return False, None

    tag = f"revtry-sent-{channel}"
    try:
        contact = await ghl.get_contact(contact_id)
        tags = contact.get("tags", []) if contact else []
        if tag in tags:
            return True, f"Contact {contact_id} has GHL tag '{tag}'"
    except Exception:
        pass  # GHL unavailable — don't block dispatch

    return False, None


# ── Combined Check ────────────────────────────────────────────────────────────


async def check_dedup(
    contact_id: str,
    channel: str,
    subject: str,
    body: str,
    draft_id: str = "",
    ghl=None,
) -> tuple[bool, Optional[str]]:
    """Run all 3 dedup layers. Returns (is_duplicate, reason)."""
    # Layer 1: Hash
    draft_hash = compute_draft_hash(contact_id, subject, body, channel)
    is_dup, reason = check_hash_dedup(draft_hash)
    if is_dup:
        return True, reason

    # Layer 2: Contact+channel window
    is_dup, reason = check_contact_window(contact_id, channel)
    if is_dup:
        return True, reason

    # Layer 3: GHL tag
    is_dup, reason = await check_ghl_tag(contact_id, channel, ghl)
    if is_dup:
        return True, reason

    return False, None
