"""Feedback processor — handles pending rejections before new pipeline runs.

Checks registry/pending_feedback/ for unprocessed rejection files.
Moves processed files to registry/pending_feedback/processed/.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FeedbackSummary:
    total_pending: int
    processed: int
    contact_ids_blocked: list[str]


def process_pending_feedback(
    feedback_dir: Optional[str] = None,
) -> FeedbackSummary:
    """Process all pending feedback files. Returns summary."""
    if feedback_dir is None:
        feedback_dir = os.environ.get("REGISTRY_DIR", "registry")

    pending_path = Path(feedback_dir) / "pending_feedback"
    processed_path = pending_path / "processed"
    processed_path.mkdir(parents=True, exist_ok=True)

    blocked: list[str] = []
    processed_count = 0

    if not pending_path.exists():
        return FeedbackSummary(total_pending=0, processed=0, contact_ids_blocked=[])

    feedback_files = list(pending_path.glob("*.md"))

    for f in feedback_files:
        try:
            text = f.read_text(encoding="utf-8")

            # Extract contact ID from feedback file
            for line in text.splitlines():
                if "**Contact**:" in line:
                    contact_id = line.split("**Contact**:")[-1].strip()
                    if contact_id:
                        blocked.append(contact_id)
                    break

            # Move to processed
            dest = processed_path / f.name
            shutil.move(str(f), str(dest))
            processed_count += 1

        except Exception:
            continue

    return FeedbackSummary(
        total_pending=len(feedback_files),
        processed=processed_count,
        contact_ids_blocked=blocked,
    )
