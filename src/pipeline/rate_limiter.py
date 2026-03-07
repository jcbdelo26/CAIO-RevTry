"""Daily Rate Limiter — file-backed per-channel dispatch counter.

RAMP (Phase 2 default): ≤5/day per channel
SUPERVISED (Phase 3): ≤25/day per channel
FULL_AUTONOMY (Phase 3): ≤100/day per channel

File state: registry/dispatch_counter_YYYY-MM-DD.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


# Autonomy level limits
RAMP_LIMIT = 5
SUPERVISED_LIMIT = 25
FULL_AUTONOMY_LIMIT = 100


def _counter_path(date_str: str | None = None) -> Path:
    registry = Path(os.environ.get("REGISTRY_DIR", "registry"))
    registry.mkdir(parents=True, exist_ok=True)
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return registry / f"dispatch_counter_{date_str}.json"


class DailyRateLimiter:
    """File-backed daily rate limiter per channel."""

    def __init__(
        self,
        daily_limit: int | None = None,
        state_path: Path | None = None,
    ):
        self._limit = daily_limit or int(os.environ.get("DISPATCH_DAILY_LIMIT", str(RAMP_LIMIT)))
        self._path = state_path or _counter_path()
        self._counters = self._load()

    def _load(self) -> dict[str, int]:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._counters, indent=2), encoding="utf-8")

    def can_send(self, channel: str) -> bool:
        """Check if the channel is under the daily limit."""
        return self._counters.get(channel, 0) < self._limit

    def record_send(self, channel: str) -> None:
        """Record a successful dispatch to a channel."""
        self._counters[channel] = self._counters.get(channel, 0) + 1
        self._save()

    def remaining(self, channel: str) -> int:
        """Return how many sends remain for this channel today."""
        return max(0, self._limit - self._counters.get(channel, 0))

    def get_counts(self) -> dict[str, int]:
        """Return current counts for all channels."""
        return dict(self._counters)

    @property
    def limit(self) -> int:
        return self._limit
