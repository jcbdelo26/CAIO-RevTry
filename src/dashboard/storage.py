"""File-based draft storage for the approval dashboard.

Drafts stored as: outputs/drafts/{draft_id}.json
Index file: outputs/drafts/index.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models.schemas import CampaignDraft, DraftApprovalStatus, StoredDraft


def _drafts_dir() -> Path:
    outputs = Path(os.environ.get("OUTPUTS_DIR", "outputs"))
    d = outputs / "drafts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _index_path() -> Path:
    return _drafts_dir() / "index.json"


def _load_index() -> dict[str, str]:
    """Load the draft index: {draft_id: file_path}."""
    path = _index_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_index(index: dict[str, str]) -> None:
    _index_path().write_text(
        json.dumps(index, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def save_draft(draft: CampaignDraft) -> StoredDraft:
    """Save a campaign draft to file storage."""
    now = datetime.now(timezone.utc).isoformat()
    stored = StoredDraft(
        draftId=draft.draft_id,
        contactId=draft.contact_id,
        icpTier=draft.icp_tier,
        angleId=draft.angle_id,
        subject=draft.subject,
        body=draft.body,
        channel=draft.channel,
        bookingLink=draft.booking_link,
        status=DraftApprovalStatus.PENDING,
        createdAt=now,
    )

    # Write draft file
    draft_path = _drafts_dir() / f"{draft.draft_id}.json"
    draft_path.write_text(
        json.dumps(stored.model_dump(by_alias=True), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Update index
    index = _load_index()
    index[draft.draft_id] = str(draft_path)
    _save_index(index)

    return stored


def get_draft(draft_id: str) -> Optional[StoredDraft]:
    """Load a single draft by ID."""
    draft_path = _drafts_dir() / f"{draft_id}.json"
    if not draft_path.exists():
        return None
    data = json.loads(draft_path.read_text(encoding="utf-8"))
    return StoredDraft.model_validate(data)


def list_drafts() -> list[StoredDraft]:
    """List all drafts, PENDING first."""
    index = _load_index()
    drafts: list[StoredDraft] = []
    for draft_id in index:
        draft = get_draft(draft_id)
        if draft:
            drafts.append(draft)

    # Sort: PENDING first, then by creation time desc
    status_order = {DraftApprovalStatus.PENDING: 0, DraftApprovalStatus.APPROVED: 1, DraftApprovalStatus.REJECTED: 2}
    drafts.sort(key=lambda d: (status_order.get(d.status, 9), d.created_at), reverse=False)
    return drafts


def approve_draft(draft_id: str) -> Optional[StoredDraft]:
    """Mark a draft as APPROVED."""
    draft = get_draft(draft_id)
    if not draft:
        return None

    draft.status = DraftApprovalStatus.APPROVED
    draft.approved_at = datetime.now(timezone.utc).isoformat()

    draft_path = _drafts_dir() / f"{draft_id}.json"
    draft_path.write_text(
        json.dumps(draft.model_dump(by_alias=True), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return draft


def reject_draft(
    draft_id: str,
    reason: str = "",
    feedback_dir: Optional[str] = None,
) -> Optional[StoredDraft]:
    """Mark a draft as REJECTED and create feedback file."""
    draft = get_draft(draft_id)
    if not draft:
        return None

    draft.status = DraftApprovalStatus.REJECTED
    draft.rejected_at = datetime.now(timezone.utc).isoformat()
    draft.rejection_reason = reason

    draft_path = _drafts_dir() / f"{draft_id}.json"
    draft_path.write_text(
        json.dumps(draft.model_dump(by_alias=True), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write feedback file
    if feedback_dir is None:
        feedback_dir = os.environ.get("REGISTRY_DIR", "registry")
    feedback_path = Path(feedback_dir) / "pending_feedback" / f"{draft_id}.md"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(
        f"# Rejection Feedback: {draft_id}\n\n"
        f"- **Contact**: {draft.contact_id}\n"
        f"- **Status**: REJECTED\n"
        f"- **Rejected At**: {draft.rejected_at}\n"
        f"- **Reason**: {reason}\n"
        f"- **Subject**: {draft.subject}\n"
        f"- **Angle**: {draft.angle_id}\n"
        f"- **Tier**: {draft.icp_tier}\n",
        encoding="utf-8",
    )

    return draft


def update_draft_ghl_result(draft_id: str, result: dict) -> Optional[StoredDraft]:
    """Store the GHL push result on an existing draft."""
    draft = get_draft(draft_id)
    if not draft:
        return None

    draft.ghl_push_result = result

    draft_path = _drafts_dir() / f"{draft_id}.json"
    draft_path.write_text(
        json.dumps(draft.model_dump(by_alias=True), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return draft
