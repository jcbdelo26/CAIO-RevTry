"""KPI Tracker — monitors dispatch metrics and triggers EMERGENCY_STOP.

EMERGENCY_STOP thresholds:
- Open rate < 30%
- 0 replies after 15 sends
- Bounce rate > 10%
- Unsubscribe rate > 5%

When any threshold is breached → trip all circuit breakers, log escalation.
File state: outputs/kpi/kpi_YYYY-MM-DD.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models.schemas import DraftApprovalStatus
from persistence.base import StorageBackend
from pipeline.circuit_breaker import CircuitBreaker


@dataclass
class KPISnapshot:
    date: str
    sent_count: int = 0
    open_count: int = 0
    reply_count: int = 0
    bounce_count: int = 0
    unsub_count: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    bounce_rate: float = 0.0
    unsub_rate: float = 0.0
    emergency_stop: bool = False
    violations: list[str] = field(default_factory=list)
    # Draft-lifecycle metrics (derived from storage)
    drafts_generated: int = 0
    drafts_edited: int = 0
    drafts_approved: int = 0
    drafts_dispatched: int = 0
    drafts_rejected: int = 0
    approval_rate: float = 0.0


# Thresholds
MIN_OPEN_RATE = 0.30
MAX_BOUNCE_RATE = 0.10
MAX_UNSUB_RATE = 0.05
MIN_REPLIES_AFTER_N_SENDS = (15, 1)  # At least 1 reply after 15 sends


def _kpi_dir(create: bool = False) -> Path:
    outputs = Path(os.environ.get("OUTPUTS_DIR", "outputs"))
    d = outputs / "kpi"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _kpi_path(date_str: str | None = None, create_dir: bool = False) -> Path:
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _kpi_dir(create=create_dir) / f"kpi_{date_str}.json"


def _escalation_path() -> Path:
    registry = Path(os.environ.get("REGISTRY_DIR", "registry"))
    registry.mkdir(parents=True, exist_ok=True)
    return registry / "escalations.md"


class KPITracker:
    """Tracks dispatch KPIs and triggers emergency stop when thresholds are breached."""

    def __init__(
        self,
        circuit_breaker: CircuitBreaker | None = None,
        storage: Optional[StorageBackend] = None,
    ):
        self.cb = circuit_breaker or CircuitBreaker()
        self.storage = storage

    def record_metrics(
        self,
        sent: int = 0,
        opens: int = 0,
        replies: int = 0,
        bounces: int = 0,
        unsubs: int = 0,
        date_str: str | None = None,
    ) -> KPISnapshot:
        """Record KPI metrics and check for threshold violations."""
        date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Load existing or start fresh
        path = _kpi_path(date, create_dir=True)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            snapshot = KPISnapshot(
                date=date,
                sent_count=data.get("sent_count", 0) + sent,
                open_count=data.get("open_count", 0) + opens,
                reply_count=data.get("reply_count", 0) + replies,
                bounce_count=data.get("bounce_count", 0) + bounces,
                unsub_count=data.get("unsub_count", 0) + unsubs,
            )
        else:
            snapshot = KPISnapshot(
                date=date,
                sent_count=sent,
                open_count=opens,
                reply_count=replies,
                bounce_count=bounces,
                unsub_count=unsubs,
            )

        # Calculate rates
        if snapshot.sent_count > 0:
            snapshot.open_rate = snapshot.open_count / snapshot.sent_count
            snapshot.reply_rate = snapshot.reply_count / snapshot.sent_count
            snapshot.bounce_rate = snapshot.bounce_count / snapshot.sent_count
            snapshot.unsub_rate = snapshot.unsub_count / snapshot.sent_count

        # Draft metrics reflect ALL drafts in storage (current-state snapshot, not today-only)
        self._populate_draft_metrics(snapshot)

        # Check thresholds (only meaningful after enough sends)
        violations: list[str] = []

        if snapshot.sent_count >= 10 and snapshot.open_rate < MIN_OPEN_RATE:
            violations.append(f"Open rate {snapshot.open_rate:.1%} < {MIN_OPEN_RATE:.0%} threshold")

        sends_threshold, min_replies = MIN_REPLIES_AFTER_N_SENDS
        if snapshot.sent_count >= sends_threshold and snapshot.reply_count < min_replies:
            violations.append(f"0 replies after {snapshot.sent_count} sends (threshold: {min_replies} after {sends_threshold})")

        if snapshot.sent_count >= 10 and snapshot.bounce_rate > MAX_BOUNCE_RATE:
            violations.append(f"Bounce rate {snapshot.bounce_rate:.1%} > {MAX_BOUNCE_RATE:.0%} threshold")

        if snapshot.sent_count >= 10 and snapshot.unsub_rate > MAX_UNSUB_RATE:
            violations.append(f"Unsub rate {snapshot.unsub_rate:.1%} > {MAX_UNSUB_RATE:.0%} threshold")

        snapshot.violations = violations
        snapshot.emergency_stop = len(violations) > 0

        # Save KPI snapshot
        kpi_data = {
            "date": snapshot.date,
            "sent_count": snapshot.sent_count,
            "open_count": snapshot.open_count,
            "reply_count": snapshot.reply_count,
            "bounce_count": snapshot.bounce_count,
            "unsub_count": snapshot.unsub_count,
            "open_rate": round(snapshot.open_rate, 4),
            "reply_rate": round(snapshot.reply_rate, 4),
            "bounce_rate": round(snapshot.bounce_rate, 4),
            "unsub_rate": round(snapshot.unsub_rate, 4),
            "emergency_stop": snapshot.emergency_stop,
            "violations": snapshot.violations,
            "drafts_generated": snapshot.drafts_generated,
            "drafts_edited": snapshot.drafts_edited,
            "drafts_approved": snapshot.drafts_approved,
            "drafts_dispatched": snapshot.drafts_dispatched,
            "drafts_rejected": snapshot.drafts_rejected,
            "approval_rate": snapshot.approval_rate,
        }
        path.write_text(json.dumps(kpi_data, indent=2), encoding="utf-8")

        # Trigger EMERGENCY_STOP
        if snapshot.emergency_stop:
            self._trigger_emergency_stop(snapshot)

        return snapshot

    def _populate_draft_metrics(self, snapshot: KPISnapshot) -> None:
        """Populate draft-lifecycle metrics on snapshot from storage. No-op if no storage."""
        if self.storage is None:
            return
        drafts = self.storage.list_followup_drafts()
        approved_statuses = {DraftApprovalStatus.APPROVED, DraftApprovalStatus.DISPATCHED}
        generated = len(drafts)
        edited = sum(1 for d in drafts if d.edit_diff is not None)
        approved = sum(1 for d in drafts if d.status in approved_statuses)
        dispatched = sum(1 for d in drafts if d.status == DraftApprovalStatus.DISPATCHED)
        rejected = sum(1 for d in drafts if d.status == DraftApprovalStatus.REJECTED)
        denominator = approved + rejected
        approval_rate = approved / denominator if denominator > 0 else 0.0
        snapshot.drafts_generated = generated
        snapshot.drafts_edited = edited
        snapshot.drafts_approved = approved
        snapshot.drafts_dispatched = dispatched
        snapshot.drafts_rejected = rejected
        snapshot.approval_rate = approval_rate

    def _trigger_emergency_stop(self, snapshot: KPISnapshot) -> None:
        """Trip all circuit breakers and log escalation."""
        self.cb.trip_all()

        # Log to escalations
        path = _escalation_path()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [f"\n## EMERGENCY STOP — {now}\n"]
        lines.append(f"- Sent: {snapshot.sent_count}")
        lines.append(f"- Opens: {snapshot.open_count} ({snapshot.open_rate:.1%})")
        lines.append(f"- Replies: {snapshot.reply_count} ({snapshot.reply_rate:.1%})")
        lines.append(f"- Bounces: {snapshot.bounce_count} ({snapshot.bounce_rate:.1%})")
        lines.append(f"- Unsubs: {snapshot.unsub_count} ({snapshot.unsub_rate:.1%})")
        lines.append("")
        lines.append("**Violations:**")
        for v in snapshot.violations:
            lines.append(f"- {v}")
        lines.append("")
        lines.append("**Action**: All circuit breakers tripped. Manual intervention required.")
        lines.append("")

        content = "\n".join(lines)
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            content = existing + content
        else:
            content = "# Escalation Log\n" + content

        path.write_text(content, encoding="utf-8")

    def get_latest_kpi(self, date_str: str | None = None) -> Optional[KPISnapshot]:
        """Load the latest KPI snapshot."""
        date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = _kpi_path(date, create_dir=False)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return KPISnapshot(
            date=data["date"],
            sent_count=data["sent_count"],
            open_count=data["open_count"],
            reply_count=data["reply_count"],
            bounce_count=data["bounce_count"],
            unsub_count=data["unsub_count"],
            open_rate=data["open_rate"],
            reply_rate=data["reply_rate"],
            bounce_rate=data["bounce_rate"],
            unsub_rate=data["unsub_rate"],
            emergency_stop=data["emergency_stop"],
            violations=data.get("violations", []),
            drafts_generated=data.get("drafts_generated", 0),
            drafts_edited=data.get("drafts_edited", 0),
            drafts_approved=data.get("drafts_approved", 0),
            drafts_dispatched=data.get("drafts_dispatched", 0),
            drafts_rejected=data.get("drafts_rejected", 0),
            approval_rate=data.get("approval_rate", 0.0),
        )
